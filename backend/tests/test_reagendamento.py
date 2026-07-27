"""Testes do recálculo em cascata (services/reagendamento.py)."""
from datetime import date, timedelta

import pytest
from sqlmodel import select

from app.models import Alocacao, Fase
from app.services.reagendamento import aplicar_reagendamento, simular_reagendamento
from app.services.receita import horas_previstas


def _fase(session, projeto, nome) -> Fase:
    return session.exec(
        select(Fase).where(Fase.projeto_id == projeto.id, Fase.nome == nome)
    ).one()


def _alocar(session, consultor, fase, horas_semana, taxa=None):
    a = Alocacao(
        consultor_id=consultor.id,
        fase_id=fase.id,
        data_inicio=fase.data_inicio_prevista,
        data_fim=fase.data_fim_prevista,
        horas_semana=horas_semana,
        taxa_hora_venda=taxa if taxa is not None else consultor.taxa_hora_venda,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_atraso_de_fase_no_meio_desloca_seguintes(session, projeto, consultor_senior):
    """Atrasar Explore em 14 dias: Realize/Deploy/Run deslocam 14 dias;
    Discover e Prepare não mudam."""
    explore = _fase(session, projeto, "Explore")
    datas_antes = {
        f.nome: (f.data_inicio_prevista, f.data_fim_prevista) for f in projeto.fases
    }
    nova_fim = explore.data_fim_prevista + timedelta(days=14)

    diff = aplicar_reagendamento(session, explore.id, nova_fim)
    assert diff["delta_dias"] == 14

    for f in session.exec(select(Fase).where(Fase.projeto_id == projeto.id)):
        inicio_antes, fim_antes = datas_antes[f.nome]
        if f.nome in ("Discover", "Prepare"):
            assert (f.data_inicio_prevista, f.data_fim_prevista) == (inicio_antes, fim_antes)
        elif f.nome == "Explore":
            assert f.data_inicio_prevista == inicio_antes
            assert f.data_fim_prevista == fim_antes + timedelta(days=14)
        else:  # Realize, Deploy, Run deslocam inteiras
            assert f.data_inicio_prevista == inicio_antes + timedelta(days=14)
            assert f.data_fim_prevista == fim_antes + timedelta(days=14)


def test_atraso_estende_alocacao_da_fase_e_desloca_das_seguintes(session, projeto, consultor_senior):
    explore = _fase(session, projeto, "Explore")
    realize = _fase(session, projeto, "Realize")
    aloc_explore = _alocar(session, consultor_senior, explore, 40)
    aloc_realize = _alocar(session, consultor_senior, realize, 20)

    inicio_explore = aloc_explore.data_inicio
    fim_explore = aloc_explore.data_fim
    inicio_realize = aloc_realize.data_inicio
    fim_realize = aloc_realize.data_fim

    aplicar_reagendamento(session, explore.id, explore.data_fim_prevista + timedelta(days=7))

    session.refresh(aloc_explore)
    session.refresh(aloc_realize)
    # alocação da fase atrasada: início mantido, fim estendido
    assert aloc_explore.data_inicio == inicio_explore
    assert aloc_explore.data_fim == fim_explore + timedelta(days=7)
    # alocação da fase seguinte: desloca inteira
    assert aloc_realize.data_inicio == inicio_realize + timedelta(days=7)
    assert aloc_realize.data_fim == fim_realize + timedelta(days=7)


def test_diff_receita_mensal_antes_depois(session, projeto, consultor_senior):
    """O diff traz receita mensal antes→depois e o aumento total corresponde
    às horas adicionais da extensão (1 semana × 40h × taxa)."""
    explore = _fase(session, projeto, "Explore")
    aloc = _alocar(session, consultor_senior, explore, 40)

    horas_antes = horas_previstas(aloc.data_inicio, aloc.data_fim, 40)
    diff = simular_reagendamento(session, explore.id, explore.data_fim_prevista + timedelta(days=7))

    assert diff["receita_total"]["antes"] == pytest.approx(horas_antes * 200.0)
    # +7 dias corridos = +5 dias úteis = +40h × R$200
    assert diff["receita_total"]["depois"] - diff["receita_total"]["antes"] == pytest.approx(8000.0)
    # todo mês do diff traz antes, depois e delta consistentes
    for linha in diff["receita_mensal"]:
        assert linha["delta"] == pytest.approx(linha["depois"] - linha["antes"], abs=0.01)
    # simulação não persiste nada
    session.refresh(aloc)
    assert horas_previstas(aloc.data_inicio, aloc.data_fim, 40) == horas_antes


def test_diff_respeita_taxa_negociada(session, projeto, consultor_senior):
    """Extensão de alocação com taxa negociada (150 ≠ 200 default) gera
    receita adicional pela taxa da alocação."""
    explore = _fase(session, projeto, "Explore")
    _alocar(session, consultor_senior, explore, 40, taxa=150.0)

    diff = simular_reagendamento(session, explore.id, explore.data_fim_prevista + timedelta(days=7))
    assert diff["receita_total"]["depois"] - diff["receita_total"]["antes"] == pytest.approx(
        5 * 8 * 150.0
    )


def test_superalocacao_causada_por_atraso(session, projeto, cliente, consultor_senior):
    """Atraso que faz Realize invadir o período de outra alocação do mesmo
    consultor gera semana >40h (superalocado)."""
    from app.models import Projeto
    from app.services.projetos import criar_projeto_com_fases
    from app.services.receita import utilizacao_semanal

    explore = _fase(session, projeto, "Explore")
    realize = _fase(session, projeto, "Realize")
    aloc_realize = _alocar(session, consultor_senior, realize, 40)

    # outro projeto, começando quando Realize terminaria: 20h/semana
    p2 = criar_projeto_com_fases(
        session,
        Projeto(nome="Projeto 2", cliente_id=cliente.id,
                data_inicio=realize.data_fim_prevista + timedelta(days=1)),
    )
    aloc_p2 = _alocar(session, consultor_senior, _fase(session, p2, "Discover"), 20)

    # sem atraso: semana do início do p2 tem 20h (ocioso)
    semana = aloc_p2.data_inicio  # é segunda? garantir via cálculo
    from app.services.receita import segunda_da_semana

    semana = segunda_da_semana(aloc_p2.data_inicio + timedelta(days=7))
    antes = utilizacao_semanal([aloc_realize, aloc_p2], semana)
    assert antes["status"] != "superalocado"

    # atraso de 3 semanas no Explore empurra Realize para cima do p2
    aplicar_reagendamento(session, explore.id, explore.data_fim_prevista + timedelta(days=21))
    session.refresh(aloc_realize)
    session.refresh(aloc_p2)

    depois = utilizacao_semanal([aloc_realize, aloc_p2], semana)
    assert depois["horas"] == 60
    assert depois["status"] == "superalocado"


def test_nova_data_fim_invalida(session, projeto):
    explore = _fase(session, projeto, "Explore")
    with pytest.raises(ValueError):
        simular_reagendamento(
            session, explore.id, explore.data_inicio_prevista - timedelta(days=1)
        )
