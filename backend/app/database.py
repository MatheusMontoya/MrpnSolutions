"""Conexão com o banco.

SQLite no desenvolvimento local; Postgres (Supabase) em produção, via DATABASE_URL.
Nenhuma outra parte do código sabe qual dos dois está em uso.
"""
import os

from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./psa.db")

# Alguns painéis do Supabase entregam a string como postgres://. O SQLAlchemy 2
# só reconhece postgresql://, então normaliza antes de criar o engine.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USA_SQLITE = DATABASE_URL.startswith("sqlite")

if USA_SQLITE:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Serverless + pooler do Supabase (Supavisor, porta 6543): o pool de conexões
    # é responsabilidade do pooler. Se o SQLAlchemy mantivesse o seu próprio, cada
    # invocação da função abriria um pool novo e as conexões do projeto esgotariam.
    # NullPool abre e devolve a conexão por requisição, que é o correto aqui.
    engine = create_engine(DATABASE_URL, poolclass=NullPool)


def criar_tabelas() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
