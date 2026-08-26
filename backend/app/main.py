"""RunRate — Professional Services Automation para consultoria SAP.

API REST JSON (OpenAPI em /docs) + frontend React servido de frontend/dist.
Toda rota /api/* exige token (Authorization: Bearer) exceto o login; mutações
são gravadas na trilha de auditoria — ambos via middleware abaixo.
"""
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from . import database
from .database import USA_SQLITE, aplicar_migracoes
from .seguranca import exigir_ceo, exigir_gestao
from .routers import (
    agil,
    alocacoes,
    apontamentos,
    aprovacoes,
    atividades,
    auditoria,
    ausencias,
    auth,
    clientes,
    configuracoes,
    consultores,
    contratos,
    copiloto,
    dashboard,
    despesas,
    exportacao,
    faturas,
    financeiro,
    governanca,
    medicoes,
    modelos,
    orcamento,
    pendencias,
    projetos,
    propostas,
    solicitacoes,
)
from .seed import seed_se_vazio

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _carregar_parametros_do_motor() -> None:
    """Leva para o motor o que a consultoria configurou: feriados, jornada e
    limiares. Sem isto a tela de Configurações dizia "Salvo" e o cálculo
    continuava usando as constantes do código."""
    from sqlmodel import Session, select

    from .database import engine
    from .models import Configuracao, Feriado
    from .services.receita import definir_feriados, definir_parametros

    with Session(engine) as s:
        definir_feriados(f.data for f in s.exec(select(Feriado)).all())
        cfg = s.exec(select(Configuracao)).first()
        if cfg:
            definir_parametros(cfg.jornada_semanal, cfg.limiar_super, cfg.limiar_ocioso)


def _garantir_modelo_padrao() -> None:
    """Bancos criados antes dos modelos ganham o padrão na subida."""
    from sqlmodel import Session, select

    from .database import engine
    from .models import ModeloProjeto
    from .services.projetos import criar_modelo_padrao

    with Session(engine) as s:
        if not s.exec(select(ModeloProjeto).where(ModeloProjeto.padrao == True)).first():  # noqa: E712
            criar_modelo_padrao(s)


def preparar_banco() -> None:
    """Cria o schema e a carga inicial. Escreve, então roda UMA vez.

    Em Postgres isto é um passo de deploy (`python -m app.bootstrap`), nunca da
    subida do processo: em serverless dois cold starts simultâneos correriam no
    CREATE TYPE dos enums e poderiam semear o banco duas vezes.
    """
    # O schema vem das MIGRAÇÕES, não do create_all: create_all cria tabela
    # nova mas não altera coluna existente, então o primeiro "adicionar um
    # campo" com dado real dentro não teria caminho seguro.
    aplicar_migracoes()
    if os.environ.get("RUNRATE_SEM_DEMO") == "1":
        print("[RunRate] RUNRATE_SEM_DEMO=1 — schema criado SEM dados de demonstração.")
    else:
        # ARMADILHA CONHECIDA: seed_se_vazio() semeia quando o banco está vazio.
        # Depois de limpar a produção, rodar o bootstrap de novo reinjetaria os
        # 3 projetos fictícios e 8 logins com senha 'psa123'. Em produção use
        # sempre RUNRATE_SEM_DEMO=1.
        seed_se_vazio()
    _garantir_modelo_padrao()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite é o banco de desenvolvimento, com um processo só: preparar na subida
    # é conveniente e não há concorrência. Em Postgres o preparo é externo.
    if USA_SQLITE:
        preparar_banco()
    # Já os feriados são cache em memória por processo: leitura, e precisa
    # acontecer em toda subida. Se o schema ainda não existe, o app sobe e
    # responde erro claro em vez de morrer na inicialização.
    try:
        _carregar_parametros_do_motor()
    except Exception as e:  # noqa: BLE001
        print(f"[RunRate] parâmetros do motor não carregados ({e}). Rodou o bootstrap?")
    yield


app = FastAPI(
    title="RunRate",
    description="RunRate by MRPN Solutions — PSA para consultoria SAP: projeto ↔ alocação ↔ receita hora-homem.",
    version="0.1.0",
    lifespan=lifespan,
)

ROTAS_LIVRES = {"/api/auth/login", "/api/saude"}


@app.get("/api/saude", include_in_schema=False)
def saude():
    """Batimento cardíaco: toca o banco de verdade.

    Duas funções ao mesmo tempo: (1) a consulta conta como atividade, o que
    impede o free tier do Supabase de pausar o projeto por inatividade — foi
    isso que derrubou a produção duas vezes; (2) responde o estado real, então
    o robô de monitoramento sabe distinguir "app no ar" de "banco fora".
    Não exige token: não expõe dado nenhum, só o veredicto.
    """
    from sqlalchemy import text

    try:
        with database.engine.connect() as con:
            con.execute(text("select 1"))
        return {"app": "ok", "banco": "ok"}
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            {"app": "ok", "banco": "indisponivel", "detalhe": str(e).strip()[:160]},
            status_code=503,
        )


# Campos que NUNCA entram na trilha, mesmo em resumo. A auditoria é lida pelo
# CEO na tela de Auditoria; gravar senha ali seria criar um segundo lugar de
# onde vazar credencial.
CAMPOS_SIGILOSOS = {
    "senha", "senha_nova", "senha_atual", "password", "token",
    "chave_anthropic", "api_key", "secret",
}
LIMITE_DETALHE = 400


def resumir_corpo(bruto: bytes) -> str:
    """Resumo legível do corpo da requisição, com os campos sigilosos mascarados.

    O campo existia no modelo desde o início e nunca era preenchido: a trilha
    dizia "PATCH /api/faturas/12" sem dizer se a fatura foi emitida, recebida ou
    cancelada — o que torna a auditoria inútil justamente onde ela importa.
    """
    if not bruto or len(bruto) > 100_000:
        return ""
    try:
        dados = json.loads(bruto)
    except (ValueError, UnicodeDecodeError):
        return ""
    if not isinstance(dados, dict):
        return ""
    limpo = {
        k: ("***" if k.lower() in CAMPOS_SIGILOSOS else v)
        for k, v in dados.items()
    }
    try:
        texto = json.dumps(limpo, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return ""
    return texto[:LIMITE_DETALHE]


@app.middleware("http")
async def autenticacao_e_auditoria(request: Request, call_next):
    """Exige token em /api/* (exceto login) e registra mutações na auditoria."""
    caminho = request.url.path
    protegida = caminho.startswith("/api") and caminho not in ROTAS_LIVRES
    if protegida:
        from .services.auth import resolver_token

        token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        with Session(database.engine) as s:
            usuario = resolver_token(s, token)
            # o dict é montado ainda com a sessão aberta (commit expira atributos)
            dados = usuario and {
                "id": usuario.id,
                "nome": usuario.nome,
                "email": usuario.email,
                "perfil": usuario.perfil,
                "consultor_id": usuario.consultor_id,
            }
        if not dados:
            return JSONResponse({"detail": "Não autenticado"}, status_code=401)
        request.state.usuario = dados

    corpo = b""
    if protegida and request.method in ("POST", "PATCH", "DELETE"):
        # Ler o corpo aqui CONSOME o stream: sem devolver um `receive` que o
        # reemite, a rota lá na frente receberia um corpo vazio e todo POST
        # quebraria com 422.
        corpo = await request.body()

        async def reemitir() -> dict:
            return {"type": "http.request", "body": corpo, "more_body": False}

        request._receive = reemitir

    resposta = await call_next(request)

    if protegida and request.method in ("POST", "PATCH", "DELETE"):
        from .models import EventoAuditoria

        u = getattr(request.state, "usuario", None) or {}
        with Session(database.engine) as s:
            s.add(EventoAuditoria(
                quando=datetime.now(),
                usuario=u.get("nome", ""),
                perfil=str(u.get("perfil", "")),
                metodo=request.method,
                caminho=caminho,
                status=resposta.status_code,
                detalhe=resumir_corpo(corpo),
            ))
            s.commit()
    return resposta


# Dois níveis gerenciais: o RH aprova e cuida de pessoas; o CEO vê o negócio
# inteiro (dinheiro, comercial, projetos, configurações).
CEO = [Depends(exigir_ceo)]
GESTAO = [Depends(exigir_gestao)]

# acessíveis aos dois perfis (writes sensíveis têm guarda própria na rota)
app.include_router(auth.router)
app.include_router(consultores.router)
app.include_router(projetos.router)
app.include_router(apontamentos.router)
app.include_router(configuracoes.router)
app.include_router(ausencias.router)
app.include_router(despesas.router)

# exclusivos do gestor
app.include_router(dashboard.router, dependencies=CEO)
app.include_router(clientes.router, dependencies=CEO)
app.include_router(alocacoes.router, dependencies=CEO)
app.include_router(atividades.router, dependencies=CEO)
app.include_router(pendencias.router, dependencies=CEO)
app.include_router(aprovacoes.router, dependencies=GESTAO)
app.include_router(propostas.router, dependencies=CEO)
app.include_router(faturas.router, dependencies=CEO)
app.include_router(contratos.router, dependencies=CEO)
app.include_router(governanca.router, dependencies=CEO)
app.include_router(financeiro.router, dependencies=CEO)
app.include_router(copiloto.router, dependencies=CEO)
app.include_router(exportacao.router, dependencies=CEO)
app.include_router(solicitacoes.router, dependencies=GESTAO)
app.include_router(medicoes.router, dependencies=CEO)
app.include_router(orcamento.router, dependencies=CEO)
app.include_router(modelos.router, dependencies=CEO)
app.include_router(agil.router, dependencies=CEO)
app.include_router(auditoria.router)  # já exige CEO internamente


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    RAIZ_ESTATICA = FRONTEND_DIST.resolve()

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        """Serve o SPA. Qualquer caminho que escape da pasta do build vira index.

        Sem o resolve()+is_relative_to, "../../backend/.env" resolvia para um
        arquivo REAL fora do build e o FileResponse o entregava sem token. Na
        Vercel o estático nem chega aqui, mas em container (Render/Fly, que o
        DEPLOY.md oferece) este handler é a porta de entrada de tudo.
        """
        alvo = (RAIZ_ESTATICA / caminho).resolve()
        dentro = alvo == RAIZ_ESTATICA or RAIZ_ESTATICA in alvo.parents
        if caminho and dentro and alvo.is_file():
            return FileResponse(alvo)
        return FileResponse(RAIZ_ESTATICA / "index.html")
