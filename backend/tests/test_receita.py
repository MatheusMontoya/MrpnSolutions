"""Testes do motor de receita hora-homem (services/receita.py)."""
import pytest
from datetime import date

from app.models import Alocacao, Apontamento, FASES_ACTIVATE
from app.services import receita as r


def test_criar_projeto_gera_6_fases_activate(projeto):
    nomes = [f.nome for f in sorted(projeto.fases, key=lambda f: f.ordem)]
    assert nomes == FASES_ACTIVATE
    # fases contíguas: cada uma começa no dia seguinte ao fim da anterior
    fases = sorted(projeto.fases, key=lambda f: f.ordem)
    for anterior, seguinte in zip(fases, fases[1:]):
        assert (seguinte.data_inicio_prevista - anterior.data_fim_prevista).days == 1
    assert fases[0].data_inicio_prevista == projeto.data_inicio


def test_horas_e_receita_prevista_semana_cheia():
    # 2 semanas exatas (seg 05/01 a sex 16/01) a 30h/semana e R$200/h
    inicio, fim = date(2026, 1, 5), date(2026, 1, 16)
    assert r.dias_uteis(inicio, fim) == 10
    assert r.horas_previstas(inicio, fim, 30) == 60
    assert r.receita_prevista(inicio, fim, 30, 200) == 12000


def test_receita_prevista_semana_parcial():
    # qua 07/01 a ter 13/01 = 5 dias úteis → exatamente 1 semana de horas
    assert r.horas_previstas(date(2026, 1, 7), date(2026, 1, 13), 40) == 40


def test_margem():
    assert r.margem(horas=100, taxa_venda=200, taxa_custo=120) == 8000


def test_alocacao_com_taxa_negociada_usa_taxa_da_alocacao(session, projeto, consultor_senior):
    """A taxa default do consultor é 200, mas a alocação foi negociada a 150."""
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[0]
    aloc = Alocacao(
        consultor_id=consultor_senior.id,
        fase_id=fase.id,
        data_inicio=date(2026, 1, 5),
        data_fim=date(2026, 1, 16),
        horas_semana=40,
        taxa_hora_venda=150.0,  # negociada, ≠ 200 do consultor
    )
    session.add(aloc)
    session.commit()

    mensal = r.receita_mensal_prevista([aloc])
    # 80h × 150 (não 200)
    assert mensal == {"2026-01": 80 * 150.0}


def test_receita_realizada_por_mes(session, projeto, consultor_senior):
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[0]
    aloc = Alocacao(
        consultor_id=consultor_senior.id,
        fase_id=fase.id,
        data_inicio=date(2026, 1, 5),
        data_fim=date(2026, 2, 27),
        horas_semana=40,
        taxa_hora_venda=200.0,
    )
    session.add(aloc)
    session.commit()
    session.add(Apontamento(alocacao_id=aloc.id, data=date(2026, 1, 30), horas=6))
    session.add(Apontamento(alocacao_id=aloc.id, data=date(2026, 2, 2), horas=8))
    session.commit()
    session.refresh(aloc)

    realizada = r.receita_mensal_realizada(aloc.apontamentos)
    assert realizada == {"2026-01": 1200.0, "2026-02": 1600.0}


def test_utilizacao_superalocado_e_ocioso(session, projeto, consultor_senior):
    """30h + 20h na mesma semana = 125% (superalocado); 12h = 30% (ocioso)."""
    fases = sorted(projeto.fases, key=lambda f: f.ordem)
    segunda = date(2026, 1, 5)

    a1 = Alocacao(consultor_id=consultor_senior.id, fase_id=fases[0].id,
                  data_inicio=segunda, data_fim=date(2026, 1, 30),
                  horas_semana=30, taxa_hora_venda=200)
    a2 = Alocacao(consultor_id=consultor_senior.id, fase_id=fases[1].id,
                  data_inicio=segunda, data_fim=date(2026, 1, 30),
                  horas_semana=20, taxa_hora_venda=200)

    u = r.utilizacao_semanal([a1, a2], segunda)
    assert u["horas"] == 50
    assert u["utilizacao"] == 1.25
    assert u["status"] == "superalocado"

    a3 = Alocacao(consultor_id=consultor_senior.id, fase_id=fases[0].id,
                  data_inicio=segunda, data_fim=date(2026, 1, 30),
                  horas_semana=12, taxa_hora_venda=200)
    u2 = r.utilizacao_semanal([a3], segunda)
    assert u2["status"] == "ocioso"

    a4 = Alocacao(consultor_id=consultor_senior.id, fase_id=fases[0].id,
                  data_inicio=segunda, data_fim=date(2026, 1, 30),
                  horas_semana=40, taxa_hora_venda=200)
    assert r.utilizacao_semanal([a4], segunda)["status"] == "ok"


def test_utilizacao_semana_parcial_conta_proporcional(session, projeto, consultor_senior):
    """Alocação que começa na quarta conta só 3/5 das horas na primeira semana."""
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[0]
    a = Alocacao(consultor_id=consultor_senior.id, fase_id=fase.id,
                 data_inicio=date(2026, 1, 7), data_fim=date(2026, 1, 30),
                 horas_semana=40, taxa_hora_venda=200)
    u = r.utilizacao_semanal([a], date(2026, 1, 5))
    assert u["horas"] == 24  # qua+qui+sex × 8h


# ---------------- capacidade: feriado, sobreposição e jornada ----------------

def test_feriado_entra_no_denominador_da_utilizacao():
    """O numerador já descontava feriado; o denominador usava a jornada cheia.
    Numa semana com feriado, quem estava 100% alocado aparecia com 80%."""
    from app.services.receita import definir_feriados, utilizacao_semanal

    seg = date(2026, 3, 2)

    class A:
        data_inicio, data_fim, horas_semana = date(2026, 1, 1), date(2026, 12, 31), 40.0

    definir_feriados([])
    assert utilizacao_semanal([A()], seg)["utilizacao"] == pytest.approx(1.0)

    definir_feriados([date(2026, 3, 4)])  # feriado na quarta
    u = utilizacao_semanal([A()], seg)["utilizacao"]
    definir_feriados([])
    assert u == pytest.approx(1.0), "com feriado, 4 dias alocados sobre 4 dias úteis ainda é 100%"


def test_ausencias_sobrepostas_nao_contam_em_dobro():
    """Férias emendada com folga contava o mesmo dia duas vezes: a capacidade
    sumia e a pessoa virava falso 'superalocado'."""
    from app.services.receita import dias_ausentes_na_semana

    seg = date(2026, 3, 2)

    class Aus:
        def __init__(self, i, f):
            self.data_inicio, self.data_fim, self.status = i, f, "aprovada"

    sobrepostas = [Aus(date(2026, 3, 2), date(2026, 3, 4)), Aus(date(2026, 3, 3), date(2026, 3, 5))]
    assert len(dias_ausentes_na_semana(sobrepostas, seg)) == 4, "seg a qui = 4 dias distintos"


def test_jornada_configurada_muda_o_calculo():
    """A tela de Configurações dizia 'Salvo' e o motor seguia com 40h fixas."""
    from app.services.receita import definir_parametros, jornada_semanal, utilizacao_semanal

    seg = date(2026, 3, 2)

    class A:
        data_inicio, data_fim, horas_semana = date(2026, 1, 1), date(2026, 12, 31), 30.0

    definir_parametros(jornada=40)
    assert utilizacao_semanal([A()], seg)["utilizacao"] == pytest.approx(0.75)
    definir_parametros(jornada=30)
    assert jornada_semanal() == 30
    assert utilizacao_semanal([A()], seg)["utilizacao"] == pytest.approx(1.0)
    definir_parametros(jornada=40)
