"""Testes da Onda 4.1: copiloto IA (insights determinísticos + plugável),
EVM (PV/EV/AC, SPI/CPI) e exportação CSV."""
from datetime import date, timedelta

import pytest

from app.models import (
    Alocacao,
    Apontamento,
    Atividade,
    Configuracao,
    Despesa,
    Fatura,
    GrauRisco,
    Risco,
    StatusAtividade,
    StatusDespesa,
    StatusFase,
    StatusFatura,
    TipoDespesa,
)
from app.routers.copiloto import insights as rota_insights, status as rota_status
from app.routers.exportacao import exportar_apontamentos, exportar_faturas
from app.routers.projetos import evm_do_projeto
from app.services.copiloto import gerar_insights, perguntar
from app.services.evm import calcular_evm
from app.services.receita import definir_feriados


@pytest.fixture(autouse=True)
def _limpar_feriados():
    definir_feriados([])
    yield
    definir_feriados([])


# ---------------- copiloto: insights determinísticos ----------------

def test_insight_fatura_vencida(session, projeto):
    session.add(Fatura(
        projeto_id=projeto.id, competencia=date(2026, 1, 1), valor=10_000,
        status=StatusFatura.emitida, data_emissao=date(2026, 1, 31),
        data_vencimento=date.today() - timedelta(days=10),
    ))
    session.commit()

    tipos = [i["tipo"] for i in gerar_insights(session)]
    assert "cobranca" in tipos
    critico = next(i for i in gerar_insights(session) if i["tipo"] == "cobranca")
    assert critico["severidade"] == "critico"
    assert "10 dias" in critico["detalhe"]


def test_insight_risco_critico(session, projeto):
    session.add(Risco(
        projeto_id=projeto.id, titulo="Key user indisponível",
        probabilidade=GrauRisco.alto, impacto=GrauRisco.alto,
    ))
    session.commit()

    riscos = [i for i in gerar_insights(session) if i["tipo"] == "risco"]
    assert len(riscos) == 1
    assert riscos[0]["severidade"] == "critico"
    assert "Key user indisponível" in riscos[0]["titulo"]


def test_insight_desvio_baseline(session, projeto):
    fase = projeto.fases[0]
    fase.data_fim_prevista = fase.baseline_fim + timedelta(days=10)
    session.add(fase)
    session.commit()

    prazos = [i for i in gerar_insights(session) if i["tipo"] == "prazo"]
    assert len(prazos) == 1
    assert "+10d" in prazos[0]["titulo"]


def test_sem_problemas_sem_insights(session, projeto):
    assert gerar_insights(session) == []


def test_insights_ordenados_por_severidade(session, projeto):
    fase = projeto.fases[0]
    fase.data_fim_prevista = fase.baseline_fim + timedelta(days=3)  # atenção
    session.add(fase)
    session.add(Fatura(  # crítico
        projeto_id=projeto.id, competencia=date(2026, 1, 1), valor=5_000,
        status=StatusFatura.emitida, data_vencimento=date.today() - timedelta(days=1),
    ))
    session.commit()

    lista = gerar_insights(session)
    assert lista[0]["severidade"] == "critico"


# ---------------- copiloto: plugável ----------------

def test_status_sem_chave_ia_inativa(session):
    session.add(Configuracao())
    session.commit()
    s = rota_status(session)
    assert s["ia_ativa"] is False


def test_status_com_chave_ia_ativa(session):
    session.add(Configuracao(anthropic_api_key="sk-ant-teste", modelo_ia="claude-sonnet-5"))
    session.commit()
    s = rota_status(session)
    assert s["ia_ativa"] is True
    assert s["modelo"] == "claude-sonnet-5"


def test_perguntar_sem_chave_responde_deterministico(session, projeto):
    session.add(Configuracao())
    session.add(Fatura(
        projeto_id=projeto.id, competencia=date(2026, 1, 1), valor=8_000,
        status=StatusFatura.emitida, data_vencimento=date.today() - timedelta(days=5),
    ))
    session.commit()

    r = perguntar(session, "como está a cobrança?")
    assert r["ia_generativa"] is False
    assert "vencida" in r["resposta"].lower()
    # deixa claro como ativar a IA generativa
    assert "Configurações" in r["resposta"]


def test_rota_insights_conta_criticos(session, projeto):
    session.add(Fatura(
        projeto_id=projeto.id, competencia=date(2026, 1, 1), valor=1_000,
        status=StatusFatura.emitida, data_vencimento=date.today() - timedelta(days=2),
    ))
    session.commit()
    r = rota_insights(session)
    assert r["total"] >= 1
    assert r["criticos"] >= 1


# ---------------- EVM ----------------

def _montar_projeto_evm(session, projeto, consultor_senior):
    """Prepare (5-16/jan/2026, 2 semanas úteis) com 40h/sem a custo 100/venda 200."""
    fase = projeto.fases[1]  # Prepare: 2026-01-05 é a data_inicio do projeto (Discover)
    aloc = Alocacao(
        consultor_id=consultor_senior.id, fase_id=fase.id,
        data_inicio=date(2026, 2, 2), data_fim=date(2026, 2, 13),
        horas_semana=40, taxa_hora_venda=200,
    )
    session.add(aloc)
    session.commit()
    session.refresh(aloc)
    return fase, aloc


def test_evm_meio_do_caminho(session, projeto, consultor_senior):
    fase, aloc = _montar_projeto_evm(session, projeto, consultor_senior)
    # 1 semana passou (PV = 40h × 100 = 4.000); metade das atividades concluída
    for a in fase.atividades:
        a.status = StatusAtividade.concluida
    n = len(fase.atividades)
    for a in fase.atividades[n // 2:]:
        a.status = StatusAtividade.pendente
    # 30h apontadas a custo 100 → AC = 3.000
    for i in range(4):
        session.add(Apontamento(alocacao_id=aloc.id, data=date(2026, 2, 2) + timedelta(days=i), horas=7.5))
    session.commit()

    evm = calcular_evm(projeto, [], hoje=date(2026, 2, 8))  # domingo após a 1ª semana
    assert evm["pv"] == 4_000  # 40h da 1ª semana × custo 100
    assert evm["bac"] == 8_000  # 80h totais × 100
    assert evm["ac"] == 3_000
    # EV = fração concluída × BAC da fase; SPI e CPI existem e são coerentes
    assert evm["ev"] > 0
    assert evm["spi"] == round(evm["ev"] / evm["pv"], 4)
    assert evm["cpi"] == round(evm["ev"] / evm["ac"], 4)


def test_evm_fase_concluida_ev_total(session, projeto, consultor_senior):
    fase, aloc = _montar_projeto_evm(session, projeto, consultor_senior)
    fase.status = StatusFase.concluida
    session.add(fase)
    session.commit()

    evm = calcular_evm(projeto, [], hoje=date(2026, 3, 1))
    assert evm["ev"] == evm["bac"] == 8_000
    assert evm["pv"] == 8_000  # alocação toda no passado
    assert evm["spi"] == 1.0


def test_evm_despesas_entram_no_ac(session, projeto, consultor_senior):
    fase, aloc = _montar_projeto_evm(session, projeto, consultor_senior)
    session.add(Apontamento(alocacao_id=aloc.id, data=date(2026, 2, 2), horas=10))
    session.commit()
    despesas = [Despesa(
        consultor_id=consultor_senior.id, projeto_id=projeto.id,
        data=date(2026, 2, 3), tipo=TipoDespesa.deslocamento, valor=500,
        status=StatusDespesa.aprovada,
    )]

    evm = calcular_evm(projeto, despesas, hoje=date(2026, 2, 8))
    assert evm["ac"] == 10 * 100 + 500


def test_evm_endpoint_404(session):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        evm_do_projeto(9999, session)


def test_evm_endpoint_ok(session, projeto, consultor_senior):
    _montar_projeto_evm(session, projeto, consultor_senior)
    r = evm_do_projeto(projeto.id, session)
    assert r["projeto_id"] == projeto.id
    assert len(r["fases"]) == 6


# ---------------- exportação CSV ----------------

def test_export_faturas_csv(session, projeto):
    session.add(Fatura(
        projeto_id=projeto.id, competencia=date(2026, 3, 1), valor=12_345.67,
        status=StatusFatura.prevista, numero="FAT-001",
    ))
    session.commit()

    resp = exportar_faturas(session)
    corpo = resp.body.decode("utf-8")
    assert resp.media_type.startswith("text/csv")
    assert 'filename="faturas.csv"' in resp.headers["content-disposition"]
    assert corpo.startswith("﻿")  # BOM para o Excel
    assert "Número;Projeto;Cliente" in corpo
    assert "12345,67" in corpo  # decimal com vírgula (Excel pt-BR)
    assert "03/2026" in corpo


def test_export_apontamentos_csv(session, projeto, consultor_senior):
    fase = projeto.fases[0]
    aloc = Alocacao(
        consultor_id=consultor_senior.id, fase_id=fase.id,
        data_inicio=date(2026, 1, 5), data_fim=date(2026, 1, 9),
        horas_semana=40, taxa_hora_venda=200,
    )
    session.add(aloc)
    session.commit()
    session.add(Apontamento(alocacao_id=aloc.id, data=date(2026, 1, 5), horas=8, descricao="Kickoff"))
    session.commit()

    corpo = exportar_apontamentos(session).body.decode("utf-8")
    assert "05/01/2026" in corpo
    assert "Consultora Sênior" in corpo
    assert "Kickoff" in corpo
    assert "1600,00" in corpo  # 8h × 200 de receita
