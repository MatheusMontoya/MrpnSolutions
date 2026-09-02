"""As migrações têm de descrever o mesmo schema que os modelos.

Este é o teste que impede a dívida de voltar. Os outros 200 testes montam o
schema com `create_all` direto dos modelos — rápido, e por isso mesmo cego:
alguém acrescenta um campo, os testes passam, e o banco de produção fica sem a
coluna porque ninguém escreveu a migração.

Aqui é o contrário: o schema nasce das MIGRAÇÕES, e depois perguntamos ao
autogenerate se sobrou diferença. Sobrou = migração faltando.

Roda em SQLite, então cobre estrutura (tabela, coluna, índice, nulidade), não
o tipo nativo de enum do Postgres — para esse há `conferir_migracoes.py`, que
usa um schema temporário no Postgres de verdade.
"""
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

from app import models  # noqa: F401  — povoa o SQLModel.metadata

RAIZ = Path(__file__).resolve().parent.parent


def config_alembic() -> Config:
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "migrations"))
    return cfg


@pytest.fixture()
def banco_migrado(tmp_path):
    """Um SQLite vazio levado ao topo pelas migrações — não por create_all."""
    arquivo = tmp_path / "migrado.db"
    engine = create_engine(f"sqlite:///{arquivo.as_posix()}")
    cfg = config_alembic()
    with engine.begin() as con:
        cfg.attributes["connection"] = con
        command.upgrade(cfg, "head")
    return engine


def test_migracoes_reproduzem_os_modelos(banco_migrado):
    """Zero diferenças. Qualquer coisa aqui é migração que ninguém escreveu."""
    with banco_migrado.connect() as con:
        ctx = MigrationContext.configure(con, opts={"compare_type": False})
        diferencas = compare_metadata(ctx, SQLModel.metadata)

    # a alembic_version é da ferramenta, não dos modelos
    diferencas = [
        d for d in diferencas
        if getattr(getattr(d, "__getitem__", lambda _: None)(1), "name", None) != "alembic_version"
        and "alembic_version" not in str(d)
    ]
    assert diferencas == [], (
        "Modelos e migrações divergiram. Gere a migração que falta:\n"
        '    cd backend && python migrar.py nova "o que mudou"\n\n'
        + "\n".join(f"  - {d}" for d in diferencas)
    )


def test_migracoes_criam_todas_as_tabelas_do_modelo(banco_migrado):
    do_modelo = set(SQLModel.metadata.tables)
    no_banco = set(inspect(banco_migrado).get_table_names()) - {"alembic_version"}
    assert do_modelo - no_banco == set(), f"tabelas sem migração: {do_modelo - no_banco}"
    assert no_banco - do_modelo == set(), f"tabelas órfãs na migração: {no_banco - do_modelo}"


def test_toda_migracao_desfaz_o_que_faz(banco_migrado):
    """Downgrade tem de devolver o banco ao vazio.

    Migração sem volta é migração que não dá para reverter num deploy ruim.
    """
    cfg = config_alembic()
    with banco_migrado.begin() as con:
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "base")

    sobraram = set(inspect(banco_migrado).get_table_names()) - {"alembic_version"}
    assert sobraram == set(), f"o downgrade deixou tabelas para trás: {sobraram}"


def test_existe_uma_unica_cabeca():
    """Duas cabeças = alguém ramificou o histórico e o `upgrade head` quebra."""
    cabecas = ScriptDirectory.from_config(config_alembic()).get_heads()
    assert len(cabecas) == 1, f"o histórico ramificou: {cabecas}"


def test_toda_revisao_tem_downgrade():
    scripts = ScriptDirectory.from_config(config_alembic())
    sem_volta = []
    for rev in scripts.walk_revisions():
        origem = Path(rev.path).read_text(encoding="utf-8")
        corpo = origem.split("def downgrade()", 1)[-1]
        if "pass" in corpo.split("\n")[1:3] and "op." not in corpo:
            sem_volta.append(rev.revision)
    assert sem_volta == [], f"revisões sem downgrade: {sem_volta}"


# ============ a transição de quem já tinha banco ============

def _preparar(monkeypatch, tmp_path, nome):
    """Aponta app.database para um SQLite descartável."""
    import app.database as db
    from sqlalchemy import create_engine

    arquivo = tmp_path / nome
    url = f"sqlite:///{arquivo.as_posix()}"
    engine = create_engine(url)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "DATABASE_URL", url)
    return db, engine


def test_banco_novo_e_construido_pelas_migracoes(monkeypatch, tmp_path):
    from sqlalchemy import inspect

    db, engine = _preparar(monkeypatch, tmp_path, "novo.db")
    db.aplicar_migracoes()
    tabelas = set(inspect(engine).get_table_names())
    assert "alembic_version" in tabelas
    assert set(SQLModel.metadata.tables) <= tabelas


def test_banco_anterior_ao_alembic_e_marcado_e_nao_recriado(monkeypatch, tmp_path):
    """O psa.db que já estava na máquina de alguém.

    Tem as 30 tabelas e nenhuma versão gravada. Um `upgrade` ali morre em
    "table cliente already exists" — e leva a subida do app junto.
    """
    from sqlalchemy import inspect, text

    db, engine = _preparar(monkeypatch, tmp_path, "antigo.db")
    SQLModel.metadata.create_all(engine)  # como era antes do Alembic
    assert "alembic_version" not in inspect(engine).get_table_names()

    db.aplicar_migracoes()

    with engine.connect() as con:
        assert con.execute(text("select version_num from alembic_version")).scalar()


def test_tentativa_que_falhou_no_meio_nao_trava_a_subida(monkeypatch, tmp_path):
    """alembic_version criada e VAZIA: existe, mas não diz nada.

    Checar só a existência da tabela mandaria este caso para o `upgrade`, que
    tentaria criar tudo de novo.
    """
    from sqlalchemy import text

    db, engine = _preparar(monkeypatch, tmp_path, "meio.db")
    SQLModel.metadata.create_all(engine)
    with engine.begin() as con:
        con.execute(text("create table alembic_version (version_num varchar(32) not null)"))

    db.aplicar_migracoes()  # não pode levantar

    with engine.connect() as con:
        assert con.execute(text("select version_num from alembic_version")).scalar()


def test_aplicar_duas_vezes_nao_muda_nada(monkeypatch, tmp_path):
    from sqlalchemy import text

    db, engine = _preparar(monkeypatch, tmp_path, "duasvezes.db")
    db.aplicar_migracoes()
    with engine.connect() as con:
        antes = con.execute(text("select version_num from alembic_version")).scalar()
    db.aplicar_migracoes()
    with engine.connect() as con:
        assert con.execute(text("select version_num from alembic_version")).scalar() == antes


# ============ a copia de seguranca ============

def test_ordem_do_backup_respeita_as_chaves_estrangeiras():
    """Pai antes de filho, senão o insert da restauração é recusado.

    A primeira versão desta ordem era uma lista escrita à mão e já nascia com
    um nome de tabela que não existia. Agora ela sai do `sorted_tables`, e este
    teste é a prova de que a derivação está certa — em toda tabela, hoje e nas
    que vierem depois.
    """
    import backup

    ordem = backup._ordem_dependencia()
    posicao = {nome: i for i, nome in enumerate(ordem)}

    violacoes = [
        f"{t.name} vem antes de {fk.column.table.name}, que ela referencia"
        for t in SQLModel.metadata.sorted_tables
        for fk in t.foreign_keys
        if fk.column.table.name != t.name
        and posicao[fk.column.table.name] > posicao[t.name]
    ]
    assert violacoes == [], "\n".join(violacoes)


def test_backup_cobre_todas_as_tabelas_do_modelo():
    """Tabela nova sem cobertura é dado que o backup não salva — e ninguém nota
    até precisar restaurar."""
    import backup

    assert set(backup._ordem_dependencia()) == set(SQLModel.metadata.tables)


def test_backup_nunca_entra_no_repositorio():
    """Um backup carrega hash de senha e token de sessão, e o repositório é
    público. Esta é a única linha entre as duas coisas."""
    import subprocess

    alvo = RAIZ / "backups" / "runrate_teste.json"
    r = subprocess.run(
        ["git", "check-ignore", str(alvo)],
        capture_output=True, cwd=RAIZ.parent,
    )
    assert r.returncode == 0, "backend/backups/ PRECISA estar no .gitignore"
