"""Testes da Onda 4.3: orçado×realizado com rubricas, modelos de projeto e
agenda mensal do consultor."""
from datetime import date, timedelta

import pytest
from conftest import RequisicaoFalsa
from fastapi import HTTPException

from app.models import (
    Alocacao,
    Apontamento,
    Ausencia,
    CategoriaOrcamento,
    Despesa,
    Feriado,
    Projeto,
    StatusAprovacao,
    StatusDespesa,
    TipoAusencia,
    TipoDespesa,
)
from app.routers.consultores import agenda_do_consultor
from app.routers.modelos import (
    AtividadeCreate,
    ModeloCreate,
    criar_atividade,
    criar_modelo,
    listar_modelos,
    obter_modelo,
    remover_atividade,
    remover_modelo,
)
from app.routers.orcamento import (
    ItemCreate,
    ItemUpdate,
    atualizar_item,
    criar_item,
    obter_orcamento,
)
from app.routers.projetos import ProjetoCreate, criar_projeto
from app.services.projetos import criar_modelo_padrao
from app.services.receita import definir_feriados


@pytest.fixture(autouse=True)
def _limpar_feriados():
    definir_feriados([])
    yield
    definir_feriados([])


SEG = date(2026, 2, 2)


def _alocar_e_apontar(session, projeto, consultor, horas_apontadas=20.0):
    aloc = Alocacao(
        consultor_id=consultor.id, fase_id=projeto.fases[1].id,
        data_inicio=SEG, data_fim=SEG + timedelta(days=11),
        horas_semana=40, taxa_hora_venda=200,
    )
    session.add(aloc)
    session.commit()
    session.refresh(aloc)
    session.add(Apontamento(alocacao_id=aloc.id, data=SEG, horas=horas_apontadas))
    session.commit()
    return aloc


# ---------------- orçamento ----------------

def test_rubricas_automaticas_nascem_com_sugestao_do_motor(session, projeto, consultor_senior):
    _alocar_e_apontar(session, projeto, consultor_senior)
    orc = obter_orcamento(projeto.id, session)

    horas = next(i for i in orc["itens"] if i["categoria"] == "horas")
    # orçado sugerido = 80h previstas × custo 100; realizado = 20h × 100
    assert horas["orcado"] == 8_000
    assert horas["realizado"] == 2_000
    assert horas["automatica"] is True

    despesas = next(i for i in orc["itens"] if i["categoria"] == "despesas")
    assert despesas["realizado"] == 0


def test_despesas_aprovadas_entram_no_realizado(session, projeto, consultor_senior):
    _alocar_e_apontar(session, projeto, consultor_senior)
    session.add(Despesa(
        consultor_id=consultor_senior.id, projeto_id=projeto.id, data=SEG,
        tipo=TipoDespesa.hospedagem, valor=1_200, status=StatusDespesa.aprovada,
    ))
    session.add(Despesa(  # pendente NÃO conta
        consultor_id=consultor_senior.id, projeto_id=projeto.id, data=SEG,
        tipo=TipoDespesa.alimentacao, valor=300, status=StatusDespesa.pendente,
    ))
    session.commit()

    orc = obter_orcamento(projeto.id, session)
    despesas = next(i for i in orc["itens"] if i["categoria"] == "despesas")
    assert despesas["realizado"] == 1_200


def test_rubrica_manual_e_totais(session, projeto, consultor_senior):
    _alocar_e_apontar(session, projeto, consultor_senior)
    item = criar_item(projeto.id, ItemCreate(
        categoria=CategoriaOrcamento.terceiros, descricao="Auditoria",
        valor_orcado=5_000, valor_realizado=2_000,
    ), session)
    assert item["automatica"] is False
    assert item["consumo"] == 0.4

    orc = obter_orcamento(projeto.id, session)
    assert orc["total_orcado"] == 8_000 + 0 + 5_000
    assert orc["total_realizado"] == 2_000 + 0 + 2_000
    assert orc["saldo"] == 9_000


def test_realizado_de_rubrica_automatica_nao_e_editavel(session, projeto, consultor_senior):
    _alocar_e_apontar(session, projeto, consultor_senior)
    orc = obter_orcamento(projeto.id, session)
    horas = next(i for i in orc["itens"] if i["categoria"] == "horas")

    # orçado pode (é a verba); realizado não (vem do motor)
    r = atualizar_item(horas["id"], ItemUpdate(valor_orcado=10_000), session)
    assert r["orcado"] == 10_000
    with pytest.raises(HTTPException):
        atualizar_item(horas["id"], ItemUpdate(valor_realizado=1), session)


# ---------------- modelos de projeto ----------------

def test_modelo_padrao_materializa_templates(session):
    m = criar_modelo_padrao(session)
    assert m.padrao is True
    detalhe = obter_modelo(m.id, session)
    assert len(detalhe["fases"]) == 6
    assert detalhe["total_atividades"] > 0
    assert detalhe["total_gates"] > 0


def test_novo_modelo_nasce_como_copia_e_e_editavel(session):
    criar_modelo_padrao(session)
    novo = criar_modelo(ModeloCreate(nome="AMS", descricao="Sustentação"), session)
    padrao = listar_modelos(session)[0]
    assert novo["total_atividades"] == padrao["total_atividades"]

    criada = criar_atividade(novo["id"], AtividadeCreate(fase="Run", titulo="Rotina de chamados"), session)
    remover_atividade(criada["id"], session)  # e remove sem erro


def test_projeto_criado_com_modelo_usa_entregas_dele(session, cliente):
    padrao = criar_modelo_padrao(session)
    novo = criar_modelo(ModeloCreate(nome="Enxuto"), session)
    # deixa o modelo Enxuto com UMA atividade no Discover
    detalhe = obter_modelo(novo["id"], session)
    discover = next(f for f in detalhe["fases"] if f["nome"] == "Discover")
    for a in discover["atividades"]:
        remover_atividade(a["id"], session)
    criar_atividade(novo["id"], AtividadeCreate(fase="Discover", titulo="Única entrega"), session)

    r = criar_projeto(ProjetoCreate(
        nome="Projeto Enxuto", cliente_id=cliente.id,
        data_inicio=date(2026, 3, 2), modelo_id=novo["id"],
    ), RequisicaoFalsa(), session)
    p = session.get(Projeto, r["id"])
    fase_discover = next(f for f in p.fases if f.nome == "Discover")
    assert [a.titulo for a in fase_discover.atividades] == ["Única entrega"]
    assert p.modelo_id == novo["id"]

    # modelo em uso não pode ser removido; o padrão também não
    with pytest.raises(HTTPException):
        remover_modelo(novo["id"], session)
    with pytest.raises(HTTPException):
        remover_modelo(padrao.id, session)


# ---------------- agenda ----------------

def test_agenda_mostra_alocacao_ausencia_e_feriado(session, projeto, consultor_senior):
    aloc = Alocacao(
        consultor_id=consultor_senior.id, fase_id=projeto.fases[1].id,
        data_inicio=date(2026, 2, 2), data_fim=date(2026, 2, 27),
        horas_semana=40, taxa_hora_venda=200,
    )
    session.add(aloc)
    session.add(Ausencia(
        consultor_id=consultor_senior.id, tipo=TipoAusencia.ferias,
        data_inicio=date(2026, 2, 9), data_fim=date(2026, 2, 13),
        status=StatusAprovacao.aprovada,
    ))
    session.add(Feriado(data=date(2026, 2, 17), nome="Carnaval"))
    session.commit()
    definir_feriados([date(2026, 2, 17)])
    session.add(Apontamento(alocacao_id=aloc.id, data=date(2026, 2, 3), horas=8))
    session.commit()

    agenda = agenda_do_consultor(consultor_senior.id, RequisicaoFalsa(), mes="2026-02", session=session)
    dias = {d["data"]: d for d in agenda["dias"]}

    assert dias["2026-02-03"]["alocacoes"][0]["horas_dia"] == 8.0
    assert dias["2026-02-03"]["horas_apontadas"] == 8.0
    assert dias["2026-02-10"]["ausencia"] == "ferias"
    assert dias["2026-02-10"]["horas_alocadas"] == 0.0  # ausência zera o dia
    assert dias["2026-02-17"]["feriado"] == "Carnaval"
    assert dias["2026-02-17"]["util"] is False
    assert dias["2026-02-07"]["util"] is False  # sábado

    assert agenda["totais"]["dias_ausente"] == 5
    assert agenda["totais"]["horas_apontadas"] == 8.0


def test_agenda_mes_invalido_da_422(session, consultor_senior):
    with pytest.raises(HTTPException):
        agenda_do_consultor(consultor_senior.id, RequisicaoFalsa(), mes="fevereiro", session=session)
