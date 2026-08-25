from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database import get_session
from ..models import Cliente, StatusProjeto
from ..services.projetos import fase_atual
from ..services.receita import (
    horas_previstas,
    margem,
    receita_mensal_prevista,
    receita_mensal_realizada,
)

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


class ClienteCreate(BaseModel):
    """Entrada explícita. Aceitar o table model direto permitia POST {} com
    nome=None: a validação só acontecia no banco e o usuário recebia 500."""

    nome: str = Field(min_length=1, max_length=200)
    contato: str = ""


def _agregados(cliente: Cliente) -> dict:
    """Nº de projetos, receita prevista/realizada e margem de um cliente."""
    alocacoes = [a for p in cliente.projetos for f in p.fases for a in f.alocacoes]
    apontamentos = [ap for a in alocacoes for ap in a.apontamentos]
    prevista = sum(receita_mensal_prevista(alocacoes).values())
    realizada = sum(receita_mensal_realizada(apontamentos).values())
    margem_total = sum(
        margem(
            horas_previstas(a.data_inicio, a.data_fim, a.horas_semana),
            a.taxa_hora_venda,
            a.consultor.taxa_hora_custo if a.consultor else 0.0,
        )
        for a in alocacoes
    )
    return {
        "n_projetos": len(cliente.projetos),
        "projetos_ativos": sum(1 for p in cliente.projetos if p.status == StatusProjeto.ativo),
        "receita_prevista": round(prevista, 2),
        "receita_realizada": round(realizada, 2),
        "margem_prevista": round(margem_total, 2),
        "margem_pct": round(margem_total / prevista, 4) if prevista else 0.0,
    }


@router.get("")
def listar_clientes(session: Session = Depends(get_session)):
    clientes = session.exec(select(Cliente).order_by(Cliente.nome)).all()
    return [
        {"id": c.id, "nome": c.nome, "contato": c.contato, **_agregados(c)}
        for c in clientes
    ]


@router.post("", response_model=Cliente, status_code=201)
def criar_cliente(dados: ClienteCreate, session: Session = Depends(get_session)):
    cliente = Cliente(nome=dados.nome.strip(), contato=dados.contato.strip())
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente


@router.get("/{cliente_id}")
def obter_cliente(cliente_id: int, session: Session = Depends(get_session)):
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    hoje = date.today()
    projetos = []
    for p in sorted(cliente.projetos, key=lambda p: p.nome):
        atual = fase_atual(p, hoje)
        projetos.append(
            {
                "id": p.id,
                "nome": p.nome,
                "data_inicio": p.data_inicio.isoformat(),
                "status": p.status,
                "fase_atual": atual.nome if atual else None,
            }
        )
    return {
        "id": cliente.id,
        "nome": cliente.nome,
        "contato": cliente.contato,
        **_agregados(cliente),
        "projetos": projetos,
    }
