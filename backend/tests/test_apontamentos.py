"""Testes do apontamento com descrição de atividade e do feed do gestor."""
from datetime import date

import pytest
from conftest import RequisicaoFalsa
from sqlmodel import select

from app.models import Alocacao, Apontamento
from app.routers.apontamentos import (
    ApontamentoUpsert,
    atividades_recentes,
    grade_semanal,
    lancar_horas,
)


@pytest.fixture()
def alocacao(session, projeto, consultor_senior):
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[2]  # Explore
    a = Alocacao(
        consultor_id=consultor_senior.id,
        fase_id=fase.id,
        data_inicio=fase.data_inicio_prevista,
        data_fim=fase.data_fim_prevista,
        horas_semana=40,
        taxa_hora_venda=consultor_senior.taxa_hora_venda,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _apontamento(session, alocacao, dia):
    return session.exec(
        select(Apontamento).where(
            Apontamento.alocacao_id == alocacao.id, Apontamento.data == dia
        )
    ).first()


def test_upsert_cria_com_descricao(session, alocacao):
    dia = alocacao.data_inicio
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=8, descricao="Workshop com key users"), RequisicaoFalsa(), session)
    ap = _apontamento(session, alocacao, dia)
    assert ap.horas == 8
    assert ap.descricao == "Workshop com key users"


def test_upsert_de_horas_preserva_descricao_existente(session, alocacao):
    """Salvar horas no blur (sem campo descricao) NÃO pode apagar o balão."""
    dia = alocacao.data_inicio
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=6, descricao="Blueprint funcional"), RequisicaoFalsa(), session)
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=7.5), RequisicaoFalsa(), session)  # só horas

    ap = _apontamento(session, alocacao, dia)
    assert ap.horas == 7.5
    assert ap.descricao == "Blueprint funcional"


def test_upsert_atualiza_descricao_mantendo_horas(session, alocacao):
    dia = alocacao.data_inicio
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=8, descricao="v1"), RequisicaoFalsa(), session)
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=8, descricao="v2 revisada"), RequisicaoFalsa(), session)

    ap = _apontamento(session, alocacao, dia)
    assert ap.descricao == "v2 revisada"
    assert ap.horas == 8


def test_horas_zero_remove_lancamento(session, alocacao):
    dia = alocacao.data_inicio
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=4, descricao="algo"), RequisicaoFalsa(), session)
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=0), RequisicaoFalsa(), session)
    assert _apontamento(session, alocacao, dia) is None


def test_grade_semanal_expoe_descricao_por_dia(session, alocacao, consultor_senior):
    dia = alocacao.data_inicio  # segunda (projeto começa numa segunda)
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=dia, horas=8, descricao="Config no DEV"), RequisicaoFalsa(), session)

    grade = grade_semanal(RequisicaoFalsa(), consultor_id=consultor_senior.id, inicio=dia, session=session)
    linha = next(l for l in grade["alocacoes"] if l["alocacao_id"] == alocacao.id)
    assert linha["descricao_por_dia"][dia.isoformat()] == "Config no DEV"
    # dia sem descrição vem como string vazia
    outro = grade["dias"][1]
    assert linha["descricao_por_dia"][outro] == ""


def test_feed_atividades_so_com_descricao_e_ordem_desc(session, alocacao):
    d1, d2, d3 = alocacao.data_inicio, alocacao.data_inicio.replace(day=alocacao.data_inicio.day + 1), alocacao.data_inicio.replace(day=alocacao.data_inicio.day + 2)
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=d1, horas=8, descricao="atividade antiga"), RequisicaoFalsa(), session)
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=d2, horas=8), RequisicaoFalsa(), session)  # sem descrição
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao.id, data=d3, horas=8, descricao="atividade recente"), RequisicaoFalsa(), session)

    feed = atividades_recentes(limite=10, session=session)
    descricoes = [f["descricao"] for f in feed]
    assert descricoes == ["atividade recente", "atividade antiga"]  # desc por data, sem o item vazio
    assert all(f["consultor"] and f["projeto"] and f["fase"] for f in feed)
