"""Testes da Onda 3.5: feriados no motor, precificação, contratos, baseline,
riscos, mudanças e status report."""
from datetime import date, timedelta

import pytest
from sqlmodel import select

from app.models import (
    Alocacao,
    Configuracao,
    Consultor,
    Contrato,
    GrauRisco,
    MudancaCR,
    Proposta,
    Risco,
    Senioridade,
    StatusMudanca,
)
from app.routers.contratos import serializar as ser_contrato
from app.routers.governanca import (
    MudancaDecisao,
    decidir_mudanca,
    severidade,
    status_report,
)
from app.routers.propostas import precificar
from app.services.reagendamento import aplicar_reagendamento
from app.services.receita import definir_feriados, dias_uteis, horas_previstas


@pytest.fixture(autouse=True)
def _limpar_feriados():
    """Estado de módulo dos feriados não pode vazar entre testes."""
    definir_feriados([])
    yield
    definir_feriados([])


# ---------------- feriados no motor ----------------

def test_feriado_reduz_dias_uteis_e_receita():
    seg, sex = date(2026, 1, 5), date(2026, 1, 9)
    assert dias_uteis(seg, sex) == 5
    assert horas_previstas(seg, sex, 40) == 40

    definir_feriados([date(2026, 1, 7)])  # quarta vira feriado
    assert dias_uteis(seg, sex) == 4
    assert horas_previstas(seg, sex, 40) == 32  # 4 dias × 8h


def test_feriado_no_fim_de_semana_nao_muda_nada():
    definir_feriados([date(2026, 1, 10)])  # sábado
    assert dias_uteis(date(2026, 1, 5), date(2026, 1, 11)) == 5


# ---------------- precificação por mix ----------------

def test_precificacao_por_mix_usa_taxas_da_config(session, cliente, consultor_senior):
    session.add(Configuracao(taxa_junior=100, taxa_pleno=200, taxa_senior=300))
    session.commit()

    p = Proposta(cliente_id=cliente.id, nome="Mix", criada_em=date(2026, 1, 5),
                 horas_junior=100, horas_pleno=50, horas_senior=10)
    precificar(session, p)

    assert p.valor_estimado == 100 * 100 + 50 * 200 + 10 * 300  # 23_000
    assert p.horas_estimadas == 160
    # margem usa custo médio real: só existe 1 sênior (custo 100); jr/pl caem
    # no fallback 55% da taxa → margem entre 0 e 1
    assert 0 < p.margem_estimada < 1


def test_precificacao_margem_com_custo_medio_real(session, cliente):
    session.add(Configuracao(taxa_senior=300))
    session.add(Consultor(nome="S1", senioridade=Senioridade.senior, taxa_hora_custo=120, taxa_hora_venda=300))
    session.add(Consultor(nome="S2", senioridade=Senioridade.senior, taxa_hora_custo=180, taxa_hora_venda=300))
    session.commit()

    p = Proposta(cliente_id=cliente.id, nome="Só sênior", criada_em=date(2026, 1, 5), horas_senior=100)
    precificar(session, p)
    # custo médio sênior = 150 → margem = (300-150)/300 = 0.5
    assert p.valor_estimado == 30_000
    assert p.margem_estimada == pytest.approx(0.5)


# ---------------- contratos ----------------

def test_contrato_a_renovar_na_janela_de_60_dias(session, cliente):
    hoje = date.today()
    perto = Contrato(cliente_id=cliente.id, nome="Perto do fim",
                     data_inicio=hoje - timedelta(days=300), data_fim=hoje + timedelta(days=30))
    longe = Contrato(cliente_id=cliente.id, nome="Longe do fim",
                     data_inicio=hoje, data_fim=hoje + timedelta(days=300))
    vencido = Contrato(cliente_id=cliente.id, nome="Vencido",
                       data_inicio=hoje - timedelta(days=400), data_fim=hoje - timedelta(days=5))
    assert ser_contrato(perto)["a_renovar"] is True
    assert ser_contrato(longe)["a_renovar"] is False
    assert ser_contrato(vencido)["vencido"] is True


# ---------------- baseline vs cascata ----------------

def test_baseline_fotografada_e_preservada_pela_cascata(session, projeto, consultor_senior):
    fases = sorted(projeto.fases, key=lambda f: f.ordem)
    for f in fases:
        assert f.baseline_inicio == f.data_inicio_prevista
        assert f.baseline_fim == f.data_fim_prevista

    explore = fases[2]
    aplicar_reagendamento(session, explore.id, explore.data_fim_prevista + timedelta(days=14))

    session.refresh(explore)
    realize = fases[3]
    session.refresh(realize)
    # previsto andou, baseline ficou → desvio mensurável
    assert (explore.data_fim_prevista - explore.baseline_fim).days == 14
    assert (realize.data_fim_prevista - realize.baseline_fim).days == 14
    assert realize.baseline_inicio == realize.baseline_fim - (realize.data_fim_prevista - realize.data_inicio_prevista)


# ---------------- riscos e mudanças ----------------

def test_matriz_de_severidade():
    assert severidade(GrauRisco.baixo, GrauRisco.baixo) == "baixa"
    assert severidade(GrauRisco.medio, GrauRisco.medio) == "moderada"
    assert severidade(GrauRisco.alto, GrauRisco.medio) == "critica"
    assert severidade(GrauRisco.alto, GrauRisco.alto) == "critica"


def test_mudanca_decidir_uma_vez(session, projeto):
    from fastapi import HTTPException
    m = MudancaCR(projeto_id=projeto.id, titulo="CR-1", impacto_horas=40,
                  impacto_valor=8000, criada_em=date(2026, 2, 2))
    session.add(m)
    session.commit()

    r = decidir_mudanca(m.id, MudancaDecisao(status=StatusMudanca.aprovada), session)
    assert r["status"] == StatusMudanca.aprovada
    with pytest.raises(HTTPException) as exc:
        decidir_mudanca(m.id, MudancaDecisao(status=StatusMudanca.rejeitada), session)
    assert exc.value.status_code == 409


# ---------------- status report ----------------

def test_status_report_consolida_projeto(session, projeto, consultor_senior):
    fases = sorted(projeto.fases, key=lambda f: f.ordem)
    explore = fases[2]
    session.add(Alocacao(consultor_id=consultor_senior.id, fase_id=explore.id,
                         data_inicio=explore.data_inicio_prevista, data_fim=explore.data_fim_prevista,
                         horas_semana=40, taxa_hora_venda=200))
    session.add(Risco(projeto_id=projeto.id, titulo="R1",
                      probabilidade=GrauRisco.alto, impacto=GrauRisco.alto))
    session.commit()

    aplicar_reagendamento(session, explore.id, explore.data_fim_prevista + timedelta(days=7))
    rep = status_report(projeto.id, session)

    assert rep["projeto"] == projeto.nome
    assert rep["receita_prevista"] > 0
    assert rep["desvio_baseline_dias"] == 7
    assert len(rep["riscos_abertos"]) == 1
    assert rep["riscos_abertos"][0]["severidade"] == "critica"
    assert len(rep["fases"]) == 6
    assert all("gate" in f and "entregas" in f for f in rep["fases"])
