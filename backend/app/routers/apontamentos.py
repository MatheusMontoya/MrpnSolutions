from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import consultor_do_filtro, eh_gestao, exigir_dono, exigir_gestao, usuario_atual
from ..models import Alocacao, Apontamento, Consultor, EnvioSemana, StatusEnvio
from ..services.receita import segunda_da_semana

router = APIRouter(prefix="/api/apontamentos", tags=["Apontamentos"])


class ApontamentoUpsert(BaseModel):
    alocacao_id: int
    data: date
    horas: float  # 0 remove o lançamento
    descricao: str | None = None  # None preserva a descrição existente


class EnviarSemana(BaseModel):
    consultor_id: int
    semana: date  # qualquer dia da semana a enviar


def _envio_da_semana(session: Session, consultor_id: int, segunda: date) -> EnvioSemana | None:
    return session.exec(
        select(EnvioSemana).where(
            EnvioSemana.consultor_id == consultor_id,
            EnvioSemana.semana == segunda,
        )
    ).first()


def _semana_bloqueada(session: Session, consultor_id: int, dia: date) -> bool:
    """Semana enviada ou aprovada não aceita mais lançamentos."""
    envio = _envio_da_semana(session, consultor_id, segunda_da_semana(dia))
    return envio is not None and envio.status in (StatusEnvio.enviada, StatusEnvio.aprovada)


@router.get("/semana")
def grade_semanal(
    request: Request,
    consultor_id: int,
    inicio: date | None = Query(default=None, description="Qualquer dia da semana desejada; default = semana corrente"),
    session: Session = Depends(get_session),
):
    """Grade semanal de apontamento: alocações ativas do consultor na semana e
    as horas já lançadas por dia."""
    consultor_id = consultor_do_filtro(request, consultor_id)
    consultor = session.get(Consultor, consultor_id)
    if not consultor:
        raise HTTPException(404, "Consultor não encontrado")

    segunda = segunda_da_semana(inicio or date.today())
    dias = [segunda + timedelta(days=i) for i in range(7)]

    alocacoes = session.exec(
        select(Alocacao).where(
            Alocacao.consultor_id == consultor_id,
            Alocacao.data_inicio <= dias[-1],
            Alocacao.data_fim >= dias[0],
        )
    ).all()

    linhas = []
    for a in alocacoes:
        registros = session.exec(
            select(Apontamento).where(
                Apontamento.alocacao_id == a.id,
                Apontamento.data >= dias[0],
                Apontamento.data <= dias[-1],
            )
        ).all()
        apontados = {ap.data.isoformat(): ap.horas for ap in registros}
        descricoes = {ap.data.isoformat(): ap.descricao for ap in registros if ap.descricao}
        fase = a.fase
        projeto = fase.projeto if fase else None
        linhas.append(
            {
                "alocacao_id": a.id,
                "projeto": projeto.nome if projeto else "",
                "fase": fase.nome if fase else "",
                "horas_semana": a.horas_semana,
                "taxa_hora_venda": a.taxa_hora_venda,
                "data_inicio": a.data_inicio.isoformat(),
                "data_fim": a.data_fim.isoformat(),
                "horas_por_dia": {d.isoformat(): apontados.get(d.isoformat(), 0.0) for d in dias},
                "descricao_por_dia": {d.isoformat(): descricoes.get(d.isoformat(), "") for d in dias},
            }
        )

    envio = _envio_da_semana(session, consultor_id, segunda)
    return {
        "consultor_id": consultor_id,
        "consultor": consultor.nome,
        "semana": segunda.isoformat(),
        "dias": [d.isoformat() for d in dias],
        "alocacoes": linhas,
        "envio": None if envio is None else {
            "id": envio.id,
            "status": envio.status,
            "total_horas": envio.total_horas,
            "comentario_gestor": envio.comentario_gestor,
            "enviado_em": envio.enviado_em.isoformat() if envio.enviado_em else None,
        },
    }


@router.post("", status_code=201)
def lancar_horas(dados: ApontamentoUpsert, request: Request, session: Session = Depends(get_session)):
    """Upsert por (alocação, dia): lançar de novo substitui; horas=0 remove."""
    if dados.horas < 0 or dados.horas > 24:
        raise HTTPException(422, "Horas devem estar entre 0 e 24")
    a = session.get(Alocacao, dados.alocacao_id)
    if not a:
        raise HTTPException(404, "Alocação não encontrada")
    # sem isto, qualquer consultor lançava (ou zerava) horas na alocação de outro
    exigir_dono(request, a.consultor_id)
    if _semana_bloqueada(session, a.consultor_id, dados.data):
        raise HTTPException(409, "Semana já enviada para aprovação — edição bloqueada")

    existente = session.exec(
        select(Apontamento).where(
            Apontamento.alocacao_id == dados.alocacao_id,
            Apontamento.data == dados.data,
        )
    ).first()

    if dados.horas == 0:
        if existente:
            session.delete(existente)
            session.commit()
        return {"ok": True, "removido": existente is not None}

    if existente:
        existente.horas = dados.horas
        if dados.descricao is not None:
            existente.descricao = dados.descricao
        session.add(existente)
    else:
        session.add(
            Apontamento(
                alocacao_id=dados.alocacao_id,
                data=dados.data,
                horas=dados.horas,
                descricao=dados.descricao or "",
            )
        )
    session.commit()
    return {"ok": True}


@router.post("/semana/enviar", status_code=201)
def enviar_semana(dados: EnviarSemana, request: Request, session: Session = Depends(get_session)):
    """Consultor envia a semana para aprovação do gestor.

    Congela a edição da grade; total de horas é fotografado no envio.
    Semana reprovada pode ser reenviada (volta a 'enviada').
    """
    exigir_dono(request, dados.consultor_id)
    consultor = session.get(Consultor, dados.consultor_id)
    if not consultor:
        raise HTTPException(404, "Consultor não encontrado")

    segunda = segunda_da_semana(dados.semana)
    dias = [segunda + timedelta(days=i) for i in range(7)]

    alocacoes = session.exec(
        select(Alocacao).where(Alocacao.consultor_id == dados.consultor_id)
    ).all()
    ids = [a.id for a in alocacoes]
    total = 0.0
    if ids:
        registros = session.exec(
            select(Apontamento).where(
                Apontamento.alocacao_id.in_(ids),
                Apontamento.data >= dias[0],
                Apontamento.data <= dias[-1],
            )
        ).all()
        total = sum(ap.horas for ap in registros)

    if total <= 0:
        raise HTTPException(422, "Não há horas lançadas nesta semana para enviar")

    envio = _envio_da_semana(session, dados.consultor_id, segunda)
    if envio and envio.status in (StatusEnvio.enviada, StatusEnvio.aprovada):
        raise HTTPException(409, "Semana já enviada ou aprovada")

    if envio:  # reprovada → reenvio
        envio.status = StatusEnvio.enviada
        envio.total_horas = round(total, 2)
        envio.enviado_em = date.today()
        envio.decidido_em = None
        envio.comentario_gestor = ""
    else:
        envio = EnvioSemana(
            consultor_id=dados.consultor_id,
            semana=segunda,
            status=StatusEnvio.enviada,
            total_horas=round(total, 2),
            enviado_em=date.today(),
        )
    session.add(envio)
    session.commit()
    session.refresh(envio)
    return {"id": envio.id, "status": envio.status, "total_horas": envio.total_horas}


@router.get("/atividades", dependencies=[Depends(exigir_gestao)])
def atividades_recentes(
    limite: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    """Feed do gestor: últimos apontamentos COM descrição do que foi feito."""
    registros = session.exec(
        select(Apontamento)
        .where(Apontamento.descricao != "")
        .order_by(Apontamento.data.desc(), Apontamento.id.desc())
        .limit(limite)
    ).all()

    feed = []
    for ap in registros:
        aloc = ap.alocacao
        consultor = aloc.consultor if aloc else None
        fase = aloc.fase if aloc else None
        projeto = fase.projeto if fase else None
        feed.append(
            {
                "id": ap.id,
                "data": ap.data.isoformat(),
                "horas": ap.horas,
                "descricao": ap.descricao,
                "consultor": consultor.nome if consultor else "",
                "consultor_id": consultor.id if consultor else None,
                "projeto": projeto.nome if projeto else "",
                "projeto_id": projeto.id if projeto else None,
                "fase": fase.nome if fase else "",
            }
        )
    return feed
