from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import exigir_gestor
from ..models import Configuracao, Feriado
from ..services.receita import definir_feriados

router = APIRouter(prefix="/api/configuracoes", tags=["Configurações"])


class FeriadoCreate(BaseModel):
    data: date
    nome: str


def _recarregar_motor(session: Session) -> None:
    definir_feriados(f.data for f in session.exec(select(Feriado)).all())


@router.get("/feriados")
def listar_feriados(session: Session = Depends(get_session)):
    return [
        {"id": f.id, "data": f.data.isoformat(), "nome": f.nome}
        for f in session.exec(select(Feriado).order_by(Feriado.data)).all()
    ]


@router.post("/feriados", status_code=201, dependencies=[Depends(exigir_gestor)])
def criar_feriado(dados: FeriadoCreate, session: Session = Depends(get_session)):
    existente = session.exec(select(Feriado).where(Feriado.data == dados.data)).first()
    if existente:
        raise HTTPException(409, "Já existe feriado nesta data")
    f = Feriado(data=dados.data, nome=dados.nome)
    session.add(f)
    session.commit()
    _recarregar_motor(session)  # o motor passa a tratar o dia como não útil
    return {"id": f.id, "data": f.data.isoformat(), "nome": f.nome}


@router.delete("/feriados/{feriado_id}", status_code=204, dependencies=[Depends(exigir_gestor)])
def remover_feriado(feriado_id: int, session: Session = Depends(get_session)):
    f = session.get(Feriado, feriado_id)
    if not f:
        raise HTTPException(404, "Feriado não encontrado")
    session.delete(f)
    session.commit()
    _recarregar_motor(session)


def _obter_ou_criar(session: Session) -> Configuracao:
    cfg = session.exec(select(Configuracao)).first()
    if cfg is None:
        cfg = Configuracao()
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
    return cfg


@router.get("", response_model=Configuracao)
def obter_configuracao(session: Session = Depends(get_session)):
    return _obter_ou_criar(session)


@router.patch("", response_model=Configuracao, dependencies=[Depends(exigir_gestor)])
def atualizar_configuracao(dados: dict, session: Session = Depends(get_session)):
    cfg = _obter_ou_criar(session)
    for campo, valor in dados.items():
        if hasattr(cfg, campo) and campo != "id":
            setattr(cfg, campo, valor)
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg
