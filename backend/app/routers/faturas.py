"""Cronograma de faturamento e contas a receber.

O plano de faturas nasce da receita mensal PREVISTA do projeto (motor de
receita) — uma fatura por mês de competência. Fluxo: prevista → emitida
(vencimento +30 dias) → recebida. Emitidas em aberto = contas a receber.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import Alocacao, Fatura, Projeto, StatusFatura
from ..services.receita import receita_mensal_prevista

router = APIRouter(prefix="/api", tags=["Faturamento"])

PRAZO_VENCIMENTO_DIAS = 30


class FaturaUpdate(BaseModel):
    status: StatusFatura
    numero: str = ""


def serializar(f: Fatura, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    vencida = (
        f.status == StatusFatura.emitida
        and f.data_vencimento is not None
        and f.data_vencimento < hoje
    )
    return {
        "id": f.id,
        "projeto_id": f.projeto_id,
        "projeto": f.projeto.nome if f.projeto else "",
        "cliente": f.projeto.cliente.nome if f.projeto and f.projeto.cliente else "",
        "competencia": f.competencia.isoformat(),
        "valor": f.valor,
        "status": f.status,
        "numero": f.numero,
        "data_emissao": f.data_emissao.isoformat() if f.data_emissao else None,
        "data_vencimento": f.data_vencimento.isoformat() if f.data_vencimento else None,
        "data_recebimento": f.data_recebimento.isoformat() if f.data_recebimento else None,
        "vencida": vencida,
        "dias_vencida": (hoje - f.data_vencimento).days if vencida else 0,
    }


@router.get("/faturas")
def listar_faturas(
    projeto_id: int | None = Query(default=None),
    status: StatusFatura | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(Fatura).order_by(Fatura.competencia)
    if projeto_id is not None:
        q = q.where(Fatura.projeto_id == projeto_id)
    if status is not None:
        q = q.where(Fatura.status == status)
    hoje = date.today()
    faturas = [serializar(f, hoje) for f in session.exec(q).all()]

    total = lambda s: round(sum(f["valor"] for f in faturas if f["status"] == s), 2)  # noqa: E731
    return {
        "faturas": faturas,
        "total_previsto": total("prevista"),
        "total_emitido": total("emitida"),
        "total_recebido": total("recebida"),
        "total_vencido": round(sum(f["valor"] for f in faturas if f["vencida"]), 2),
    }


def gerar_plano_de_faturas(session: Session, projeto: Projeto) -> list[Fatura]:
    """(Re)gera as faturas PREVISTAS do projeto a partir da receita mensal
    prevista. Faturas já emitidas/recebidas são preservadas; os meses delas
    não entram no novo plano."""
    alocacoes = session.exec(
        select(Alocacao).where(Alocacao.fase_id.in_([f.id for f in projeto.fases]))
    ).all() if projeto.fases else []
    receita = receita_mensal_prevista(alocacoes)

    existentes = session.exec(select(Fatura).where(Fatura.projeto_id == projeto.id)).all()
    protegidas = {f.competencia for f in existentes if f.status != StatusFatura.prevista}
    for f in existentes:
        if f.status == StatusFatura.prevista:
            session.delete(f)

    novas = []
    for mes, valor in sorted(receita.items()):
        ano, m = map(int, mes.split("-"))
        competencia = date(ano, m, 1)
        if competencia in protegidas or valor <= 0:
            continue
        fatura = Fatura(projeto_id=projeto.id, competencia=competencia, valor=round(valor, 2))
        session.add(fatura)
        novas.append(fatura)
    session.commit()
    return novas


@router.post("/projetos/{projeto_id}/faturas/gerar", status_code=201)
def gerar_faturas(projeto_id: int, session: Session = Depends(get_session)):
    projeto = session.get(Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    novas = gerar_plano_de_faturas(session, projeto)
    return {"geradas": len(novas), "total": round(sum(f.valor for f in novas), 2)}


@router.patch("/faturas/{fatura_id}")
def atualizar_fatura(fatura_id: int, dados: FaturaUpdate, session: Session = Depends(get_session)):
    f = session.get(Fatura, fatura_id)
    if not f:
        raise HTTPException(404, "Fatura não encontrada")

    hoje = date.today()
    if dados.status == StatusFatura.emitida:
        if f.status != StatusFatura.prevista:
            raise HTTPException(409, "Só faturas previstas podem ser emitidas")
        f.status = StatusFatura.emitida
        f.numero = dados.numero or f.numero
        f.data_emissao = hoje
        f.data_vencimento = hoje + timedelta(days=PRAZO_VENCIMENTO_DIAS)
    elif dados.status == StatusFatura.recebida:
        if f.status != StatusFatura.emitida:
            raise HTTPException(409, "Só faturas emitidas podem ser recebidas")
        f.status = StatusFatura.recebida
        f.data_recebimento = hoje
    elif dados.status == StatusFatura.cancelada:
        if f.status == StatusFatura.recebida:
            raise HTTPException(409, "Fatura recebida não pode ser cancelada")
        f.status = StatusFatura.cancelada
    else:
        raise HTTPException(422, "Transição inválida")

    session.add(f)
    session.commit()
    return serializar(f)
