"""Autenticação: hash de senha (pbkdf2-sha256, stdlib) e sessões por token.

Sem dependências novas: hashlib + secrets. O token é opaco (não JWT) e vive
na tabela SessaoAcesso com expiração deslizante — logout revoga na hora.
"""
import hashlib
import os
import hmac
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from ..models import SessaoAcesso, Usuario

# 600k é a recomendação da OWASP para PBKDF2-HMAC-SHA256. Hashes antigos
# continuam válidos: o número de iterações vai gravado no próprio hash.
#
# A suíte de testes baixa este número por variável de ambiente — não para
# afrouxar produção, mas porque cada teste que faz login pagava 600k iterações
# e a suíte inteira triplicou de 77s para 199s. O que se testa é o fluxo, não
# a dureza do hash.
ITERACOES = int(os.environ.get("RUNRATE_PBKDF2_ITER") or 600_000)
VALIDADE_SESSAO = timedelta(hours=12)
# Teto ABSOLUTO. Sem ele a expiração deslizante nunca vence: quem usar o sistema
# a cada 11h mantém a mesma sessão para sempre, e um token roubado idem.
VIDA_MAXIMA_SESSAO = timedelta(days=7)
# Barreira de força bruta: N falhas na janela e o e-mail espera.
MAX_FALHAS = 5
JANELA_FALHAS = timedelta(minutes=15)


# Formato antigo: "salt$hash", sem registrar com quantas voltas foi derivado.
# Enquanto o número era constante no código isso funcionava — até o dia em que
# ele mudou. Todo hash novo grava o próprio custo; os antigos são lidos com o
# valor que valia quando foram criados.
ITERACOES_LEGADO = 200_000
MARCA = "pbkdf2_sha256"


def _derivar(senha: str, salt: str, iteracoes: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), iteracoes).hex()


def _partes(senha_hash: str) -> tuple[str, str, int] | None:
    """(salt, hash, iterações) — ou None se o registro não for reconhecível."""
    p = senha_hash.split("$")
    if len(p) == 4 and p[0] == MARCA:
        try:
            return p[2], p[3], int(p[1])
        except ValueError:
            return None
    if len(p) == 2:
        return p[0], p[1], ITERACOES_LEGADO
    return None


def gerar_hash(senha: str) -> str:
    salt = secrets.token_hex(16)
    return f"{MARCA}${ITERACOES}${salt}${_derivar(senha, salt, ITERACOES)}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    partes = _partes(senha_hash)
    if not partes:
        return False
    salt, esperado, iteracoes = partes
    return hmac.compare_digest(_derivar(senha, salt, iteracoes), esperado)


def precisa_reforcar(senha_hash: str) -> bool:
    """Hash gravado com menos voltas do que a política atual exige."""
    partes = _partes(senha_hash)
    return bool(partes) and partes[2] < ITERACOES


# hash descartável só para gastar o mesmo tempo quando o e-mail não existe
_HASH_FALSO = None


def autenticar(session: Session, email: str, senha: str) -> Usuario | None:
    global _HASH_FALSO
    if _HASH_FALSO is None:
        _HASH_FALSO = gerar_hash("comparacao-em-tempo-constante")
    usuario = session.exec(
        select(Usuario).where(Usuario.email == email.strip().lower())
    ).first()
    # Verifica a senha SEMPRE, mesmo sem usuário: o curto-circuito fazia
    # e-mail inexistente responder ~40x mais rápido que senha errada, e essa
    # diferença de tempo revelava quem tem conta — a mensagem era igual, mas o
    # relógio entregava.
    hash_alvo = usuario.senha_hash if usuario else _HASH_FALSO
    senha_confere = verificar_senha(senha, hash_alvo)
    if not usuario or not usuario.ativo or not senha_confere:
        return None
    if precisa_reforcar(usuario.senha_hash):
        # A senha está certa, mas guardada com menos voltas do que a política de
        # hoje exige. Regrava com o custo atual sem pedir nada: é o único momento
        # em que a senha em claro passa por aqui, e ninguém precisa ser avisado.
        usuario.senha_hash = gerar_hash(senha)
        session.add(usuario)
        session.commit()
        session.refresh(usuario)
    return usuario


def criar_sessao(session: Session, usuario: Usuario) -> SessaoAcesso:
    agora = datetime.now()
    s = SessaoAcesso(
        token=secrets.token_urlsafe(32),
        usuario_id=usuario.id,
        criada_em=agora,
        expira_em=agora + VALIDADE_SESSAO,
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def resolver_token(session: Session, token: str) -> Usuario | None:
    """Valida o token e renova a expiração (sessão deslizante)."""
    if not token:
        return None
    s = session.exec(select(SessaoAcesso).where(SessaoAcesso.token == token)).first()
    if not s:
        return None
    agora = datetime.now()
    if s.expira_em < agora or (agora - s.criada_em) > VIDA_MAXIMA_SESSAO:
        session.delete(s)
        session.commit()
        return None
    usuario = s.usuario
    if not usuario or not usuario.ativo:
        return None
    s.expira_em = agora + VALIDADE_SESSAO
    session.add(s)
    session.commit()
    return usuario


def revogar_token(session: Session, token: str) -> None:
    s = session.exec(select(SessaoAcesso).where(SessaoAcesso.token == token)).first()
    if s:
        session.delete(s)
        session.commit()


def revogar_sessoes_do_usuario(session: Session, usuario_id: int, manter_token: str | None = None) -> int:
    """Derruba as sessões do usuário, opcionalmente poupando a atual.

    É o que faz a troca de senha valer alguma coisa: sem isto, trocar a senha —
    o gesto que se faz justamente ao suspeitar de invasão — não expulsa quem já
    tem um token roubado na mão.
    """
    sessoes = session.exec(select(SessaoAcesso).where(SessaoAcesso.usuario_id == usuario_id)).all()
    n = 0
    for s in sessoes:
        if manter_token and s.token == manter_token:
            continue
        session.delete(s)
        n += 1
    session.commit()
    return n


def registrar_falha(session: Session, email: str) -> None:
    from ..models import TentativaLogin

    session.add(TentativaLogin(email=email.strip().lower(), quando=datetime.now()))
    session.commit()


def limpar_falhas(session: Session, email: str) -> None:
    from ..models import TentativaLogin

    for t in session.exec(select(TentativaLogin).where(TentativaLogin.email == email.strip().lower())).all():
        session.delete(t)
    session.commit()


def bloqueado_por_forca_bruta(session: Session, email: str) -> bool:
    """True quando o e-mail já falhou demais na janela recente."""
    from ..models import TentativaLogin

    corte = datetime.now() - JANELA_FALHAS
    recentes = session.exec(
        select(TentativaLogin).where(
            TentativaLogin.email == email.strip().lower(),
            TentativaLogin.quando >= corte,
        )
    ).all()
    return len(recentes) >= MAX_FALHAS
