"""Ambiente do Alembic — o schema real do RunRate mora aqui.

A URL do banco NUNCA vem do alembic.ini: vem do `DATABASE_URL`, exatamente
como a aplicação lê. Isso mantém um só lugar de verdade e evita a senha do
Postgres num arquivo versionado.

    cd backend
    DATABASE_URL="postgresql://..." python -m alembic upgrade head
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Importar app.models é o que POVOA o SQLModel.metadata. Sem esta linha o
# autogenerate acha que o banco tem 30 tabelas a mais e escreve um drop_table
# para cada uma.
from app import models  # noqa: F401
from ferramentas_migracao import carregar_env, url_para_ddl

config = context.config

# Quem chamou já pode ter definido a URL (o migrar.py define). Só preenchemos
# quando está vazia — sobrescrever aqui foi o que mandava o comando de volta
# para a porta 6543 depois de a ferramenta ter escolhido a 5432.
if not config.get_main_option("sqlalchemy.url", ""):
    carregar_env()
    config.set_main_option("sqlalchemy.url", url_para_ddl().replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def executar_offline() -> None:
    """Gera o SQL sem conectar (`--sql`), para revisar antes de aplicar."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _rodar(conexao) -> None:
    context.configure(
        connection=conexao,
        target_metadata=target_metadata,
        # compare_type detecta troca de tipo de coluna; sem ele, mudar um
        # Float para Numeric passaria batido e o autogenerate ficaria mudo.
        compare_type=True,
        compare_server_default=True,
        # SQLite não sabe ALTER COLUMN: o batch recria a tabela por baixo.
        # Só afeta o desenvolvimento — em produção é Postgres.
        render_as_batch=conexao.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    # Conexão injetada por quem chamou (testes e o script da linha de base
    # passam a sua, já configurada). Sem ela, abre uma pelo DATABASE_URL.
    injetada = config.attributes.get("connection")
    if injetada is not None:
        _rodar(injetada)
        return

    conexao_config = config.get_section(config.config_ini_section, {})
    engine = engine_from_config(conexao_config, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as conexao:
        _rodar(conexao)


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
