from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Alocacao,
    Apontamento,
    Ausencia,
    Configuracao,
    Consultor,
    Despesa,
    EnvioSemana,
    Pendencia,
    Projeto,
    StatusAprovacao,
    StatusDespesa,
    StatusEnvio,
    StatusPendencia,
    StatusProjeto,
)
from ..services.projetos import fase_atual
from ..services.receita import (
    horas_previstas,
    margem,
    receita_mensal_prevista,
    receita_mensal_realizada,
    segunda_da_semana,
    utilizacao_semanal,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(session: Session = Depends(get_session)):
    hoje = date.today()
    cfg = session.exec(select(Configuracao)).first()
    meta_margem = cfg.meta_margem if cfg else 0.45

    # --- receita prevista vs realizada por mês (todos os projetos) ---
    alocacoes = session.exec(select(Alocacao)).all()
    apontamentos = session.exec(select(Apontamento)).all()
    prevista = receita_mensal_prevista(alocacoes)
    realizada = receita_mensal_realizada(apontamentos)

    # margem = receita - custo, sobre o mesmo volume de horas
    margem_prevista = sum(
        margem(
            horas_previstas(a.data_inicio, a.data_fim, a.horas_semana),
            a.taxa_hora_venda,
            a.consultor.taxa_hora_custo if a.consultor else 0.0,
        )
        for a in alocacoes
    )
    margem_realizada = sum(
        margem(
            ap.horas,
            ap.alocacao.taxa_hora_venda,
            ap.alocacao.consultor.taxa_hora_custo if ap.alocacao and ap.alocacao.consultor else 0.0,
        )
        for ap in apontamentos
    )
    meses = sorted(set(prevista) | set(realizada))
    receita_mensal = [
        {
            "mes": m,
            "prevista": round(prevista.get(m, 0.0), 2),
            "realizada": round(realizada.get(m, 0.0), 2),
        }
        for m in meses
    ]

    # --- utilização dos consultores na semana corrente ---
    segunda = segunda_da_semana(hoje)
    consultores = session.exec(select(Consultor).order_by(Consultor.nome)).all()
    utilizacao = []
    todas_ausencias = session.exec(select(Ausencia)).all()
    for c in consultores:
        alocs = [a for a in alocacoes if a.consultor_id == c.id]
        aus = [x for x in todas_ausencias if x.consultor_id == c.id]
        u = utilizacao_semanal(alocs, segunda, aus)
        utilizacao.append(
            {
                "consultor_id": c.id,
                "nome": c.nome,
                "senioridade": c.senioridade,
                "modulo_sap": c.modulo_sap,
                **u,
            }
        )

    # --- projetos ativos com fase Activate atual ---
    projetos = session.exec(
        select(Projeto).where(Projeto.status == StatusProjeto.ativo).order_by(Projeto.nome)
    ).all()
    projetos_ativos = []
    for p in projetos:
        atual = fase_atual(p, hoje)
        alocs_projeto = [a for f in p.fases for a in f.alocacoes]
        aps_projeto = [ap for a in alocs_projeto for ap in a.apontamentos]
        prev = receita_mensal_prevista(alocs_projeto)
        real = receita_mensal_realizada(aps_projeto)
        projetos_ativos.append(
            {
                "id": p.id,
                "nome": p.nome,
                "cliente": p.cliente.nome if p.cliente else "",
                "fase_atual": atual.nome if atual else None,
                "fase_atual_ordem": atual.ordem if atual else None,
                "receita_prevista": round(sum(prev.values()), 2),
                "receita_realizada": round(sum(real.values()), 2),
            }
        )

    # --- pendências de decisão do gestor (aprovações + pendências abertas) ---
    aprovacoes_pendentes = (
        len(session.exec(select(EnvioSemana).where(EnvioSemana.status == StatusEnvio.enviada)).all())
        + len(session.exec(select(Ausencia).where(Ausencia.status == StatusAprovacao.pendente)).all())
        + len(session.exec(select(Despesa).where(Despesa.status == StatusDespesa.pendente)).all())
    )
    pendencias_abertas = len(
        session.exec(select(Pendencia).where(Pendencia.status != StatusPendencia.resolvida)).all()
    )

    return {
        "hoje": hoje.isoformat(),
        "semana_corrente": segunda.isoformat(),
        "aprovacoes_pendentes": aprovacoes_pendentes,
        "pendencias_abertas": pendencias_abertas,
        "receita_mensal": receita_mensal,
        "margem_prevista": round(margem_prevista, 2),
        "margem_realizada": round(margem_realizada, 2),
        "meta_margem": meta_margem,
        "utilizacao_semana": utilizacao,
        "projetos_ativos": projetos_ativos,
    }
