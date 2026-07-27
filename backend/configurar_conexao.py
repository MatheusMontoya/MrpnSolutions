"""Monta a DATABASE_URL a partir da senha crua, com percent-encoding correto.

Senha de banco quase sempre tem caractere reservado de URI, e escrever a string
na mao quebra em silencio: '#' inicia o fragment (a senha chega truncada), '/'
encerra a autoridade, '@' separa credencial de host, ':' separa usuario de senha.
Aqui quem codifica e o urllib, entao qualquer senha funciona sem voce precisar
saber disso.

Uso:
    1. Salve a senha CRUA, sozinha, em backend/senha.txt (sem aspas, sem prefixo)
    2. python configurar_conexao.py

O arquivo da senha e apagado no fim. A senha nunca e impressa na tela.
"""
from pathlib import Path
from urllib.parse import quote

REF = "fxenxbrpsddmqupvxngn"
HOST = "aws-0-ca-central-1.pooler.supabase.com"
PORTA = 6543

AQUI = Path(__file__).resolve().parent
ARQ_SENHA = AQUI / "senha.txt"
ARQ_ENV = AQUI / ".env"


def main() -> int:
    if not ARQ_SENHA.exists():
        print(f"Falta o arquivo {ARQ_SENHA.name}: salve a senha crua nele e rode de novo.")
        return 1

    bruto = ARQ_SENHA.read_text(encoding="utf-8")
    senha = bruto.strip("\r\n")
    if not senha:
        print("O arquivo da senha esta vazio.")
        return 1
    if senha != senha.strip():
        print("Aviso: a senha tem espaco no inicio ou no fim — mantendo como esta.")
    if senha.startswith("- "):
        print("Aviso: a senha comeca com '- '. Se isso era marcador de lista e nao")
        print("parte da senha, remova do arquivo e rode de novo.")

    # safe="" garante que TODO caractere reservado seja codificado
    codificada = quote(senha, safe="")
    url = f"postgresql://postgres.{REF}:{codificada}@{HOST}:{PORTA}/postgres"

    reservados = [c for c in "#/@:?&%" if c in senha]
    print(f"Senha lida: {len(senha)} caracteres.")
    print(f"Caracteres reservados de URI encontrados: {reservados or 'nenhum'}")
    print(f"Apos codificar, a senha ocupa {len(codificada)} caracteres na URL.")

    cabecalho = (
        "# Conexao com o Postgres do Supabase.\n"
        "# Gerado por configurar_conexao.py — a senha ja esta percent-encoded.\n"
        "# Este arquivo NAO vai para o GitHub nem para a Vercel.\n\n"
    )
    ARQ_ENV.write_text(cabecalho + f"DATABASE_URL={url}\n", encoding="utf-8")
    print(f"Escrito em {ARQ_ENV.name}.")

    try:
        import psycopg2

        conexao = psycopg2.connect(url, connect_timeout=15)
        with conexao.cursor() as cur:
            cur.execute("select current_database(), version()")
            banco, versao = cur.fetchone()
        conexao.close()
        print(f"CONEXAO OK — banco '{banco}', {versao.split(',')[0]}")
        return 0
    except ImportError:
        print("psycopg2 nao instalado; nao deu para testar a conexao agora.")
        return 0
    except Exception as e:  # noqa: BLE001
        # a mensagem do driver nao inclui a senha, so o motivo da recusa
        print(f"FALHOU AO CONECTAR: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    codigo = main()
    if ARQ_SENHA.exists():
        ARQ_SENHA.unlink()
        print("senha.txt apagado.")
    raise SystemExit(codigo)
