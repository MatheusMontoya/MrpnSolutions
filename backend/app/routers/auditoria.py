"""Trilha de auditoria — leitura (gestor). A escrita é feita pelo middleware
em main.py: toda mutação /api/* (POST/PATCH/DELETE) vira um evento."""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import EventoAuditoria
from ..seguranca import exigir_ceo

router = APIRouter(
    prefix="/api/auditoria",
    tags=["Auditoria"],
    dependencies=[Depends(exigir_ceo)],
)


@router.get("")
def listar_eventos(
    limite: int = Query(default=100, ge=1, le=500),
    usuario: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(EventoAuditoria).order_by(EventoAuditoria.id.desc()).limit(limite)  # type: ignore[attr-defined]
    if usuario:
        q = q.where(EventoAuditoria.usuario == usuario)
    eventos = session.exec(q).all()
    return [{
        "id": e.id,
        "quando": e.quando.isoformat(timespec="seconds"),
        "usuario": e.usuario,
        "perfil": e.perfil,
        "metodo": e.metodo,
        "caminho": e.caminho,
        "status": e.status,
        "detalhe": e.detalhe,
    } for e in eventos]
