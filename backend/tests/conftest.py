import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATABASE_URL"] = "sqlite://"  # em memória, isolado por engine
# Hash barato SÓ nos testes. Produção usa as 600k da recomendação OWASP; aqui o
# que interessa é o fluxo de login, não o custo do hash — com 600k a suíte
# levava 199s contra 77s.
os.environ.setdefault("RUNRATE_PBKDF2_ITER", "1000")

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.models import Cliente, Consultor, Projeto, Senioridade
from app.services.projetos import criar_projeto_com_fases


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def cliente(session):
    c = Cliente(nome="Cliente Teste", contato="teste@cliente.com")
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@pytest.fixture()
def consultor_senior(session):
    c = Consultor(
        nome="Consultora Sênior",
        senioridade=Senioridade.senior,
        taxa_hora_custo=100.0,
        taxa_hora_venda=200.0,
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@pytest.fixture()
def projeto(session, cliente):
    from datetime import date

    # segunda-feira, para datas de fase previsíveis nos testes
    return criar_projeto_com_fases(
        session,
        Projeto(nome="Projeto Teste", cliente_id=cliente.id, data_inicio=date(2026, 1, 5)),
    )

class _EstadoFalso:
    def __init__(self, usuario):
        self.usuario = usuario


class RequisicaoFalsa:
    """Stub de Request para os testes que chamam routers como função pura.

    O middleware de autenticação não roda aí, então é aqui que se diz quem está
    pedindo. O padrão é o CEO — quem quiser exercitar as guardas de isolamento
    passa perfil='consultor' e o consultor_id.
    """

    def __init__(self, perfil="ceo", consultor_id=None, nome="Teste", id=1):
        self.state = _EstadoFalso(
            {"id": id, "nome": nome, "email": f"{perfil}@teste.com",
             "perfil": perfil, "consultor_id": consultor_id}
        )


@pytest.fixture()
def req():
    """Requisitante padrão dos testes unitários: CEO, que enxerga tudo."""
    return RequisicaoFalsa()
