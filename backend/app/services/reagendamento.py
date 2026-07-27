"""Recálculo em cascata quando a data-fim de uma fase muda (atraso/adiantamento).

Determinístico, 100% em código — a futura camada de IA consumirá o diff
produzido aqui, nunca o substituirá.

Regras:
- delta = nova_data_fim - data_fim_prevista atual da fase.
- Fases seguintes do projeto deslocam inteiras (início e fim) pelo delta.
- Alocações da fase alterada têm a data_fim estendida pelo delta.
- Alocações das fases seguintes deslocam inteiras pelo delta.
- Receita mensal prevista do projeto é recomputada; o diff antes→depois
  é sempre calculado antes de aplicar qualquer mudança.
"""
from dataclasses import dataclass, replace
from datetime import date, timedelta

from sqlmodel import Session, select

from ..models import Alocacao, Fase
from .receita import horas_previstas, receita_mensal_prevista


@dataclass(frozen=True)
class AlocacaoSim:
    """Cópia imutável de uma alocação para simulação, no formato que o motor
    de receita espera."""

    id: int
    consultor_id: int
    consultor_nome: str
    fase_id: int
    fase_nome: str
    data_inicio: date
    data_fim: date
    horas_semana: float
    taxa_hora_venda: float


def _snapshot_alocacoes(fases: list[Fase]) -> list[AlocacaoSim]:
    sims = []
    for fase in fases:
        for a in fase.alocacoes:
            sims.append(
                AlocacaoSim(
                    id=a.id,
                    consultor_id=a.consultor_id,
                    consultor_nome=a.consultor.nome if a.consultor else "",
                    fase_id=fase.id,
                    fase_nome=fase.nome,
                    data_inicio=a.data_inicio,
                    data_fim=a.data_fim,
                    horas_semana=a.horas_semana,
                    taxa_hora_venda=a.taxa_hora_venda,
                )
            )
    return sims


def simular_reagendamento(session: Session, fase_id: int, nova_data_fim: date) -> dict:
    """Calcula o plano e o diff antes→depois SEM alterar o banco."""
    fase = session.get(Fase, fase_id)
    if fase is None:
        raise ValueError(f"Fase {fase_id} não encontrada")
    if nova_data_fim < fase.data_inicio_prevista:
        raise ValueError("A nova data-fim não pode ser anterior ao início da fase")

    delta = (nova_data_fim - fase.data_fim_prevista).days

    fases = list(
        session.exec(
            select(Fase).where(Fase.projeto_id == fase.projeto_id).order_by(Fase.ordem)
        )
    )
    antes_aloc = _snapshot_alocacoes(fases)

    # --- plano das fases ---
    fases_diff = []
    for f in fases:
        alterada = False
        novo_inicio, novo_fim = f.data_inicio_prevista, f.data_fim_prevista
        if f.id == fase.id:
            novo_fim = nova_data_fim
            alterada = delta != 0
        elif f.ordem > fase.ordem:
            novo_inicio = f.data_inicio_prevista + timedelta(days=delta)
            novo_fim = f.data_fim_prevista + timedelta(days=delta)
            alterada = delta != 0
        fases_diff.append(
            {
                "id": f.id,
                "nome": f.nome,
                "ordem": f.ordem,
                "alterada": alterada,
                "antes": {
                    "data_inicio_prevista": f.data_inicio_prevista.isoformat(),
                    "data_fim_prevista": f.data_fim_prevista.isoformat(),
                },
                "depois": {
                    "data_inicio_prevista": novo_inicio.isoformat(),
                    "data_fim_prevista": novo_fim.isoformat(),
                },
            }
        )

    # --- plano das alocações ---
    depois_aloc: list[AlocacaoSim] = []
    ordem_por_fase = {f.id: f.ordem for f in fases}
    for a in antes_aloc:
        if a.fase_id == fase.id:
            # fase atrasada: alocações são estendidas
            nova = replace(a, data_fim=a.data_fim + timedelta(days=delta))
        elif ordem_por_fase[a.fase_id] > fase.ordem:
            # fases seguintes: alocações deslocam inteiras
            nova = replace(
                a,
                data_inicio=a.data_inicio + timedelta(days=delta),
                data_fim=a.data_fim + timedelta(days=delta),
            )
        else:
            nova = a
        depois_aloc.append(nova)

    alocacoes_diff = []
    for antes, depois in zip(antes_aloc, depois_aloc):
        if antes == depois:
            continue
        h_antes = horas_previstas(antes.data_inicio, antes.data_fim, antes.horas_semana)
        h_depois = horas_previstas(depois.data_inicio, depois.data_fim, depois.horas_semana)
        alocacoes_diff.append(
            {
                "id": antes.id,
                "consultor": antes.consultor_nome,
                "fase": antes.fase_nome,
                "antes": {
                    "data_inicio": antes.data_inicio.isoformat(),
                    "data_fim": antes.data_fim.isoformat(),
                    "horas_previstas": round(h_antes, 2),
                    "receita_prevista": round(h_antes * antes.taxa_hora_venda, 2),
                },
                "depois": {
                    "data_inicio": depois.data_inicio.isoformat(),
                    "data_fim": depois.data_fim.isoformat(),
                    "horas_previstas": round(h_depois, 2),
                    "receita_prevista": round(h_depois * depois.taxa_hora_venda, 2),
                },
            }
        )

    # --- diff de receita mensal do projeto ---
    receita_antes = receita_mensal_prevista(antes_aloc)
    receita_depois = receita_mensal_prevista(depois_aloc)
    meses = sorted(set(receita_antes) | set(receita_depois))
    receita_mensal = [
        {
            "mes": m,
            "antes": round(receita_antes.get(m, 0.0), 2),
            "depois": round(receita_depois.get(m, 0.0), 2),
            "delta": round(receita_depois.get(m, 0.0) - receita_antes.get(m, 0.0), 2),
        }
        for m in meses
    ]

    return {
        "fase_id": fase.id,
        "fase_nome": fase.nome,
        "projeto_id": fase.projeto_id,
        "delta_dias": delta,
        "nova_data_fim": nova_data_fim.isoformat(),
        "fases": fases_diff,
        "alocacoes": alocacoes_diff,
        "receita_mensal": receita_mensal,
        "receita_total": {
            "antes": round(sum(receita_antes.values()), 2),
            "depois": round(sum(receita_depois.values()), 2),
        },
    }


def aplicar_reagendamento(session: Session, fase_id: int, nova_data_fim: date) -> dict:
    """Simula, aplica as mudanças no banco e devolve o mesmo diff."""
    diff = simular_reagendamento(session, fase_id, nova_data_fim)

    novas_datas_fase = {
        f["id"]: (
            date.fromisoformat(f["depois"]["data_inicio_prevista"]),
            date.fromisoformat(f["depois"]["data_fim_prevista"]),
        )
        for f in diff["fases"]
        if f["alterada"]
    }
    for f_id, (inicio, fim) in novas_datas_fase.items():
        f = session.get(Fase, f_id)
        f.data_inicio_prevista = inicio
        f.data_fim_prevista = fim
        session.add(f)

    for a_diff in diff["alocacoes"]:
        a = session.get(Alocacao, a_diff["id"])
        a.data_inicio = date.fromisoformat(a_diff["depois"]["data_inicio"])
        a.data_fim = date.fromisoformat(a_diff["depois"]["data_fim"])
        session.add(a)

    session.commit()
    return diff
