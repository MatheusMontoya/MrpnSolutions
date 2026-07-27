from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..database import get_session
from ..models import Alocacao, Consultor, Fase
from ..services.receita import horas_previstas

router = APIRouter(prefix="/api/alocacoes", tags=["Alocações"])


class AlocacaoCreate(BaseModel):
    consultor_id: int
    fase_id: int
    data_inicio: date | None = None  # default: início previsto da fase
    data_fim: date | None = None  # default: fim previsto da fase
    horas_semana: float
    taxa_hora_venda: float | None = None  # default: taxa do consultor (negociável)


class AlocacaoUpdate(BaseModel):
    data_inicio: date | None = None
    data_fim: date | None = None
    horas_semana: float | None = None
    taxa_hora_venda: float | None = None


def _serializar(a: Alocacao) -> dict:
    horas = horas_previstas(a.data_inicio, a.data_fim, a.horas_semana)
    return {
        "id": a.id,
        "consultor_id": a.consultor_id,
        "fase_id": a.fase_id,
        "data_inicio": a.data_inicio.isoformat(),
        "data_fim": a.data_fim.isoformat(),
        "horas_semana": a.horas_semana,
        "taxa_hora_venda": a.taxa_hora_venda,
        "horas_previstas": round(horas, 2),
        "receita_prevista": round(horas * a.taxa_hora_venda, 2),
    }


@router.post("", status_code=201)
def criar_alocacao(dados: AlocacaoCreate, session: Session = Depends(get_session)):
    consultor = session.get(Consultor, dados.consultor_id)
    if not consultor:
        raise HTTPException(404, "Consultor não encontrado")
    fase = session.get(Fase, dados.fase_id)
    if not fase:
        raise HTTPException(404, "Fase não encontrada")

    a = Alocacao(
        consultor_id=dados.consultor_id,
        fase_id=dados.fase_id,
        data_inicio=dados.data_inicio or fase.data_inicio_prevista,
        data_fim=dados.data_fim or fase.data_fim_prevista,
        horas_semana=dados.horas_semana,
        # taxa negociada por alocação; sem override, herda a taxa do consultor
        taxa_hora_venda=dados.taxa_hora_venda if dados.taxa_hora_venda is not None else consultor.taxa_hora_venda,
    )
    if a.data_fim < a.data_inicio:
        raise HTTPException(422, "data_fim anterior a data_inicio")
    session.add(a)
    session.commit()
    session.refresh(a)
    return _serializar(a)


@router.patch("/{alocacao_id}")
def atualizar_alocacao(alocacao_id: int, dados: AlocacaoUpdate, session: Session = Depends(get_session)):
    a = session.get(Alocacao, alocacao_id)
    if not a:
        raise HTTPException(404, "Alocação não encontrada")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(a, campo, valor)
    if a.data_fim < a.data_inicio:
        raise HTTPException(422, "data_fim anterior a data_inicio")
    session.add(a)
    session.commit()
    session.refresh(a)
    return _serializar(a)


@router.delete("/{alocacao_id}", status_code=204)
def remover_alocacao(alocacao_id: int, session: Session = Depends(get_session)):
    a = session.get(Alocacao, alocacao_id)
    if not a:
        raise HTTPException(404, "Alocação não encontrada")
    session.delete(a)
    session.commit()
