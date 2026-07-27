"""Preparo único do banco: schema + carga inicial.

Rode uma vez por ambiente, apontando DATABASE_URL para o destino:

    DATABASE_URL="postgresql://...pooler.supabase.com:6543/postgres" \
        python -m app.bootstrap

É idempotente: o schema usa checkfirst e a carga só entra em banco vazio.
Existe como comando separado justamente para não rodar em cold start —
veja o porquê em app/main.py: preparar_banco().
"""
from .database import DATABASE_URL
from .main import preparar_banco

if __name__ == "__main__":
    destino = "SQLite local" if DATABASE_URL.startswith("sqlite") else "Postgres"
    # nunca imprime a URL: ela carrega a senha do banco
    print(f"Preparando o banco ({destino})…")
    preparar_banco()
    print("Pronto. Schema criado e carga inicial aplicada.")
