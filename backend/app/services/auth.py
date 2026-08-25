"""Autenticação: hash de senha (pbkdf2-sha256, stdlib) e sessões por token.

Sem dependências novas: hashlib + secrets. O token é opaco (não JWT) e vive
na tabela SessaoAcesso com expiração deslizante — logout revoga na hora.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from ..models import SessaoAcesso, Usuario

ITERACOES = 200_000
VALIDADE_SESSAO = timedelta(hours=12)
# Teto ABSOLUTO. Sem ele a expiração deslizante nunca vence: quem usar o sistema
# a cada 11h mantém a mesma sessão para sempre, e um token roubado idem.
VIDA_MAXIMA_SESSAO = timedelta(days=7)
# Barreira de força bruta: N falhas na janela e o e-mail espera.
MAX_FALHAS = 5
JANELA_FALHAS = timedelta(minutes=15)


def gerar_hash(senha: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), ITERACOES)
    return f"{salt}${h.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        salt, esperado = senha_hash.split("$", 1)
    except ValueError:
        return False
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), ITERACOES)
    return hmac.compare_digest(h.hex(), esperado)


def autenticar(session: Session, email: str, senha: str) -> Usuario | None:
    usuario = session.exec(
        select(Usuario).where(Usuario.email == email.strip().lower())
    ).first()
    if not usuario or not usuario.ativo or not verificar_senha(senha, usuario.senha_hash):
        return None
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
