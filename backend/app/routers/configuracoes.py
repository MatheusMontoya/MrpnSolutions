from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import eh_ceo, eh_gestao, exigir_ceo, usuario_atual
from ..models import Configuracao, Feriado
from ..services.receita import definir_feriados

router = APIRouter(prefix="/api/configuracoes", tags=["Configurações"])


class ConfiguracaoUpdate(BaseModel):
    """Campos editáveis, com faixa. Antes era `dados: dict` com setattr em laço:
    jornada negativa, limiar acima de 1 e meta de margem absurda entravam sem
    reclamação e envenenavam o cálculo de utilização da empresa inteira."""

    nome_consultoria: str | None = Field(default=None, min_length=1, max_length=200)
    cnpj: str | None = None
    jornada_semanal: float | None = Field(default=None, gt=0, le=168)
    limiar_super: float | None = Field(default=None, gt=0, le=5)
    limiar_ocioso: float | None = Field(default=None, gt=0, le=1)
    meta_margem: float | None = Field(default=None, ge=0, le=1)
    taxa_junior: float | None = Field(default=None, ge=0)
    taxa_pleno: float | None = Field(default=None, ge=0)
    taxa_senior: float | None = Field(default=None, ge=0)
    taxa_km: float | None = Field(default=None, ge=0)
    formato_data: str | None = None
    moeda: str | None = None
    fuso: str | None = None
    anthropic_api_key: str | None = None
    modelo_ia: str | None = None


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


# Segredo não sai em resposta de API — nem para o CEO. A tela precisa saber SE
# existe chave configurada, não QUAL é; se vazar o payload num log, num print de
# tela ou no cache do navegador, a chave vaza junto.
CAMPOS_SECRETOS = ("anthropic_api_key",)
# Preço de venda, meta de margem e CNPJ são decisão comercial: o RH não vê.
CAMPOS_COMERCIAIS = ("cnpj", "meta_margem", "taxa_junior", "taxa_pleno", "taxa_senior")


@router.get("")
def obter_configuracao(request: Request, session: Session = Depends(get_session)):
    cfg = _obter_ou_criar(session)
    u = usuario_atual(request)
    if not eh_gestao(u):
        return {campo: getattr(cfg, campo) for campo in CAMPOS_OPERACIONAIS}

    dados = {c: getattr(cfg, c) for c in cfg.model_dump() if c not in CAMPOS_SECRETOS}
    # a tela mostra "configurada" ou "não configurada", nunca o valor
    dados["tem_chave_ia"] = bool(cfg.anthropic_api_key)
    if not eh_ceo(u):
        for campo in CAMPOS_COMERCIAIS:
            dados.pop(campo, None)
    return dados


@router.patch("", response_model=Configuracao, dependencies=[Depends(exigir_ceo)])
def atualizar_configuracao(dados: ConfiguracaoUpdate, session: Session = Depends(get_session)):
    cfg = _obter_ou_criar(session)
    # exclude_unset: só grava o que veio, sem zerar o resto com os defaults
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(cfg, campo, valor)
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    # recarrega o motor na hora: sem isto a mudança só valeria no próximo deploy
    from ..services.receita import definir_parametros

    definir_parametros(cfg.jornada_semanal, cfg.limiar_super, cfg.limiar_ocioso)
    return cfg
