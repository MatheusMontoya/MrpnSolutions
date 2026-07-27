"""Testes da Onda 1+2: templates Activate, capacidade com ausências,
envio/aprovação de semana, despesas (km) e pendências."""
from datetime import date, timedelta

import pytest
from sqlmodel import select

from app.models import (
    Alocacao,
    Ausencia,
    Configuracao,
    EnvioSemana,
    StatusAprovacao,
    StatusDespesa,
    StatusEnvio,
    StatusGate,
    TipoAusencia,
    TipoDespesa,
)
from app.routers.apontamentos import ApontamentoUpsert, EnviarSemana, enviar_semana, lancar_horas
from app.routers.aprovacoes import DecisaoEnvio, decidir_envio, fila_de_aprovacoes
from app.routers.atividades import resumo_gate
from app.routers.despesas import DespesaCreate, lancar_despesa
from app.services.receita import horas_ausentes_na_semana, utilizacao_semanal
from app.services.templates_activate import ATIVIDADES_PADRAO, GATES_PADRAO


# ---------- Onda 1: templates Activate ----------

def test_projeto_nasce_com_atividades_e_gates(projeto):
    for fase in projeto.fases:
        assert [a.titulo for a in fase.atividades] == ATIVIDADES_PADRAO[fase.nome]
        assert [g.codigo for g in fase.itens_gate] == [c for c, _, _ in GATES_PADRAO[fase.nome]]
        assert all(g.status == StatusGate.nao_verificado for g in fase.itens_gate)


def test_resumo_gate_aprovado_so_com_tudo_verde(session, projeto):
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[0]  # Discover: 3 itens
    assert resumo_gate(fase)["aprovado"] is False

    for item in fase.itens_gate:
        item.status = StatusGate.verde
        session.add(item)
    session.commit()
    session.refresh(fase)

    r = resumo_gate(fase)
    assert r["verde"] == r["total"] == 3
    assert r["aprovado"] is True


# ---------- Onda 1: capacidade com ausências ----------

def test_ausencia_aprovada_reduz_capacidade(session, projeto, consultor_senior):
    segunda = date(2026, 1, 5)
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[0]
    aloc = Alocacao(consultor_id=consultor_senior.id, fase_id=fase.id,
                    data_inicio=segunda, data_fim=date(2026, 1, 30),
                    horas_semana=32, taxa_hora_venda=200)
    session.add(aloc)
    # 2 dias úteis de folga aprovada → capacidade 40-16 = 24h
    aus = Ausencia(consultor_id=consultor_senior.id, tipo=TipoAusencia.folga,
                   data_inicio=segunda, data_fim=segunda + timedelta(days=1),
                   status=StatusAprovacao.aprovada)
    session.add(aus)
    session.commit()

    assert horas_ausentes_na_semana([aus], segunda) == 16
    u = utilizacao_semanal([aloc], segunda, [aus])
    assert u["capacidade"] == 24
    # 32h alocadas / 24h de capacidade → superalocado (sem a ausência seria 80% ok)
    assert u["status"] == "superalocado"

    sem_ausencia = utilizacao_semanal([aloc], segunda)
    assert sem_ausencia["status"] == "ok"


def test_ausencia_pendente_nao_afeta_capacidade(session, consultor_senior):
    segunda = date(2026, 1, 5)
    aus = Ausencia(consultor_id=consultor_senior.id, tipo=TipoAusencia.ferias,
                   data_inicio=segunda, data_fim=segunda + timedelta(days=4),
                   status=StatusAprovacao.pendente)
    assert horas_ausentes_na_semana([aus], segunda) == 0


def test_semana_toda_ausente_fica_ausente_ou_superalocado(session, projeto, consultor_senior):
    segunda = date(2026, 1, 5)
    aus = Ausencia(consultor_id=consultor_senior.id, tipo=TipoAusencia.ferias,
                   data_inicio=segunda, data_fim=segunda + timedelta(days=4),
                   status=StatusAprovacao.aprovada)
    assert utilizacao_semanal([], segunda, [aus])["status"] == "ausente"

    fase = sorted(projeto.fases, key=lambda f: f.ordem)[0]
    aloc = Alocacao(consultor_id=consultor_senior.id, fase_id=fase.id,
                    data_inicio=segunda, data_fim=segunda + timedelta(days=4),
                    horas_semana=20, taxa_hora_venda=200)
    assert utilizacao_semanal([aloc], segunda, [aus])["status"] == "superalocado"


# ---------- Onda 2: envio e aprovação de semana ----------

@pytest.fixture()
def alocacao_com_horas(session, projeto, consultor_senior):
    fase = sorted(projeto.fases, key=lambda f: f.ordem)[2]  # Explore
    a = Alocacao(consultor_id=consultor_senior.id, fase_id=fase.id,
                 data_inicio=fase.data_inicio_prevista, data_fim=fase.data_fim_prevista,
                 horas_semana=40, taxa_hora_venda=200)
    session.add(a)
    session.commit()
    session.refresh(a)
    lancar_horas(ApontamentoUpsert(alocacao_id=a.id, data=a.data_inicio, horas=8), session)
    return a


def test_enviar_semana_congela_edicao(session, alocacao_com_horas, consultor_senior):
    dia = alocacao_com_horas.data_inicio
    enviar_semana(EnviarSemana(consultor_id=consultor_senior.id, semana=dia), session)

    envio = session.exec(select(EnvioSemana)).one()
    assert envio.status == StatusEnvio.enviada
    assert envio.total_horas == 8

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        lancar_horas(ApontamentoUpsert(alocacao_id=alocacao_com_horas.id, data=dia, horas=6), session)
    assert exc.value.status_code == 409


def test_reprovacao_reabre_edicao_e_permite_reenvio(session, alocacao_com_horas, consultor_senior):
    dia = alocacao_com_horas.data_inicio
    enviar_semana(EnviarSemana(consultor_id=consultor_senior.id, semana=dia), session)
    envio = session.exec(select(EnvioSemana)).one()

    decidir_envio(envio.id, DecisaoEnvio(status=StatusEnvio.reprovada, comentario_gestor="Faltou sexta"), session)

    # edição liberada de novo
    lancar_horas(ApontamentoUpsert(alocacao_id=alocacao_com_horas.id, data=dia, horas=7), session)
    # e reenvio possível
    r = enviar_semana(EnviarSemana(consultor_id=consultor_senior.id, semana=dia), session)
    assert r["status"] == StatusEnvio.enviada
    assert r["total_horas"] == 7


def test_reprovar_exige_comentario(session, alocacao_com_horas, consultor_senior):
    from fastapi import HTTPException
    enviar_semana(EnviarSemana(consultor_id=consultor_senior.id, semana=alocacao_com_horas.data_inicio), session)
    envio = session.exec(select(EnvioSemana)).one()
    with pytest.raises(HTTPException) as exc:
        decidir_envio(envio.id, DecisaoEnvio(status=StatusEnvio.reprovada), session)
    assert exc.value.status_code == 422


def test_fila_agrega_envios_ausencias_despesas(session, alocacao_com_horas, consultor_senior, projeto):
    enviar_semana(EnviarSemana(consultor_id=consultor_senior.id, semana=alocacao_com_horas.data_inicio), session)
    session.add(Ausencia(consultor_id=consultor_senior.id, tipo=TipoAusencia.folga,
                         data_inicio=date(2026, 3, 2), data_fim=date(2026, 3, 3)))
    session.commit()
    lancar_despesa(DespesaCreate(consultor_id=consultor_senior.id, projeto_id=projeto.id,
                                 data=date(2026, 2, 2), tipo=TipoDespesa.alimentacao,
                                 descricao="Almoço", valor=50.0), session)

    fila = fila_de_aprovacoes(session)
    assert len(fila["envios"]) == 1
    assert len(fila["ausencias"]) == 1
    assert len(fila["despesas"]) == 1
    assert fila["total_pendente"] == 3
    # detalhamento do envio traz os lançamentos
    assert fila["envios"][0]["lancamentos"][0]["horas"] == 8


# ---------- Onda 2: despesas ----------

def test_despesa_km_calcula_valor_pela_taxa(session, consultor_senior, projeto):
    session.add(Configuracao(taxa_km=2.00))
    session.commit()
    d = lancar_despesa(DespesaCreate(consultor_id=consultor_senior.id, projeto_id=projeto.id,
                                     data=date(2026, 2, 3), tipo=TipoDespesa.quilometragem,
                                     km=150), session)
    assert d["valor"] == 300.0
    assert d["status"] == StatusDespesa.pendente


def test_despesa_km_sem_km_rejeita(session, consultor_senior, projeto):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        lancar_despesa(DespesaCreate(consultor_id=consultor_senior.id, projeto_id=projeto.id,
                                     data=date(2026, 2, 3), tipo=TipoDespesa.quilometragem), session)
    assert exc.value.status_code == 422
