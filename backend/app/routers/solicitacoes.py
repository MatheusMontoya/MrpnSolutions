"""Solicitações de alocação: pedido → fila de aprovações → Alocacao.

O conflito é recalculado a cada consulta (não é snapshot): se o cenário do
consultor mudou entre o pedido e a decisão, o gestor vê a foto atual.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Alocacao,
    Consultor,
    Fase,
    SolicitacaoAlocacao,
    StatusAprovacao,
)
from ..services.alocacoes import detectar_conflitos

router = APIRouter(prefix="/api/solicitacoes-alocacao", tags=["Solicitações de alocação"])


class SolicitacaoCreate(BaseModel):
    consultor_id: int
    fase_id: int
    data_inicio: date
    data_fim: date
    horas_semana: float
    taxa_hora_venda: float | None = None
    justificativa: str = ""
    solicitante: str = ""


class PreviaConflitos(BaseModel):
    consultor_id: int
    data_inicio: date
    data_fim: date
    horas_semana: float


class Decisao(BaseModel):
    status: StatusAprovacao  # aprovada | recusada
    comentario_gestor: str = ""


def serializar(session: Session, s: SolicitacaoAlocacao) -> dict:
    fase = s.fase
    projeto = fase.projeto if fase else None
    pendente = s.status == StatusAprovacao.pendente
    return {
        "id": s.id,
        "consultor_id": s.consultor_id,
        "consultor": s.consultor.nome if s.consultor else "",
        "senioridade": s.consultor.senioridade if s.consultor else None,
        "fase_id": s.fase_id,
        "fase": fase.nome if fase else "",
        "projeto_id": projeto.id if projeto else None,
        "projeto": projeto.nome if projeto else "",
        "data_inicio": s.data_inicio.isoformat(),
        "data_fim": s.data_fim.isoformat(),
        "horas_semana": s.horas_semana,
        "taxa_hora_venda": s.taxa_hora_venda,
        "justificativa": s.justificativa,
        "solicitante": s.solicitante,
        "status": s.status,
        "comentario_gestor": s.comentario_gestor,
        "criada_em": s.criada_em.isoformat(),
        "decidida_em": s.decidida_em.isoformat() if s.decidida_em else None,
        # conflitos só interessam enquanto a decisão está em aberto
        "conflitos": detectar_conflitos(
            session, s.consultor_id, s.data_inicio, s.data_fim, s.horas_semana
        ) if pendente else None,
    }


@router.post("/previa-conflitos")
def previa_conflitos(dados: PreviaConflitos, session: Session = Depends(get_session)):
    """Prévia para o formulário: mostra o conflito ANTES de submeter o pedido."""
    if not session.get(Consultor, dados.consultor_id):
        raise HTTPException(404, "Consultor não encontrado")
    return detectar_conflitos(
        session, dados.consultor_id, dados.data_inicio, dados.data_fim, dados.horas_semana
    )


@router.post("", status_code=201)
def criar_solicitacao(dados: SolicitacaoCreate, session: Session = Depends(get_session)):
    if not session.get(Consultor, dados.consultor_id):
        raise HTTPException(404, "Consultor não encontrado")
    if not session.get(Fase, dados.fase_id):
        raise HTTPException(404, "Fase não encontrada")
    if dados.data_fim < dados.data_inicio:
        raise HTTPException(422, "data_fim deve ser >= data_inicio")
    if dados.horas_semana <= 0:
        raise HTTPException(422, "horas_semana deve ser positivo")

    s = SolicitacaoAlocacao(**dados.model_dump(), criada_em=date.today())
    session.add(s)
    session.commit()
    session.refresh(s)
    return serializar(session, s)


@router.get("")
def listar_solicitacoes(
    status: StatusAprovacao | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(SolicitacaoAlocacao).order_by(SolicitacaoAlocacao.criada_em)
    if status is not None:
        q = q.where(SolicitacaoAlocacao.status == status)
    return [serializar(session, s) for s in session.exec(q).all()]


@router.patch("/{solicitacao_id}/decidir")
def decidir_solicitacao(solicitacao_id: int, dados: Decisao, session: Session = Depends(get_session)):
    s = session.get(SolicitacaoAlocacao, solicitacao_id)
    if not s:
        raise HTTPException(404, "Solicitação não encontrada")
    if s.status != StatusAprovacao.pendente:
        raise HTTPException(409, "Solicitação já decidida")
    if dados.status not in (StatusAprovacao.aprovada, StatusAprovacao.recusada):
        raise HTTPException(422, "Decisão deve ser aprovada ou recusada")
    if dados.status == StatusAprovacao.recusada and not dados.comentario_gestor.strip():
        raise HTTPException(422, "Recusa exige comentário para o solicitante")

    if dados.status == StatusAprovacao.aprovada:
        taxa = s.taxa_hora_venda
        if taxa is None:
            taxa = s.consultor.taxa_hora_venda if s.consultor else 0.0
        alocacao = Alocacao(
            consultor_id=s.consultor_id,
            fase_id=s.fase_id,
            data_inicio=s.data_inicio,
            data_fim=s.data_fim,
            horas_semana=s.horas_semana,
            taxa_hora_venda=taxa,
        )
        session.add(alocacao)
        session.flush()
        s.alocacao_id = alocacao.id

    s.status = dados.status
    s.comentario_gestor = dados.comentario_gestor
    s.decidida_em = date.today()
    session.add(s)
    session.commit()
    session.refresh(s)
    return serializar(session, s)
