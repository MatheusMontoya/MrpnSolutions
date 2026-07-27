"""Pendências/ocorrências de projeto: registro, responsável e acompanhamento."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Pendencia,
    PrioridadePendencia,
    Projeto,
    StatusPendencia,
)

router = APIRouter(prefix="/api/pendencias", tags=["Pendências"])


class PendenciaCreate(BaseModel):
    projeto_id: int
    fase_id: int | None = None
    titulo: str
    descricao: str = ""
    responsavel_id: int | None = None
    prioridade: PrioridadePendencia = PrioridadePendencia.media


class PendenciaUpdate(BaseModel):
    titulo: str | None = None
    descricao: str | None = None
    responsavel_id: int | None = None
    prioridade: PrioridadePendencia | None = None
    status: StatusPendencia | None = None
    fase_id: int | None = None


def serializar(p: Pendencia) -> dict:
    return {
        "id": p.id,
        "projeto_id": p.projeto_id,
        "projeto": p.projeto.nome if p.projeto else "",
        "fase_id": p.fase_id,
        "fase": p.fase.nome if p.fase else None,
        "titulo": p.titulo,
        "descricao": p.descricao,
        "responsavel_id": p.responsavel_id,
        "responsavel": p.responsavel.nome if p.responsavel else None,
        "prioridade": p.prioridade,
        "status": p.status,
        "criada_em": p.criada_em.isoformat(),
        "resolvida_em": p.resolvida_em.isoformat() if p.resolvida_em else None,
    }


@router.get("")
def listar_pendencias(
    projeto_id: int | None = Query(default=None),
    status: StatusPendencia | None = Query(default=None),
    responsavel_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(Pendencia).order_by(Pendencia.status, Pendencia.prioridade.desc(), Pendencia.criada_em.desc())
    if projeto_id is not None:
        q = q.where(Pendencia.projeto_id == projeto_id)
    if status is not None:
        q = q.where(Pendencia.status == status)
    if responsavel_id is not None:
        q = q.where(Pendencia.responsavel_id == responsavel_id)
    return [serializar(p) for p in session.exec(q).all()]


@router.post("", status_code=201)
def criar_pendencia(dados: PendenciaCreate, session: Session = Depends(get_session)):
    if not session.get(Projeto, dados.projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    p = Pendencia(**dados.model_dump(), criada_em=date.today())
    session.add(p)
    session.commit()
    session.refresh(p)
    return serializar(p)


@router.patch("/{pendencia_id}")
def atualizar_pendencia(pendencia_id: int, dados: PendenciaUpdate, session: Session = Depends(get_session)):
    p = session.get(Pendencia, pendencia_id)
    if not p:
        raise HTTPException(404, "Pendência não encontrada")
    payload = dados.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        setattr(p, campo, valor)
    if payload.get("status") == StatusPendencia.resolvida and p.resolvida_em is None:
        p.resolvida_em = date.today()
    if payload.get("status") in (StatusPendencia.aberta, StatusPendencia.em_andamento):
        p.resolvida_em = None
    session.add(p)
    session.commit()
    session.refresh(p)
    return serializar(p)


@router.delete("/{pendencia_id}", status_code=204)
def remover_pendencia(pendencia_id: int, session: Session = Depends(get_session)):
    p = session.get(Pendencia, pendencia_id)
    if not p:
        raise HTTPException(404, "Pendência não encontrada")
    session.delete(p)
    session.commit()
