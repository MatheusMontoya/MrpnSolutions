"""Prova que a VOLTA funciona — num schema temporário, nunca na produção.

Backup que ninguém restaurou não é backup, é um arquivo. Este script fecha o
ciclo inteiro num schema descartável do próprio Postgres:

    1. cria `backup_conferencia` e leva ao topo das migrações
    2. planta dado com acento, dinheiro, data e chave estrangeira
    3. grava o backup
    4. apaga tudo
    5. restaura
    6. compara linha por linha
    7. derruba o schema

    cd backend
    python conferir_backup.py
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, pool, text

import backup
from ferramentas_migracao import carregar_env, exigir_postgres

AQUI = Path(__file__).resolve().parent
SCHEMA_TEMP = "backup_conferencia"


def _plantar(con) -> None:
    """Dado com as armadilhas de verdade: acento, decimal, data, FK.

    Pelo ORM, não por SQL escrito à mão: o modelo é quem sabe quais colunas
    existem e quais têm valor padrão. SQL à mão aqui só reescreve o schema de
    memória — e erra.
    """
    from sqlmodel import Session

    from app.models import Cliente, Consultor, Projeto, Senioridade

    with Session(con) as s:
        s.add(Cliente(id=1, nome="Indústria Ação & Cia", contato="contato@acao.com.br"))
        s.add(Consultor(
            id=1, nome="José da Conceição", senioridade=Senioridade.senior,
            modulo_sap="MM", skills="S/4HANA",
            taxa_hora_custo=137.55, taxa_hora_venda=289.90,
        ))
        s.add(Projeto(id=1, nome="Rollout Filial São Paulo", cliente_id=1,
                      data_inicio=date(2026, 3, 15)))
        s.flush()


def main() -> int:
    carregar_env()
    engine_raiz = create_engine(exigir_postgres(), poolclass=pool.NullPool)
    cfg = Config(str(AQUI / "alembic.ini"))
    cfg.set_main_option("script_location", str(AQUI / "migrations"))

    arquivo = None
    with engine_raiz.connect() as con:
        con.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA_TEMP}" CASCADE'))
        con.execute(text(f'CREATE SCHEMA "{SCHEMA_TEMP}"'))
        con.commit()
        try:
            con.execute(text(f'SET search_path TO "{SCHEMA_TEMP}"'))
            cfg.attributes["connection"] = con
            command.upgrade(cfg, "head")
            _plantar(con)
            con.commit()

            antes = {
                t: con.execute(text(f"select count(*) from {t}")).scalar()
                for t in ("cliente", "consultor", "projeto")
            }
            nome_antes = con.execute(text("select nome from cliente where id=1")).scalar()
            taxa_antes = con.execute(text("select taxa_hora_venda from consultor where id=1")).scalar()
            data_antes = con.execute(text("select data_inicio from projeto where id=1")).scalar()
            print(f"plantado: {antes}")

            # ---- 3. grava
            arquivo = backup.gravar(engine=_ligado(con))
            print()

            # ---- 4. apaga tudo
            for t in ("projeto", "consultor", "cliente"):
                con.execute(text(f"delete from {t}"))
            con.commit()
            vazio = con.execute(text("select count(*) from cliente")).scalar()
            assert vazio == 0
            print("banco esvaziado — agora a volta\n")

            # ---- 5. restaura
            backup.restaurar(str(arquivo), engine=_ligado(con), confirmado=True)
            con.commit()

            # ---- 6. compara
            depois = {
                t: con.execute(text(f"select count(*) from {t}")).scalar()
                for t in ("cliente", "consultor", "projeto")
            }
            nome_depois = con.execute(text("select nome from cliente where id=1")).scalar()
            taxa_depois = con.execute(text("select taxa_hora_venda from consultor where id=1")).scalar()
            data_depois = con.execute(text("select data_inicio from projeto where id=1")).scalar()

            # e a sequência: o próximo insert não pode colidir de id
            novo_id = con.execute(text(
                "insert into cliente (nome, contato) values ('Depois', 'd@d.com') returning id"
            )).scalar()
            con.rollback()

            problemas = []
            if antes != depois:
                problemas.append(f"contagem mudou: {antes} -> {depois}")
            if nome_antes != nome_depois:
                problemas.append(f"acento perdido: {nome_antes!r} -> {nome_depois!r}")
            if abs(float(taxa_antes) - float(taxa_depois)) > 1e-9:
                problemas.append(f"dinheiro mudou: {taxa_antes} -> {taxa_depois}")
            if data_antes != data_depois:
                problemas.append(f"data mudou: {data_antes} -> {data_depois}")
            if novo_id is None or novo_id <= 1:
                problemas.append(f"sequência não avançou: próximo id seria {novo_id}")
        finally:
            con.rollback()
            con.execute(text('SET search_path TO "public"'))
            con.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA_TEMP}" CASCADE'))
            con.commit()
            print("\nschema temporário removido")
            if arquivo and arquivo.exists():
                arquivo.unlink()  # era de teste, não polui a pasta de backups

    if problemas:
        print("\nA VOLTA NÃO CONFERE:")
        for p in problemas:
            print("  -", p)
        return 1
    print("\nCiclo completo: gravou, apagou, restaurou, e tudo voltou igual.")
    print(f"  acento preservado:  {nome_depois!r}")
    print(f"  decimal preservado: {taxa_depois}")
    print(f"  data preservada:    {data_depois}")
    print(f"  sequência correta:  próximo id = {novo_id}")
    return 0


class _ligado:
    """Faz uma conexão já aberta parecer um engine para o backup.py.

    O backup abre a conexão dele; aqui precisamos que use ESTA, que está com o
    search_path apontado para o schema temporário.
    """

    def __init__(self, con):
        self._con = con

    def connect(self):
        return _SemFechar(self._con)

    def begin(self):
        return _SemFechar(self._con)


class _SemFechar:
    def __init__(self, con):
        self._con = con

    def __enter__(self):
        return self._con

    def __exit__(self, *a):
        return False


if __name__ == "__main__":
    sys.exit(main())
