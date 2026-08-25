from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..seguranca import eh_ceo, eh_gestao, exigir_ceo, exigir_gestao, sem_dinheiro, usuario_atual
from ..models import Alocacao, Cliente, Fase, Projeto, StatusProjeto
from ..services.projetos import criar_projeto_com_fases, fase_atual
from .atividades import resumo_gate
from ..services.reagendamento import aplicar_reagendamento, simular_reagendamento
from ..services.receita import (
    horas_previstas,
    margem,
    receita_mensal_prevista,
    receita_mensal_realizada,
    receita_prevista,
)

router = APIRouter(prefix="/api", tags=["Projetos"])


class ProjetoCreate(BaseModel):
    nome: str
    cliente_id: int
    data_inicio: date
    status: StatusProjeto = StatusProjeto.ativo
    modelo_id: int | None = None  # None = templates padrão do Activate


class FaseUpdate(BaseModel):
    data_inicio_prevista: date | None = None
    status: str | None = None


class ReagendamentoRequest(BaseModel):
    nova_data_fim: date
    aplicar: bool = False


@router.get("/projetos")
def listar_projetos(request: Request, session: Session = Depends(get_session)):
    """Gestão vê a carteira inteira; consultor vê só os projetos em que tem
    alocação — a lista serve a ele apenas para escolher o projeto da despesa."""
    projetos = session.exec(select(Projeto).order_by(Projeto.nome)).all()
    u = usuario_atual(request)
    if not eh_gestao(u):
        alocacoes = session.exec(
            select(Alocacao).where(Alocacao.consultor_id == u.get("consultor_id"))
        ).all()
        meus = {a.fase.projeto_id for a in alocacoes if a.fase}
        projetos = [p for p in projetos if p.id in meus]
    hoje = date.today()
    resposta = []
    for p in projetos:
        atual = fase_atual(p, hoje)
        resposta.append(
            {
                "id": p.id,
                "nome": p.nome,
                "cliente": p.cliente.nome if p.cliente else "",
                "cliente_id": p.cliente_id,
                "data_inicio": p.data_inicio.isoformat(),
                "status": p.status,
                "fase_atual": atual.nome if atual else None,
                "fases": [
                    {
                        "id": f.id,
                        "nome": f.nome,
                        "ordem": f.ordem,
                        "data_inicio_prevista": f.data_inicio_prevista.isoformat(),
                        "data_fim_prevista": f.data_fim_prevista.isoformat(),
                        "status": f.status,
                    }
                    for f in sorted(p.fases, key=lambda f: f.ordem)
                ],
            }
        )
    return resposta


@router.post("/projetos", status_code=201, dependencies=[Depends(exigir_ceo)])
def criar_projeto(dados: ProjetoCreate, request: Request, session: Session = Depends(get_session)):
    if not session.get(Cliente, dados.cliente_id):
        raise HTTPException(404, "Cliente não encontrado")
    modelo = None
    if dados.modelo_id is not None:
        from ..models import ModeloProjeto

        modelo = session.get(ModeloProjeto, dados.modelo_id)
        if not modelo:
            raise HTTPException(404, "Modelo de projeto não encontrado")
    projeto = Projeto(**dados.model_dump(exclude={"modelo_id"}))
    projeto = criar_projeto_com_fases(session, projeto, modelo)
    return obter_projeto(projeto.id, request, session)


@router.get("/projetos/{projeto_id}", dependencies=[Depends(exigir_gestao)])
def obter_projeto(projeto_id: int, request: Request, session: Session = Depends(get_session)):
    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")
    hoje = date.today()
    atual = fase_atual(p, hoje)

    fases = []
    todas_alocacoes = []
    for f in sorted(p.fases, key=lambda f: f.ordem):
        alocacoes = []
        for a in f.alocacoes:
            horas = horas_previstas(a.data_inicio, a.data_fim, a.horas_semana)
            horas_reais = sum(ap.horas for ap in a.apontamentos)
            taxa_custo = a.consultor.taxa_hora_custo if a.consultor else 0.0
            alocacoes.append(
                {
                    "id": a.id,
                    "consultor_id": a.consultor_id,
                    "consultor": a.consultor.nome if a.consultor else "",
                    "senioridade": a.consultor.senioridade if a.consultor else None,
                    "modulo_sap": a.consultor.modulo_sap if a.consultor else "",
                    "data_inicio": a.data_inicio.isoformat(),
                    "data_fim": a.data_fim.isoformat(),
                    "horas_semana": a.horas_semana,
                    "taxa_hora_venda": a.taxa_hora_venda,
                    "taxa_negociada": a.consultor is not None
                    and a.taxa_hora_venda != a.consultor.taxa_hora_venda,
                    "horas_previstas": round(horas, 2),
                    "horas_realizadas": round(horas_reais, 2),
                    "receita_prevista": round(horas * a.taxa_hora_venda, 2),
                    "receita_realizada": round(horas_reais * a.taxa_hora_venda, 2),
                    "margem_prevista": round(margem(horas, a.taxa_hora_venda, taxa_custo), 2),
                }
            )
            todas_alocacoes.append(a)
        atividades = [
            {
                "id": at.id,
                "titulo": at.titulo,
                "ordem": at.ordem,
                "responsavel_id": at.responsavel_id,
                "responsavel": at.responsavel.nome if at.responsavel else None,
                "data_prevista": at.data_prevista.isoformat() if at.data_prevista else None,
                "status": at.status,
            }
            for at in sorted(f.atividades, key=lambda x: x.ordem)
        ]
        itens_gate = [
            {
                "id": ig.id,
                "codigo": ig.codigo,
                "pergunta": ig.pergunta,
                "risco": ig.risco,
                "status": ig.status,
                "plano_acao": ig.plano_acao,
                "responsavel": ig.responsavel,
            }
            for ig in sorted(f.itens_gate, key=lambda x: x.codigo)
        ]
        fases.append(
            {
                "id": f.id,
                "nome": f.nome,
                "ordem": f.ordem,
                "data_inicio_prevista": f.data_inicio_prevista.isoformat(),
                "data_fim_prevista": f.data_fim_prevista.isoformat(),
                "baseline_fim": f.baseline_fim.isoformat() if f.baseline_fim else None,
                "desvio_baseline_dias": (f.data_fim_prevista - f.baseline_fim).days if f.baseline_fim else 0,
                "status": f.status,
                "atual": atual is not None and f.id == atual.id,
                "receita_prevista": round(sum(al["receita_prevista"] for al in alocacoes), 2),
                "receita_realizada": round(sum(al["receita_realizada"] for al in alocacoes), 2),
                "alocacoes": alocacoes,
                "atividades": atividades,
                "gate": {"itens": itens_gate, **resumo_gate(f)},
            }
        )

    apontamentos = [ap for a in todas_alocacoes for ap in a.apontamentos]
    # O RH precisa saber QUEM está alocado em que projeto; não precisa saber
    # quanto o projeto fatura. O dinheiro sai do payload dele em três níveis:
    # topo, fase e alocação — senão a margem se recompõe somando as partes.
    DINHEIRO_ALOCACAO = ("taxa_hora_venda", "taxa_negociada", "receita_prevista",
                         "receita_realizada", "margem_prevista")
    DINHEIRO_FASE = ("receita_prevista", "receita_realizada")
    if not eh_ceo(usuario_atual(request)):
        fases = [
            {
                **{k: v for k, v in f.items() if k not in DINHEIRO_FASE},
                "alocacoes": [
                    {k: v for k, v in a.items() if k not in DINHEIRO_ALOCACAO}
                    for a in f.get("alocacoes", [])
                ],
            }
            for f in fases
        ]

    return sem_dinheiro({
        "id": p.id,
        "nome": p.nome,
        "cliente": p.cliente.nome if p.cliente else "",
        "cliente_id": p.cliente_id,
        "data_inicio": p.data_inicio.isoformat(),
        "status": p.status,
        "fase_atual": atual.nome if atual else None,
        "fases": fases,
        "receita_mensal_prevista": receita_mensal_prevista(todas_alocacoes),
        "receita_mensal_realizada": receita_mensal_realizada(apontamentos),
        "receita_prevista_total": round(sum(f.get("receita_prevista", 0) for f in fases), 2),
        "receita_realizada_total": round(sum(f.get("receita_realizada", 0) for f in fases), 2),
    }, usuario_atual(request),
        ("receita_mensal_prevista", "receita_mensal_realizada",
         "receita_prevista_total", "receita_realizada_total"))


@router.get("/projetos/{projeto_id}/evm", dependencies=[Depends(exigir_ceo)])
def evm_do_projeto(projeto_id: int, session: Session = Depends(get_session)):
    """Valor agregado (EVM): PV/EV/AC, SPI/CPI e EAC — tudo derivado do motor."""
    from ..models import Despesa
    from ..services.evm import calcular_evm

    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")
    despesas = session.exec(select(Despesa).where(Despesa.projeto_id == projeto_id)).all()
    return calcular_evm(p, despesas)


@router.patch("/projetos/{projeto_id}", dependencies=[Depends(exigir_ceo)])
def atualizar_projeto(projeto_id: int, dados: dict, session: Session = Depends(get_session)):
    p = session.get(Projeto, projeto_id)
    if not p:
        raise HTTPException(404, "Projeto não encontrado")
    if "status" in dados:
        p.status = StatusProjeto(dados["status"])
    if "nome" in dados:
        p.nome = dados["nome"]
    session.add(p)
    session.commit()
    return {"ok": True}


@router.post("/fases/{fase_id}/reagendar", dependencies=[Depends(exigir_ceo)])
def reagendar_fase(fase_id: int, req: ReagendamentoRequest, session: Session = Depends(get_session)):
    """Move a data-fim de uma fase. Com aplicar=false devolve só a simulação
    (diff antes→depois); com aplicar=true persiste a cascata."""
    try:
        if req.aplicar:
            return aplicar_reagendamento(session, fase_id, req.nova_data_fim)
        return simular_reagendamento(session, fase_id, req.nova_data_fim)
    except ValueError as e:
        raise HTTPException(422, str(e))
