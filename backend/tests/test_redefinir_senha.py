"""A saída de emergência: redefinir senha pela linha de comando.

O CEO é a única conta que ninguém pode socorrer de dentro do produto — não há
autoatendimento e não há outro gestor. Se este comando quebrar, o jeito de
destrancar o sistema desaparece junto, então ele é testado como qualquer rota.
"""
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

import app.database as db
from app.models import PerfilUsuario, SessaoAcesso, Usuario
from app.redefinir_senha import main, redefinir
from app.services.auth import autenticar, criar_sessao, gerar_hash


@pytest.fixture()
def engine(monkeypatch):
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(eng)
    monkeypatch.setattr(db, "engine", eng)
    with Session(eng) as s:
        s.add(Usuario(
            email="chefe@t.com", nome="Chefe", perfil=PerfilUsuario.ceo,
            senha_hash=gerar_hash("senhaAntiga1"),
        ))
        s.commit()
    return eng


def test_troca_a_senha_e_a_antiga_para_de_valer(engine):
    assert redefinir("chefe@t.com", "senhaNova9") == "Chefe"
    with Session(engine) as s:
        assert autenticar(s, "chefe@t.com", "senhaNova9") is not None
        assert autenticar(s, "chefe@t.com", "senhaAntiga1") is None


def test_email_e_normalizado(engine):
    """Quem digita o próprio e-mail no terminal digita como lembra."""
    assert redefinir("  CHEFE@T.COM  ", "senhaNova9") == "Chefe"


def test_derruba_as_sessoes_abertas(engine):
    """Perder a senha e ter sido invadido se parecem muito — na dúvida, derruba."""
    with Session(engine) as s:
        usuario = s.exec(select(Usuario)).one()
        criar_sessao(s, usuario)
        criar_sessao(s, usuario)
        assert len(s.exec(select(SessaoAcesso)).all()) == 2

    redefinir("chefe@t.com", "senhaNova9")

    with Session(engine) as s:
        assert s.exec(select(SessaoAcesso)).all() == []


def test_reativa_conta_desativada(engine):
    """Desativar a própria conta é o outro jeito de se trancar para fora."""
    with Session(engine) as s:
        usuario = s.exec(select(Usuario)).one()
        usuario.ativo = False
        s.add(usuario)
        s.commit()

    redefinir("chefe@t.com", "senhaNova9")

    with Session(engine) as s:
        assert s.exec(select(Usuario)).one().ativo is True


def test_recusa_senha_curta_sem_gravar_nada(engine):
    with pytest.raises(SystemExit):
        redefinir("chefe@t.com", "abc")
    with Session(engine) as s:
        assert autenticar(s, "chefe@t.com", "senhaAntiga1") is not None


def test_recusa_email_inexistente(engine):
    with pytest.raises(SystemExit):
        redefinir("ninguem@t.com", "senhaNova9")


def test_sem_argumento_explica_o_uso(engine):
    with pytest.raises(SystemExit) as e:
        main([])
    assert "redefinir_senha" in str(e.value)


def test_senha_pela_linha_de_comando(engine):
    main(["chefe@t.com", "senhaNova9"])
    with Session(engine) as s:
        assert autenticar(s, "chefe@t.com", "senhaNova9") is not None
