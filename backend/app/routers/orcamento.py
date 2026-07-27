"""Orçado × realizado do projeto, por rubrica.

'horas' e 'despesas' são rubricas AUTOMÁTICAS: o realizado vem do motor
(custo das horas apontadas / despesas aprovadas) e o orçado nasce com a
sugestão do motor (custo previsto das alocações). As demais (terceiros,
licenças, outros) são manuais — orçado e realizado lançados pelo gestor.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    CategoriaOrcamento,
    Despesa,
    ItemOrcamento,
    Projeto,
    StatusDespesa,
)
from ..services.receita import horas_previstas

router = APIRouter(prefix="/api", tags=["Orçamento"])

AUTOMATICAS = (CategoriaOrcamento.horas, CategoriaOrcamento.despesas)

ROTULOS = {
    CategoriaOrcamento.horas: "Horas (custo interno)",
    CategoriaOrcamento.despesas: "Despesas reembolsáveis",
    CategoriaOrcamento.terceiros: "Terceiros / subcontratação",
    CategoriaOrcamento.licencas: "Licenças / software",
    CategoriaOrcamento.outros: "Outros custos",
}


class ItemCreate(BaseModel):
    categoria: CategoriaOrcamento
    descricao: str = ""
    valor_orcado: float = 0.0
    valor_realizado: float = 0.0


class ItemUpdate(BaseModel):
    descricao: str | None = None
    valor_orcado: float | None = None
    valor_realizado: float | None = None


def _custo_previsto_horas(projeto: Projeto) -> float:
    return sum(
        horas_previstas(a.data_inicio, a.data_fim, a.horas_semana)
        * (a.consultor.taxa_hora_custo if a.consultor else 0.0)
        for f in projeto.fases for a in f.alocacoes
    )


def _realizado_motor(session: Session, projeto: Projeto, categoria: CategoriaOrcamento) -> float:
    if categoria == CategoriaOrcamento.horas:
        return sum(
            ap.horas * (a.consultor.taxa_hora_custo if a.consultor else 0.0)
            for f in projeto.fases for a in f.alocacoes for ap in a.apontamentos
        )
    if categoria == CategoriaOrcamento.despesas:
        return sum(
            d.valor for d in session.exec(
                select(Despesa).where(Despesa.projeto_id == projeto.id)
            ).all()
            if d.status in (StatusDespesa.aprovada, StatusDespesa.reembolsada)
        )
    return 0.0


def _garantir_automaticas(session: Session, projeto: Projeto) -> None:
    """Cria as rubricas automáticas na primeira consulta, com o orçado
    sugerido pelo motor (custo previsto) — o gestor edita depois."""
    existentes = {
        i.categoria for i in session.exec(
            select(ItemOrcamento).where(ItemOrcamento.projeto_id == projeto.id)
        ).all()
    }
    criou = False
    if CategoriaOrcamento.horas not in existentes:
        session.add(ItemOrcamento(
            projeto_id=projeto.id, categoria=CategoriaOrcamento.horas,
            valor_orcado=round(_custo_previsto_horas(projeto), 2),
        ))
        criou = True
    if CategoriaOrcamento.despesas not in existentes:
        session.add(ItemOrcamento(projeto_id=projeto.id, categoria=CategoriaOrcamento.despesas))
        criou = True
    if criou:
        session.commit()


def _serializar(session: Session, projeto: Projeto, item: ItemOrcamento) -> dict:
    automatica = item.categoria in AUTOMATICAS
    realizado = _realizado_motor(session, projeto, item.categoria) if automatica else item.valor_realizado
    return {
        "id": item.id,
        "categoria": item.categoria,
        "rotulo": ROTULOS.get(item.categoria, item.categoria),
        "descricao": item.descricao,
        "orcado": round(item.valor_orcado, 2),
        "realizado": round(realizado, 2),
        "consumo": round(realizado / item.valor_orcado, 4) if item.valor_orcado > 0 else None,
        "automatica": automatica,
        "sugestao_motor": round(_custo_previsto_horas(projeto), 2)
        if item.categoria == CategoriaOrcamento.horas else None,
    }


@router.get("/projetos/{projeto_id}/orcamento")
def obter_orcamento(projeto_id: int, session: Session = Depends(get_session)):
    projeto = session.get(Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    _garantir_automaticas(session, projeto)

    itens = [
        _serializar(session, projeto, i)
        for i in session.exec(
            select(ItemOrcamento).where(ItemOrcamento.projeto_id == projeto_id)
        ).all()
    ]
    ordem = list(ROTULOS)
    itens.sort(key=lambda x: ordem.index(x["categoria"]))
    total_orcado = round(sum(i["orcado"] for i in itens), 2)
    total_realizado = round(sum(i["realizado"] for i in itens), 2)
    return {
        "itens": itens,
        "total_orcado": total_orcado,
        "total_realizado": total_realizado,
        "consumo": round(total_realizado / total_orcado, 4) if total_orcado > 0 else None,
        "saldo": round(total_orcado - total_realizado, 2),
    }


@router.post("/projetos/{projeto_id}/orcamento/itens", status_code=201)
def criar_item(projeto_id: int, dados: ItemCreate, session: Session = Depends(get_session)):
    projeto = session.get(Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    if dados.categoria in AUTOMATICAS:
        raise HTTPException(422, "Rubricas de horas e despesas são automáticas — edite o orçado nelas")
    item = ItemOrcamento(projeto_id=projeto_id, **dados.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return _serializar(session, projeto, item)


@router.patch("/orcamento/itens/{item_id}")
def atualizar_item(item_id: int, dados: ItemUpdate, session: Session = Depends(get_session)):
    item = session.get(ItemOrcamento, item_id)
    if not item:
        raise HTTPException(404, "Rubrica não encontrada")
    if dados.descricao is not None:
        item.descricao = dados.descricao
    if dados.valor_orcado is not None:
        item.valor_orcado = dados.valor_orcado
    if dados.valor_realizado is not None:
        if item.categoria in AUTOMATICAS:
            raise HTTPException(422, "O realizado desta rubrica vem do motor — não é editável")
        item.valor_realizado = dados.valor_realizado
    session.add(item)
    session.commit()
    session.refresh(item)
    return _serializar(session, item.projeto, item)


@router.delete("/orcamento/itens/{item_id}", status_code=204)
def remover_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(ItemOrcamento, item_id)
    if not item:
        raise HTTPException(404, "Rubrica não encontrada")
    if item.categoria in AUTOMATICAS:
        raise HTTPException(422, "Rubricas automáticas não podem ser removidas")
    session.delete(item)
    session.commit()
