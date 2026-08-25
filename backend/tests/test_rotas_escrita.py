"""Cobertura das rotas que ESCREVEM no banco.

Escrito depois de medir que 58 rotas de escrita não apareciam em teste nenhum —
o mesmo ponto cego que deixou 22 vazamentos de dado passarem despercebidos.

Foco em três perguntas por rota, nesta ordem:
  1. faz o que promete?
  2. recusa entrada inválida em vez de gravar lixo?
  3. respeita a transição de estado (não aprova duas vezes, não reembolsa o que
     não foi aprovado, não apaga o que sustenta outra coisa)?
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.database as db
from app.main import app
from app.models import PerfilUsuario, Usuario
from app.services.auth import gerar_hash
from app.services.projetos import criar_modelo_padrao

HOJE = date.today()
SEGUNDA = HOJE - timedelta(days=HOJE.weekday())


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    with Session(engine) as s:
        criar_modelo_padrao(s)
        for email, perfil in (("ceo@t.com", PerfilUsuario.ceo), ("rh@t.com", PerfilUsuario.rh)):
            s.add(Usuario(email=email, nome=email, perfil=perfil, senha_hash=gerar_hash("segredo1")))
        s.commit()
    return TestClient(app)


def _tok(api, email="ceo@t.com"):
    r = api.post("/api/auth/login", json={"email": email, "senha": "segredo1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def h(api):
    return _tok(api)


@pytest.fixture()
def cenario(api, h):
    """Um projeto real com fase, consultor e alocação — a base de quase tudo."""
    cli = api.post("/api/clientes", headers=h, json={"nome": "Cliente"}).json()
    proj = api.post("/api/projetos", headers=h, json={
        "nome": "Projeto", "cliente_id": cli["id"], "data_inicio": HOJE.isoformat(),
    }).json()
    cons = api.post("/api/consultores", headers=h, json={
        "nome": "Ana", "senioridade": "senior", "taxa_hora_custo": 120, "taxa_hora_venda": 260,
    }).json()
    fase = proj["fases"][2]
    aloc = api.post("/api/alocacoes", headers=h, json={
        "consultor_id": cons["id"], "fase_id": fase["id"], "horas_semana": 40,
    }).json()
    return {"cliente": cli, "projeto": proj, "consultor": cons, "fase": fase, "alocacao": aloc}


# ============ decisões: dinheiro e estado ============

def test_despesa_segue_a_ordem_dos_estados(api, h, cenario):
    d = api.post("/api/despesas", headers=h, json={
        "consultor_id": cenario["consultor"]["id"], "projeto_id": cenario["projeto"]["id"],
        "data": HOJE.isoformat(), "tipo": "outros", "valor": 100.0, "descricao": "taxi",
    })
    assert d.status_code == 201, d.text
    did = d.json()["id"]
    assert api.patch(f"/api/despesas/{did}/decidir", headers=h, json={"status": "aprovada"}).status_code == 200
    assert api.patch(f"/api/despesas/{did}/decidir", headers=h, json={"status": "reembolsada"}).status_code == 200
    assert api.patch(f"/api/despesas/{did}/decidir", headers=h, json={"status": "pendente"}).status_code == 422


def test_reembolsar_despesa_nao_aprovada_e_recusado(api, h, cenario):
    d = api.post("/api/despesas", headers=h, json={
        "consultor_id": cenario["consultor"]["id"], "projeto_id": cenario["projeto"]["id"],
        "data": HOJE.isoformat(), "tipo": "outros", "valor": 50.0,
    }).json()
    r = api.patch(f"/api/despesas/{d['id']}/decidir", headers=h, json={"status": "reembolsada"})
    assert r.status_code == 409, "nao se reembolsa o que ainda nao foi aprovado"


def test_ausencia_decidida(api, h, cenario):
    a = api.post("/api/ausencias", headers=h, json={
        "consultor_id": cenario["consultor"]["id"], "tipo": "ferias",
        "data_inicio": (SEGUNDA + timedelta(days=7)).isoformat(),
        "data_fim": (SEGUNDA + timedelta(days=11)).isoformat(),
    })
    assert a.status_code == 201, a.text
    aid = a.json()["id"]
    assert api.patch(f"/api/ausencias/{aid}/decidir", headers=h, json={"status": "aprovada"}).status_code == 200
    assert api.patch(f"/api/ausencias/{aid}/decidir", headers=h, json={"status": "pendente"}).status_code == 422


def test_rh_decide_despesa_mas_nao_toca_em_fatura(api, cenario):
    hr = _tok(api, "rh@t.com")
    hc = _tok(api)
    d = api.post("/api/despesas", headers=hc, json={
        "consultor_id": cenario["consultor"]["id"], "projeto_id": cenario["projeto"]["id"],
        "data": HOJE.isoformat(), "tipo": "outros", "valor": 10.0,
    }).json()
    assert api.patch(f"/api/despesas/{d['id']}/decidir", headers=hr,
                     json={"status": "aprovada"}).status_code == 200
    assert api.get("/api/faturas", headers=hr).status_code == 403


def test_mudanca_cr_decidida(api, h, cenario):
    m = api.post("/api/mudancas", headers=h, json={
        "projeto_id": cenario["projeto"]["id"], "titulo": "Escopo extra",
        "impacto_horas": 40, "impacto_valor": 10400,
    })
    assert m.status_code == 201, m.text
    assert api.patch(f"/api/mudancas/{m.json()['id']}/decidir", headers=h,
                     json={"status": "aprovada"}).status_code == 200


# ============ destrutivas ============

def test_remover_alocacao_e_proposta(api, h, cenario):
    assert api.delete(f"/api/alocacoes/{cenario['alocacao']['id']}", headers=h).status_code == 204
    p = api.post("/api/propostas", headers=h, json={
        "cliente_id": cenario["cliente"]["id"], "nome": "Prop", "horas_senior": 10,
    }).json()
    assert api.delete(f"/api/propostas/{p['id']}", headers=h).status_code == 204
    assert api.delete(f"/api/propostas/{p['id']}", headers=h).status_code == 404


def test_remover_pendencia_risco_e_feriado(api, h, cenario):
    pen = api.post("/api/pendencias", headers=h, json={
        "projeto_id": cenario["projeto"]["id"], "titulo": "Acesso ao ambiente",
    })
    assert pen.status_code == 201, pen.text
    assert api.delete(f"/api/pendencias/{pen.json()['id']}", headers=h).status_code == 204

    r = api.post("/api/riscos", headers=h, json={
        "projeto_id": cenario["projeto"]["id"], "titulo": "Chave em falta",
    })
    assert r.status_code == 201, r.text
    assert api.delete(f"/api/riscos/{r.json()['id']}", headers=h).status_code == 204

    f = api.post("/api/configuracoes/feriados", headers=h,
                 json={"data": "2026-11-20", "nome": "Consciencia Negra"})
    assert f.status_code == 201, f.text
    assert api.delete(f"/api/configuracoes/feriados/{f.json()['id']}", headers=h).status_code == 204


def test_item_de_orcamento(api, h, cenario):
    it = api.post(f"/api/projetos/{cenario['projeto']['id']}/orcamento/itens", headers=h,
                  json={"categoria": "licencas", "descricao": "SAP", "valor_orcado": 5000})
    assert it.status_code == 201, it.text
    iid = it.json()["id"]
    assert api.patch(f"/api/orcamento/itens/{iid}", headers=h,
                     json={"valor_realizado": 4200}).status_code == 200
    assert api.delete(f"/api/orcamento/itens/{iid}", headers=h).status_code == 204


def test_contrato_criado_alterado_e_removido(api, h, cenario):
    c = api.post("/api/contratos", headers=h, json={
        "cliente_id": cenario["cliente"]["id"], "nome": "MSA",
        "data_inicio": HOJE.isoformat(), "data_fim": (HOJE + timedelta(days=365)).isoformat(),
        "valor": 500000,
    })
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    assert api.patch(f"/api/contratos/{cid}", headers=h, json={"valor": 600000}).status_code == 200
    assert api.delete(f"/api/contratos/{cid}", headers=h).status_code == 204


# ============ alteração de estado ============

def test_atividade_da_fase(api, h, cenario):
    a = api.post("/api/atividades", headers=h, json={
        "fase_id": cenario["fase"]["id"], "titulo": "Workshop",
    })
    assert a.status_code == 201, a.text
    aid = a.json()["id"]
    assert api.patch(f"/api/atividades/{aid}", headers=h, json={"status": "concluida"}).status_code == 200
    assert api.delete(f"/api/atividades/{aid}", headers=h).status_code == 204


def test_reagendar_fase_simula_antes_de_aplicar(api, h, cenario):
    """simular NAO pode tocar no banco — e o que permite mostrar o efeito em
    cascata ao usuario antes de ele confirmar."""
    fase_id = cenario["fase"]["id"]
    pid = cenario["projeto"]["id"]
    nova = (HOJE + timedelta(days=120)).isoformat()

    previa = api.post(f"/api/fases/{fase_id}/reagendar", headers=h,
                      json={"nova_data_fim": nova, "aplicar": False})
    assert previa.status_code == 200, previa.text
    antes = api.get(f"/api/projetos/{pid}", headers=h).json()
    assert [f for f in antes["fases"] if f["id"] == fase_id][0]["data_fim_prevista"] != nova

    aplicado = api.post(f"/api/fases/{fase_id}/reagendar", headers=h,
                        json={"nova_data_fim": nova, "aplicar": True})
    assert aplicado.status_code == 200, aplicado.text
    depois = api.get(f"/api/projetos/{pid}", headers=h).json()
    assert [f for f in depois["fases"] if f["id"] == fase_id][0]["data_fim_prevista"] == nova


def test_sprint_ciclo_completo(api, h, cenario):
    pid = cenario["projeto"]["id"]
    s = api.post(f"/api/projetos/{pid}/sprints", headers=h, json={
        "data_inicio": SEGUNDA.isoformat(), "data_fim": (SEGUNDA + timedelta(days=13)).isoformat(),
        "meta": "Integracao MM",
    })
    assert s.status_code == 201, s.text
    sid = s.json()["id"]
    assert api.patch(f"/api/sprints/{sid}", headers=h, json={"meta": "Outra"}).status_code == 200
    assert api.post(f"/api/sprints/{sid}/iniciar", headers=h, json={}).status_code == 200
    enc = api.post(f"/api/sprints/{sid}/encerrar", headers=h, json={})
    assert enc.status_code == 200, enc.text
    assert "carry_over" in enc.json()


def test_so_uma_sprint_ativa_por_projeto(api, h, cenario):
    pid = cenario["projeto"]["id"]
    a = api.post(f"/api/projetos/{pid}/sprints", headers=h, json={
        "data_inicio": SEGUNDA.isoformat(), "data_fim": (SEGUNDA + timedelta(days=13)).isoformat(),
    }).json()
    b = api.post(f"/api/projetos/{pid}/sprints", headers=h, json={
        "data_inicio": (SEGUNDA + timedelta(days=14)).isoformat(),
        "data_fim": (SEGUNDA + timedelta(days=27)).isoformat(),
    }).json()
    assert api.post(f"/api/sprints/{a['id']}/iniciar", headers=h, json={}).status_code == 200
    assert api.post(f"/api/sprints/{b['id']}/iniciar", headers=h, json={}).status_code == 409


def test_solicitacao_de_alocacao_com_previa_de_conflito(api, h, cenario):
    corpo = {
        "consultor_id": cenario["consultor"]["id"], "fase_id": cenario["fase"]["id"],
        "data_inicio": SEGUNDA.isoformat(), "data_fim": (SEGUNDA + timedelta(days=30)).isoformat(),
        "horas_semana": 40, "justificativa": "reforco",
    }
    previa = api.post("/api/solicitacoes-alocacao/previa-conflitos", headers=h, json={
        k: corpo[k] for k in ("consultor_id", "data_inicio", "data_fim", "horas_semana")
    })
    assert previa.status_code == 200, previa.text

    s = api.post("/api/solicitacoes-alocacao", headers=h, json=corpo)
    assert s.status_code == 201, s.text
    assert api.patch(f"/api/solicitacoes-alocacao/{s.json()['id']}/decidir", headers=h,
                     json={"status": "aprovada"}).status_code == 200


def test_encerrar_projeto_formalmente(api, h, cenario):
    pid = cenario["projeto"]["id"]
    r = api.post(f"/api/projetos/{pid}/encerrar", headers=h,
                 json={"licoes_aprendidas": "Acesso ao ambiente atrasou o Explore"})
    assert r.status_code == 200, r.text
    assert api.get(f"/api/projetos/{pid}", headers=h).json()["status"] == "encerrado"


def test_modelo_de_projeto_com_atividade_e_gate(api, h):
    m = api.post("/api/modelos", headers=h, json={"nome": "Rollout enxuto"})
    assert m.status_code == 201, m.text
    mid = m.json()["id"]
    assert api.patch(f"/api/modelos/{mid}", headers=h, json={"nome": "Rollout"}).status_code == 200
    a = api.post(f"/api/modelos/{mid}/atividades", headers=h,
                 json={"fase": "Explore", "titulo": "Fit-to-standard"})
    assert a.status_code == 201, a.text
    g = api.post(f"/api/modelos/{mid}/gates", headers=h,
                 json={"fase": "Explore", "codigo": "EX-01", "pergunta": "Backlog aprovado?"})
    assert g.status_code == 201, g.text
    assert api.delete(f"/api/modelos/atividades/{a.json()['id']}", headers=h).status_code == 204
    assert api.delete(f"/api/modelos/gates/{g.json()['id']}", headers=h).status_code == 204
    assert api.delete(f"/api/modelos/{mid}", headers=h).status_code == 204


def test_projeto_alterado(api, h, cenario):
    pid = cenario["projeto"]["id"]
    r = api.patch(f"/api/projetos/{pid}", headers=h, json={"nome": "Projeto renomeado"})
    assert r.status_code == 200, r.text
    assert api.get(f"/api/projetos/{pid}", headers=h).json()["nome"] == "Projeto renomeado"


def test_alocacao_alterada(api, h, cenario):
    aid = cenario["alocacao"]["id"]
    r = api.patch(f"/api/alocacoes/{aid}", headers=h, json={"horas_semana": 20})
    assert r.status_code == 200, r.text


def test_pendencia_e_risco_alterados(api, h, cenario):
    pid = cenario["projeto"]["id"]
    pen = api.post("/api/pendencias", headers=h, json={"projeto_id": pid, "titulo": "P"}).json()
    assert api.patch(f"/api/pendencias/{pen['id']}", headers=h,
                     json={"status": "resolvida"}).status_code == 200
    r = api.post("/api/riscos", headers=h, json={"projeto_id": pid, "titulo": "R"}).json()
    assert api.patch(f"/api/riscos/{r['id']}", headers=h,
                     json={"impacto": "alto"}).status_code == 200


def test_proposta_alterada(api, h, cenario):
    p = api.post("/api/propostas", headers=h, json={
        "cliente_id": cenario["cliente"]["id"], "nome": "Prop", "horas_pleno": 100,
    }).json()
    r = api.patch(f"/api/propostas/{p['id']}", headers=h, json={"horas_pleno": 200})
    assert r.status_code == 200, r.text


# ============ entrada inválida ============

@pytest.mark.parametrize("caminho,corpo", [
    ("/api/clientes", {}),
    ("/api/pendencias", {"titulo": "sem projeto"}),
    ("/api/riscos", {"titulo": "sem projeto"}),
    ("/api/mudancas", {"titulo": "sem projeto"}),
])
def test_criacao_sem_campo_obrigatorio_e_recusada(api, h, caminho, corpo):
    assert api.post(caminho, headers=h, json=corpo).status_code == 422


def test_id_inexistente_devolve_404_e_nao_500(api, h):
    casos = [("patch", "/api/pendencias/99999", {"titulo": "x"}),
             ("delete", "/api/riscos/99999", None),
             ("patch", "/api/contratos/99999", {"valor": 1}),
             ("delete", "/api/alocacoes/99999", None)]
    for metodo, caminho, corpo in casos:
        r = getattr(api, metodo)(caminho, headers=h, json=corpo) if corpo is not None \
            else getattr(api, metodo)(caminho, headers=h)
        assert r.status_code == 404, f"{metodo.upper()} {caminho} devolveu {r.status_code}"
