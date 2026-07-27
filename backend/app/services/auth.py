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
    if s.expira_em < agora:
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
