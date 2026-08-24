"""Migra bancos existentes de 2 perfis (gestor/consultor) para 3 (ceo/rh/consultor).

O que faz, de forma idempotente (rodar duas vezes não quebra nada):
1. Postgres: renomeia o rótulo 'gestor' do tipo nativo perfilusuario para 'ceo'
   (o rename muda também o valor já gravado nas linhas) e adiciona 'rh'.
   SQLite: UPDATE simples, porque lá o enum é texto.
2. Renomeia a conta de demonstração gestor@psa.com -> ceo@psa.com.
3. Cria o usuário de demonstração do RH (rh@psa.com, senha psa123) se faltar.

Uso (mesma pegada do bootstrap):
    DATABASE_URL="postgresql://..." python -m app.migrar_perfis

Rode ANTES de subir o código novo: o código antigo não conhece 'ceo' e o novo
não conhece 'gestor' — a janela entre migrar e deployar deve ser curta.
"""
from sqlalchemy import text

from .database import USA_SQLITE, engine


def migrar() -> None:
    with engine.connect() as con:
        con = con.execution_options(isolation_level="AUTOCOMMIT")

        if USA_SQLITE:
            n = con.execute(text("UPDATE usuario SET perfil='ceo' WHERE perfil='gestor'")).rowcount
            print(f"SQLite: {n} usuário(s) gestor -> ceo")
        else:
            ja_tem_ceo = con.execute(text(
                "SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = 'perfilusuario' AND e.enumlabel = 'ceo'"
            )).first()
            if ja_tem_ceo:
                print("Postgres: rótulo 'ceo' já existe no tipo")
            else:
                con.execute(text("ALTER TYPE perfilusuario RENAME VALUE 'gestor' TO 'ceo'"))
                print("Postgres: rótulo 'gestor' renomeado para 'ceo' (linhas acompanham)")
            con.execute(text("ALTER TYPE perfilusuario ADD VALUE IF NOT EXISTS 'rh'"))
            print("Postgres: rótulo 'rh' garantido")

        n = con.execute(text(
            "UPDATE usuario SET email='ceo@psa.com', nome='CEO Demo' WHERE email='gestor@psa.com'"
        )).rowcount
        print(f"conta de demonstração renomeada: {n} linha(s)")

    # o usuário do RH entra pelo ORM para gerar o hash do jeito oficial
    from sqlmodel import Session, select

    from .models import PerfilUsuario, Usuario
    from .services.auth import gerar_hash

    with Session(engine) as s:
        if s.exec(select(Usuario).where(Usuario.email == "rh@psa.com")).first():
            print("rh@psa.com já existe")
        else:
            s.add(Usuario(email="rh@psa.com", nome="RH Demo",
                          perfil=PerfilUsuario.rh, senha_hash=gerar_hash("psa123")))
            s.commit()
            print("rh@psa.com criado (senha psa123)")

        perfis = {}
        for u in s.exec(select(Usuario)).all():
            perfis[u.perfil.value] = perfis.get(u.perfil.value, 0) + 1
        print("perfis no banco:", perfis)


if __name__ == "__main__":
    migrar()
    print("Migração concluída.")
