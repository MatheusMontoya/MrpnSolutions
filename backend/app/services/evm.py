"""EVM — Earned Value Management (valor agregado) por projeto.

Todas as grandezas derivam do motor determinístico:
- PV (Planned Value): custo planejado do trabalho que DEVERIA estar feito até
  hoje = horas previstas das alocações (recortadas em `hoje`) × taxa de custo.
- EV (Earned Value): custo planejado do trabalho REALMENTE feito = progresso
  físico da fase (atividades concluídas / total; fallback horas ou status da
  fase quando não há atividades) × custo total planejado da fase.
- AC (Actual Cost): custo real = horas apontadas × taxa de custo do consultor
  + despesas reembolsáveis do projeto.

SPI = EV/PV (ritmo: <1 atrasado) · CPI = EV/AC (custo: <1 estourando).
"""
from datetime import date

from ..models import Projeto, StatusAtividade, StatusDespesa, StatusFase
from .receita import horas_previstas


def _progresso_fisico(fase) -> float:
    """Fração 0..1 do trabalho da fase concluído (medida física, não financeira)."""
    if fase.status == StatusFase.concluida:
        return 1.0
    atividades = fase.atividades or []
    if atividades:
        pesos = {
            StatusAtividade.concluida: 1.0,
            StatusAtividade.em_andamento: 0.5,
            StatusAtividade.pendente: 0.0,
        }
        return sum(pesos.get(a.status, 0.0) for a in atividades) / len(atividades)
    if fase.status == StatusFase.nao_iniciada:
        return 0.0
    # fase em andamento sem atividades: aproxima pelo esforço (horas apontadas/previstas)
    prev = sum(horas_previstas(a.data_inicio, a.data_fim, a.horas_semana) for a in fase.alocacoes)
    real = sum(ap.horas for a in fase.alocacoes for ap in a.apontamentos)
    return min(real / prev, 1.0) if prev > 0 else 0.0


def calcular_evm(projeto: Projeto, despesas: list, hoje: date | None = None,
                 orcamento_despesas: float = 0.0) -> dict:
    hoje = hoje or date.today()
    pv = ev = ac = bac = 0.0
    fases = []

    for fase in projeto.fases:
        custo_fase = 0.0  # BAC da fase (orçamento a custo)
        pv_fase = 0.0
        for a in fase.alocacoes:
            taxa_custo = a.consultor.taxa_hora_custo if a.consultor else 0.0
            custo_fase += horas_previstas(a.data_inicio, a.data_fim, a.horas_semana) * taxa_custo
            if a.data_inicio <= hoje:
                pv_fase += horas_previstas(a.data_inicio, min(a.data_fim, hoje), a.horas_semana) * taxa_custo
        progresso = _progresso_fisico(fase)
        ev_fase = progresso * custo_fase
        ac_fase = sum(
            ap.horas * (a.consultor.taxa_hora_custo if a.consultor else 0.0)
            for a in fase.alocacoes for ap in a.apontamentos
        )
        pv += pv_fase
        ev += ev_fase
        ac += ac_fase
        bac += custo_fase
        fases.append({
            "fase": fase.nome,
            "progresso_fisico": round(progresso, 4),
            "pv": round(pv_fase, 2),
            "ev": round(ev_fase, 2),
            "ac": round(ac_fase, 2),
        })

    # Despesa reembolsável entra no custo real (AC) — e o ORÇADO dela precisa
    # entrar no BAC junto, senão a conta fica torta: com despesa só no AC, o
    # CPI (EV/AC) saía subestimado e o EAC (BAC/CPI) inflado em TODO projeto
    # com reembolso. Sem rubrica de despesa no orçamento, o gasto aparece como
    # estouro — o que é o comportamento correto, não um erro.
    ac += sum(
        d.valor for d in despesas
        if d.status in (StatusDespesa.aprovada, StatusDespesa.reembolsada)
    )
    if orcamento_despesas:
        # o PV/EV da rubrica acompanha o avanço físico do trabalho, para o SPI
        # não ser distorcido por uma linha que não tem cronograma próprio
        base_trabalho = bac
        avanco = (ev / base_trabalho) if base_trabalho else 0.0
        avanco = min(1.0, max(0.0, avanco))
        bac += orcamento_despesas
        pv += orcamento_despesas * avanco
        ev += orcamento_despesas * avanco

    spi = round(ev / pv, 4) if pv > 0 else None
    cpi = round(ev / ac, 4) if ac > 0 else None
    return {
        "projeto_id": projeto.id,
        "data_referencia": hoje.isoformat(),
        "bac": round(bac, 2),
        "pv": round(pv, 2),
        "ev": round(ev, 2),
        "ac": round(ac, 2),
        "spi": spi,
        "cpi": cpi,
        # variações clássicas: SV = EV−PV (cronograma), CV = EV−AC (custo)
        "sv": round(ev - pv, 2),
        "cv": round(ev - ac, 2),
        # estimativa no término mantendo a eficiência atual (EAC = BAC/CPI)
        "eac": round(bac / cpi, 2) if cpi else None,
        "orcamento_despesas": round(orcamento_despesas, 2),
        "fases": fases,
    }
