"""Fecha os últimos buracos de cobertura das rotas de escrita.

O test_rotas_escrita.py cobriu 66 das 70 rotas que gravam. Sobraram quatro —
riscos (PATCH/DELETE), item de gate (PATCH) e a pergunta ao copiloto — mais o
que mudou nesta rodada: número de nota fiscal, PATCH de projeto tipado e a
trilha de auditoria, que registrava a rota e nunca o que foi feito nela.
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

import app.database as db
from app.main import app
from app.models import EventoAuditoria, PerfilUsuario, Usuario
from app.services.auth import gerar_hash
from app.services.projetos import criar_modelo_padrao

HOJE = date.today()


@pytest.fixture()
def engine_teste(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    with Session(engine) as s:
        criar_modelo_padrao(s)
        s.add(Usuario(
            email="ceo@t.com", nome="CEO", perfil=PerfilUsuario.ceo,
            senha_hash=gerar_hash("segredo1"),
        ))
        s.commit()
    return engine


@pytest.fixture()
def api(engine_teste):
    return TestClient(app)


@pytest.fixture()
def h(api):
    r = api.post("/api/auth/login", json={"email": "ceo@t.com", "senha": "segredo1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def projeto(api, h):
    cli = api.post("/api/clientes", headers=h, json={"nome": "Cliente"}).json()
    return api.post("/api/projetos", headers=h, json={
        "nome": "Projeto", "cliente_id": cli["id"], "data_inicio": HOJE.isoformat(),
    }).json()


# ============ riscos: as duas rotas que nunca foram exercidas ============

def test_risco_muda_severidade_ao_reclassificar(api, h, projeto):
    """Severidade é derivada de probabilidade × impacto — o PATCH tem de refleti-la."""
    r = api.post("/api/riscos", headers=h, json={
        "projeto_id": projeto["id"], "titulo": "Consultor-chave sai",
        "probabilidade": "baixo", "impacto": "baixo",
    })
    assert r.status_code == 201, r.text
    risco = r.json()
    assert risco["severidade"] == "baixa"

    r = api.patch(f"/api/riscos/{risco['id']}", headers=h,
                  json={"probabilidade": "alto", "impacto": "alto"})
    assert r.status_code == 200, r.text
    assert r.json()["severidade"] == "critica"


def test_risco_aceita_fechamento_e_recusa_status_invalido(api, h, projeto):
    risco = api.post("/api/riscos", headers=h, json={
        "projeto_id": projeto["id"], "titulo": "Escopo cresce",
    }).json()

    assert api.patch(f"/api/riscos/{risco['id']}", headers=h,
                     json={"status": "mitigado"}).json()["status"] == "mitigado"
    # enum inválido é 422, não 500
    assert api.patch(f"/api/riscos/{risco['id']}", headers=h,
                     json={"status": "resolvido_talvez"}).status_code == 422


def test_risco_removido_some_da_lista(api, h, projeto):
    risco = api.post("/api/riscos", headers=h, json={
        "projeto_id": projeto["id"], "titulo": "Integração atrasa",
    }).json()

    assert api.delete(f"/api/riscos/{risco['id']}", headers=h).status_code == 204
    lista = api.get(f"/api/riscos?projeto_id={projeto['id']}", headers=h).json()
    assert [x["id"] for x in lista] == []
    # segunda remoção não pode virar 500
    assert api.delete(f"/api/riscos/{risco['id']}", headers=h).status_code == 404


def test_risco_em_projeto_inexistente_e_404(api, h):
    r = api.post("/api/riscos", headers=h, json={"projeto_id": 9999, "titulo": "X"})
    assert r.status_code == 404


# ============ item de gate ============

def _primeiro_item_de_gate(api, h, projeto_id):
    detalhe = api.get(f"/api/projetos/{projeto_id}", headers=h).json()
    for fase in detalhe["fases"]:
        itens = fase.get("gate", {}).get("itens") or []
        if itens:
            return fase, itens[0]
    pytest.skip("modelo padrão não trouxe itens de gate")


def test_item_de_gate_muda_o_semaforo_da_fase(api, h, projeto):
    fase, item = _primeiro_item_de_gate(api, h, projeto["id"])

    r = api.patch(f"/api/gates/{item['id']}", headers=h, json={
        "status": "vermelho", "plano_acao": "Reunir com o cliente", "responsavel": "Ana",
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "vermelho"
    assert r.json()["plano_acao"] == "Reunir com o cliente"

    # o resumo da fase tem de acompanhar
    detalhe = api.get(f"/api/projetos/{projeto['id']}", headers=h).json()
    atual = next(f for f in detalhe["fases"] if f["id"] == fase["id"])
    assert atual["gate"]["vermelho"] >= 1


def test_item_de_gate_recusa_status_invalido_e_id_inexistente(api, h, projeto):
    _, item = _primeiro_item_de_gate(api, h, projeto["id"])
    assert api.patch(f"/api/gates/{item['id']}", headers=h,
                     json={"status": "roxo"}).status_code == 422
    assert api.patch("/api/gates/999999", headers=h,
                     json={"status": "verde"}).status_code == 404


# ============ copiloto ============

def test_copiloto_responde_sem_chave_configurada(api, h):
    """Sem chave da Anthropic o copiloto degrada para a resposta determinística —
    o que o motor calculou —, nunca para um 500."""
    r = api.post("/api/copiloto/perguntar", headers=h, json={"pergunta": "Como está a margem?"})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["ia_generativa"] is False
    assert corpo["resposta"].strip()


def test_copiloto_recusa_corpo_sem_pergunta(api, h):
    assert api.post("/api/copiloto/perguntar", headers=h, json={}).status_code == 422


# ============ PATCH /projetos tipado ============

def test_projeto_renomeia_e_recusa_status_invalido(api, h, projeto):
    assert api.patch(f"/api/projetos/{projeto['id']}", headers=h,
                     json={"nome": "Projeto Renomeado"}).status_code == 200
    assert api.get(f"/api/projetos/{projeto['id']}", headers=h).json()["nome"] == "Projeto Renomeado"

    # antes de virar schema, isto era ValueError → 500
    assert api.patch(f"/api/projetos/{projeto['id']}", headers=h,
                     json={"status": "quase_pronto"}).status_code == 422
    # nome vazio também não passa
    assert api.patch(f"/api/projetos/{projeto['id']}", headers=h,
                     json={"nome": ""}).status_code == 422


# ============ número da nota fiscal ============

@pytest.fixture()
def fatura(api, h, projeto):
    """Uma fatura prevista: precisa de alocação para o motor gerar receita."""
    cons = api.post("/api/consultores", headers=h, json={
        "nome": "Ana", "senioridade": "senior", "taxa_hora_custo": 120, "taxa_hora_venda": 260,
    }).json()
    fase = projeto["fases"][2]
    api.post("/api/alocacoes", headers=h, json={
        "consultor_id": cons["id"], "fase_id": fase["id"], "horas_semana": 40,
    })
    api.post(f"/api/projetos/{projeto['id']}/faturas/gerar", headers=h, json={})
    faturas = api.get("/api/faturas", headers=h).json()["faturas"]
    assert faturas, "o motor não gerou fatura prevista"
    return faturas[0]


def test_numero_da_nota_e_digitavel_depois_da_emissao(api, h, fatura):
    """A coluna existia na tela e nunca podia ser preenchida: o número só era
    aceito junto da emissão, quando a nota ainda nem saiu do sistema fiscal."""
    assert api.patch(f"/api/faturas/{fatura['id']}", headers=h,
                     json={"status": "emitida"}).status_code == 200

    r = api.patch(f"/api/faturas/{fatura['id']}", headers=h, json={"numero": " 001234 "})
    assert r.status_code == 200, r.text
    assert r.json()["numero"] == "001234"
    assert r.json()["status"] == "emitida"  # o status não se mexe

    # corrigir depois também vale
    assert api.patch(f"/api/faturas/{fatura['id']}", headers=h,
                     json={"numero": "9999"}).json()["numero"] == "9999"


def test_numero_recusado_em_fatura_ainda_prevista(api, h, fatura):
    r = api.patch(f"/api/faturas/{fatura['id']}", headers=h, json={"numero": "001"})
    assert r.status_code == 409


def test_patch_de_fatura_sem_status_nem_numero_e_422(api, h, fatura):
    assert api.patch(f"/api/faturas/{fatura['id']}", headers=h, json={}).status_code == 422


# ============ trilha de auditoria ============

def test_auditoria_registra_o_que_mudou(api, h, engine_teste, projeto):
    """Antes gravava só 'PATCH /api/projetos/1' — sem dizer o quê."""
    api.patch(f"/api/projetos/{projeto['id']}", headers=h, json={"status": "concluido"})

    with Session(engine_teste) as s:
        evento = s.exec(
            select(EventoAuditoria)
            .where(EventoAuditoria.caminho == f"/api/projetos/{projeto['id']}")
            .where(EventoAuditoria.metodo == "PATCH")
        ).first()
    assert evento is not None
    assert "concluido" in evento.detalhe
    assert evento.usuario == "CEO"


def test_auditoria_nunca_grava_senha(api, h, engine_teste):
    """A tela de Auditoria é lida pelo CEO: senha ali seria um segundo lugar
    de onde vazar credencial."""
    api.post("/api/auth/trocar-senha", headers=h,
             json={"senha_atual": "segredo1", "senha_nova": "outroSegredo9"})

    with Session(engine_teste) as s:
        eventos = s.exec(
            select(EventoAuditoria).where(EventoAuditoria.caminho == "/api/auth/trocar-senha")
        ).all()
    assert eventos, "a troca de senha não foi auditada"
    for e in eventos:
        assert "segredo1" not in e.detalhe
        assert "outroSegredo9" not in e.detalhe
        assert '"senha_nova": "***"' in e.detalhe


def test_corpo_da_requisicao_chega_intacto_na_rota(api, h, projeto):
    """O middleware CONSOME o stream para auditar. Se não reemitir o corpo,
    toda rota POST passa a receber vazio e responde 422."""
    r = api.post("/api/riscos", headers=h, json={
        "projeto_id": projeto["id"], "titulo": "Corpo tem de chegar inteiro",
        "resposta": "x" * 300,
    })
    assert r.status_code == 201, r.text
    assert r.json()["titulo"] == "Corpo tem de chegar inteiro"
    assert len(r.json()["resposta"]) == 300


def test_auditoria_aguenta_corpo_que_nao_e_json(api, h):
    """DELETE não manda corpo; corpo inválido não pode derrubar o middleware."""
    r = api.request("DELETE", "/api/riscos/999999", headers=h)
    assert r.status_code == 404  # 404 da rota, não 500 do middleware
