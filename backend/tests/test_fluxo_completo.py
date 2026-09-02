"""A jornada inteira do negócio, por HTTP, do zero à fatura recebida.

É o teste mais importante do repositório: prova a promessa central do produto —
que projeto, alocação e receita são a mesma coisa vista de ângulos diferentes —
percorrendo o caminho real de um CEO num banco vazio.

Por HTTP (TestClient) e não chamando as funções: só assim passa pelo middleware
de token, pelas guardas de perfil e pela serialização. Era exatamente essa
camada que estava sem cobertura enquanto 22 vazamentos de dado passavam.
"""
from datetime import date, timedelta

from conftest import competencia_estavel, segunda_estavel

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.database as db
from app.main import app
from app.models import PerfilUsuario, Usuario
from app.services.auth import gerar_hash
from app.services.projetos import criar_modelo_padrao


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db, "engine", engine)
    with Session(engine) as s:
        criar_modelo_padrao(s)   # o template Activate, como em produção
        s.add(Usuario(email="ceo@t.com", nome="CEO", perfil=PerfilUsuario.ceo,
                      senha_hash=gerar_hash("segredo1")))
        s.commit()
    return TestClient(app)


@pytest.fixture()
def h(api):
    r = api.post("/api/auth/login", json={"email": "ceo@t.com", "senha": "segredo1"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_do_cliente_ate_a_fatura_recebida(api, h):
    hoje = competencia_estavel()

    # 1. cliente
    cli = api.post("/api/clientes", headers=h, json={"nome": "Aurora", "contato": "a@a.com"})
    assert cli.status_code == 201, cli.text
    cliente_id = cli.json()["id"]

    # 2. proposta com mix de senioridade — o valor sai do cálculo, não do chute
    prop = api.post("/api/propostas", headers=h, json={
        "cliente_id": cliente_id, "nome": "Implantação S/4",
        "horas_junior": 100, "horas_pleno": 200, "horas_senior": 300,
    })
    assert prop.status_code == 201, prop.text
    proposta_id = prop.json()["id"]
    assert prop.json()["valor_estimado"] > 0, "a precificação por mix tem de gerar valor"

    # 3. avança no funil até aprovada
    for _ in range(3):
        api.post(f"/api/propostas/{proposta_id}/avancar", headers=h, json={})
    assert api.get("/api/propostas", headers=h).json()["propostas"][0]["estagio"] == "aprovada"

    # 4. converter cria o projeto COM as 6 fases do Activate
    conv = api.post(f"/api/propostas/{proposta_id}/converter", headers=h,
                    json={"data_inicio": hoje.isoformat()})
    assert conv.status_code in (200, 201), conv.text
    projeto_id = conv.json()["projeto_id"]
    projeto = api.get(f"/api/projetos/{projeto_id}", headers=h).json()
    assert len(projeto["fases"]) == 6, "todo projeto nasce com as 6 fases"
    fase_id = projeto["fases"][2]["id"]  # Explore

    # 5. consultor e alocação — é aqui que o projeto vira receita prevista
    cons = api.post("/api/consultores", headers=h, json={
        "nome": "Ana", "senioridade": "senior", "taxa_hora_custo": 120, "taxa_hora_venda": 260,
    })
    assert cons.status_code == 201, cons.text
    consultor_id = cons.json()["id"]

    aloc = api.post("/api/alocacoes", headers=h, json={
        "consultor_id": consultor_id, "fase_id": fase_id, "horas_semana": 40,
    })
    assert aloc.status_code == 201, aloc.text
    alocacao_id = aloc.json()["id"]

    depois = api.get(f"/api/projetos/{projeto_id}", headers=h).json()
    assert depois["receita_prevista_total"] > 0, "alocar tem de gerar receita prevista"

    # 6. o consultor lança horas na própria alocação
    api.post("/api/usuarios", headers=h, json={
        "email": "ana@t.com", "nome": "Ana", "senha": "segredo1",
        "perfil": "consultor", "consultor_id": consultor_id,
    })
    ha = {"Authorization": f"Bearer {api.post('/api/auth/login', json={'email': 'ana@t.com', 'senha': 'segredo1'}).json()['token']}"}

    segunda = segunda_estavel()
    for i in range(5):
        r = api.post("/api/apontamentos", headers=ha, json={
            "alocacao_id": alocacao_id, "data": (segunda + timedelta(days=i)).isoformat(),
            "horas": 8, "descricao": "Workshop fit-to-standard",
        })
        assert r.status_code == 201, r.text

    # 7. envia a semana e o CEO aprova
    env = api.post("/api/apontamentos/semana/enviar", headers=ha,
                   json={"consultor_id": consultor_id, "semana": segunda.isoformat()})
    assert env.status_code == 201, env.text
    envio_id = env.json()["id"]

    fila = api.get("/api/aprovacoes", headers=h).json()
    assert fila["total_pendente"] >= 1, "o envio tem de aparecer na fila do gestor"

    dec = api.patch(f"/api/aprovacoes/envios/{envio_id}/decidir", headers=h,
                    json={"status": "aprovada", "comentario_gestor": "ok"})
    assert dec.status_code == 200, dec.text

    # 8. medição do mês → aceite emite a fatura
    med = api.post(f"/api/projetos/{projeto_id}/medicoes", headers=h,
                   json={"competencia": hoje.isoformat()})
    assert med.status_code == 201, med.text
    medicao_id = med.json()["id"]
    assert med.json()["total_valor"] > 0, "40h aprovadas a 260/h têm de virar valor"

    ace = api.post(f"/api/medicoes/{medicao_id}/aceitar", headers=h, json={"numero": "NF-001"})
    assert ace.status_code == 200, ace.text

    # 9. a fatura existe e pode ser recebida
    faturas = api.get("/api/faturas", headers=h).json()["faturas"]
    assert faturas, "o aceite da medição tem de emitir fatura"
    fatura_id = faturas[0]["id"]
    rec = api.patch(f"/api/faturas/{fatura_id}", headers=h,
                    json={"status": "recebida", "numero": "NF-001"})
    assert rec.status_code == 200, rec.text

    # 10. o dinheiro aparece no financeiro — o ciclo fechou
    rent = api.get("/api/financeiro/rentabilidade", headers=h).json()
    assert rent, "o projeto tem de aparecer na rentabilidade"


def test_medicao_sem_horas_e_recusada(api, h):
    """Medir um mês sem hora apontada não faz sentido: o produto recusa, e é o
    comportamento certo — foi o teste que estava errado, não o código."""
    hoje = competencia_estavel()
    cli = api.post("/api/clientes", headers=h, json={"nome": "X"}).json()
    proj = api.post("/api/projetos", headers=h, json={
        "nome": "P", "cliente_id": cli["id"], "data_inicio": hoje.isoformat(),
    }).json()
    r = api.post(f"/api/projetos/{proj['id']}/medicoes", headers=h,
                 json={"competencia": hoje.isoformat()})
    assert r.status_code == 422
    assert "nada a medir" in r.text


def test_medicao_contestada_nao_emite_fatura(api, h):
    """O caminho infeliz: o cliente contesta e a medição NÃO vira cobrança."""
    hoje = competencia_estavel()
    segunda = segunda_estavel()
    cli = api.post("/api/clientes", headers=h, json={"nome": "Y"}).json()
    proj = api.post("/api/projetos", headers=h, json={
        "nome": "Q", "cliente_id": cli["id"], "data_inicio": hoje.isoformat(),
    }).json()
    cons = api.post("/api/consultores", headers=h, json={
        "nome": "Bruno", "senioridade": "pleno", "taxa_hora_custo": 90, "taxa_hora_venda": 200,
    }).json()
    aloc = api.post("/api/alocacoes", headers=h, json={
        "consultor_id": cons["id"], "fase_id": proj["fases"][2]["id"], "horas_semana": 40,
    }).json()
    api.post("/api/apontamentos", headers=h, json={
        "alocacao_id": aloc["id"], "data": segunda.isoformat(), "horas": 8, "descricao": "x",
    })
    # a semana precisa estar APROVADA para virar medição — sem isso não há o que medir
    env = api.post("/api/apontamentos/semana/enviar", headers=h,
                   json={"consultor_id": cons["id"], "semana": segunda.isoformat()}).json()
    api.patch(f"/api/aprovacoes/envios/{env['id']}/decidir", headers=h, json={"status": "aprovada"})
    med = api.post(f"/api/projetos/{proj['id']}/medicoes", headers=h,
                   json={"competencia": hoje.isoformat()})
    assert med.status_code == 201, med.text
    antes = len(api.get("/api/faturas", headers=h).json()["faturas"])
    r = api.post(f"/api/medicoes/{med.json()['id']}/contestar", headers=h,
                 json={"observacoes": "horas do dia 12 não conferem"})
    assert r.status_code == 200, r.text
    assert len(api.get("/api/faturas", headers=h).json()["faturas"]) == antes, "contestada não emite fatura"


def test_medicao_so_cobra_hora_aprovada(api, h):
    """O achado mais grave da auditoria: a medição — que vira nota fiscal —
    ignorava o EnvioSemana e cobrava rascunho, pendente e REPROVADO igual.
    Todo o fluxo de aprovação era decorativo para o faturamento."""
    hoje = competencia_estavel()
    segunda = segunda_estavel()
    cli = api.post("/api/clientes", headers=h, json={"nome": "Cli"}).json()
    proj = api.post("/api/projetos", headers=h, json={
        "nome": "Proj", "cliente_id": cli["id"], "data_inicio": hoje.isoformat(),
    }).json()
    cons = api.post("/api/consultores", headers=h, json={
        "nome": "Ana", "senioridade": "senior", "taxa_hora_custo": 100, "taxa_hora_venda": 200,
    }).json()
    aloc = api.post("/api/alocacoes", headers=h, json={
        "consultor_id": cons["id"], "fase_id": proj["fases"][2]["id"], "horas_semana": 40,
    }).json()

    # 8h lançadas mas NUNCA enviadas: puro rascunho
    api.post("/api/apontamentos", headers=h, json={
        "alocacao_id": aloc["id"], "data": segunda.isoformat(), "horas": 8, "descricao": "rascunho",
    })
    r = api.post(f"/api/projetos/{proj['id']}/medicoes", headers=h,
                 json={"competencia": hoje.isoformat()})
    assert r.status_code == 422, "rascunho não pode virar nota"

    # agora envia e o gestor REPROVA
    env = api.post("/api/apontamentos/semana/enviar", headers=h,
                   json={"consultor_id": cons["id"], "semana": segunda.isoformat()}).json()
    api.patch(f"/api/aprovacoes/envios/{env['id']}/decidir", headers=h,
              json={"status": "reprovada", "comentario_gestor": "faltou descrição"})
    r = api.post(f"/api/projetos/{proj['id']}/medicoes", headers=h,
                 json={"competencia": hoje.isoformat()})
    assert r.status_code == 422, "hora REPROVADA jamais pode ser cobrada do cliente"

    # reenvia e aprova: agora sim
    api.post("/api/apontamentos/semana/enviar", headers=h,
             json={"consultor_id": cons["id"], "semana": segunda.isoformat()})
    envios = api.get("/api/aprovacoes", headers=h).json()
    eid = envios["envios"][0]["id"] if isinstance(envios, dict) and envios.get("envios") else env["id"]
    api.patch(f"/api/aprovacoes/envios/{eid}/decidir", headers=h, json={"status": "aprovada"})
    r = api.post(f"/api/projetos/{proj['id']}/medicoes", headers=h,
                 json={"competencia": hoje.isoformat()})
    assert r.status_code == 201, r.text
    assert r.json()["total_horas"] == 8
    assert r.json()["total_valor"] == 1600, "8h x R$200 = R$1.600"
