"""Ausências (férias/folga/afastamento): solicitação do consultor e decisão do
gestor. Ausência aprovada reduz a capacidade no motor de utilização."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import consultor_do_filtro, eh_gestao, exigir_gestao, usuario_atual
from ..models import Ausencia, Consultor, StatusAprovacao, TipoAusencia

router = APIRouter(prefix="/api/ausencias", tags=["Ausências"])


class AusenciaCreate(BaseModel):
    consultor_id: int
    tipo: TipoAusencia
    data_inicio: date
    data_fim: date
    motivo: str = ""


class DecisaoAusencia(BaseModel):
    status: StatusAprovacao  # aprovada | recusada
    comentario_gestor: str = ""


def serializar(a: Ausencia) -> dict:
    return {
        "id": a.id,
        "consultor_id": a.consultor_id,
        "consultor": a.consultor.nome if a.consultor else "",
        "tipo": a.tipo,
        "data_inicio": a.data_inicio.isoformat(),
        "data_fim": a.data_fim.isoformat(),
        "motivo": a.motivo,
        "status": a.status,
        "comentario_gestor": a.comentario_gestor,
    }


@router.get("")
def listar_ausencias(
    request: Request,
    consultor_id: int | None = Query(default=None),
    status: StatusAprovacao | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(Ausencia).order_by(Ausencia.data_inicio.desc())
    consultor_id = consultor_do_filtro(request, consultor_id)
    if consultor_id is not None:
        q = q.where(Ausencia.consultor_id == consultor_id)
    if status is not None:
        q = q.where(Ausencia.status == status)
    return [serializar(a) for a in session.exec(q).all()]


@router.post("", status_code=201)
def solicitar_ausencia(request: Request, dados: AusenciaCreate, session: Session = Depends(get_session)):
    dono = consultor_do_filtro(request, dados.consultor_id)
    if dono != dados.consultor_id:
        # consultor lançando em nome de outro: o dono correto prevalece
        dados.consultor_id = dono
    if not session.get(Consultor, dados.consultor_id):
        raise HTTPException(404, "Consultor não encontrado")
    if dados.data_fim < dados.data_inicio:
        raise HTTPException(422, "data_fim anterior a data_inicio")
    a = Ausencia(**dados.model_dump())
    session.add(a)
    session.commit()
    session.refresh(a)
    return serializar(a)


@router.patch("/{ausencia_id}/decidir", dependencies=[Depends(exigir_gestao)])
def decidir_ausencia(ausencia_id: int, dados: DecisaoAusencia, session: Session = Depends(get_session)):
    a = session.get(Ausencia, ausencia_id)
    if not a:
        raise HTTPException(404, "Ausência não encontrada")
    if dados.status == StatusAprovacao.pendente:
        raise HTTPException(422, "Decisão deve ser aprovada ou recusada")
    a.status = dados.status
    a.comentario_gestor = dados.comentario_gestor
    session.add(a)
    session.commit()
    return serializar(a)


@router.delete("/{ausencia_id}", status_code=204)
def cancelar_ausencia(ausencia_id: int, request: Request, session: Session = Depends(get_session)):
    """Consultor cancela a própria solicitação enquanto pendente."""
    a = session.get(Ausencia, ausencia_id)
    if not a:
        raise HTTPException(404, "Ausência não encontrada")
    if not eh_gestao(usuario_atual(request)) and a.consultor_id != usuario_atual(request).get("consultor_id"):
        raise HTTPException(403, "Você só pode remover os seus próprios registros")
    if a.status != StatusAprovacao.pendente:
        raise HTTPException(409, "Só é possível cancelar solicitações pendentes")
    session.delete(a)
    session.commit()
