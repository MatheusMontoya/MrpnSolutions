"""Testes da Onda 4.2: solicitação de alocação com conflitos, medição com
aceite do cliente e TAP (termo de abertura)."""
from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models import (
    Alocacao,
    Apontamento,
    Ausencia,
    Fatura,
    Proposta,
    StatusAprovacao,
    StatusFatura,
    StatusMedicao,
    TipoAusencia,
)
from app.routers.aprovacoes import fila_de_aprovacoes
from app.routers.governanca import termo_de_abertura
from app.routers.medicoes import (
    Aceite,
    Contestacao,
    MedicaoCreate,
    aceitar_medicao,
    contestar_medicao,
    gerar_medicao,
    obter_medicao,
)
from app.routers.solicitacoes import (
    Decisao,
    SolicitacaoCreate,
    criar_solicitacao,
    decidir_solicitacao,
)
from app.services.alocacoes import detectar_conflitos
from app.services.receita import definir_feriados


@pytest.fixture(autouse=True)
def _limpar_feriados():
    definir_feriados([])
    yield
    definir_feriados([])


SEG = date(2026, 2, 2)  # segunda-feira


def _alocar(session, consultor, fase, horas, inicio=SEG, fim=SEG + timedelta(days=11)):
    a = Alocacao(
        consultor_id=consultor.id, fase_id=fase.id,
        data_inicio=inicio, data_fim=fim,
        horas_semana=horas, taxa_hora_venda=consultor.taxa_hora_venda,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


# ---------------- conflitos ----------------

def test_sem_conflito_quando_ha_capacidade(session, projeto, consultor_senior):
    _alocar(session, consultor_senior, projeto.fases[1], 20)
    r = detectar_conflitos(session, consultor_senior.id, SEG, SEG + timedelta(days=4), 20)
    assert r["conflito"] is False
    assert r["sobreposicoes"]  # a alocação existente aparece como contexto


def test_conflito_acima_da_jornada(session, projeto, consultor_senior):
    _alocar(session, consultor_senior, projeto.fases[1], 30)
    r = detectar_conflitos(session, consultor_senior.id, SEG, SEG + timedelta(days=4), 20)
    assert r["conflito"] is True
    assert r["semanas"][0]["excesso"] == 10.0


def test_conflito_durante_ausencia_aprovada(session, projeto, consultor_senior):
    session.add(Ausencia(
        consultor_id=consultor_senior.id, tipo=TipoAusencia.ferias,
        data_inicio=SEG, data_fim=SEG + timedelta(days=4),
        status=StatusAprovacao.aprovada,
    ))
    session.commit()
    r = detectar_conflitos(session, consultor_senior.id, SEG, SEG + timedelta(days=4), 8)
    assert r["conflito"] is True
    assert r["ausencias"][0]["dias_uteis"] == 5


# ---------------- solicitação → aprovação → alocação ----------------

def _solicitar(session, projeto, consultor, horas=20):
    return criar_solicitacao(SolicitacaoCreate(
        consultor_id=consultor.id, fase_id=projeto.fases[1].id,
        data_inicio=SEG, data_fim=SEG + timedelta(days=11),
        horas_semana=horas, justificativa="Reforço no Prepare",
        solicitante="Gestor Demo",
    ), session)


def test_solicitacao_aprovada_vira_alocacao(session, projeto, consultor_senior):
    s = _solicitar(session, projeto, consultor_senior)
    assert s["status"] == "pendente"
    assert s["conflitos"]["conflito"] is False

    r = decidir_solicitacao(s["id"], Decisao(status=StatusAprovacao.aprovada), session)
    assert r["status"] == "aprovada"
    alocacoes = session.exec(select(Alocacao)).all()
    assert len(alocacoes) == 1
    # sem taxa negociada no pedido, herda a taxa padrão do consultor
    assert alocacoes[0].taxa_hora_venda == consultor_senior.taxa_hora_venda
    assert alocacoes[0].horas_semana == 20


def test_solicitacao_recusada_nao_cria_alocacao_e_exige_comentario(session, projeto, consultor_senior):
    s = _solicitar(session, projeto, consultor_senior)
    with pytest.raises(HTTPException):  # recusa sem comentário
        decidir_solicitacao(s["id"], Decisao(status=StatusAprovacao.recusada), session)
    decidir_solicitacao(s["id"], Decisao(
        status=StatusAprovacao.recusada, comentario_gestor="Priorizar outro projeto",
    ), session)
    assert session.exec(select(Alocacao)).all() == []


def test_solicitacao_entra_na_fila_unificada(session, projeto, consultor_senior):
    _solicitar(session, projeto, consultor_senior)
    fila = fila_de_aprovacoes(session)
    assert len(fila["solicitacoes_alocacao"]) == 1
    assert fila["total_pendente"] == 1


# ---------------- medição ----------------

def _preparar_apontamentos(session, projeto, consultor):
    """40h na 1ª semana de fevereiro, com a semana APROVADA.

    A aprovação faz parte do preparo desde que a medição passou a só cobrar
    hora aprovada. Antes destes testes passavam sem ela — e passavam porque o
    produto faturava rascunho e reprovado do mesmo jeito."""
    from app.models import EnvioSemana, StatusEnvio

    aloc = _alocar(session, consultor, projeto.fases[1], 40)
    for i in range(5):
        session.add(Apontamento(alocacao_id=aloc.id, data=SEG + timedelta(days=i), horas=8))
    session.add(EnvioSemana(consultor_id=consultor.id, semana=SEG,
                            status=StatusEnvio.aprovada, total_horas=40))
    session.commit()
    return aloc


def test_medicao_gerada_dos_apontamentos(session, projeto, consultor_senior):
    _preparar_apontamentos(session, projeto, consultor_senior)
    m = gerar_medicao(projeto.id, MedicaoCreate(competencia=date(2026, 2, 15)), session)
    assert m["competencia"] == "2026-02-01"  # normaliza para o dia 1
    assert m["total_horas"] == 40
    assert m["total_valor"] == 40 * 200
    assert m["linhas"][0]["consultor"] == "Consultora Sênior"
    assert m["status"] == "gerada"


def test_medicao_sem_horas_da_422(session, projeto):
    with pytest.raises(HTTPException):
        gerar_medicao(projeto.id, MedicaoCreate(competencia=date(2026, 2, 1)), session)


def test_medicao_duplicada_da_409(session, projeto, consultor_senior):
    _preparar_apontamentos(session, projeto, consultor_senior)
    gerar_medicao(projeto.id, MedicaoCreate(competencia=date(2026, 2, 1)), session)
    with pytest.raises(HTTPException):
        gerar_medicao(projeto.id, MedicaoCreate(competencia=date(2026, 2, 1)), session)


def test_aceite_emite_fatura_e_substitui_prevista(session, projeto, consultor_senior):
    _preparar_apontamentos(session, projeto, consultor_senior)
    # havia uma fatura PREVISTA do plano para o mesmo mês
    session.add(Fatura(projeto_id=projeto.id, competencia=date(2026, 2, 1), valor=9_999))
    session.commit()

    m = gerar_medicao(projeto.id, MedicaoCreate(competencia=date(2026, 2, 1)), session)
    r = aceitar_medicao(m["id"], Aceite(numero="NF-042"), session)

    assert r["status"] == "aceita"
    faturas = session.exec(select(Fatura).where(Fatura.projeto_id == projeto.id)).all()
    assert len(faturas) == 1  # a prevista foi substituída
    f = faturas[0]
    assert f.status == StatusFatura.emitida
    assert f.valor == 8_000  # 40h × 200 (da medição, não do plano)
    assert f.numero == "NF-042"
    assert f.data_vencimento == f.data_emissao + timedelta(days=30)
    assert r["fatura_id"] == f.id


def test_contestacao_permite_nova_medicao(session, projeto, consultor_senior):
    _preparar_apontamentos(session, projeto, consultor_senior)
    m = gerar_medicao(projeto.id, MedicaoCreate(competencia=date(2026, 2, 1)), session)
    contestar_medicao(m["id"], Contestacao(observacoes="Horas de 05/02 não reconhecidas"), session)

    m2 = gerar_medicao(projeto.id, MedicaoCreate(competencia=date(2026, 2, 1)), session)
    assert m2["status"] == "gerada"
    detalhe = obter_medicao(m2["id"], session)
    assert detalhe["linhas"]


# ---------------- TAP ----------------

def test_tap_consolida_proposta_equipe_e_baseline(session, projeto, consultor_senior, cliente):
    _alocar(session, consultor_senior, projeto.fases[1], 40)
    session.add(Proposta(
        cliente_id=cliente.id, nome="Proposta Origem", criada_em=date(2026, 1, 2),
        escopo="Implantação FI/CO", premissas="Key users dedicados",
        valor_estimado=100_000, horas_estimadas=500, projeto_id=projeto.id,
    ))
    session.commit()

    tap = termo_de_abertura(projeto.id, session)
    assert tap["escopo"] == "Implantação FI/CO"
    assert tap["valor_estimado"] == 100_000
    assert len(tap["fases_baseline"]) == 6
    assert tap["termino_previsto"] == tap["fases_baseline"][-1]["fim"]
    assert tap["equipe"][0]["consultor"] == "Consultora Sênior"
    assert "SAP Activate" in tap["metodologia"]


def test_tap_sem_proposta_usa_motor(session, projeto, consultor_senior):
    _alocar(session, consultor_senior, projeto.fases[1], 40)
    tap = termo_de_abertura(projeto.id, session)
    assert tap["proposta"] is None
    assert tap["valor_estimado"] == tap["receita_prevista_motor"] > 0
