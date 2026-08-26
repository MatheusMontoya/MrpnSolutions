"""Peças compartilhadas pelos comandos de migração.

Duas coisas que todo comando administrativo precisa e nenhum deveria repetir:
carregar o `.env` sem imprimir a senha, e escolher a porta certa do pooler.
"""
import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent

# Supabase: 6543 é o pooler em modo TRANSAÇÃO — ótimo para a aplicação (muitas
# conexões curtas), ruim para DDL, que precisa de recursos de sessão. 5432 é o
# mesmo pooler em modo SESSÃO. A documentação do Supabase recomenda sessão para
# migração, e de quebra resolve um problema prático: a 6543 costuma estar
# bloqueada em rede corporativa, e é dessa rede que o comando é rodado.
PORTA_TRANSACAO = ":6543/"
PORTA_SESSAO = ":5432/"


def carregar_env() -> None:
    """Lê backend/.env para o ambiente. Não imprime nada — a senha mora ali."""
    arq = AQUI / ".env"
    if not arq.exists():
        return
    for linha in arq.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def url_para_ddl() -> str:
    """A URL que os comandos administrativos usam.

    `RUNRATE_DDL_URL` tem prioridade, para quem precisa apontar para outro lugar.
    """
    manual = os.environ.get("RUNRATE_DDL_URL")
    if manual:
        return manual.replace("postgres://", "postgresql://", 1)

    url = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
    if "pooler.supabase.com" in url and PORTA_TRANSACAO in url:
        return url.replace(PORTA_TRANSACAO, PORTA_SESSAO, 1)
    return url


def exigir_postgres() -> str:
    url = url_para_ddl()
    if not url.startswith("postgresql://"):
        raise SystemExit(
            "Este comando precisa de um Postgres. Preencha backend/.env com a\n"
            "DATABASE_URL do Supabase, ou exporte RUNRATE_DDL_URL."
        )
    return url
