from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import eh_ceo, eh_gestao, exigir_ceo, exigir_dono, exigir_gestao, sem_dinheiro, usuario_atual
from pydantic import BaseModel, Field

from ..models import HORAS_SEMANA_PADRAO, Alocacao, Apontamento, Ausencia, Consultor, Senioridade
from ..services.receita import (
    capacidade_na_semana,
    horas_alocadas_na_semana,
    horas_ausentes_na_semana,
    horas_previstas,
    segunda_da_semana,
    utilizacao_semanal,
)

router = APIRouter(prefix="/api/consultores", tags=["Consultores"])


class ConsultorCreate(BaseModel):
    """Entrada explícita, e o motivo é grave.

    Em SQLModel, classe com table=True NÃO valida na construção — é desligado de
    propósito. Aceitar o modelo de tabela como corpo deixava passar
    senioridade="imperador" e taxa negativa, o commit acontecia ANTES da
    validação da resposta, e a linha envenenada ficava. Depois disso todo
    select(Consultor) estourava no fetch do enum: dashboard, lista, heatmap e
    capacidade caíam em 500 de forma permanente, sem rota para desfazer.
    """

    nome: str = Field(min_length=1, max_length=200)
    senioridade: Senioridade
    modulo_sap: str = ""
    skills: str = ""
    taxa_hora_custo: float = Field(default=0.0, ge=0)
    taxa_hora_venda: float = Field(default=0.0, ge=0)


class ConsultorUpdate(BaseModel):
    """Consultor deixou de ser permanente: dá para corrigir taxa, promover e
    desligar sem mexer no banco na mão."""

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    senioridade: Senioridade | None = None
    modulo_sap: str | None = None
    skills: str | None = None
    taxa_hora_custo: float | None = Field(default=None, ge=0)
    taxa_hora_venda: float | None = Field(default=None, ge=0)


@router.get("")
def listar_consultores(request: Request, session: Session = Depends(get_session)):
    """Gestão vê a equipe inteira com as taxas; consultor vê só a si mesmo e sem
    taxa nenhuma — custo/hora e taxa de venda são dado comercial da consultoria."""
    u = usuario_atual(request)
    consultores = session.exec(select(Consultor).order_by(Consultor.nome)).all()
    if eh_ceo(u):
        return consultores
    if eh_gestao(u):  # RH: a equipe inteira, mas sem taxa nenhuma
        return [
            {"id": c.id, "nome": c.nome, "senioridade": c.senioridade,
             "modulo_sap": c.modulo_sap, "skills": c.skills}
            for c in consultores
        ]
    return [
        {
            "id": c.id, "nome": c.nome, "senioridade": c.senioridade,
            "modulo_sap": c.modulo_sap, "skills": c.skills,
        }
        for c in consultores if c.id == u.get("consultor_id")
    ]


@router.post("", response_model=Consultor, status_code=201, dependencies=[Depends(exigir_ceo)])
def criar_consultor(dados: ConsultorCreate, session: Session = Depends(get_session)):
    consultor = Consultor(**dados.model_dump())
    session.add(consultor)
    session.commit()
    session.refresh(consultor)
    return consultor


@router.patch("/{consultor_id}", response_model=Consultor, dependencies=[Depends(exigir_ceo)])
def atualizar_consultor(consultor_id: int, dados: ConsultorUpdate, session: Session = Depends(get_session)):
    c = session.get(Consultor, consultor_id)
    if not c:
        raise HTTPException(404, "Consultor não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(c, campo, valor)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@router.delete("/{consultor_id}", status_code=204, dependencies=[Depends(exigir_ceo)])
def remover_consultor(consultor_id: int, session: Session = Depends(get_session)):
    """Só remove quem nunca foi alocado — histórico de hora faturada não se apaga."""
    c = session.get(Consultor, consultor_id)
    if not c:
        raise HTTPException(404, "Consultor não encontrado")
    if c.alocacoes:
        raise HTTPException(409, "Consultor já alocado em projeto: o histórico não pode ser removido")
    session.delete(c)
    session.commit()


@router.get("/utilizacao", dependencies=[Depends(exigir_gestao)])
def utilizacao_heatmap(
    request: Request,
    inicio: date | None = Query(default=None, description="Qualquer dia da primeira semana; default = 4 semanas atrás"),
    semanas: int = Query(default=12, ge=1, le=26),
    session: Session = Depends(get_session),
):
    """Utilização semana a semana de todos os consultores (dados do heatmap)."""
    hoje = date.today()
    base = segunda_da_semana(inicio or (hoje - timedelta(weeks=4)))
    segundas = [base + timedelta(weeks=i) for i in range(semanas)]
    semana_corrente = segunda_da_semana(hoje)

    ceo = eh_ceo(usuario_atual(request))
    consultores = session.exec(select(Consultor).order_by(Consultor.nome)).all()
    resultado = []
    for c in consultores:
        alocacoes = session.exec(select(Alocacao).where(Alocacao.consultor_id == c.id)).all()
        ausencias = session.exec(select(Ausencia).where(Ausencia.consultor_id == c.id)).all()
        semanas_dados = []
        for seg in segundas:
            u = utilizacao_semanal(alocacoes, seg, ausencias)
            u["semana"] = seg.isoformat()
            u["corrente"] = seg == semana_corrente
            semanas_dados.append(u)
        resultado.append(
            {
                "consultor_id": c.id,
                "nome": c.nome,
                "senioridade": c.senioridade,
                "modulo_sap": c.modulo_sap,
                # taxa só para o CEO: custo + venda entregam a margem da pessoa
                **({"taxa_hora_custo": c.taxa_hora_custo,
                    "taxa_hora_venda": c.taxa_hora_venda} if ceo else {}),
                "semanas": semanas_dados,
            }
        )
    return {"semanas": [s.isoformat() for s in segundas], "consultores": resultado}


@router.get("/capacidade", dependencies=[Depends(exigir_gestao)])
def demanda_vs_capacidade(
    inicio: date | None = Query(default=None, description="Qualquer dia da primeira semana; default = semana corrente"),
    semanas: int = Query(default=12, ge=1, le=26),
    session: Session = Depends(get_session),
):
    """Demanda (horas alocadas) × capacidade (jornada − ausências aprovadas) da
    empresa inteira, semana a semana — antecipação de gargalos de equipe."""
    hoje = date.today()
    base = segunda_da_semana(inicio or hoje)
    segundas = [base + timedelta(weeks=i) for i in range(semanas)]
    semana_corrente = segunda_da_semana(hoje)

    consultores = session.exec(select(Consultor)).all()
    alocacoes_por_consultor = {
        c.id: session.exec(select(Alocacao).where(Alocacao.consultor_id == c.id)).all()
        for c in consultores
    }
    ausencias_por_consultor = {
        c.id: session.exec(select(Ausencia).where(Ausencia.consultor_id == c.id)).all()
        for c in consultores
    }

    serie = []
    for seg in segundas:
        demanda = sum(
            horas_alocadas_na_semana(a, seg)
            for alocs in alocacoes_por_consultor.values()
            for a in alocs
        )
        capacidade = sum(
            capacidade_na_semana(ausencias_por_consultor[c.id], seg)
            for c in consultores
        )
        serie.append(
            {
                "semana": seg.isoformat(),
                "demanda": round(demanda, 1),
                "capacidade": round(capacidade, 1),
                "corrente": seg == semana_corrente,
                "gargalo": demanda > capacidade,
            }
        )
    return {"consultores": len(consultores), "serie": serie}


@router.get("/{consultor_id}/painel", dependencies=[Depends(exigir_gestao)])
def painel_consultor(consultor_id: int, request: Request, session: Session = Depends(get_session)):
    """Detalhe do consultor: taxas, KPIs (utilização média, horas/receita/margem do
    mês) e alocações ativas cross-projeto."""
    c = session.get(Consultor, consultor_id)
    if not c:
        raise HTTPException(404, "Consultor não encontrado")

    hoje = date.today()
    alocacoes = session.exec(select(Alocacao).where(Alocacao.consultor_id == consultor_id)).all()

    # utilização média das últimas 12 semanas
    base = segunda_da_semana(hoje - timedelta(weeks=11))
    segundas = [base + timedelta(weeks=i) for i in range(12)]
    # sem passar as ausências, a MESMA pessoa aparecia com 125% no heatmap e
    # 50% aqui — dois números para o mesmo fato, e o gestor não sabe em qual crer
    ausencias = session.exec(select(Ausencia).where(Ausencia.consultor_id == consultor_id)).all()
    utils = [utilizacao_semanal(alocacoes, s, ausencias)["utilizacao"] for s in segundas]
    utilizacao_media = sum(utils) / len(utils) if utils else 0.0

    # mês atual (do dia 1 até hoje)
    inicio_mes = hoje.replace(day=1)
    apontamentos = [
        ap
        for a in alocacoes
        for ap in a.apontamentos
        if inicio_mes <= ap.data <= hoje
    ]
    horas_mes = sum(ap.horas for ap in apontamentos)
    receita_mes = sum(ap.horas * ap.alocacao.taxa_hora_venda for ap in apontamentos)
    custo_mes = horas_mes * c.taxa_hora_custo
    margem_mes = (receita_mes - custo_mes) / receita_mes if receita_mes else 0.0

    ativas = []
    for a in alocacoes:
        if a.data_fim < hoje:
            continue
        fase = a.fase
        projeto = fase.projeto if fase else None
        ativas.append(
            {
                "alocacao_id": a.id,
                "projeto": projeto.nome if projeto else "",
                "projeto_id": projeto.id if projeto else None,
                "fase": fase.nome if fase else "",
                "data_inicio": a.data_inicio.isoformat(),
                "data_fim": a.data_fim.isoformat(),
                "horas_semana": a.horas_semana,
                "taxa_hora_venda": a.taxa_hora_venda,
                "horas_previstas": round(horas_previstas(a.data_inicio, a.data_fim, a.horas_semana), 2),
                "horas_realizadas": round(sum(ap.horas for ap in a.apontamentos), 2),
            }
        )

    return sem_dinheiro({
        "id": c.id,
        "nome": c.nome,
        "senioridade": c.senioridade,
        "modulo_sap": c.modulo_sap,
        "skills": c.skills,
        "taxa_hora_custo": c.taxa_hora_custo,
        "taxa_hora_venda": c.taxa_hora_venda,
        "utilizacao_media": round(utilizacao_media, 4),
        "horas_mes": round(horas_mes, 2),
        "receita_mes": round(receita_mes, 2),
        "margem_mes": round(margem_mes, 4),
        "alocacoes_ativas": [
            {k: v for k, v in a.items() if k != "taxa_hora_venda"} for a in ativas
        ] if not eh_ceo(usuario_atual(request)) else ativas,
    }, usuario_atual(request),
        ("taxa_hora_custo", "taxa_hora_venda", "receita_mes", "margem_mes"))


@router.get("/{consultor_id}/agenda")
def agenda_do_consultor(
    consultor_id: int,
    request: Request,
    mes: str = Query(default=None, description="YYYY-MM; default = mês corrente"),
    session: Session = Depends(get_session),
):
    """Calendário mensal do consultor: alocações (h/dia), ausências aprovadas,
    feriados do calendário corporativo e horas apontadas por dia."""
    exigir_dono(request, consultor_id)
    from ..models import Feriado, StatusAprovacao
    from ..services.receita import eh_dia_util

    consultor = session.get(Consultor, consultor_id)
    if not consultor:
        raise HTTPException(404, "Consultor não encontrado")

    hoje = date.today()
    if mes:
        try:
            ano, m = map(int, mes.split("-"))
            primeiro = date(ano, m, 1)
        except ValueError:
            raise HTTPException(422, "mes deve estar no formato YYYY-MM")
    else:
        primeiro = hoje.replace(day=1)
    proximo = (primeiro.replace(day=28) + timedelta(days=4)).replace(day=1)

    alocacoes = session.exec(
        select(Alocacao).where(Alocacao.consultor_id == consultor_id)
    ).all()
    ausencias = [
        x for x in session.exec(
            select(Ausencia).where(
                Ausencia.consultor_id == consultor_id,
                Ausencia.status == StatusAprovacao.aprovada,
            )
        ).all()
        if x.data_inicio < proximo and x.data_fim >= primeiro
    ]
    feriados = {
        f.data: f.nome for f in session.exec(select(Feriado)).all()
        if primeiro <= f.data < proximo
    }
    ids = [a.id for a in alocacoes]
    apontadas: dict[date, float] = {}
    if ids:
        for ap in session.exec(
            select(Apontamento).where(
                Apontamento.alocacao_id.in_(ids),
                Apontamento.data >= primeiro,
                Apontamento.data < proximo,
            )
        ).all():
            apontadas[ap.data] = apontadas.get(ap.data, 0.0) + ap.horas

    dias = []
    d = primeiro
    while d < proximo:
        util = eh_dia_util(d)
        ausencia = next((x.tipo for x in ausencias if x.data_inicio <= d <= x.data_fim), None)
        aloc_dia = [{
            "projeto": a.fase.projeto.nome if a.fase and a.fase.projeto else "",
            "fase": a.fase.nome if a.fase else "",
            "horas_dia": round(a.horas_semana / 5.0, 1),
        } for a in alocacoes if a.data_inicio <= d <= a.data_fim] if util else []
        dias.append({
            "data": d.isoformat(),
            "dia_semana": d.weekday(),  # 0 = segunda
            "util": util,
            "hoje": d == hoje,
            "feriado": feriados.get(d),
            "ausencia": ausencia,
            "alocacoes": aloc_dia,
            "horas_alocadas": round(sum(x["horas_dia"] for x in aloc_dia), 1) if not ausencia else 0.0,
            "horas_apontadas": round(apontadas.get(d, 0.0), 1),
        })
        d += timedelta(days=1)

    return {
        "consultor_id": consultor_id,
        "consultor": consultor.nome,
        "mes": primeiro.isoformat()[:7],
        "dias": dias,
        "totais": {
            "dias_uteis": sum(1 for x in dias if x["util"]),
            "dias_ausente": sum(1 for x in dias if x["ausencia"] and x["util"]),
            "horas_alocadas": round(sum(x["horas_alocadas"] for x in dias), 1),
            "horas_apontadas": round(sum(x["horas_apontadas"] for x in dias), 1),
        },
    }


@router.get("/{consultor_id}", response_model=Consultor)
def obter_consultor(consultor_id: int, request: Request, session: Session = Depends(get_session)):
    exigir_dono(request, consultor_id)
    consultor = session.get(Consultor, consultor_id)
    if not consultor:
        raise HTTPException(404, "Consultor não encontrado")
    return consultor
