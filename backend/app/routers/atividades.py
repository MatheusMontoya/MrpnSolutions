"""Atividades/entregáveis por fase e itens do Quality Gate."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..database import get_session
from ..models import Atividade, Fase, ItemGate, StatusAtividade, StatusGate

router = APIRouter(prefix="/api", tags=["Atividades e Quality Gate"])


class AtividadeCreate(BaseModel):
    fase_id: int
    titulo: str
    responsavel_id: int | None = None
    data_prevista: date | None = None


class AtividadeUpdate(BaseModel):
    titulo: str | None = None
    responsavel_id: int | None = None
    data_prevista: date | None = None
    status: StatusAtividade | None = None
    ordem: int | None = None


class ItemGateUpdate(BaseModel):
    status: StatusGate | None = None
    plano_acao: str | None = None
    responsavel: str | None = None


def _serializar_atividade(a: Atividade) -> dict:
    return {
        "id": a.id,
        "fase_id": a.fase_id,
        "titulo": a.titulo,
        "ordem": a.ordem,
        "responsavel_id": a.responsavel_id,
        "responsavel": a.responsavel.nome if a.responsavel else None,
        "data_prevista": a.data_prevista.isoformat() if a.data_prevista else None,
        "status": a.status,
    }


@router.post("/atividades", status_code=201)
def criar_atividade(dados: AtividadeCreate, session: Session = Depends(get_session)):
    fase = session.get(Fase, dados.fase_id)
    if not fase:
        raise HTTPException(404, "Fase não encontrada")
    ordem = max((x.ordem for x in fase.atividades), default=-1) + 1
    a = Atividade(**dados.model_dump(), ordem=ordem)
    session.add(a)
    session.commit()
    session.refresh(a)
    return _serializar_atividade(a)


@router.patch("/atividades/{atividade_id}")
def atualizar_atividade(atividade_id: int, dados: AtividadeUpdate, session: Session = Depends(get_session)):
    a = session.get(Atividade, atividade_id)
    if not a:
        raise HTTPException(404, "Atividade não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(a, campo, valor)
    session.add(a)
    session.commit()
    session.refresh(a)
    return _serializar_atividade(a)


@router.delete("/atividades/{atividade_id}", status_code=204)
def remover_atividade(atividade_id: int, session: Session = Depends(get_session)):
    a = session.get(Atividade, atividade_id)
    if not a:
        raise HTTPException(404, "Atividade não encontrada")
    session.delete(a)
    session.commit()


@router.patch("/gates/{item_id}")
def atualizar_item_gate(item_id: int, dados: ItemGateUpdate, session: Session = Depends(get_session)):
    item = session.get(ItemGate, item_id)
    if not item:
        raise HTTPException(404, "Item de gate não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)
    session.add(item)
    session.commit()
    return {
        "id": item.id,
        "fase_id": item.fase_id,
        "codigo": item.codigo,
        "status": item.status,
        "plano_acao": item.plano_acao,
        "responsavel": item.responsavel,
    }


def resumo_gate(fase: Fase) -> dict:
    """Resumo semáforo do gate de uma fase (usado no detalhe do projeto)."""
    itens = fase.itens_gate
    contagem = {"verde": 0, "amarelo": 0, "vermelho": 0, "nao_verificado": 0}
    for i in itens:
        contagem[i.status.value if hasattr(i.status, "value") else str(i.status)] += 1
    total = len(itens)
    return {
        "total": total,
        **contagem,
        "aprovado": total > 0 and contagem["verde"] == total,
    }
