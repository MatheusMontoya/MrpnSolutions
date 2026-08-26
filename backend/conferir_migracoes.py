"""Prova que as migrações constroem EXATAMENTE o schema que os modelos descrevem.

Roda o `upgrade head` num schema temporário e vazio do próprio Postgres e depois
pergunta ao autogenerate se sobrou alguma diferença. Zero diferenças = a
migração reproduz o modelo. Qualquer coisa listada é migração faltando.

    cd backend
    python conferir_migracoes.py

Não encosta no `public`: cria, usa e derruba `alembic_conferencia`.
"""
import sys
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, pool, text
from sqlmodel import SQLModel

from app import models  # noqa: F401  — povoa o SQLModel.metadata
from ferramentas_migracao import carregar_env, exigir_postgres

AQUI = Path(__file__).resolve().parent
SCHEMA_TEMP = "alembic_conferencia"


def main() -> int:
    carregar_env()
    engine = create_engine(exigir_postgres(), poolclass=pool.NullPool)
    cfg = Config(str(AQUI / "alembic.ini"))
    cfg.set_main_option("script_location", str(AQUI / "migrations"))

    with engine.connect() as con:
        con.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA_TEMP}" CASCADE'))
        con.execute(text(f'CREATE SCHEMA "{SCHEMA_TEMP}"'))
        con.commit()
        try:
            con.execute(text(f'SET search_path TO "{SCHEMA_TEMP}"'))
            cfg.attributes["connection"] = con
            command.upgrade(cfg, "head")
            print("upgrade head aplicado no schema temporário")

            tabelas = con.execute(text(
                "select count(*) from information_schema.tables where table_schema = :s"
            ), {"s": SCHEMA_TEMP}).scalar()
            enums = con.execute(text(
                "select count(*) from pg_type t join pg_namespace n on n.oid = t.typnamespace"
                " where n.nspname = :s and t.typtype = 'e'"
            ), {"s": SCHEMA_TEMP}).scalar()
            print(f"criou {tabelas} tabelas e {enums} tipos enum")

            ctx = MigrationContext.configure(
                con, opts={"compare_type": True, "compare_server_default": True}
            )
            diferencas = compare_metadata(ctx, SQLModel.metadata)
            # a própria alembic_version não está nos modelos: é da ferramenta
            diferencas = [
                d for d in diferencas
                if not (isinstance(d, tuple) and len(d) > 1
                        and getattr(d[1], "name", None) == "alembic_version")
            ]
        finally:
            con.rollback()
            con.execute(text('SET search_path TO "public"'))
            con.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA_TEMP}" CASCADE'))
            con.commit()
            print("schema temporário removido")

    if diferencas:
        print(f"\n{len(diferencas)} DIFERENÇA(S) entre migrações e modelos:")
        for d in diferencas:
            print("  -", d)
        return 1
    print("\nSem diferenças: as migrações reproduzem o modelo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
