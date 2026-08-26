"""O hash tem de sobreviver a uma mudança de política de custo.

O formato antigo era `salt$hash` — não registrava com quantas iterações foi
derivado. Enquanto o número era uma constante no código isso funcionava; no dia
em que ele subiu de 200k para 600k, TODA senha já gravada deixou de conferir.
Inclusive a do CEO em produção, que é justamente a conta que ninguém socorre.
"""
import hashlib
import secrets

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.models import PerfilUsuario, Usuario
from app.services import auth
from app.services.auth import (
    ITERACOES_LEGADO,
    autenticar,
    gerar_hash,
    precisa_reforcar,
    verificar_senha,
)


def hash_no_formato_antigo(senha: str, iteracoes: int = ITERACOES_LEGADO) -> str:
    """Reproduz exatamente o que estava gravado antes desta mudança."""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), iteracoes)
    return f"{salt}${h.hex()}"


@pytest.fixture()
def engine(monkeypatch):
    import app.database as db

    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(eng)
    monkeypatch.setattr(db, "engine", eng)
    return eng


# ============ compatibilidade com o que já está gravado ============

def test_senha_do_formato_antigo_continua_valendo():
    antigo = hash_no_formato_antigo("senhaDoMichel")
    assert verificar_senha("senhaDoMichel", antigo) is True
    assert verificar_senha("outraCoisa", antigo) is False


def test_hash_novo_grava_o_proprio_custo():
    novo = gerar_hash("qualquer1")
    marca, iteracoes, salt, digest = novo.split("$")
    assert marca == "pbkdf2_sha256"
    assert int(iteracoes) == auth.ITERACOES
    assert len(salt) == 32
    assert len(digest) == 64
    assert verificar_senha("qualquer1", novo) is True


def test_hash_gravado_com_outro_custo_ainda_confere(monkeypatch):
    """É o teste que faltava: mudar a política não pode trancar ninguém."""
    monkeypatch.setattr(auth, "ITERACOES", 1200)
    gravado = gerar_hash("senhaDoMichel")

    monkeypatch.setattr(auth, "ITERACOES", 3400)  # a política subiu
    assert verificar_senha("senhaDoMichel", gravado) is True


def test_hash_ilegivel_nao_explode():
    for lixo in ("", "sem-cifrao", "pbkdf2_sha256$abc$s$h", "a$b$c$d$e"):
        assert verificar_senha("x", lixo) is False


# ============ reforço silencioso ============

def test_precisa_reforcar_so_para_hash_mais_fraco(monkeypatch):
    monkeypatch.setattr(auth, "ITERACOES", 500_000)
    assert precisa_reforcar(hash_no_formato_antigo("x")) is True

    monkeypatch.setattr(auth, "ITERACOES", 1000)
    assert precisa_reforcar(gerar_hash("x")) is False


def test_login_regrava_o_hash_antigo_sem_avisar(engine, monkeypatch):
    """Quem entra com a senha certa sai com o hash no padrão atual."""
    monkeypatch.setattr(auth, "ITERACOES", 600_000)  # a política nova
    antigo = hash_no_formato_antigo("senhaDoMichel")  # 200k, como está gravado hoje
    with Session(engine) as s:
        s.add(Usuario(
            email="michel@t.com", nome="Michel", perfil=PerfilUsuario.ceo,
            senha_hash=antigo,
        ))
        s.commit()

    with Session(engine) as s:
        assert autenticar(s, "michel@t.com", "senhaDoMichel") is not None

    with Session(engine) as s:
        atual = s.exec(select(Usuario)).one().senha_hash
    assert atual != antigo
    assert atual.startswith("pbkdf2_sha256$600000$")
    # e a senha continua a mesma para quem digita
    assert verificar_senha("senhaDoMichel", atual) is True


def test_senha_errada_nao_regrava_nada(engine, monkeypatch):
    monkeypatch.setattr(auth, "ITERACOES", 600_000)  # a política nova
    antigo = hash_no_formato_antigo("senhaDoMichel")  # 200k, como está gravado hoje
    with Session(engine) as s:
        s.add(Usuario(
            email="michel@t.com", nome="Michel", perfil=PerfilUsuario.ceo,
            senha_hash=antigo,
        ))
        s.commit()

    with Session(engine) as s:
        assert autenticar(s, "michel@t.com", "chutando") is None

    with Session(engine) as s:
        assert s.exec(select(Usuario)).one().senha_hash == antigo
