from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import eh_gestao, exigir_ceo, usuario_atual
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


@router.post("/feriados", status_code=201, dependencies=[Depends(exigir_ceo)])
def criar_feriado(dados: FeriadoCreate, session: Session = Depends(get_session)):
    existente = session.exec(select(Feriado).where(Feriado.data == dados.data)).first()
    if existente:
        raise HTTPException(409, "Já existe feriado nesta data")
    f = Feriado(data=dados.data, nome=dados.nome)
    session.add(f)
    session.commit()
    _recarregar_motor(session)  # o motor passa a tratar o dia como não útil
    return {"id": f.id, "data": f.data.isoformat(), "nome": f.nome}


@router.delete("/feriados/{feriado_id}", status_code=204, dependencies=[Depends(exigir_ceo)])
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


# O consultor precisa de UM parâmetro daqui: a taxa por km, para lançar despesa
# de quilometragem. Todo o resto — chave da API, CNPJ, meta de margem e a tabela
# de preço de venda — é dado de gestão e não pode sair na mesma resposta.
CAMPOS_OPERACIONAIS = ("nome_consultoria", "jornada_semanal", "taxa_km", "formato_data", "moeda", "fuso")


@router.get("")
def obter_configuracao(request: Request, session: Session = Depends(get_session)):
    cfg = _obter_ou_criar(session)
    if eh_gestao(usuario_atual(request)):
        return cfg
    return {campo: getattr(cfg, campo) for campo in CAMPOS_OPERACIONAIS}


@router.patch("", response_model=Configuracao, dependencies=[Depends(exigir_ceo)])
def atualizar_configuracao(dados: dict, session: Session = Depends(get_session)):
    cfg = _obter_ou_criar(session)
    for campo, valor in dados.items():
        if hasattr(cfg, campo) and campo != "id":
            setattr(cfg, campo, valor)
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg
