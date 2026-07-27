"""Modelos de projeto: entregas e Quality Gates por fase, por tipo de trabalho.

As 6 fases Activate são fixas — o modelo define O QUE cada fase entrega.
Novos modelos nascem como cópia de um existente (padrão, por default) e são
editados item a item. Projetos novos escolhem o modelo na criação.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    FASES_ACTIVATE,
    ModeloAtividade,
    ModeloItemGate,
    ModeloProjeto,
    Projeto,
)

router = APIRouter(prefix="/api/modelos", tags=["Modelos de projeto"])


class ModeloCreate(BaseModel):
    nome: str
    descricao: str = ""
    copiar_de: int | None = None  # None = copia do modelo padrão


class ModeloUpdate(BaseModel):
    nome: str | None = None
    descricao: str | None = None


class AtividadeCreate(BaseModel):
    fase: str
    titulo: str


class GateCreate(BaseModel):
    fase: str
    codigo: str
    pergunta: str
    risco: str = ""


def _resumo(session: Session, m: ModeloProjeto) -> dict:
    projetos = len(session.exec(select(Projeto).where(Projeto.modelo_id == m.id)).all())
    return {
        "id": m.id,
        "nome": m.nome,
        "descricao": m.descricao,
        "padrao": m.padrao,
        "total_atividades": len(m.atividades),
        "total_gates": len(m.itens_gate),
        "projetos_usando": projetos,
    }


def _detalhe(session: Session, m: ModeloProjeto) -> dict:
    return {
        **_resumo(session, m),
        "fases": [{
            "nome": fase,
            "atividades": [
                {"id": a.id, "titulo": a.titulo}
                for a in m.atividades if a.fase == fase
            ],
            "gates": [
                {"id": g.id, "codigo": g.codigo, "pergunta": g.pergunta, "risco": g.risco}
                for g in m.itens_gate if g.fase == fase
            ],
        } for fase in FASES_ACTIVATE],
    }


def _validar_fase(fase: str) -> None:
    if fase not in FASES_ACTIVATE:
        raise HTTPException(422, f"Fase deve ser uma de: {', '.join(FASES_ACTIVATE)}")


@router.get("")
def listar_modelos(session: Session = Depends(get_session)):
    modelos = session.exec(select(ModeloProjeto).order_by(ModeloProjeto.nome)).all()
    # padrão primeiro — é a referência
    modelos.sort(key=lambda m: (not m.padrao, m.nome))
    return [_resumo(session, m) for m in modelos]


@router.get("/{modelo_id}")
def obter_modelo(modelo_id: int, session: Session = Depends(get_session)):
    m = session.get(ModeloProjeto, modelo_id)
    if not m:
        raise HTTPException(404, "Modelo não encontrado")
    return _detalhe(session, m)


@router.post("", status_code=201)
def criar_modelo(dados: ModeloCreate, session: Session = Depends(get_session)):
    if dados.copiar_de is not None:
        origem = session.get(ModeloProjeto, dados.copiar_de)
    else:
        origem = session.exec(select(ModeloProjeto).where(ModeloProjeto.padrao == True)).first()  # noqa: E712
    if not origem:
        raise HTTPException(404, "Modelo de origem não encontrado")

    novo = ModeloProjeto(nome=dados.nome, descricao=dados.descricao)
    session.add(novo)
    session.flush()
    for a in origem.atividades:
        session.add(ModeloAtividade(modelo_id=novo.id, fase=a.fase, titulo=a.titulo, ordem=a.ordem))
    for g in origem.itens_gate:
        session.add(ModeloItemGate(modelo_id=novo.id, fase=g.fase, codigo=g.codigo, pergunta=g.pergunta, risco=g.risco))
    session.commit()
    session.refresh(novo)
    return _detalhe(session, novo)


@router.patch("/{modelo_id}")
def atualizar_modelo(modelo_id: int, dados: ModeloUpdate, session: Session = Depends(get_session)):
    m = session.get(ModeloProjeto, modelo_id)
    if not m:
        raise HTTPException(404, "Modelo não encontrado")
    if dados.nome is not None:
        m.nome = dados.nome
    if dados.descricao is not None:
        m.descricao = dados.descricao
    session.add(m)
    session.commit()
    return _resumo(session, m)


@router.delete("/{modelo_id}", status_code=204)
def remover_modelo(modelo_id: int, session: Session = Depends(get_session)):
    m = session.get(ModeloProjeto, modelo_id)
    if not m:
        raise HTTPException(404, "Modelo não encontrado")
    if m.padrao:
        raise HTTPException(422, "O modelo padrão não pode ser removido")
    usando = session.exec(select(Projeto).where(Projeto.modelo_id == m.id)).first()
    if usando:
        raise HTTPException(409, "Há projetos criados a partir deste modelo — não pode ser removido")
    session.delete(m)
    session.commit()


@router.post("/{modelo_id}/atividades", status_code=201)
def criar_atividade(modelo_id: int, dados: AtividadeCreate, session: Session = Depends(get_session)):
    m = session.get(ModeloProjeto, modelo_id)
    if not m:
        raise HTTPException(404, "Modelo não encontrado")
    _validar_fase(dados.fase)
    ordem = max((a.ordem for a in m.atividades if a.fase == dados.fase), default=-1) + 1
    a = ModeloAtividade(modelo_id=modelo_id, fase=dados.fase, titulo=dados.titulo, ordem=ordem)
    session.add(a)
    session.commit()
    return {"id": a.id, "fase": a.fase, "titulo": a.titulo}


@router.delete("/atividades/{atividade_id}", status_code=204)
def remover_atividade(atividade_id: int, session: Session = Depends(get_session)):
    a = session.get(ModeloAtividade, atividade_id)
    if not a:
        raise HTTPException(404, "Atividade não encontrada")
    session.delete(a)
    session.commit()


@router.post("/{modelo_id}/gates", status_code=201)
def criar_gate(modelo_id: int, dados: GateCreate, session: Session = Depends(get_session)):
    m = session.get(ModeloProjeto, modelo_id)
    if not m:
        raise HTTPException(404, "Modelo não encontrado")
    _validar_fase(dados.fase)
    g = ModeloItemGate(modelo_id=modelo_id, **dados.model_dump())
    session.add(g)
    session.commit()
    return {"id": g.id, "fase": g.fase, "codigo": g.codigo, "pergunta": g.pergunta}


@router.delete("/gates/{gate_id}", status_code=204)
def remover_gate(gate_id: int, session: Session = Depends(get_session)):
    g = session.get(ModeloItemGate, gate_id)
    if not g:
        raise HTTPException(404, "Item de gate não encontrado")
    session.delete(g)
    session.commit()
