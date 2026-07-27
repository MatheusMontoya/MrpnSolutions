"""Fila unificada de aprovações do gestor: semanas de apontamento enviadas,
ausências pendentes e despesas pendentes."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Alocacao,
    Apontamento,
    Ausencia,
    Despesa,
    EnvioSemana,
    SolicitacaoAlocacao,
    StatusAprovacao,
    StatusDespesa,
    StatusEnvio,
)
from .ausencias import serializar as serializar_ausencia
from .despesas import serializar as serializar_despesa
from .solicitacoes import serializar as serializar_solicitacao

router = APIRouter(prefix="/api/aprovacoes", tags=["Aprovações"])


class DecisaoEnvio(BaseModel):
    status: StatusEnvio  # aprovada | reprovada
    comentario_gestor: str = ""


def _serializar_envio(session: Session, e: EnvioSemana) -> dict:
    """Envio com o detalhamento do que foi lançado na semana (para o drawer)."""
    dias = [e.semana + timedelta(days=i) for i in range(7)]
    alocacoes = session.exec(
        select(Alocacao).where(Alocacao.consultor_id == e.consultor_id)
    ).all()
    ids = [a.id for a in alocacoes]
    registros = []
    if ids:
        registros = session.exec(
            select(Apontamento).where(
                Apontamento.alocacao_id.in_(ids),
                Apontamento.data >= dias[0],
                Apontamento.data <= dias[-1],
            ).order_by(Apontamento.data)
        ).all()

    detalhes = []
    for ap in registros:
        aloc = ap.alocacao
        fase = aloc.fase if aloc else None
        projeto = fase.projeto if fase else None
        detalhes.append(
            {
                "data": ap.data.isoformat(),
                "horas": ap.horas,
                "descricao": ap.descricao,
                "projeto": projeto.nome if projeto else "",
                "fase": fase.nome if fase else "",
            }
        )

    return {
        "id": e.id,
        "consultor_id": e.consultor_id,
        "consultor": e.consultor.nome if e.consultor else "",
        "semana": e.semana.isoformat(),
        "status": e.status,
        "total_horas": e.total_horas,
        "comentario_gestor": e.comentario_gestor,
        "enviado_em": e.enviado_em.isoformat() if e.enviado_em else None,
        "lancamentos": detalhes,
    }


@router.get("")
def fila_de_aprovacoes(session: Session = Depends(get_session)):
    """Tudo que aguarda decisão do gestor, num payload só."""
    envios = session.exec(
        select(EnvioSemana).where(EnvioSemana.status == StatusEnvio.enviada).order_by(EnvioSemana.semana)
    ).all()
    ausencias = session.exec(
        select(Ausencia).where(Ausencia.status == StatusAprovacao.pendente).order_by(Ausencia.data_inicio)
    ).all()
    despesas = session.exec(
        select(Despesa).where(Despesa.status == StatusDespesa.pendente).order_by(Despesa.data)
    ).all()
    # aprovadas aguardando reembolso também interessam ao gestor
    reembolsos = session.exec(
        select(Despesa).where(Despesa.status == StatusDespesa.aprovada).order_by(Despesa.data)
    ).all()
    solicitacoes = session.exec(
        select(SolicitacaoAlocacao)
        .where(SolicitacaoAlocacao.status == StatusAprovacao.pendente)
        .order_by(SolicitacaoAlocacao.criada_em)
    ).all()

    return {
        "envios": [_serializar_envio(session, e) for e in envios],
        "ausencias": [serializar_ausencia(a) for a in ausencias],
        "despesas": [serializar_despesa(d) for d in despesas],
        "reembolsos_pendentes": [serializar_despesa(d) for d in reembolsos],
        "solicitacoes_alocacao": [serializar_solicitacao(session, s) for s in solicitacoes],
        "total_pendente": len(envios) + len(ausencias) + len(despesas) + len(solicitacoes),
    }


@router.patch("/envios/{envio_id}/decidir")
def decidir_envio(envio_id: int, dados: DecisaoEnvio, session: Session = Depends(get_session)):
    e = session.get(EnvioSemana, envio_id)
    if not e:
        raise HTTPException(404, "Envio não encontrado")
    if e.status != StatusEnvio.enviada:
        raise HTTPException(409, "Envio já decidido")
    if dados.status not in (StatusEnvio.aprovada, StatusEnvio.reprovada):
        raise HTTPException(422, "Decisão deve ser aprovada ou reprovada")
    if dados.status == StatusEnvio.reprovada and not dados.comentario_gestor.strip():
        raise HTTPException(422, "Reprovação exige comentário para o consultor")

    e.status = dados.status
    e.comentario_gestor = dados.comentario_gestor
    e.decidido_em = date.today()
    session.add(e)
    session.commit()
    return {"id": e.id, "status": e.status, "comentario_gestor": e.comentario_gestor}
