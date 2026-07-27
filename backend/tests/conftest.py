import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATABASE_URL"] = "sqlite://"  # em memória, isolado por engine

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
