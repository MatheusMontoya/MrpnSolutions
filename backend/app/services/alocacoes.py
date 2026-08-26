"""Detecção de conflitos de alocação — usada na solicitação e na fila.

Um pedido conflita quando, em alguma semana do período:
- a soma das alocações existentes + o pedido ultrapassa a capacidade REAL
  da semana (jornada − ausências aprovadas), ou
- o consultor tem ausência aprovada cobrindo dias úteis do pedido.

Tudo deriva do motor (`services/receita.py`) — mesma régua do heatmap.
"""
from datetime import date, timedelta

from sqlmodel import Session, select

from ..models import HORAS_SEMANA_PADRAO, Alocacao, Ausencia, StatusAprovacao
from .receita import (
    capacidade_na_semana,
    dias_uteis,
    horas_alocadas_na_semana,
    horas_ausentes_na_semana,
    segunda_da_semana,
)


class _Pedido:
    """Duck-type mínimo para reusar horas_alocadas_na_semana no pedido."""

    def __init__(self, data_inicio: date, data_fim: date, horas_semana: float):
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.horas_semana = horas_semana


def detectar_conflitos(
    session: Session,
    consultor_id: int,
    data_inicio: date,
    data_fim: date,
    horas_semana: float,
    ignorar_alocacao_id: int | None = None,
) -> dict:
    """Avalia o pedido semana a semana contra as alocações e ausências do
    consultor. Retorna {conflito, semanas: [...], sobreposicoes: [...],
    ausencias: [...]} — as listas explicam o porquê para o gestor decidir."""
    alocacoes = [
        a for a in session.exec(
            select(Alocacao).where(Alocacao.consultor_id == consultor_id)
        ).all()
        if a.id != ignorar_alocacao_id
        and a.data_inicio <= data_fim and a.data_fim >= data_inicio
    ]
    ausencias = [
        x for x in session.exec(
            select(Ausencia).where(
                Ausencia.consultor_id == consultor_id,
                Ausencia.status == StatusAprovacao.aprovada,
            )
        ).all()
        if x.data_inicio <= data_fim and x.data_fim >= data_inicio
    ]
    pedido = _Pedido(data_inicio, data_fim, horas_semana)

    semanas_conflito = []
    seg = segunda_da_semana(data_inicio)
    while seg <= data_fim:
        horas_pedido = horas_alocadas_na_semana(pedido, seg)
        if horas_pedido > 0:
            existentes = sum(horas_alocadas_na_semana(a, seg) for a in alocacoes)
            capacidade = capacidade_na_semana(ausencias, seg)
            total = existentes + horas_pedido
            if total > capacidade:
                semanas_conflito.append({
                    "semana": seg.isoformat(),
                    "horas_existentes": round(existentes, 1),
                    "horas_pedido": round(horas_pedido, 1),
                    "capacidade": round(capacidade, 1),
                    "excesso": round(total - capacidade, 1),
                })
        seg += timedelta(weeks=1)

    sobreposicoes = [{
        "projeto": a.fase.projeto.nome if a.fase and a.fase.projeto else "",
        "fase": a.fase.nome if a.fase else "",
        "horas_semana": a.horas_semana,
        "data_inicio": a.data_inicio.isoformat(),
        "data_fim": a.data_fim.isoformat(),
    } for a in alocacoes]

    ausencias_periodo = [{
        "tipo": x.tipo,
        "data_inicio": x.data_inicio.isoformat(),
        "data_fim": x.data_fim.isoformat(),
        "dias_uteis": dias_uteis(max(x.data_inicio, data_inicio), min(x.data_fim, data_fim)),
    } for x in ausencias]

    return {
        "conflito": bool(semanas_conflito or ausencias_periodo),
        "semanas": semanas_conflito,
        "sobreposicoes": sobreposicoes,
        "ausencias": ausencias_periodo,
    }
