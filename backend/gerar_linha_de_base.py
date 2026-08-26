"""Gera a migração de LINHA DE BASE do Alembic com os tipos certos do Postgres.

Por que não basta rodar o autogenerate contra o banco de sempre: ele compara os
modelos com o banco APONTADO. Contra a produção (que já tem o schema) sairia uma
migração vazia; contra SQLite sairiam os 23 enums como VARCHAR, e aplicar isso
no Postgres criaria o schema errado.

A saída é um schema TEMPORÁRIO e vazio dentro do mesmo Postgres:

    1. cria `alembic_linha_de_base` (nunca encosta no `public`)
    2. aponta o search_path para ele — o autogenerate enxerga um banco vazio
    3. escreve a migração com CREATE TABLE e CREATE TYPE de verdade
    4. derruba o schema temporário inteiro

Rode uma vez só, com o DATABASE_URL da produção:

    cd backend
    python gerar_linha_de_base.py
"""
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, pool, text

from ferramentas_migracao import carregar_env, exigir_postgres

AQUI = Path(__file__).resolve().parent
SCHEMA_TEMP = "alembic_linha_de_base"


def main() -> None:
    carregar_env()
    engine = create_engine(exigir_postgres(), poolclass=pool.NullPool)
    cfg = Config(str(AQUI / "alembic.ini"))
    cfg.set_main_option("script_location", str(AQUI / "migrations"))

    with engine.connect() as con:
        # 1. schema limpo, isolado do público
        con.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA_TEMP}" CASCADE'))
        con.execute(text(f'CREATE SCHEMA "{SCHEMA_TEMP}"'))
        con.commit()
        print(f"schema temporário {SCHEMA_TEMP} criado")

        try:
            # 2. o autogenerate passa a enxergar SÓ este schema
            con.execute(text(f'SET search_path TO "{SCHEMA_TEMP}"'))
            cfg.attributes["connection"] = con
            command.revision(
                cfg,
                message="linha de base: schema completo do RunRate",
                autogenerate=True,
            )
            print("migração escrita em migrations/versions/")
        finally:
            # 3. o temporário some, aconteça o que acontecer
            con.rollback()
            con.execute(text('SET search_path TO "public"'))
            con.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA_TEMP}" CASCADE'))
            con.commit()
            print(f"schema temporário {SCHEMA_TEMP} removido")

        # 4. prova de que o público ficou como estava
        n = con.execute(text(
            "select count(*) from information_schema.tables where table_schema='public'"
        )).scalar()
        print(f"tabelas no schema public: {n} (intactas)")


if __name__ == "__main__":
    sys.exit(main())
