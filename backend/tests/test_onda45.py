"""Testes da Onda 4.5: modo ágil/híbrido — sprints, backlog e kanban."""
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.models import Alocacao, Apontamento, StatusAtividade
from app.routers.agil import (
    MoverAtividade,
    SprintCreate,
    criar_sprint,
    encerrar_sprint,
    iniciar_sprint,
    mover_atividade,
    quadro_agil,
)
from app.services.receita import definir_feriados


@pytest.fixture(autouse=True)
def _limpar_feriados():
    definir_feriados([])
    yield
    definir_feriados([])


SEG = date(2026, 2, 2)


def _sprint(session, projeto, inicio=SEG, fim=SEG + timedelta(days=11)):
    return criar_sprint(projeto.id, SprintCreate(
        meta="Meta de teste", data_inicio=inicio, data_fim=fim,
    ), session)


def test_sprint_numera_sequencialmente(session, projeto):
    s1 = _sprint(session, projeto)
    s2 = _sprint(session, projeto)
    assert (s1["numero"], s2["numero"]) == (1, 2)
    assert s1["nome"] == "Sprint 1"  # nome default


def test_so_uma_sprint_ativa_por_projeto(session, projeto):
    s1 = _sprint(session, projeto)
    s2 = _sprint(session, projeto)
    iniciar_sprint(s1["id"], session)
    with pytest.raises(HTTPException):
        iniciar_sprint(s2["id"], session)


def test_backlog_traz_entregas_abertas_e_puxar_para_sprint(session, projeto):
    s = _sprint(session, projeto)
    quadro = quadro_agil(projeto.id, session)
    assert len(quadro["backlog"]) > 0  # entregas padrão das 6 fases
    atividade = quadro["backlog"][0]

    r = mover_atividade(atividade["id"], MoverAtividade(sprint_id=s["id"]), session)
    assert r["sprint_id"] == s["id"]

    quadro = quadro_agil(projeto.id, session)
    assert all(a["id"] != atividade["id"] for a in quadro["backlog"])
    sprint = next(x for x in quadro["sprints"] if x["id"] == s["id"])
    assert sprint["total"] == 1


def test_atividade_de_outro_projeto_nao_entra(session, projeto, cliente):
    from datetime import date as d

    from app.models import Projeto
    from app.services.projetos import criar_projeto_com_fases

    outro = criar_projeto_com_fases(session, Projeto(
        nome="Outro", cliente_id=cliente.id, data_inicio=d(2026, 3, 2),
    ))
    s = _sprint(session, projeto)
    atividade_do_outro = outro.fases[0].atividades[0]
    with pytest.raises(HTTPException):
        mover_atividade(atividade_do_outro.id, MoverAtividade(sprint_id=s["id"]), session)


def test_encerrar_devolve_pendentes_ao_backlog_com_carry_over(session, projeto):
    s = _sprint(session, projeto)
    iniciar_sprint(s["id"], session)
    quadro = quadro_agil(projeto.id, session)
    tres = quadro["backlog"][:3]
    for a in tres:
        mover_atividade(a["id"], MoverAtividade(sprint_id=s["id"]), session)
    # conclui só a primeira
    from app.models import Atividade

    atv = session.get(Atividade, tres[0]["id"])
    atv.status = StatusAtividade.concluida
    session.add(atv)
    session.commit()

    r = encerrar_sprint(s["id"], session)
    assert r["status"] == "encerrada"
    assert r["carry_over"] == 2
    assert r["concluidas"] == 1  # a concluída permanece na sprint (histórico)

    quadro = quadro_agil(projeto.id, session)
    ids_backlog = {a["id"] for a in quadro["backlog"]}
    assert tres[1]["id"] in ids_backlog and tres[2]["id"] in ids_backlog


def test_encerrar_sprint_planejada_da_409(session, projeto):
    s = _sprint(session, projeto)
    with pytest.raises(HTTPException):
        encerrar_sprint(s["id"], session)


def test_horas_do_periodo_da_sprint(session, projeto, consultor_senior):
    aloc = Alocacao(
        consultor_id=consultor_senior.id, fase_id=projeto.fases[1].id,
        data_inicio=SEG, data_fim=SEG + timedelta(days=11),
        horas_semana=40, taxa_hora_venda=200,
    )
    session.add(aloc)
    session.commit()
    session.refresh(aloc)
    session.add(Apontamento(alocacao_id=aloc.id, data=SEG + timedelta(days=1), horas=8))
    session.add(Apontamento(alocacao_id=aloc.id, data=SEG + timedelta(days=30), horas=5))  # fora
    session.commit()

    s = _sprint(session, projeto)
    quadro = quadro_agil(projeto.id, session)
    sprint = next(x for x in quadro["sprints"] if x["id"] == s["id"])
    assert sprint["horas_no_periodo"] == 8.0


def test_sprint_ativa_id_no_quadro(session, projeto):
    s = _sprint(session, projeto)
    assert quadro_agil(projeto.id, session)["sprint_ativa_id"] is None
    iniciar_sprint(s["id"], session)
    assert quadro_agil(projeto.id, session)["sprint_ativa_id"] == s["id"]
