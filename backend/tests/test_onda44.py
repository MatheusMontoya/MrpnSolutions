"""Testes da Onda 4.4: autenticação real, RBAC e trilha de auditoria.

Diferente dos demais testes (que chamam funções dos routers), aqui usamos o
TestClient: middleware de token, guardas de perfil e auditoria só existem na
camada HTTP.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

import app.database as db
from app.main import app
from app.models import Consultor, PerfilUsuario, Senioridade, Usuario
from app.services.auth import gerar_hash, verificar_senha


@pytest.fixture()
def api(monkeypatch):
    """TestClient sobre um banco em memória com um gestor e uma consultora."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)

    with Session(engine) as s:
        consultora = Consultor(
            nome="Ana Teste", senioridade=Senioridade.senior,
            taxa_hora_custo=100, taxa_hora_venda=200,
        )
        s.add(consultora)
        s.commit()
        s.refresh(consultora)
        s.add(Usuario(
            email="gestor@teste.com", nome="Gestor Teste",
            perfil=PerfilUsuario.gestor, senha_hash=gerar_hash("segredo1"),
        ))
        s.add(Usuario(
            email="ana@teste.com", nome="Ana Teste",
            perfil=PerfilUsuario.consultor, consultor_id=consultora.id,
            senha_hash=gerar_hash("segredo1"),
        ))
        s.commit()
    return TestClient(app)


def _logar(api, email="gestor@teste.com", senha="segredo1"):
    r = api.post("/api/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------------- hash ----------------

def test_hash_e_verificacao():
    h = gerar_hash("minha-senha")
    assert verificar_senha("minha-senha", h)
    assert not verificar_senha("outra", h)
    assert gerar_hash("minha-senha") != h  # salt diferente a cada geração


# ---------------- login e token ----------------

def test_login_ok_e_senha_errada(api):
    r = api.post("/api/auth/login", json={"email": "gestor@teste.com", "senha": "segredo1"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["perfil"] == "gestor"
    assert corpo["token"]

    r = api.post("/api/auth/login", json={"email": "gestor@teste.com", "senha": "errada"})
    assert r.status_code == 401


def test_api_exige_token(api):
    assert api.get("/api/projetos").status_code == 401
    assert api.get("/api/clientes").status_code == 401


def test_logout_revoga_token(api):
    h = _logar(api)
    assert api.get("/api/auth/eu", headers=h).status_code == 200
    api.post("/api/auth/logout", headers=h)
    assert api.get("/api/auth/eu", headers=h).status_code == 401


def test_trocar_senha(api):
    h = _logar(api, "ana@teste.com")
    r = api.post("/api/auth/trocar-senha", headers=h,
                 json={"senha_atual": "errada", "senha_nova": "nova-senha"})
    assert r.status_code == 401
    r = api.post("/api/auth/trocar-senha", headers=h,
                 json={"senha_atual": "segredo1", "senha_nova": "nova-senha"})
    assert r.status_code == 200
    assert api.post("/api/auth/login", json={"email": "ana@teste.com", "senha": "nova-senha"}).status_code == 200
    assert api.post("/api/auth/login", json={"email": "ana@teste.com", "senha": "segredo1"}).status_code == 401


# ---------------- RBAC ----------------

def test_consultor_bloqueado_em_rota_de_gestor(api):
    h = _logar(api, "ana@teste.com")
    assert api.get("/api/propostas", headers=h).status_code == 403
    assert api.get("/api/aprovacoes", headers=h).status_code == 403
    assert api.get("/api/copiloto/insights", headers=h).status_code == 403
    assert api.get("/api/usuarios", headers=h).status_code == 403
    # writes guardados em routers mistos
    assert api.post("/api/projetos", headers=h, json={
        "nome": "X", "cliente_id": 1, "data_inicio": "2026-03-02",
    }).status_code == 403


def test_consultor_acessa_o_proprio_espaco(api):
    h = _logar(api, "ana@teste.com")
    assert api.get("/api/projetos", headers=h).status_code == 200
    assert api.get("/api/consultores", headers=h).status_code == 200
    assert api.get("/api/configuracoes", headers=h).status_code == 200
    assert api.get("/api/consultores/1/agenda", headers=h).status_code == 200


def test_gestor_acessa_tudo(api):
    h = _logar(api)
    assert api.get("/api/propostas", headers=h).status_code == 200
    assert api.get("/api/aprovacoes", headers=h).status_code == 200
    assert api.get("/api/usuarios", headers=h).status_code == 200


# ---------------- gestão de usuários ----------------

def test_gestor_cria_usuario_e_email_duplicado_da_409(api):
    h = _logar(api)
    novo = {"email": "novo@teste.com", "nome": "Novo", "senha": "segredo2", "perfil": "gestor"}
    assert api.post("/api/usuarios", headers=h, json=novo).status_code == 201
    assert api.post("/api/usuarios", headers=h, json=novo).status_code == 409
    assert api.post("/api/auth/login", json={"email": "novo@teste.com", "senha": "segredo2"}).status_code == 200


def test_usuario_desativado_nao_loga_e_sessao_morre(api):
    h = _logar(api)
    hc = _logar(api, "ana@teste.com")
    with Session(db.engine) as s:
        ana = s.exec(select(Usuario).where(Usuario.email == "ana@teste.com")).first()
        ana_id = ana.id
    r = api.patch(f"/api/usuarios/{ana_id}", headers=h, json={"ativo": False})
    assert r.status_code == 200
    assert api.post("/api/auth/login", json={"email": "ana@teste.com", "senha": "segredo1"}).status_code == 401
    assert api.get("/api/auth/eu", headers=hc).status_code == 401  # sessão viva morre junto


def test_gestor_nao_desativa_a_si_mesmo(api):
    h = _logar(api)
    eu = api.get("/api/auth/eu", headers=h).json()
    assert api.patch(f"/api/usuarios/{eu['id']}", headers=h, json={"ativo": False}).status_code == 422


# ---------------- auditoria ----------------

def test_mutacoes_entram_na_trilha_de_auditoria(api):
    h = _logar(api)
    api.post("/api/clientes", headers=h, json={"nome": "Cliente Audit", "contato": "x@x.com"})

    r = api.get("/api/auditoria", headers=h)
    assert r.status_code == 200
    eventos = r.json()
    alvo = next(e for e in eventos if e["caminho"] == "/api/clientes")
    assert alvo["metodo"] == "POST"
    assert alvo["status"] == 201
    assert alvo["usuario"] == "Gestor Teste"


def test_auditoria_e_so_do_gestor(api):
    hc = _logar(api, "ana@teste.com")
    assert api.get("/api/auditoria", headers=hc).status_code == 403
