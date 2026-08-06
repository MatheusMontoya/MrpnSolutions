"""Monta a DATABASE_URL a partir da string do painel + a senha crua.

Duas coisas que quebram em silencio quando se escreve a string na mao:

1. Caractere reservado de URI na senha. '#' inicia o fragment (a senha chega
   truncada ao servidor), '/' encerra a autoridade, '@' separa credencial de
   host, ':' separa usuario de senha. Aqui quem codifica e o urllib.
2. Ref e regiao do projeto. Mudam a cada projeto novo do Supabase, entao nada
   e cravado neste arquivo: a string vem do painel, como esta la.

Uso:
    1. backend/conexao.txt  -> a string do painel (Connect > Transaction pooler),
                               exatamente como copiada, com o [YOUR-PASSWORD]
    2. backend/senha.txt    -> a senha crua, sozinha
    3. python configurar_conexao.py

Os dois arquivos temporarios sao apagados no fim. A senha nunca e impressa.
"""
import re
from pathlib import Path
from urllib.parse import quote

AQUI = Path(__file__).resolve().parent
ARQ_CONEXAO = AQUI / "conexao.txt"
ARQ_SENHA = AQUI / "senha.txt"
ARQ_ENV = AQUI / ".env"

PLACEHOLDERS = ("[YOUR-PASSWORD]", "[YOUR_PASSWORD]", "YOUR-PASSWORD", "SUA_SENHA")


def limpar() -> None:
    for f in (ARQ_CONEXAO, ARQ_SENHA):
        if f.exists():
            f.unlink()
            print(f"{f.name} apagado.")


def main() -> int:
    faltando = [f.name for f in (ARQ_CONEXAO, ARQ_SENHA) if not f.exists()]
    if faltando:
        print("Falta(m): " + ", ".join(faltando))
        print("Veja as instrucoes no topo deste arquivo.")
        return 1

    modelo = ARQ_CONEXAO.read_text(encoding="utf-8").strip()
    senha = ARQ_SENHA.read_text(encoding="utf-8").strip("\r\n")
    if not modelo or not senha:
        print("conexao.txt ou senha.txt esta vazio.")
        return 1

    if not modelo.startswith(("postgresql://", "postgres://")):
        print(f"conexao.txt nao parece uma connection string: comeca com '{modelo[:18]}...'")
        print("Copie a da aba 'Transaction pooler' no botao Connect do Supabase.")
        return 1

    if ":6543/" not in modelo:
        porta = re.search(r":(\d{4,5})/", modelo)
        print(f"AVISO: a porta e {porta.group(1) if porta else '?'}, esperava 6543 (Transaction pooler).")
        print("A conexao direta (5432) esgota conexoes em serverless. Prossiga so se souber o que faz.")

    codificada = quote(senha, safe="")
    url = modelo
    for ph in PLACEHOLDERS:
        url = url.replace(ph, codificada)
    if codificada not in url:
        print("Nao achei o placeholder da senha na string. Substituindo o trecho entre ':' e '@'…")
        url = re.sub(r"://([^:]+):[^@]*@", lambda m: f"://{m.group(1)}:{codificada}@", modelo, count=1)

    ref = re.search(r"://(?:postgres\.)?([a-z0-9]{16,})[:.]", url)
    host = re.search(r"@([^:/]+)", url)
    reservados = [c for c in "#/@:?&%" if c in senha]
    print(f"Projeto: {ref.group(1) if ref else '?'} | host: {host.group(1) if host else '?'}")
    print(f"Senha: {len(senha)} caracteres | reservados de URI: {reservados or 'nenhum'} | {len(codificada)} apos codificar")

    cabecalho = (
        "# Conexao com o Postgres do Supabase.\n"
        "# Gerado por configurar_conexao.py — a senha ja esta percent-encoded.\n"
        "# Este arquivo NAO vai para o GitHub nem para a Vercel.\n\n"
    )
    ARQ_ENV.write_text(cabecalho + f"DATABASE_URL={url}\n", encoding="utf-8")
    print(f"Escrito em {ARQ_ENV.name}.")

    try:
        import psycopg2

        conexao = psycopg2.connect(url, connect_timeout=20)
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
        # a mensagem do driver traz o motivo da recusa, nunca a senha
        print(f"FALHOU AO CONECTAR: {type(e).__name__}: {str(e).strip()[:200]}")
        return 2


if __name__ == "__main__":
    codigo = main()
    limpar()
    raise SystemExit(codigo)
