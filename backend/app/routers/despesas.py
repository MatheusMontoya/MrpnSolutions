"""Despesas de projeto: lançamento pelo consultor (inclusive por km),
aprovação e reembolso pelo gestor."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import consultor_do_filtro, eh_gestao, exigir_gestao, usuario_atual
from ..models import (
    Configuracao,
    Consultor,
    Despesa,
    Projeto,
    StatusDespesa,
    TipoDespesa,
)

router = APIRouter(prefix="/api/despesas", tags=["Despesas"])


class DespesaCreate(BaseModel):
    consultor_id: int
    projeto_id: int
    data: date
    tipo: TipoDespesa
    descricao: str = ""
    valor: float | None = None  # obrigatório exceto quilometragem
    km: float | None = None  # obrigatório para quilometragem


class DecisaoDespesa(BaseModel):
    status: StatusDespesa  # aprovada | recusada | reembolsada
    comentario_gestor: str = ""


def serializar(d: Despesa) -> dict:
    return {
        "id": d.id,
        "consultor_id": d.consultor_id,
        "consultor": d.consultor.nome if d.consultor else "",
        "projeto_id": d.projeto_id,
        "projeto": d.projeto.nome if d.projeto else "",
        "data": d.data.isoformat(),
        "tipo": d.tipo,
        "descricao": d.descricao,
        "valor": d.valor,
        "km": d.km,
        "status": d.status,
        "comentario_gestor": d.comentario_gestor,
    }


@router.get("")
def listar_despesas(
    request: Request,
    consultor_id: int | None = Query(default=None),
    projeto_id: int | None = Query(default=None),
    status: StatusDespesa | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(Despesa).order_by(Despesa.data.desc(), Despesa.id.desc())
    consultor_id = consultor_do_filtro(request, consultor_id)
    if consultor_id is not None:
        q = q.where(Despesa.consultor_id == consultor_id)
    if projeto_id is not None:
        q = q.where(Despesa.projeto_id == projeto_id)
    if status is not None:
        q = q.where(Despesa.status == status)
    return [serializar(d) for d in session.exec(q).all()]


@router.post("", status_code=201)
def lancar_despesa(request: Request, dados: DespesaCreate, session: Session = Depends(get_session)):
    dono = consultor_do_filtro(request, dados.consultor_id)
    if dono != dados.consultor_id:
        # consultor lançando em nome de outro: o dono correto prevalece
        dados.consultor_id = dono
    if not session.get(Consultor, dados.consultor_id):
        raise HTTPException(404, "Consultor não encontrado")
    if not session.get(Projeto, dados.projeto_id):
        raise HTTPException(404, "Projeto não encontrado")

    valor = dados.valor
    if dados.tipo == TipoDespesa.quilometragem:
        if not dados.km or dados.km <= 0:
            raise HTTPException(422, "Informe os km rodados para despesa de quilometragem")
        cfg = session.exec(select(Configuracao)).first()
        taxa_km = cfg.taxa_km if cfg else 1.20
        valor = round(dados.km * taxa_km, 2)
    elif valor is None or valor <= 0:
        raise HTTPException(422, "Informe o valor da despesa")

    d = Despesa(
        consultor_id=dados.consultor_id,
        projeto_id=dados.projeto_id,
        data=dados.data,
        tipo=dados.tipo,
        descricao=dados.descricao,
        valor=valor,
        km=dados.km if dados.tipo == TipoDespesa.quilometragem else None,
    )
    session.add(d)
    session.commit()
    session.refresh(d)
    return serializar(d)


@router.patch("/{despesa_id}/decidir", dependencies=[Depends(exigir_gestao)])
def decidir_despesa(despesa_id: int, dados: DecisaoDespesa, session: Session = Depends(get_session)):
    d = session.get(Despesa, despesa_id)
    if not d:
        raise HTTPException(404, "Despesa não encontrada")
    if dados.status == StatusDespesa.pendente:
        raise HTTPException(422, "Decisão deve ser aprovada, recusada ou reembolsada")
    if dados.status == StatusDespesa.reembolsada and d.status != StatusDespesa.aprovada:
        raise HTTPException(409, "Só é possível reembolsar despesa já aprovada")
    d.status = dados.status
    d.comentario_gestor = dados.comentario_gestor
    session.add(d)
    session.commit()
    return serializar(d)


@router.delete("/{despesa_id}", status_code=204)
def remover_despesa(despesa_id: int, request: Request, session: Session = Depends(get_session)):
    """Consultor remove a própria despesa enquanto pendente."""
    d = session.get(Despesa, despesa_id)
    if not d:
        raise HTTPException(404, "Despesa não encontrada")
    if not eh_gestao(usuario_atual(request)) and d.consultor_id != usuario_atual(request).get("consultor_id"):
        raise HTTPException(403, "Você só pode remover os seus próprios registros")
    if d.status != StatusDespesa.pendente:
        raise HTTPException(409, "Só é possível remover despesas pendentes")
    session.delete(d)
    session.commit()
