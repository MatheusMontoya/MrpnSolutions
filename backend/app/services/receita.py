"""Motor de receita hora-homem. Funções puras e determinísticas.

É por cima deste módulo (e de reagendamento.py) que a camada de IA será
plugada futuramente — nenhuma função aqui chama rede ou IA.

Convenção: horas semanais são distribuídas uniformemente pelos 5 dias úteis
(seg-sex) do intervalo da alocação. Receita de um dia útil =
(horas_semana / 5) * taxa_hora_venda.
"""
from collections import defaultdict
from datetime import date, timedelta

from ..models import HORAS_SEMANA_PADRAO

LIMIAR_SUPERALOCADO = 1.0  # >100% da jornada
LIMIAR_OCIOSO = 0.6  # <60% da jornada

# Feriados do calendário corporativo (carregados do banco no startup e após
# edição em Configurações). Mantido como registro de módulo para que TODO o
# motor (receita, capacidade, faturas, cascata) respeite feriados sem mudar
# a assinatura das funções puras.
_FERIADOS: frozenset = frozenset()


def definir_feriados(datas) -> None:
    global _FERIADOS
    _FERIADOS = frozenset(datas)


def eh_dia_util(d: date) -> bool:
    return d.weekday() < 5 and d not in _FERIADOS


def dias_uteis(inicio: date, fim: date) -> int:
    """Quantidade de dias úteis (seg-sex) no intervalo fechado [inicio, fim]."""
    if fim < inicio:
        return 0
    total = 0
    d = inicio
    while d <= fim:
        if eh_dia_util(d):
            total += 1
        d += timedelta(days=1)
    return total


def segunda_da_semana(d: date) -> date:
    return d - timedelta(days=d.weekday())


def horas_previstas(data_inicio: date, data_fim: date, horas_semana: float) -> float:
    """Horas previstas de uma alocação: dias úteis do intervalo × horas/dia."""
    return dias_uteis(data_inicio, data_fim) * (horas_semana / 5.0)


def receita_prevista(data_inicio: date, data_fim: date, horas_semana: float, taxa_venda: float) -> float:
    return horas_previstas(data_inicio, data_fim, horas_semana) * taxa_venda


def margem(horas: float, taxa_venda: float, taxa_custo: float) -> float:
    """Margem = receita - custo, para um mesmo volume de horas."""
    return horas * (taxa_venda - taxa_custo)


def receita_mensal_prevista(alocacoes) -> dict[str, float]:
    """Distribui a receita prevista de cada alocação pelos meses ("YYYY-MM").

    `alocacoes` é qualquer iterável de objetos com data_inicio, data_fim,
    horas_semana e taxa_hora_venda (funciona com o modelo ou com dataclasses
    de simulação do reagendamento).
    """
    receita: dict[str, float] = defaultdict(float)
    for a in alocacoes:
        if a.data_fim < a.data_inicio:
            continue
        valor_dia = (a.horas_semana / 5.0) * a.taxa_hora_venda
        d = a.data_inicio
        while d <= a.data_fim:
            if eh_dia_util(d):
                receita[f"{d.year:04d}-{d.month:02d}"] += valor_dia
            d += timedelta(days=1)
    return dict(receita)


def receita_mensal_realizada(apontamentos) -> dict[str, float]:
    """Receita realizada por mês: horas lançadas × taxa de venda da alocação."""
    receita: dict[str, float] = defaultdict(float)
    for ap in apontamentos:
        mes = f"{ap.data.year:04d}-{ap.data.month:02d}"
        receita[mes] += ap.horas * ap.alocacao.taxa_hora_venda
    return dict(receita)


def horas_alocadas_na_semana(alocacao, segunda: date) -> float:
    """Horas de uma alocação que caem na semana que começa em `segunda`.

    Conta os dias úteis da semana que estão dentro do intervalo da alocação,
    a (horas_semana/5) por dia — semanas parciais contam proporcionalmente.
    """
    sexta = segunda + timedelta(days=4)
    inicio = max(alocacao.data_inicio, segunda)
    fim = min(alocacao.data_fim, sexta)
    return dias_uteis(inicio, fim) * (alocacao.horas_semana / 5.0)


def horas_ausentes_na_semana(ausencias, segunda: date, horas_dia: float = HORAS_SEMANA_PADRAO / 5) -> float:
    """Horas de capacidade perdidas na semana por ausências APROVADAS.

    Conta os dias úteis da semana dentro do período de cada ausência × horas/dia.
    `ausencias` é iterável de objetos com data_inicio, data_fim e status.
    """
    sexta = segunda + timedelta(days=4)
    total = 0.0
    for aus in ausencias:
        if getattr(aus, "status", "aprovada") != "aprovada":  # str-enum compara direto
            continue
        inicio = max(aus.data_inicio, segunda)
        fim = min(aus.data_fim, sexta)
        total += dias_uteis(inicio, fim) * horas_dia
    return min(total, HORAS_SEMANA_PADRAO)


def utilizacao_semanal(alocacoes, segunda: date, ausencias=None) -> dict:
    """Utilização de um consultor numa semana: horas alocadas / capacidade REAL.

    Capacidade = jornada padrão − horas de ausência aprovada na semana.
    Sem capacidade (semana toda ausente): status 'ausente' — a menos que ainda
    haja horas alocadas, o que caracteriza superalocação (alocado durante férias).
    """
    horas = sum(horas_alocadas_na_semana(a, segunda) for a in alocacoes)
    ausentes = horas_ausentes_na_semana(ausencias or [], segunda)
    capacidade = HORAS_SEMANA_PADRAO - ausentes

    if capacidade <= 0:
        status = "superalocado" if horas > 0 else "ausente"
        utilizacao = horas / HORAS_SEMANA_PADRAO if horas > 0 else 0.0
    else:
        utilizacao = horas / capacidade
        if utilizacao > LIMIAR_SUPERALOCADO:
            status = "superalocado"
        elif utilizacao < LIMIAR_OCIOSO:
            status = "ocioso"
        else:
            status = "ok"

    return {
        "horas": round(horas, 2),
        "capacidade": round(capacidade, 2),
        "utilizacao": round(utilizacao, 4),
        "status": status,
    }
