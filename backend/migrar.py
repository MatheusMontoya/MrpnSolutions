"""Atalho para o Alembic que já carrega o `backend/.env`.

    python migrar.py                 # aplica o que falta (upgrade head)
    python migrar.py estado          # em que revisão o banco está
    python migrar.py historico       # a fila de migrações
    python migrar.py sql             # imprime o SQL sem aplicar (revisão)
    python migrar.py marcar          # marca como aplicado SEM rodar (schema já existe)
    python migrar.py nova "mensagem"  # gera migração a partir da diferença dos modelos
    python migrar.py voltar          # desfaz a última (só com backup na mão)

Sem isto, cada comando exigiria colar a DATABASE_URL — que carrega a senha do
Postgres — na linha de comando, onde ela fica no histórico do shell.
"""
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

AQUI = Path(__file__).resolve().parent


def configurar() -> Config:
    from ferramentas_migracao import carregar_env, exigir_postgres

    carregar_env()
    cfg = Config(str(AQUI / "alembic.ini"))
    cfg.set_main_option("script_location", str(AQUI / "migrations"))
    # a porta de DDL pode diferir da que a aplicação usa — ver ferramentas_migracao
    cfg.set_main_option("sqlalchemy.url", exigir_postgres().replace("%", "%%"))
    return cfg


def main(argv: list[str]) -> None:
    acao = argv[0] if argv else "aplicar"
    cfg = configurar()

    if acao in ("aplicar", "upgrade", "head"):
        command.upgrade(cfg, "head")
        print("Banco no topo das migrações.")
    elif acao in ("estado", "current"):
        command.current(cfg, verbose=True)
    elif acao in ("historico", "history"):
        command.history(cfg, verbose=False)
    elif acao == "sql":
        # revisa antes de aplicar: útil quando o alvo é a produção
        command.upgrade(cfg, "head", sql=True)
    elif acao in ("marcar", "stamp"):
        # O schema já existe (foi criado por create_all antes do Alembic entrar).
        # Marcar diz "considere estas migrações aplicadas" sem executá-las —
        # rodar o upgrade aqui tentaria criar 30 tabelas que já estão lá.
        command.stamp(cfg, "head")
        print("Banco marcado no topo, sem executar nada.")
    elif acao in ("nova", "revision"):
        if len(argv) < 2:
            raise SystemExit('uso: python migrar.py nova "o que mudou"')
        command.revision(cfg, message=argv[1], autogenerate=True)
    elif acao in ("voltar", "downgrade"):
        command.downgrade(cfg, "-1")
        print("Uma migração desfeita.")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
