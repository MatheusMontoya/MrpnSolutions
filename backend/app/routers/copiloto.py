"""Copiloto IA: insights determinísticos sempre; IA generativa quando a chave
da Anthropic estiver configurada (Configurações → Copiloto IA)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import Configuracao
from ..services import copiloto

router = APIRouter(prefix="/api/copiloto", tags=["Copiloto IA"])


class Pergunta(BaseModel):
    pergunta: str


@router.get("/status")
def status(session: Session = Depends(get_session)):
    cfg = session.exec(select(Configuracao)).first()
    ia_ativa = bool(cfg and cfg.anthropic_api_key.strip())
    return {"ia_ativa": ia_ativa, "modelo": cfg.modelo_ia if cfg else ""}


@router.get("/insights")
def insights(session: Session = Depends(get_session)):
    lista = copiloto.gerar_insights(session)
    return {
        "insights": lista,
        "total": len(lista),
        "criticos": sum(1 for i in lista if i["severidade"] == "critico"),
    }


@router.post("/perguntar")
def perguntar(corpo: Pergunta, session: Session = Depends(get_session)):
    return copiloto.perguntar(session, corpo.pergunta)
