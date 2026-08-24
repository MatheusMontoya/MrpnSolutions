"""Isolamento horizontal: um consultor não alcança o dado de outro.

O RBAC de perfil (test_onda44) responde "esta ROTA é do seu perfil?".
Estes testes respondem a outra pergunta, que estava sem guarda nenhuma:
"esta LINHA é sua?". Foram escritos a partir de 22 vazamentos confirmados —
custo/hora de colegas, horas lançadas, agenda, despesas e a chave da API.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.database as db
from app.main import app
from app.models import (
    Alocacao, Cliente, Configuracao, Consultor, Despesa, Fase, PerfilUsuario,
    Projeto, Senioridade, StatusDespesa, TipoDespesa, Usuario,
)
from app.services.auth import gerar_hash
from datetime import date, timedelta


@pytest.fixture()
def api(monkeypatch):
    """Duas consultoras (Ana id=1, Bruno id=2), um CEO, e dado de cada uma."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)

    with Session(engine) as s:
        ana = Consultor(nome="Ana", senioridade=Senioridade.senior, taxa_hora_custo=120, taxa_hora_venda=260)
        bruno = Consultor(nome="Bruno", senioridade=Senioridade.pleno, taxa_hora_custo=90, taxa_hora_venda=200)
        s.add(ana); s.add(bruno); s.commit(); s.refresh(ana); s.refresh(bruno)

        cliente = Cliente(nome="Cliente X")
        s.add(cliente); s.commit(); s.refresh(cliente)
        proj = Projeto(nome="Projeto do Bruno", cliente_id=cliente.id, data_inicio=date.today())
        s.add(proj); s.commit(); s.refresh(proj)
        fase = Fase(projeto_id=proj.id, nome="Realize", ordem=3,
                    data_inicio_prevista=date.today(), data_fim_prevista=date.today() + timedelta(days=30))
        s.add(fase); s.commit(); s.refresh(fase)
        aloc_bruno = Alocacao(consultor_id=bruno.id, fase_id=fase.id, horas_semana=40,
                              taxa_hora_venda=200, data_inicio=date.today(),
                              data_fim=date.today() + timedelta(days=30))
        s.add(aloc_bruno); s.commit(); s.refresh(aloc_bruno)

        s.add(Despesa(consultor_id=bruno.id, projeto_id=proj.id, tipo=TipoDespesa.outros,
                      data=date.today(), valor=999.0, descricao="secreta do Bruno",
                      status=StatusDespesa.pendente))
        s.add(Configuracao(anthropic_api_key="sk-ant-SEGREDO", cnpj="11.111.111/0001-11"))
        for email, perfil, cid in (("ana@t.com", PerfilUsuario.consultor, ana.id),
                                   ("bruno@t.com", PerfilUsuario.consultor, bruno.id),
                                   ("ceo@t.com", PerfilUsuario.ceo, None)):
            s.add(Usuario(email=email, nome=email, perfil=perfil, consultor_id=cid,
                          senha_hash=gerar_hash("segredo1")))
        s.commit()
        pytest.ALOC_BRUNO = aloc_bruno.id
        pytest.PROJ = proj.id
    return TestClient(app)


def _h(api, email):
    r = api.post("/api/auth/login", json={"email": email, "senha": "segredo1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------- o bug relatado: horas e custo de colegas ----------

def test_consultor_nao_ve_taxas_de_ninguem(api):
    cs = api.get("/api/consultores", headers=_h(api, "ana@t.com")).json()
    assert len(cs) == 1 and cs[0]["nome"] == "Ana", "deveria ver só a si mesma"
    assert "taxa_hora_custo" not in cs[0] and "taxa_hora_venda" not in cs[0]


def test_consultor_nao_le_horas_de_outro(api):
    h = _h(api, "ana@t.com")
    r = api.get("/api/apontamentos/semana?consultor_id=2", headers=h)
    # o filtro é forçado para o próprio: nunca devolve dado do Bruno
    assert r.status_code != 200 or r.json()["consultor_id"] == 1


def test_consultor_nao_ve_agenda_nem_ficha_de_outro(api):
    h = _h(api, "ana@t.com")
    assert api.get("/api/consultores/2/agenda", headers=h).status_code == 403
    assert api.get("/api/consultores/2", headers=h).status_code == 403
    assert api.get("/api/consultores/2/painel", headers=h).status_code == 403


def test_consultor_nao_ve_heatmap_nem_capacidade(api):
    h = _h(api, "ana@t.com")
    assert api.get("/api/consultores/utilizacao", headers=h).status_code == 403
    assert api.get("/api/consultores/capacidade", headers=h).status_code == 403


# ---------- escrita em registro alheio ----------

def test_consultor_nao_lanca_horas_na_alocacao_de_outro(api):
    h = _h(api, "ana@t.com")
    r = api.post("/api/apontamentos", headers=h, json={
        "alocacao_id": pytest.ALOC_BRUNO, "data": date.today().isoformat(), "horas": 8,
    })
    assert r.status_code == 403


def test_consultor_nao_envia_semana_de_outro(api):
    h = _h(api, "ana@t.com")
    r = api.post("/api/apontamentos/semana/enviar", headers=h,
                 json={"consultor_id": 2, "semana": date.today().isoformat()})
    assert r.status_code == 403


# ---------- despesas ----------

def test_consultor_so_ve_as_proprias_despesas(api):
    ds = api.get("/api/despesas", headers=_h(api, "ana@t.com")).json()
    assert all(d["consultor_id"] == 1 for d in ds)
    assert not any("secreta do Bruno" in (d.get("descricao") or "") for d in ds)


def test_consultor_nao_apaga_despesa_alheia(api):
    h = _h(api, "ana@t.com")
    ds = api.get("/api/despesas", headers=_h(api, "ceo@t.com")).json()
    do_bruno = next(d["id"] for d in ds if d["consultor_id"] == 2)
    assert api.delete(f"/api/despesas/{do_bruno}", headers=h).status_code == 403


def test_despesa_lancada_por_consultor_fica_no_nome_dele(api):
    h = _h(api, "ana@t.com")
    r = api.post("/api/despesas", headers=h, json={
        "consultor_id": 2,  # tentando lançar no nome do Bruno
        "projeto_id": pytest.PROJ, "tipo": "outros",
        "data": date.today().isoformat(), "valor": 10.0, "descricao": "x",
    })
    assert r.status_code == 201
    assert r.json()["consultor_id"] == 1, "o dono deve ser forçado para quem enviou"


# ---------- segredos da configuração ----------

def test_consultor_nao_recebe_a_chave_da_api(api):
    cfg = api.get("/api/configuracoes", headers=_h(api, "ana@t.com")).json()
    for proibido in ("anthropic_api_key", "cnpj", "meta_margem", "taxa_senior"):
        assert proibido not in cfg, f"{proibido} vazou para o consultor"
    assert "taxa_km" in cfg, "o consultor precisa da taxa de km para lançar despesa"


def test_gestao_continua_vendo_tudo(api):
    h = _h(api, "ceo@t.com")
    assert api.get("/api/consultores", headers=h).status_code == 200
    assert len(api.get("/api/consultores", headers=h).json()) == 2
    assert api.get("/api/consultores/utilizacao", headers=h).status_code == 200
    assert api.get("/api/consultores/2/agenda", headers=h).status_code == 200
    assert "anthropic_api_key" in api.get("/api/configuracoes", headers=h).json()


# ---------- projetos ----------

def test_consultor_nao_ve_projeto_alheio_nem_financeiro(api):
    h = _h(api, "ana@t.com")
    assert api.get("/api/projetos", headers=h).json() == [], "Ana não tem alocação"
    assert api.get(f"/api/projetos/{pytest.PROJ}", headers=h).status_code == 403
    assert api.get(f"/api/projetos/{pytest.PROJ}/evm", headers=h).status_code == 403


def test_consultor_ve_o_projeto_em_que_esta_alocado(api):
    ps = api.get("/api/projetos", headers=_h(api, "bruno@t.com")).json()
    assert len(ps) == 1 and ps[0]["nome"] == "Projeto do Bruno"
