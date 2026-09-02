"""Cópia de segurança do banco de produção — e a volta dela.

Por que existe: o free tier do Supabase **não faz backup automático**. Enquanto
o banco era demonstração isso não custava nada. A partir do momento em que hora
lançada e cliente real entram aqui, um acidente não tem desfazer.

    cd backend
    python backup.py                    # grava um instantâneo em backups/
    python backup.py listar             # o que já foi guardado
    python backup.py restaurar ARQUIVO  # devolve o instantâneo ao banco

Não usa `pg_dump` de propósito: ele não está instalado na máquina de ninguém
aqui, e exigir instalar Postgres para conseguir fazer backup é a receita para
não fazer backup nenhum. Isto roda com o que o projeto já tem.

## O que este backup É e o que NÃO É

**É** um instantâneo completo: todas as linhas de todas as tabelas, no momento
em que você rodou. Serve para o acidente comum — apagou o que não devia, uma
migração deu errado, alguém mexeu onde não podia.

**Não é** point-in-time recovery. Se o backup é de terça e o acidente é na
quinta, você perde quarta e quinta. Rode antes de qualquer coisa arriscada, e
com regularidade — semanal, no mínimo, enquanto forem duas pessoas.

**Não substitui plano pago.** Quando entrar dado de cliente que a consultoria
não pode perder, o backup gerenciado do Supabase é outro nível de garantia.
Isto aqui é o que impede a perda total até lá.
"""
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, inspect, pool, text

from ferramentas_migracao import carregar_env, exigir_postgres

AQUI = Path(__file__).resolve().parent
PASTA = AQUI / "backups"

def _ordem_dependencia() -> list[str]:
    """Pai antes de filho, senão a chave estrangeira recusa o insert.

    Vem do `sorted_tables` do SQLAlchemy, que deriva a ordem das chaves
    estrangeiras declaradas nos modelos. A primeira versão disto era uma lista
    escrita à mão — e já nascia com um `envioSemana` em camelCase que nem
    existe. Lista à mão envelhece à revelia: quem criar a tabela 31 não vai
    lembrar de vir aqui.
    """
    from sqlmodel import SQLModel

    from app import models  # noqa: F401  — povoa o metadata

    return [t.name for t in SQLModel.metadata.sorted_tables]


def _serializar(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (bytes, memoryview)):
        return bytes(valor).hex()
    return valor


def _ordenar(tabelas: list[str]) -> list[str]:
    """As conhecidas na ordem de dependência; o que sobrar, no fim."""
    ordem = _ordem_dependencia()
    conhecidas = [t for t in ordem if t in tabelas]
    return conhecidas + sorted(set(tabelas) - set(conhecidas))


def gravar(engine=None) -> Path:
    if engine is None:
        carregar_env()
        engine = create_engine(exigir_postgres(), poolclass=pool.NullPool)
    PASTA.mkdir(exist_ok=True)

    with engine.connect() as con:
        tabelas = [t for t in inspect(con).get_table_names() if t != "alembic_version"]
        versao = con.execute(text("select version_num from alembic_version")).scalar()

        dados, total = {}, 0
        for tabela in _ordenar(tabelas):
            linhas = [
                {k: _serializar(v) for k, v in linha.items()}
                for linha in con.execute(text(f'select * from "{tabela}"')).mappings()
            ]
            dados[tabela] = linhas
            total += len(linhas)
            if linhas:
                print(f"  {tabela:<22} {len(linhas)}")

    carimbo = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    destino = PASTA / f"runrate_{carimbo}.json"
    destino.write_text(json.dumps({
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        # a revisão fica junto: restaurar num schema de outra versão é o jeito
        # mais rápido de transformar um backup em um problema novo
        "revisao_alembic": versao,
        "tabelas": dados,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    mb = destino.stat().st_size / 1_048_576
    print(f"\n{total} linhas em {len(tabelas)} tabelas -> {destino.name} ({mb:.2f} MB)")
    print(f"revisão do schema: {versao}")
    return destino


def listar() -> None:
    if not PASTA.exists() or not any(PASTA.glob("runrate_*.json")):
        print("Nenhum backup ainda. Rode: python backup.py")
        return
    for arq in sorted(PASTA.glob("runrate_*.json"), reverse=True):
        d = json.loads(arq.read_text(encoding="utf-8"))
        linhas = sum(len(v) for v in d["tabelas"].values())
        mb = arq.stat().st_size / 1_048_576
        print(f"  {arq.name:<34} {linhas:>6} linhas  {mb:>6.2f} MB  rev {d.get('revisao_alembic')}")


def restaurar(caminho: str, engine=None, confirmado: bool = False) -> None:
    arq = Path(caminho)
    if not arq.is_absolute():
        arq = PASTA / arq
    if not arq.exists():
        raise SystemExit(f"não achei {arq}")

    pacote = json.loads(arq.read_text(encoding="utf-8"))
    if engine is None:
        carregar_env()
        engine = create_engine(exigir_postgres(), poolclass=pool.NullPool)

    with engine.connect() as con:
        versao_banco = con.execute(text("select version_num from alembic_version")).scalar()
    versao_backup = pacote.get("revisao_alembic")
    if versao_banco != versao_backup:
        raise SystemExit(
            f"O backup é do schema {versao_backup} e o banco está em {versao_banco}.\n"
            "Restaurar assim mistura duas versões do schema. Leve o banco à mesma\n"
            "revisão primeiro (python migrar.py) ou use um backup correspondente."
        )

    total = sum(len(v) for v in pacote["tabelas"].values())
    print(f"Backup de {pacote['gerado_em']} — {total} linhas.")
    if not confirmado:
        print("\nISTO APAGA TUDO QUE ESTÁ NO BANCO HOJE e põe o backup no lugar.")
        if input('Digite "restaurar" para confirmar: ').strip() != "restaurar":
            raise SystemExit("cancelado — nada foi tocado")

    ordem = _ordenar(list(pacote["tabelas"]))
    with engine.begin() as con:  # tudo ou nada
        # apaga na ordem inversa: filho antes de pai
        for tabela in reversed(ordem):
            con.execute(text(f'delete from "{tabela}"'))
        for tabela in ordem:
            linhas = pacote["tabelas"][tabela]
            if not linhas:
                continue
            colunas = ", ".join(f'"{c}"' for c in linhas[0])
            marcas = ", ".join(f":{c}" for c in linhas[0])
            con.execute(text(f'insert into "{tabela}" ({colunas}) values ({marcas})'), linhas)
            print(f"  {tabela:<22} {len(linhas)}")

        # as sequências ficam onde estavam; sem isto o próximo insert repete id
        for tabela in ordem:
            if pacote["tabelas"][tabela]:
                con.execute(text(
                    f"select setval(pg_get_serial_sequence('\"{tabela}\"', 'id'),"
                    f' coalesce((select max(id) from "{tabela}"), 1))'
                ))

    print(f"\nRestaurado. {total} linhas.")


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "gravar"
    if acao in ("gravar", "backup"):
        gravar()
    elif acao == "listar":
        listar()
    elif acao == "restaurar":
        if len(sys.argv) < 3:
            raise SystemExit("uso: python backup.py restaurar runrate_AAAA-MM-DD_HHMM.json")
        restaurar(sys.argv[2])
    else:
        raise SystemExit(__doc__)
