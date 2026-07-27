"""Testes da Onda 3: pipeline de propostas e cronograma de faturamento."""
from datetime import date

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models import (
    Alocacao,
    EstagioProposta,
    Fatura,
    Proposta,
    StatusFatura,
)
from app.routers.faturas import FaturaUpdate, atualizar_fatura, gerar_plano_de_faturas
from app.routers.propostas import (
    ConverterProposta,
    avancar_estagio,
    converter_em_projeto,
)
from app.services.receita import horas_previstas, receita_mensal_prevista


@pytest.fixture()
def proposta(session, cliente):
    p = Proposta(cliente_id=cliente.id, nome="Implementação Teste",
                 valor_estimado=100_000, probabilidade=0.5, criada_em=date(2026, 1, 2))
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def test_funil_avanca_ate_aprovada(session, proposta):
    assert proposta.estagio == EstagioProposta.qualificacao
    for esperado in (EstagioProposta.proposta, EstagioProposta.negociacao, EstagioProposta.aprovada):
        r = avancar_estagio(proposta.id, session)
        assert r["estagio"] == esperado
    with pytest.raises(HTTPException) as exc:
        avancar_estagio(proposta.id, session)  # aprovada não avança mais
    assert exc.value.status_code == 409


def test_converter_exige_aprovada(session, proposta):
    with pytest.raises(HTTPException) as exc:
        converter_em_projeto(proposta.id, ConverterProposta(data_inicio=date(2026, 3, 2)), session)
    assert exc.value.status_code == 409


def test_converter_cria_projeto_completo(session, proposta):
    proposta.estagio = EstagioProposta.aprovada
    session.add(proposta)
    session.commit()

    r = converter_em_projeto(proposta.id, ConverterProposta(data_inicio=date(2026, 3, 2)), session)
    session.refresh(proposta)

    assert proposta.estagio == EstagioProposta.convertida
    assert proposta.projeto_id == r["projeto_id"]
    projeto = proposta.projeto
    assert projeto.nome == "Implementação Teste"
    assert [f.nome for f in projeto.fases] == ["Discover", "Prepare", "Explore", "Realize", "Deploy", "Run"]
    # nasce com entregas e quality gates dos templates Activate
    assert all(len(f.atividades) > 0 for f in projeto.fases)
    assert all(len(f.itens_gate) > 0 for f in projeto.fases)


def test_plano_de_faturas_bate_com_receita_prevista(session, projeto, consultor_senior):
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[2]  # Explore
    aloc = Alocacao(consultor_id=consultor_senior.id, fase_id=fase.id,
                    data_inicio=fase.data_inicio_prevista, data_fim=fase.data_fim_prevista,
                    horas_semana=40, taxa_hora_venda=200)
    session.add(aloc)
    session.commit()

    faturas = gerar_plano_de_faturas(session, projeto)
    receita = receita_mensal_prevista([aloc])

    assert len(faturas) == len(receita)
    assert sum(f.valor for f in faturas) == pytest.approx(sum(receita.values()), abs=0.05)
    assert all(f.status == StatusFatura.prevista for f in faturas)


def test_fluxo_fatura_emitir_receber(session, projeto, consultor_senior):
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[0]
    aloc = Alocacao(consultor_id=consultor_senior.id, fase_id=fase.id,
                    data_inicio=fase.data_inicio_prevista, data_fim=fase.data_fim_prevista,
                    horas_semana=40, taxa_hora_venda=100)
    session.add(aloc)
    session.commit()
    fatura = gerar_plano_de_faturas(session, projeto)[0]

    r = atualizar_fatura(fatura.id, FaturaUpdate(status=StatusFatura.emitida, numero="NF-1"), session)
    assert r["status"] == StatusFatura.emitida
    assert r["data_vencimento"] is not None

    # emitir de novo → 409
    with pytest.raises(HTTPException) as exc:
        atualizar_fatura(fatura.id, FaturaUpdate(status=StatusFatura.emitida), session)
    assert exc.value.status_code == 409

    r = atualizar_fatura(fatura.id, FaturaUpdate(status=StatusFatura.recebida), session)
    assert r["status"] == StatusFatura.recebida
    assert r["data_recebimento"] is not None


def test_regerar_plano_preserva_emitidas(session, projeto, consultor_senior):
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[2]
    aloc = Alocacao(consultor_id=consultor_senior.id, fase_id=fase.id,
                    data_inicio=fase.data_inicio_prevista, data_fim=fase.data_fim_prevista,
                    horas_semana=40, taxa_hora_venda=200)
    session.add(aloc)
    session.commit()

    faturas = gerar_plano_de_faturas(session, projeto)
    primeira = faturas[0]
    atualizar_fatura(primeira.id, FaturaUpdate(status=StatusFatura.emitida), session)

    regeradas = gerar_plano_de_faturas(session, projeto)
    todas = session.exec(select(Fatura).where(Fatura.projeto_id == projeto.id)).all()

    emitidas = [f for f in todas if f.status == StatusFatura.emitida]
    assert len(emitidas) == 1 and emitidas[0].competencia == primeira.competencia
    # o mês da emitida não foi duplicado no novo plano
    assert all(f.competencia != primeira.competencia for f in regeradas)
