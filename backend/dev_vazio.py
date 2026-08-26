"""Sobe o RunRate contra um banco VAZIO, para conferir o primeiro uso.

Existe porque o dashboard, o roteiro de primeiros passos e os estados vazios só
aparecem quando não há dado nenhum — e o psa.db local está cheio de demonstração.
Cria um SQLite à parte (psa_vazio.db) com um único usuário CEO:

    python dev_vazio.py            # http://127.0.0.1:8001

    e-mail: ceo@local   senha: local123

Nunca encosta no psa.db nem em produção: o banco é outro arquivo e o comando
não lê DATABASE_URL do ambiente.
"""
import os
from pathlib import Path

BANCO = Path(__file__).parent / "psa_vazio.db"
os.environ["DATABASE_URL"] = f"sqlite:///{BANCO.as_posix()}"
os.environ["RUNRATE_SEM_DEMO"] = "1"  # sem os 3 projetos fictícios e os 8 logins psa123
os.environ.setdefault("RUNRATE_PBKDF2_ITER", "10000")  # login rápido no desenvolvimento

from sqlmodel import Session, select  # noqa: E402

from app.database import criar_tabelas, engine  # noqa: E402
from app.models import PerfilUsuario, Usuario  # noqa: E402
from app.services.auth import gerar_hash  # noqa: E402
from app.services.projetos import criar_modelo_padrao  # noqa: E402


def preparar() -> None:
    criar_tabelas()
    with Session(engine) as s:
        if not s.exec(select(Usuario)).first():
            s.add(Usuario(
                email="ceo@local", nome="CEO Local", perfil=PerfilUsuario.ceo,
                senha_hash=gerar_hash("local123"),
            ))
            criar_modelo_padrao(s)
            s.commit()
            print("Banco vazio criado com um CEO (ceo@local / local123).")


if __name__ == "__main__":
    import uvicorn

    preparar()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001)
