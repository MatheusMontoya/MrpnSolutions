"""Contratos firmados: vigência, situação e relatório de renovação."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import Cliente, Contrato, StatusContrato

router = APIRouter(prefix="/api/contratos", tags=["Contratos"])

JANELA_RENOVACAO_DIAS = 60


class ContratoCreate(BaseModel):
    cliente_id: int
    nome: str
    data_inicio: date
    data_fim: date
    valor: float = 0.0
    observacoes: str = ""


class ContratoUpdate(BaseModel):
    nome: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    valor: float | None = None
    status: StatusContrato | None = None
    observacoes: str | None = None


def serializar(c: Contrato, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    a_renovar = (
        c.status == StatusContrato.vigente
        and hoje <= c.data_fim <= hoje + timedelta(days=JANELA_RENOVACAO_DIAS)
    )
    vencido = c.status == StatusContrato.vigente and c.data_fim < hoje
    return {
        "id": c.id,
        "cliente_id": c.cliente_id,
        "cliente": c.cliente.nome if c.cliente else "",
        "nome": c.nome,
        "data_inicio": c.data_inicio.isoformat(),
        "data_fim": c.data_fim.isoformat(),
        "valor": c.valor,
        "status": c.status,
        "observacoes": c.observacoes,
        "a_renovar": a_renovar,
        "vencido": vencido,
        "dias_para_fim": (c.data_fim - hoje).days,
    }


@router.get("")
def listar_contratos(session: Session = Depends(get_session)):
    hoje = date.today()
    contratos = [serializar(c, hoje) for c in session.exec(select(Contrato).order_by(Contrato.data_fim)).all()]
    return {
        "contratos": contratos,
        "a_renovar": sum(1 for c in contratos if c["a_renovar"]),
        "vencidos": sum(1 for c in contratos if c["vencido"]),
    }


@router.post("", status_code=201)
def criar_contrato(dados: ContratoCreate, session: Session = Depends(get_session)):
    if not session.get(Cliente, dados.cliente_id):
        raise HTTPException(404, "Cliente não encontrado")
    if dados.data_fim < dados.data_inicio:
        raise HTTPException(422, "data_fim anterior a data_inicio")
    c = Contrato(**dados.model_dump())
    session.add(c)
    session.commit()
    session.refresh(c)
    return serializar(c)


@router.patch("/{contrato_id}")
def atualizar_contrato(contrato_id: int, dados: ContratoUpdate, session: Session = Depends(get_session)):
    c = session.get(Contrato, contrato_id)
    if not c:
        raise HTTPException(404, "Contrato não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(c, campo, valor)
    session.add(c)
    session.commit()
    session.refresh(c)
    return serializar(c)


@router.delete("/{contrato_id}", status_code=204)
def remover_contrato(contrato_id: int, session: Session = Depends(get_session)):
    c = session.get(Contrato, contrato_id)
    if not c:
        raise HTTPException(404, "Contrato não encontrado")
    session.delete(c)
    session.commit()
