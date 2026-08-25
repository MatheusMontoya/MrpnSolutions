"""Medição mensal: relatório de horas realizadas × taxa para o aceite do
cliente ANTES do faturamento.

Fluxo: gerar (dos apontamentos do mês) → aceitar (emite a fatura vinculada,
substituindo a prevista do mesmo mês, se houver) ou contestar (permite
corrigir apontamentos e gerar outra).
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Alocacao,
    Apontamento,
    Fatura,
    Medicao,
    Projeto,
    StatusFatura,
    StatusMedicao,
)
from .faturas import PRAZO_VENCIMENTO_DIAS

router = APIRouter(prefix="/api", tags=["Medições"])


class MedicaoCreate(BaseModel):
    competencia: date  # qualquer dia do mês; normalizamos para o dia 1


class Contestacao(BaseModel):
    observacoes: str


class Aceite(BaseModel):
    numero: str = ""  # número da fatura a emitir (opcional)


def _apontamentos_do_mes(session: Session, projeto: Projeto, competencia: date) -> list[Apontamento]:
    fase_ids = [f.id for f in projeto.fases]
    if not fase_ids:
        return []
    alocacoes = session.exec(select(Alocacao).where(Alocacao.fase_id.in_(fase_ids))).all()
    ids = [a.id for a in alocacoes]
    if not ids:
        return []
    proximo_mes = (competencia.replace(day=28) + timedelta(days=4)).replace(day=1)
    apontamentos = session.exec(
        select(Apontamento).where(
            Apontamento.alocacao_id.in_(ids),
            Apontamento.data >= competencia,
            Apontamento.data < proximo_mes,
        ).order_by(Apontamento.data)
    ).all()

    # SÓ HORA APROVADA VIRA MEDIÇÃO — e a medição vira nota.
    # Sem este filtro o fluxo de aprovação era decorativo para o faturamento:
    # rascunho nunca enviado, semana aguardando decisão e semana REPROVADA
    # entravam na medição e eram cobradas do cliente do mesmo jeito.
    from ..models import EnvioSemana, StatusEnvio
    from ..services.receita import segunda_da_semana

    consultor_por_alocacao = {a.id: a.consultor_id for a in alocacoes}
    aprovadas = {
        (e.consultor_id, e.semana)
        for e in session.exec(
            select(EnvioSemana).where(EnvioSemana.status == StatusEnvio.aprovada)
        ).all()
    }
    return [
        ap for ap in apontamentos
        if (consultor_por_alocacao.get(ap.alocacao_id), segunda_da_semana(ap.data)) in aprovadas
    ]


def _linhas(apontamentos: list[Apontamento]) -> list[dict]:
    """Detalhamento por consultor+fase+taxa — o que o cliente confere."""
    grupos: dict[tuple, dict] = {}
    for ap in apontamentos:
        aloc = ap.alocacao
        consultor = aloc.consultor if aloc else None
        fase = aloc.fase if aloc else None
        chave = (consultor.id if consultor else 0, fase.id if fase else 0, aloc.taxa_hora_venda if aloc else 0)
        g = grupos.setdefault(chave, {
            "consultor": consultor.nome if consultor else "?",
            "senioridade": consultor.senioridade if consultor else None,
            "fase": fase.nome if fase else "?",
            "taxa_hora": aloc.taxa_hora_venda if aloc else 0.0,
            "horas": 0.0,
            "valor": 0.0,
        })
        g["horas"] += ap.horas
        g["valor"] += ap.horas * (aloc.taxa_hora_venda if aloc else 0.0)
    linhas = sorted(grupos.values(), key=lambda x: (-x["valor"], x["consultor"]))
    for g in linhas:
        g["horas"] = round(g["horas"], 2)
        g["valor"] = round(g["valor"], 2)
    return linhas


def serializar(m: Medicao, linhas: list[dict] | None = None) -> dict:
    dados = {
        "id": m.id,
        "projeto_id": m.projeto_id,
        "projeto": m.projeto.nome if m.projeto else "",
        "cliente": m.projeto.cliente.nome if m.projeto and m.projeto.cliente else "",
        "competencia": m.competencia.isoformat(),
        "total_horas": m.total_horas,
        "total_valor": m.total_valor,
        "status": m.status,
        "observacoes": m.observacoes,
        "criada_em": m.criada_em.isoformat(),
        "decidida_em": m.decidida_em.isoformat() if m.decidida_em else None,
        "fatura_id": m.fatura_id,
    }
    if linhas is not None:
        dados["linhas"] = linhas
    return dados


@router.post("/projetos/{projeto_id}/medicoes", status_code=201)
def gerar_medicao(projeto_id: int, dados: MedicaoCreate, session: Session = Depends(get_session)):
    projeto = session.get(Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    competencia = dados.competencia.replace(day=1)

    aberta = session.exec(
        select(Medicao).where(
            Medicao.projeto_id == projeto_id,
            Medicao.competencia == competencia,
            Medicao.status != StatusMedicao.contestada,
        )
    ).first()
    if aberta:
        raise HTTPException(409, "Já existe medição gerada ou aceita para esta competência")

    apontamentos = _apontamentos_do_mes(session, projeto, competencia)
    if not apontamentos:
        raise HTTPException(422, "Sem horas apontadas na competência — nada a medir")

    linhas = _linhas(apontamentos)
    m = Medicao(
        projeto_id=projeto_id,
        competencia=competencia,
        total_horas=round(sum(x["horas"] for x in linhas), 2),
        total_valor=round(sum(x["valor"] for x in linhas), 2),
        criada_em=date.today(),
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return serializar(m, linhas)


@router.get("/medicoes")
def listar_medicoes(
    projeto_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
):
    q = select(Medicao).order_by(Medicao.competencia.desc())  # type: ignore[attr-defined]
    if projeto_id is not None:
        q = q.where(Medicao.projeto_id == projeto_id)
    medicoes = session.exec(q).all()
    return {
        "medicoes": [serializar(m) for m in medicoes],
        "aguardando_aceite": sum(1 for m in medicoes if m.status == StatusMedicao.gerada),
    }


@router.get("/medicoes/{medicao_id}")
def obter_medicao(medicao_id: int, session: Session = Depends(get_session)):
    m = session.get(Medicao, medicao_id)
    if not m:
        raise HTTPException(404, "Medição não encontrada")
    apontamentos = _apontamentos_do_mes(session, m.projeto, m.competencia)
    return serializar(m, _linhas(apontamentos))


@router.post("/medicoes/{medicao_id}/aceitar")
def aceitar_medicao(medicao_id: int, dados: Aceite, session: Session = Depends(get_session)):
    m = session.get(Medicao, medicao_id)
    if not m:
        raise HTTPException(404, "Medição não encontrada")
    if m.status != StatusMedicao.gerada:
        raise HTTPException(409, "Só medições aguardando aceite podem ser aceitas")

    # a medição vira A fatura do mês: substitui a prevista da mesma competência
    prevista = session.exec(
        select(Fatura).where(
            Fatura.projeto_id == m.projeto_id,
            Fatura.competencia == m.competencia,
            Fatura.status == StatusFatura.prevista,
        )
    ).first()
    if prevista:
        session.delete(prevista)

    hoje = date.today()
    fatura = Fatura(
        projeto_id=m.projeto_id,
        competencia=m.competencia,
        valor=m.total_valor,
        status=StatusFatura.emitida,
        numero=dados.numero,
        data_emissao=hoje,
        data_vencimento=hoje + timedelta(days=PRAZO_VENCIMENTO_DIAS),
    )
    session.add(fatura)
    session.flush()

    m.status = StatusMedicao.aceita
    m.fatura_id = fatura.id
    m.decidida_em = hoje
    session.add(m)
    session.commit()
    session.refresh(m)
    return serializar(m)


@router.post("/medicoes/{medicao_id}/contestar")
def contestar_medicao(medicao_id: int, dados: Contestacao, session: Session = Depends(get_session)):
    m = session.get(Medicao, medicao_id)
    if not m:
        raise HTTPException(404, "Medição não encontrada")
    if m.status != StatusMedicao.gerada:
        raise HTTPException(409, "Só medições aguardando aceite podem ser contestadas")
    if not dados.observacoes.strip():
        raise HTTPException(422, "Contestação exige o motivo do cliente")

    m.status = StatusMedicao.contestada
    m.observacoes = dados.observacoes
    m.decidida_em = date.today()
    session.add(m)
    session.commit()
    return serializar(m)
