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
    """Cria o schema DIRETO dos modelos, sem passar pelas migrações.

    Serve para teste e para banco descartável, onde velocidade importa e não
    existe histórico a preservar. Ambiente que guarda dado usa
    `aplicar_migracoes()`: create_all cria tabela que falta, mas nunca ALTERA
    coluna existente — é exatamente por isso que o Alembic entrou.
    """
    SQLModel.metadata.create_all(engine)


def aplicar_migracoes() -> None:
    """Leva o banco ao topo das migrações. É este o caminho de produção.

    Banco que já existia de antes do Alembic é MARCADO, não migrado: ele tem as
    30 tabelas mas nenhuma linha em `alembic_version`, e um `upgrade` ali tenta
    criar tudo de novo e morre em "table cliente already exists". Acontece com
    todo psa.db de desenvolvimento que já estava na máquina de alguém.
    """
    from pathlib import Path as _Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text

    raiz = _Path(__file__).resolve().parent.parent
    cfg = Config(str(raiz / "alembic.ini"))
    cfg.set_main_option("script_location", str(raiz / "migrations"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

    # O que decide não é a EXISTÊNCIA da alembic_version — uma tentativa que
    # falhou no meio já a deixa criada e vazia. O que decide é ter versão
    # gravada nela: sem versão, e com tabelas de aplicação por perto, o schema
    # veio de antes do Alembic.
    tabelas = set(inspect(engine).get_table_names())
    do_app = tabelas - {"alembic_version"}
    versao_atual = None
    if "alembic_version" in tabelas:
        with engine.connect() as con:
            versao_atual = con.execute(text("select version_num from alembic_version")).scalar()

    if do_app and versao_atual is None:
        print("[RunRate] schema anterior ao Alembic — marcando na linha de base.")
        command.stamp(cfg, "head")
        return

    command.upgrade(cfg, "head")


def get_session():
    with Session(engine) as session:
        yield session
