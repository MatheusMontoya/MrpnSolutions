"""Governança do projeto: riscos (matriz prob×impacto), solicitações de
mudança (CR), status report consolidado e encerramento formal."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    GrauRisco,
    MudancaCR,
    Pendencia,
    Projeto,
    Risco,
    StatusMudanca,
    StatusPendencia,
    StatusProjeto,
    StatusRisco,
)
from ..services.projetos import fase_atual
from ..services.receita import (
    horas_previstas,
    receita_mensal_prevista,
    receita_mensal_realizada,
)
from .atividades import resumo_gate

router = APIRouter(prefix="/api", tags=["Governança"])

# severidade da matriz 3×3 (probabilidade × impacto)
_PESO = {GrauRisco.baixo: 1, GrauRisco.medio: 2, GrauRisco.alto: 3}


def severidade(prob: GrauRisco, imp: GrauRisco) -> str:
    s = _PESO[prob] * _PESO[imp]
    return "critica" if s >= 6 else "moderada" if s >= 3 else "baixa"


# ---------------- riscos ----------------

class RiscoCreate(BaseModel):
    projeto_id: int
    titulo: str
    probabilidade: GrauRisco = GrauRisco.medio
    impacto: GrauRisco = GrauRisco.medio
    resposta: str = ""


class RiscoUpdate(BaseModel):
    titulo: str | None = None
    probabilidade: GrauRisco | None = None
    impacto: GrauRisco | None = None
    resposta: str | None = None
    status: StatusRisco | None = None


def _ser_risco(r: Risco) -> dict:
    return {
        "id": r.id,
        "projeto_id": r.projeto_id,
        "titulo": r.titulo,
        "probabilidade": r.probabilidade,
        "impacto": r.impacto,
        "severidade": severidade(r.probabilidade, r.impacto),
        "resposta": r.resposta,
        "status": r.status,
    }


@router.get("/riscos")
def listar_riscos(projeto_id: int, session: Session = Depends(get_session)):
    riscos = session.exec(select(Risco).where(Risco.projeto_id == projeto_id)).all()
    ordem = {"critica": 0, "moderada": 1, "baixa": 2}
    return sorted((_ser_risco(r) for r in riscos), key=lambda x: (x["status"] != "aberto", ordem[x["severidade"]]))


@router.post("/riscos", status_code=201)
def criar_risco(dados: RiscoCreate, session: Session = Depends(get_session)):
    if not session.get(Projeto, dados.projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    r = Risco(**dados.model_dump())
    session.add(r)
    session.commit()
    session.refresh(r)
    return _ser_risco(r)


@router.patch("/riscos/{risco_id}")
def atualizar_risco(risco_id: int, dados: RiscoUpdate, session: Session = Depends(get_session)):
    r = session.get(Risco, risco_id)
    if not r:
        raise HTTPException(404, "Risco não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(r, campo, valor)
    session.add(r)
    session.commit()
    session.refresh(r)
    return _ser_risco(r)


@router.delete("/riscos/{risco_id}", status_code=204)
def remover_risco(risco_id: int, session: Session = Depends(get_session)):
    r = session.get(Risco, risco_id)
    if not r:
        raise HTTPException(404, "Risco não encontrado")
    session.delete(r)
    session.commit()


# ---------------- mudanças (CR) ----------------

class MudancaCreate(BaseModel):
    projeto_id: int
    titulo: str
    descricao: str = ""
    impacto_horas: float = 0.0
    impacto_valor: float = 0.0


class MudancaDecisao(BaseModel):
    status: StatusMudanca  # aprovada | rejeitada


def _ser_mudanca(m: MudancaCR) -> dict:
    return {
        "id": m.id,
        "projeto_id": m.projeto_id,
        "titulo": m.titulo,
        "descricao": m.descricao,
        "impacto_horas": m.impacto_horas,
        "impacto_valor": m.impacto_valor,
        "status": m.status,
        "criada_em": m.criada_em.isoformat(),
        "decidida_em": m.decidida_em.isoformat() if m.decidida_em else None,
    }


@router.get("/mudancas")
def listar_mudancas(projeto_id: int, session: Session = Depends(get_session)):
    ms = session.exec(
        select(MudancaCR).where(MudancaCR.projeto_id == projeto_id).order_by(MudancaCR.criada_em.desc())
    ).all()
    return [_ser_mudanca(m) for m in ms]


@router.post("/mudancas", status_code=201)
def criar_mudanca(dados: MudancaCreate, session: Session = Depends(get_session)):
    if not session.get(Projeto, dados.projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    m = MudancaCR(**dados.model_dump(), criada_em=date.today())
    session.add(m)
    session.commit()
    session.refresh(m)
    return _ser_mudanca(m)


@router.patch("/mudancas/{mudanca_id}/decidir")
def decidir_mudanca(mudanca_id: int, dados: MudancaDecisao, session: Session = Depends(get_session)):
    m = session.get(MudancaCR, mudanca_id)
    if not m:
        raise HTTPException(404, "Mudança não encontrada")
    if m.status != StatusMudanca.aberta:
        raise HTTPException(409, "Mudança já decidida")
    if dados.status == StatusMudanca.aberta:
        raise HTTPException(422, "Decisão deve ser aprovada ou rejeitada")
    m.status = dados.status
    m.decidida_em = date.today()
    session.add(m)
    session.commit()
    return _ser_mudanca(m)


# ---------------- status report + encerramento ----------------

@router.get("/projetos/{projeto_id}/status-report")
def status_report(projeto_id: int, session: Session = Depends(get_session)):
    """Relatório de status consolidado — gerado automaticamente dos dados
    que o sistema já tem (o PSOffice preenche na mão; aqui é 1 clique)."""
    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")
    hoje = date.today()
    atual = fase_atual(p, hoje)

    alocacoes = [a for f in p.fases for a in f.alocacoes]
    apontamentos = [ap for a in alocacoes for ap in a.apontamentos]
    receita_prev = sum(receita_mensal_prevista(alocacoes).values())
    receita_real = sum(receita_mensal_realizada(apontamentos).values())

    fases = []
    for f in sorted(p.fases, key=lambda x: x.ordem):
        atividades_total = len(f.atividades)
        atividades_ok = sum(1 for a in f.atividades if str(a.status) == "concluida")
        desvio = (f.data_fim_prevista - f.baseline_fim).days if f.baseline_fim else 0
        fases.append({
            "nome": f.nome,
            "atual": atual is not None and f.id == atual.id,
            "inicio": f.data_inicio_prevista.isoformat(),
            "fim": f.data_fim_prevista.isoformat(),
            "desvio_baseline_dias": desvio,
            "entregas": f"{atividades_ok}/{atividades_total}",
            "gate": resumo_gate(f),
        })

    riscos = [_ser_risco(r) for r in session.exec(select(Risco).where(Risco.projeto_id == p.id)).all()]
    mudancas = [_ser_mudanca(m) for m in session.exec(select(MudancaCR).where(MudancaCR.projeto_id == p.id)).all()]
    pendencias_abertas = len(session.exec(
        select(Pendencia).where(Pendencia.projeto_id == p.id, Pendencia.status != StatusPendencia.resolvida)
    ).all())

    horas_prev = sum(horas_previstas(a.data_inicio, a.data_fim, a.horas_semana) for a in alocacoes)
    horas_real = sum(ap.horas for ap in apontamentos)

    return {
        "gerado_em": hoje.isoformat(),
        "projeto": p.nome,
        "cliente": p.cliente.nome if p.cliente else "",
        "status": p.status,
        "fase_atual": atual.nome if atual else None,
        "receita_prevista": round(receita_prev, 2),
        "receita_realizada": round(receita_real, 2),
        "horas_previstas": round(horas_prev, 1),
        "horas_realizadas": round(horas_real, 1),
        "desvio_baseline_dias": max((f["desvio_baseline_dias"] for f in fases), default=0),
        "fases": fases,
        "riscos_abertos": [r for r in riscos if r["status"] == "aberto"],
        "mudancas_abertas": [m for m in mudancas if m["status"] == "aberta"],
        "pendencias_abertas": pendencias_abertas,
        "licoes_aprendidas": p.licoes_aprendidas,
    }


@router.get("/projetos/{projeto_id}/tap")
def termo_de_abertura(projeto_id: int, session: Session = Depends(get_session)):
    """TAP — Termo de Abertura do Projeto, consolidado em 1 clique.

    Escopo/premissas/valores vêm da proposta convertida (quando existir);
    cronograma é a LINHA DE BASE (o compromisso original, não o replanejado);
    equipe e receita vêm do motor.
    """
    from ..models import Proposta

    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")

    proposta = session.exec(select(Proposta).where(Proposta.projeto_id == p.id)).first()
    alocacoes = [a for f in p.fases for a in f.alocacoes]
    receita_prev = sum(receita_mensal_prevista(alocacoes).values())
    horas_prev = sum(horas_previstas(a.data_inicio, a.data_fim, a.horas_semana) for a in alocacoes)

    equipe = [{
        "consultor": a.consultor.nome if a.consultor else "?",
        "senioridade": a.consultor.senioridade if a.consultor else None,
        "modulo_sap": a.consultor.modulo_sap if a.consultor else "",
        "fase": a.fase.nome if a.fase else "",
        "horas_semana": a.horas_semana,
        "periodo": f"{a.data_inicio.isoformat()} a {a.data_fim.isoformat()}",
    } for a in alocacoes]

    fases_baseline = [{
        "nome": f.nome,
        "inicio": (f.baseline_inicio or f.data_inicio_prevista).isoformat(),
        "fim": (f.baseline_fim or f.data_fim_prevista).isoformat(),
    } for f in sorted(p.fases, key=lambda x: x.ordem)]

    riscos_iniciais = [_ser_risco(r) for r in session.exec(
        select(Risco).where(Risco.projeto_id == p.id, Risco.status == StatusRisco.aberto)
    ).all()]

    return {
        "gerado_em": date.today().isoformat(),
        "projeto": p.nome,
        "cliente": p.cliente.nome if p.cliente else "",
        "data_inicio": p.data_inicio.isoformat(),
        "termino_previsto": fases_baseline[-1]["fim"] if fases_baseline else None,
        "escopo": proposta.escopo if proposta else "",
        "premissas": proposta.premissas if proposta else "",
        "valor_estimado": proposta.valor_estimado if proposta else round(receita_prev, 2),
        "horas_estimadas": proposta.horas_estimadas if proposta else round(horas_prev, 1),
        "receita_prevista_motor": round(receita_prev, 2),
        "horas_previstas_motor": round(horas_prev, 1),
        "metodologia": "SAP Activate — Discover · Prepare · Explore · Realize · Deploy · Run",
        "fases_baseline": fases_baseline,
        "equipe": equipe,
        "riscos_iniciais": riscos_iniciais,
        "proposta_id": proposta.id if proposta else None,
        "proposta": proposta.nome if proposta else None,
    }


class Encerramento(BaseModel):
    licoes_aprendidas: str = ""


@router.post("/projetos/{projeto_id}/encerrar")
def encerrar_projeto(projeto_id: int, dados: Encerramento, session: Session = Depends(get_session)):
    """Encerramento formal: registra lições aprendidas e muda o status.
    O status report vigente serve como termo de encerramento."""
    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")
    if p.status == StatusProjeto.encerrado:
        raise HTTPException(409, "Projeto já encerrado")
    p.status = StatusProjeto.encerrado
    p.licoes_aprendidas = dados.licoes_aprendidas
    p.encerrado_em = date.today()
    session.add(p)
    session.commit()
    return {"ok": True, "encerrado_em": p.encerrado_em.isoformat()}
