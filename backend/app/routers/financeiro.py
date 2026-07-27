"""Financeiro gerencial: fluxo de caixa mensal, ranking de rentabilidade e
contas a pagar (reembolsos aprovados)."""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Apontamento,
    Despesa,
    Fatura,
    Projeto,
    StatusDespesa,
    StatusFatura,
)
from ..services.receita import receita_mensal_realizada
from .despesas import serializar as ser_despesa

router = APIRouter(prefix="/api/financeiro", tags=["Financeiro gerencial"])


def _mes(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


@router.get("/fluxo-caixa")
def fluxo_de_caixa(session: Session = Depends(get_session)):
    """Série mensal: entradas (faturas por competência, separando recebido de
    projetado) × saídas (custo das horas apontadas + despesas reembolsáveis)."""
    entradas_recebidas: dict[str, float] = defaultdict(float)
    entradas_projetadas: dict[str, float] = defaultdict(float)
    for f in session.exec(select(Fatura)).all():
        m = _mes(f.competencia)
        if f.status == StatusFatura.recebida:
            entradas_recebidas[m] += f.valor
        elif f.status in (StatusFatura.emitida, StatusFatura.prevista):
            entradas_projetadas[m] += f.valor

    saidas: dict[str, float] = defaultdict(float)
    for ap in session.exec(select(Apontamento)).all():
        custo = ap.alocacao.consultor.taxa_hora_custo if ap.alocacao and ap.alocacao.consultor else 0.0
        saidas[_mes(ap.data)] += ap.horas * custo
    for d in session.exec(select(Despesa)).all():
        if d.status in (StatusDespesa.aprovada, StatusDespesa.reembolsada):
            saidas[_mes(d.data)] += d.valor

    meses = sorted(set(entradas_recebidas) | set(entradas_projetadas) | set(saidas))
    serie = []
    acumulado = 0.0
    for m in meses:
        entrada = entradas_recebidas.get(m, 0.0) + entradas_projetadas.get(m, 0.0)
        saida = saidas.get(m, 0.0)
        acumulado += entrada - saida
        serie.append({
            "mes": m,
            "entrada_recebida": round(entradas_recebidas.get(m, 0.0), 2),
            "entrada_projetada": round(entradas_projetadas.get(m, 0.0), 2),
            "saida": round(saida, 2),
            "resultado": round(entrada - saida, 2),
            "acumulado": round(acumulado, 2),
        })
    return {"serie": serie}


@router.get("/rentabilidade")
def rentabilidade(session: Session = Depends(get_session)):
    """Ranking de rentabilidade REALIZADA por projeto: receita apontada −
    custo das horas − despesas reembolsáveis."""
    projetos = session.exec(select(Projeto)).all()
    ranking = []
    for p in projetos:
        alocacoes = [a for f in p.fases for a in f.alocacoes]
        apontamentos = [ap for a in alocacoes for ap in a.apontamentos]
        receita = sum(receita_mensal_realizada(apontamentos).values())
        custo_horas = sum(
            ap.horas * (ap.alocacao.consultor.taxa_hora_custo if ap.alocacao.consultor else 0.0)
            for ap in apontamentos
        )
        despesas = sum(
            d.valor for d in session.exec(
                select(Despesa).where(Despesa.projeto_id == p.id)
            ).all()
            if d.status in (StatusDespesa.aprovada, StatusDespesa.reembolsada)
        )
        margem = receita - custo_horas - despesas
        ranking.append({
            "projeto_id": p.id,
            "projeto": p.nome,
            "cliente": p.cliente.nome if p.cliente else "",
            "status": p.status,
            "receita_realizada": round(receita, 2),
            "custo_horas": round(custo_horas, 2),
            "despesas": round(despesas, 2),
            "margem": round(margem, 2),
            "margem_pct": round(margem / receita, 4) if receita else 0.0,
        })
    ranking.sort(key=lambda x: x["margem"], reverse=True)
    return {"ranking": ranking}


@router.get("/contas-a-pagar")
def contas_a_pagar(session: Session = Depends(get_session)):
    """Reembolsos devidos aos consultores (despesas aprovadas não reembolsadas)."""
    aprovadas = session.exec(
        select(Despesa).where(Despesa.status == StatusDespesa.aprovada).order_by(Despesa.data)
    ).all()
    por_consultor: dict[str, float] = defaultdict(float)
    for d in aprovadas:
        por_consultor[d.consultor.nome if d.consultor else "?"] += d.valor
    return {
        "despesas": [ser_despesa(d) for d in aprovadas],
        "total": round(sum(d.valor for d in aprovadas), 2),
        "por_consultor": [
            {"consultor": k, "total": round(v, 2)}
            for k, v in sorted(por_consultor.items(), key=lambda x: -x[1])
        ],
    }
