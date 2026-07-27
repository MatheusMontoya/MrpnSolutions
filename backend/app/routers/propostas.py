"""Pipeline comercial de propostas de projeto. Foco em proposta → projeto
(sem gestão de contatos/atividades de CRM, por decisão de escopo)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Cliente,
    Configuracao,
    Consultor,
    EstagioProposta,
    Projeto,
    Proposta,
    Senioridade,
)
from ..services.projetos import criar_projeto_com_fases

router = APIRouter(prefix="/api/propostas", tags=["Propostas"])

# transições permitidas no funil (perdida pode voltar para negociação)
AVANCO = {
    EstagioProposta.qualificacao: EstagioProposta.proposta,
    EstagioProposta.proposta: EstagioProposta.negociacao,
    EstagioProposta.negociacao: EstagioProposta.aprovada,
}


class PropostaCreate(BaseModel):
    cliente_id: int
    nome: str
    descricao: str = ""
    escopo: str = ""
    premissas: str = ""
    horas_junior: float = 0.0
    horas_pleno: float = 0.0
    horas_senior: float = 0.0
    valor_estimado: float = 0.0  # usado só quando o mix de horas é zero
    probabilidade: float = 0.5
    validade: date | None = None


class PropostaUpdate(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    escopo: str | None = None
    premissas: str | None = None
    horas_junior: float | None = None
    horas_pleno: float | None = None
    horas_senior: float | None = None
    valor_estimado: float | None = None
    probabilidade: float | None = None
    validade: date | None = None
    estagio: EstagioProposta | None = None


def precificar(session: Session, p: Proposta) -> None:
    """Precificação pelo mix de senioridade: valor = Σ horas × taxa padrão da
    Configuração; margem estimada usa o CUSTO MÉDIO REAL dos consultores de
    cada senioridade (fallback: 55% da taxa de venda)."""
    total = p.horas_junior + p.horas_pleno + p.horas_senior
    if total <= 0:
        p.horas_estimadas = p.horas_estimadas or 0.0
        return

    cfg = session.exec(select(Configuracao)).first()
    taxas = {
        Senioridade.junior: cfg.taxa_junior if cfg else 150.0,
        Senioridade.pleno: cfg.taxa_pleno if cfg else 220.0,
        Senioridade.senior: cfg.taxa_senior if cfg else 350.0,
    }

    custos: dict[Senioridade, float] = {}
    for sen in Senioridade:
        consultores = session.exec(select(Consultor).where(Consultor.senioridade == sen)).all()
        custos[sen] = (
            sum(c.taxa_hora_custo for c in consultores) / len(consultores)
            if consultores else taxas[sen] * 0.55
        )

    mix = [
        (p.horas_junior, Senioridade.junior),
        (p.horas_pleno, Senioridade.pleno),
        (p.horas_senior, Senioridade.senior),
    ]
    valor = sum(h * taxas[s] for h, s in mix)
    custo = sum(h * custos[s] for h, s in mix)

    p.horas_estimadas = total
    p.valor_estimado = round(valor, 2)
    p.margem_estimada = round((valor - custo) / valor, 4) if valor else 0.0


class ConverterProposta(BaseModel):
    data_inicio: date


def serializar(p: Proposta) -> dict:
    return {
        "id": p.id,
        "cliente_id": p.cliente_id,
        "cliente": p.cliente.nome if p.cliente else "",
        "nome": p.nome,
        "descricao": p.descricao,
        "escopo": p.escopo,
        "premissas": p.premissas,
        "horas_junior": p.horas_junior,
        "horas_pleno": p.horas_pleno,
        "horas_senior": p.horas_senior,
        "valor_estimado": p.valor_estimado,
        "margem_estimada": p.margem_estimada,
        "horas_estimadas": p.horas_estimadas,
        "probabilidade": p.probabilidade,
        "validade": p.validade.isoformat() if p.validade else None,
        "estagio": p.estagio,
        "criada_em": p.criada_em.isoformat(),
        "decidida_em": p.decidida_em.isoformat() if p.decidida_em else None,
        "projeto_id": p.projeto_id,
    }


@router.get("")
def listar_propostas(session: Session = Depends(get_session)):
    propostas = session.exec(select(Proposta).order_by(Proposta.criada_em.desc())).all()
    ativas = [p for p in propostas if p.estagio not in (EstagioProposta.perdida, EstagioProposta.convertida)]
    ponderado = sum(p.valor_estimado * p.probabilidade for p in ativas)
    return {
        "propostas": [serializar(p) for p in propostas],
        "funil_total": round(sum(p.valor_estimado for p in ativas), 2),
        "funil_ponderado": round(ponderado, 2),
    }


@router.post("", status_code=201)
def criar_proposta(dados: PropostaCreate, session: Session = Depends(get_session)):
    if not session.get(Cliente, dados.cliente_id):
        raise HTTPException(404, "Cliente não encontrado")
    if not 0 <= dados.probabilidade <= 1:
        raise HTTPException(422, "Probabilidade deve estar entre 0 e 1")
    p = Proposta(**dados.model_dump(), criada_em=date.today())
    precificar(session, p)  # mix de senioridade → valor + margem estimada
    session.add(p)
    session.commit()
    session.refresh(p)
    return serializar(p)


@router.patch("/{proposta_id}")
def atualizar_proposta(proposta_id: int, dados: PropostaUpdate, session: Session = Depends(get_session)):
    p = session.get(Proposta, proposta_id)
    if not p:
        raise HTTPException(404, "Proposta não encontrada")
    if p.estagio == EstagioProposta.convertida:
        raise HTTPException(409, "Proposta já convertida em projeto")
    payload = dados.model_dump(exclude_unset=True)
    if "estagio" in payload and payload["estagio"] == EstagioProposta.convertida:
        raise HTTPException(422, "Use o endpoint de conversão")
    for campo, valor in payload.items():
        setattr(p, campo, valor)
    if any(k in payload for k in ("horas_junior", "horas_pleno", "horas_senior")):
        precificar(session, p)
    if payload.get("estagio") in (EstagioProposta.perdida,):
        p.decidida_em = date.today()
    session.add(p)
    session.commit()
    session.refresh(p)
    return serializar(p)


@router.post("/{proposta_id}/avancar")
def avancar_estagio(proposta_id: int, session: Session = Depends(get_session)):
    """Move a proposta para o próximo estágio do funil."""
    p = session.get(Proposta, proposta_id)
    if not p:
        raise HTTPException(404, "Proposta não encontrada")
    proximo = AVANCO.get(p.estagio)
    if proximo is None:
        raise HTTPException(409, f"Proposta em '{p.estagio}' não tem próximo estágio")
    p.estagio = proximo
    session.add(p)
    session.commit()
    return serializar(p)


@router.post("/{proposta_id}/converter", status_code=201)
def converter_em_projeto(proposta_id: int, dados: ConverterProposta, session: Session = Depends(get_session)):
    """Proposta aprovada vira projeto — nasce com as 6 fases Activate,
    entregas padrão e Quality Gates."""
    p = session.get(Proposta, proposta_id)
    if not p:
        raise HTTPException(404, "Proposta não encontrada")
    if p.estagio != EstagioProposta.aprovada:
        raise HTTPException(409, "Só propostas aprovadas podem ser convertidas")

    projeto = criar_projeto_com_fases(
        session,
        Projeto(nome=p.nome, cliente_id=p.cliente_id, data_inicio=dados.data_inicio),
    )
    p.estagio = EstagioProposta.convertida
    p.projeto_id = projeto.id
    p.decidida_em = date.today()
    session.add(p)
    session.commit()
    return {"proposta": serializar(p), "projeto_id": projeto.id}


@router.delete("/{proposta_id}", status_code=204)
def remover_proposta(proposta_id: int, session: Session = Depends(get_session)):
    p = session.get(Proposta, proposta_id)
    if not p:
        raise HTTPException(404, "Proposta não encontrada")
    if p.estagio == EstagioProposta.convertida:
        raise HTTPException(409, "Proposta convertida não pode ser removida")
    session.delete(p)
    session.commit()
