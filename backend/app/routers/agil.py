"""Modo ágil/híbrido (estilo J.Agile): sprints + backlog + kanban POR CIMA
do cronograma Activate.

O waterfall continua dono do prazo e da receita (fases, gates, cascata); a
sprint organiza a execução: atividades saem do backlog (todas as entregas
das fases) para a sprint, andam no kanban pelo status que já existe e, no
encerramento, o que não concluiu volta ao backlog (carry-over medido).
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Apontamento,
    Atividade,
    Projeto,
    Sprint,
    StatusAtividade,
    StatusSprint,
)

router = APIRouter(prefix="/api", tags=["Ágil"])


class SprintCreate(BaseModel):
    nome: str = ""
    meta: str = ""
    data_inicio: date
    data_fim: date


class SprintUpdate(BaseModel):
    nome: str | None = None
    meta: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None


class MoverAtividade(BaseModel):
    sprint_id: int | None  # None = devolver ao backlog


def _horas_no_periodo(session: Session, projeto: Projeto, inicio: date, fim: date) -> float:
    ids = [a.id for f in projeto.fases for a in f.alocacoes]
    if not ids:
        return 0.0
    apontamentos = session.exec(
        select(Apontamento).where(
            Apontamento.alocacao_id.in_(ids),
            Apontamento.data >= inicio,
            Apontamento.data <= fim,
        )
    ).all()
    return round(sum(ap.horas for ap in apontamentos), 1)


def _ser_atividade(a: Atividade) -> dict:
    return {
        "id": a.id,
        "titulo": a.titulo,
        "status": a.status,
        "fase": a.fase.nome if a.fase else "",
        "fase_id": a.fase_id,
        "responsavel": a.responsavel.nome if a.responsavel else None,
        "data_prevista": a.data_prevista.isoformat() if a.data_prevista else None,
        "sprint_id": a.sprint_id,
    }


def _ser_sprint(session: Session, s: Sprint) -> dict:
    atividades = [_ser_atividade(a) for a in s.atividades]
    total = len(atividades)
    feitas = sum(1 for a in atividades if a["status"] == "concluida")
    return {
        "id": s.id,
        "numero": s.numero,
        "nome": s.nome or f"Sprint {s.numero}",
        "meta": s.meta,
        "data_inicio": s.data_inicio.isoformat(),
        "data_fim": s.data_fim.isoformat(),
        "status": s.status,
        "encerrada_em": s.encerrada_em.isoformat() if s.encerrada_em else None,
        "carry_over": s.carry_over,
        "total": total,
        "concluidas": feitas,
        "progresso": round(feitas / total, 4) if total else 0.0,
        "horas_no_periodo": _horas_no_periodo(session, s.projeto, s.data_inicio, s.data_fim)
        if s.projeto else 0.0,
        "atividades": atividades,
    }


@router.get("/projetos/{projeto_id}/agil")
def quadro_agil(projeto_id: int, session: Session = Depends(get_session)):
    """Estado completo do modo ágil: sprints (com kanban) + backlog por fase."""
    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")

    sprints = session.exec(
        select(Sprint).where(Sprint.projeto_id == projeto_id).order_by(Sprint.numero)
    ).all()
    backlog = [
        _ser_atividade(a)
        for f in sorted(p.fases, key=lambda x: x.ordem)
        for a in sorted(f.atividades, key=lambda x: x.ordem)
        if a.sprint_id is None and a.status != StatusAtividade.concluida
    ]
    ativa = next((s for s in sprints if s.status == StatusSprint.ativa), None)
    return {
        "projeto_id": p.id,
        "projeto": p.nome,
        "sprints": [_ser_sprint(session, s) for s in sprints],
        "sprint_ativa_id": ativa.id if ativa else None,
        "backlog": backlog,
    }


@router.post("/projetos/{projeto_id}/sprints", status_code=201)
def criar_sprint(projeto_id: int, dados: SprintCreate, session: Session = Depends(get_session)):
    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")
    if dados.data_fim < dados.data_inicio:
        raise HTTPException(422, "data_fim deve ser >= data_inicio")
    numero = max(
        (s.numero for s in session.exec(
            select(Sprint).where(Sprint.projeto_id == projeto_id)
        ).all()),
        default=0,
    ) + 1
    s = Sprint(projeto_id=projeto_id, numero=numero, **dados.model_dump())
    session.add(s)
    session.commit()
    session.refresh(s)
    return _ser_sprint(session, s)


@router.patch("/sprints/{sprint_id}")
def atualizar_sprint(sprint_id: int, dados: SprintUpdate, session: Session = Depends(get_session)):
    s = session.get(Sprint, sprint_id)
    if not s:
        raise HTTPException(404, "Sprint não encontrada")
    if s.status == StatusSprint.encerrada:
        raise HTTPException(409, "Sprint encerrada não pode ser alterada")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(s, campo, valor)
    if s.data_fim < s.data_inicio:
        raise HTTPException(422, "data_fim deve ser >= data_inicio")
    session.add(s)
    session.commit()
    session.refresh(s)
    return _ser_sprint(session, s)


@router.post("/sprints/{sprint_id}/iniciar")
def iniciar_sprint(sprint_id: int, session: Session = Depends(get_session)):
    s = session.get(Sprint, sprint_id)
    if not s:
        raise HTTPException(404, "Sprint não encontrada")
    if s.status != StatusSprint.planejada:
        raise HTTPException(409, "Só sprints planejadas podem ser iniciadas")
    outra = session.exec(
        select(Sprint).where(
            Sprint.projeto_id == s.projeto_id,
            Sprint.status == StatusSprint.ativa,
        )
    ).first()
    if outra:
        raise HTTPException(409, f"A Sprint {outra.numero} ainda está ativa — encerre-a antes")
    s.status = StatusSprint.ativa
    session.add(s)
    session.commit()
    session.refresh(s)
    return _ser_sprint(session, s)


@router.post("/sprints/{sprint_id}/encerrar")
def encerrar_sprint(sprint_id: int, session: Session = Depends(get_session)):
    """Encerra a sprint: o que não concluiu volta ao backlog (carry-over)."""
    s = session.get(Sprint, sprint_id)
    if not s:
        raise HTTPException(404, "Sprint não encontrada")
    if s.status != StatusSprint.ativa:
        raise HTTPException(409, "Só sprints ativas podem ser encerradas")

    devolvidas = 0
    for a in list(s.atividades):
        if a.status != StatusAtividade.concluida:
            a.sprint_id = None
            devolvidas += 1
            session.add(a)
    s.status = StatusSprint.encerrada
    s.encerrada_em = date.today()
    s.carry_over = devolvidas
    session.add(s)
    session.commit()
    session.refresh(s)
    return _ser_sprint(session, s)


@router.patch("/atividades/{atividade_id}/sprint")
def mover_atividade(atividade_id: int, dados: MoverAtividade, session: Session = Depends(get_session)):
    """Puxa a atividade do backlog para a sprint (ou devolve)."""
    a = session.get(Atividade, atividade_id)
    if not a:
        raise HTTPException(404, "Atividade não encontrada")
    if dados.sprint_id is not None:
        s = session.get(Sprint, dados.sprint_id)
        if not s:
            raise HTTPException(404, "Sprint não encontrada")
        if s.status == StatusSprint.encerrada:
            raise HTTPException(409, "Sprint encerrada não recebe atividades")
        projeto_da_fase = a.fase.projeto_id if a.fase else None
        if projeto_da_fase != s.projeto_id:
            raise HTTPException(422, "Atividade e sprint precisam ser do mesmo projeto")
    a.sprint_id = dados.sprint_id
    session.add(a)
    session.commit()
    session.refresh(a)
    return _ser_atividade(a)
