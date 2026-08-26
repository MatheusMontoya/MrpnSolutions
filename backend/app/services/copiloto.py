"""Copiloto IA — a camada de inteligência POR CIMA do motor determinístico.

Arquitetura plugável:
- `gerar_insights()` varre o motor (baseline, capacidade, faturas, riscos,
  gates, pipeline) e produz insights determinísticos — funciona SEMPRE.
- `perguntar()` responde perguntas: com a chave da API Anthropic configurada,
  envia o contexto do motor para o modelo; sem chave, responde com os
  insights determinísticos relevantes.

Nenhuma regra de cálculo vive aqui — o copiloto LÊ o motor, nunca o substitui.
"""
from datetime import date, timedelta

from sqlmodel import Session, select

from ..models import (
    HORAS_SEMANA_PADRAO,
    Alocacao,
    Ausencia,
    Configuracao,
    Consultor,
    EstagioProposta,
    Fatura,
    MudancaCR,
    Pendencia,
    Projeto,
    Proposta,
    Risco,
    StatusFatura,
    StatusMudanca,
    StatusPendencia,
    StatusProjeto,
    StatusRisco,
)
from .receita import (
    capacidade_na_semana,
    horas_alocadas_na_semana,
    horas_ausentes_na_semana,
    segunda_da_semana,
)

SEVERIDADES = {"critico": 0, "atencao": 1, "info": 2}


def _insight(tipo: str, severidade: str, titulo: str, detalhe: str, link: str | None = None) -> dict:
    return {"tipo": tipo, "severidade": severidade, "titulo": titulo, "detalhe": detalhe, "link": link}


def gerar_insights(session: Session) -> list[dict]:
    """Varre o motor e devolve os insights ordenados por severidade."""
    hoje = date.today()
    insights: list[dict] = []

    # ---- faturas vencidas (inadimplência) ----
    vencidas = [
        f for f in session.exec(select(Fatura).where(Fatura.status == StatusFatura.emitida)).all()
        if f.data_vencimento and f.data_vencimento < hoje
    ]
    if vencidas:
        total = sum(f.valor for f in vencidas)
        pior = max(vencidas, key=lambda f: (hoje - f.data_vencimento).days)
        insights.append(_insight(
            "cobranca", "critico",
            f"R$ {total:,.0f} em faturas vencidas".replace(",", "."),
            f"{len(vencidas)} fatura(s) em aberto após o vencimento — a mais antiga "
            f"({pior.projeto.nome if pior.projeto else '?'}) está {((hoje - pior.data_vencimento).days)} dias vencida.",
            "/contas-a-receber",
        ))

    # ---- desvio de baseline por projeto ----
    for p in session.exec(select(Projeto).where(Projeto.status == StatusProjeto.ativo)).all():
        desvios = [
            (f.data_fim_prevista - f.baseline_fim).days
            for f in p.fases if f.baseline_fim
        ]
        pior_desvio = max(desvios, default=0)
        if pior_desvio > 0:
            insights.append(_insight(
                "prazo", "atencao" if pior_desvio <= 14 else "critico",
                f"{p.nome}: +{pior_desvio}d vs linha de base",
                "O replanejamento acumulado já desloca o fim do projeto — avalie o impacto "
                "na receita mensal com o diff da cascata antes de novos adiamentos.",
                f"/projetos/{p.id}",
            ))

    # ---- capacidade: gargalos nas próximas 6 semanas ----
    consultores = session.exec(select(Consultor)).all()
    alocacoes = session.exec(select(Alocacao)).all()
    ausencias = session.exec(select(Ausencia)).all()
    base = segunda_da_semana(hoje)
    for i in range(6):
        seg = base + timedelta(weeks=i)
        demanda = sum(horas_alocadas_na_semana(a, seg) for a in alocacoes)
        capacidade = sum(
            capacidade_na_semana([x for x in ausencias if x.consultor_id == c.id], seg)
            for c in consultores
        )
        if demanda > capacidade:
            insights.append(_insight(
                "capacidade", "atencao",
                f"Gargalo na semana de {seg.strftime('%d/%m')}",
                f"Demanda de {demanda:.0f}h contra capacidade de {capacidade:.0f}h "
                f"({demanda - capacidade:.0f}h acima) — redistribua alocações ou reveja ausências.",
                "/consultores",
            ))
            break  # um aviso de gargalo basta

    # ---- consultores superalocados / ociosos na semana corrente ----
    from .receita import utilizacao_semanal
    for c in consultores:
        u = utilizacao_semanal(
            [a for a in alocacoes if a.consultor_id == c.id],
            base,
            [x for x in ausencias if x.consultor_id == c.id],
        )
        if u["status"] == "superalocado":
            insights.append(_insight(
                "alocacao", "atencao",
                f"{c.nome} superalocado nesta semana",
                f"{u['horas']}h alocadas para capacidade de {u['capacidade']}h — risco de atraso ou hora extra.",
                f"/consultores/{c.id}",
            ))

    # ---- riscos críticos abertos ----
    from ..routers.governanca import severidade as calc_sev
    riscos = session.exec(select(Risco).where(Risco.status == StatusRisco.aberto)).all()
    criticos = [r for r in riscos if calc_sev(r.probabilidade, r.impacto) == "critica"]
    for r in criticos:
        insights.append(_insight(
            "risco", "critico",
            f"Risco crítico aberto: {r.titulo}",
            (f"Projeto {r.projeto.nome}. " if r.projeto else "") +
            (f"Resposta planejada: {r.resposta}" if r.resposta else "Sem plano de resposta definido — defina um."),
            f"/projetos/{r.projeto_id}",
        ))

    # ---- CRs abertas com impacto ----
    crs = session.exec(select(MudancaCR).where(MudancaCR.status == StatusMudanca.aberta)).all()
    if crs:
        total_valor = sum(m.impacto_valor for m in crs)
        insights.append(_insight(
            "mudanca", "atencao",
            f"{len(crs)} mudança(s) aguardando decisão",
            f"Impacto potencial de R$ {total_valor:,.0f} e {sum(m.impacto_horas for m in crs):.0f}h — "
            "escopo aberto corrói margem em silêncio.".replace(",", "."),
            f"/projetos/{crs[0].projeto_id}",
        ))

    # ---- propostas: validade vencendo / paradas ----
    ativas = [
        p for p in session.exec(select(Proposta)).all()
        if p.estagio not in (EstagioProposta.perdida, EstagioProposta.convertida)
    ]
    for p in ativas:
        if p.validade and hoje <= p.validade <= hoje + timedelta(days=7):
            insights.append(_insight(
                "comercial", "atencao",
                f"Proposta '{p.nome}' vence em {(p.validade - hoje).days} dia(s)",
                f"Cliente {p.cliente.nome if p.cliente else '?'} — renove a validade ou force a decisão.",
                "/propostas",
            ))
        elif (hoje - p.criada_em).days > 30:
            insights.append(_insight(
                "comercial", "info",
                f"Proposta '{p.nome}' parada há {(hoje - p.criada_em).days} dias",
                f"Estágio '{p.estagio}'. Funil parado esfria — agende follow-up.",
                "/propostas",
            ))

    # ---- pendências de alta prioridade abertas ----
    pend = session.exec(select(Pendencia).where(
        Pendencia.status != StatusPendencia.resolvida
    )).all()
    altas = [x for x in pend if x.prioridade == "alta"]  # str-enum compara direto
    if altas:
        insights.append(_insight(
            "pendencia", "atencao",
            f"{len(altas)} pendência(s) de alta prioridade em aberto",
            "; ".join(x.titulo for x in altas[:3]) + ("…" if len(altas) > 3 else ""),
            "/pendencias",
        ))

    insights.sort(key=lambda i: SEVERIDADES.get(i["severidade"], 9))
    return insights


def montar_contexto(session: Session) -> str:
    """Contexto compacto do estado da consultoria, para o modelo de IA."""
    from ..routers.financeiro import fluxo_de_caixa, rentabilidade

    insights = gerar_insights(session)
    fluxo = fluxo_de_caixa(session)["serie"][-4:]
    rank = rentabilidade(session)["ranking"]

    linhas = ["# Estado atual da consultoria (dados do motor determinístico)", "", "## Alertas ativos"]
    for i in insights:
        linhas.append(f"- [{i['severidade']}] {i['titulo']}: {i['detalhe']}")
    linhas.append("")
    linhas.append("## Fluxo de caixa recente/projetado")
    for m in fluxo:
        linhas.append(
            f"- {m['mes']}: recebido {m['entrada_recebida']:.0f}, projetado {m['entrada_projetada']:.0f}, "
            f"saídas {m['saida']:.0f}, acumulado {m['acumulado']:.0f}"
        )
    linhas.append("")
    linhas.append("## Rentabilidade por projeto (realizada)")
    for r in rank:
        linhas.append(f"- {r['projeto']} ({r['cliente']}): receita {r['receita_realizada']:.0f}, margem {r['margem']:.0f} ({r['margem_pct']:.0%})")
    return "\n".join(linhas)


def _responder_deterministico(pergunta: str, insights: list[dict]) -> str:
    """Sem chave de API: responde com os insights mais relevantes à pergunta."""
    p = pergunta.lower()
    afinidade = {
        "cobranca": ["fatura", "venc", "receb", "cobra", "inadimpl"],
        "prazo": ["atras", "prazo", "baseline", "cronograma", "fase"],
        "capacidade": ["capacidade", "gargalo", "aloc", "equipe", "demanda"],
        "alocacao": ["superaloc", "ocioso", "consultor", "aloc"],
        "risco": ["risco"],
        "mudanca": ["mudan", "cr", "escopo"],
        "comercial": ["proposta", "funil", "pipeline", "venda", "cliente"],
        "pendencia": ["pendên", "pendenc", "ocorrênc"],
    }
    relevantes = [
        i for i in insights
        if any(t in p for t in afinidade.get(i["tipo"], []))
    ] or insights[:5]

    corpo = "\n".join(f"• {i['titulo']} — {i['detalhe']}" for i in relevantes[:6])
    rodape = (
        "\n\n(Resposta gerada pelos insights determinísticos do motor. "
        "Configure a chave da API Anthropic em Configurações → Copiloto IA "
        "para respostas em linguagem natural sobre qualquer pergunta.)"
    )
    if not relevantes:
        return "Nenhum alerta ativo no momento — operação saudável." + rodape
    return corpo + rodape


def _responder_com_ia(pergunta: str, contexto: str, cfg: Configuracao) -> str:
    """Com chave: chama a API da Anthropic com o contexto do motor."""
    import httpx

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": cfg.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": cfg.modelo_ia or "claude-sonnet-5",
            "max_tokens": 1024,
            "system": (
                "Você é o copiloto do RunRate, sistema de gestão de uma consultoria SAP "
                "que fatura por hora-homem (metodologia SAP Activate, 6 fases). Responda em "
                "português brasileiro, de forma direta e acionável, SEMPRE fundamentado nos "
                "dados do contexto — nunca invente números. Os cálculos vêm do motor "
                "determinístico do sistema; seu papel é interpretar, priorizar e recomendar."
            ),
            "messages": [{
                "role": "user",
                "content": f"{contexto}\n\n# Pergunta do gestor\n{pergunta}",
            }],
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    dados = resp.json()
    return "".join(b.get("text", "") for b in dados.get("content", []))


def perguntar(session: Session, pergunta: str) -> dict:
    cfg = session.exec(select(Configuracao)).first()
    insights = gerar_insights(session)
    ia_ativa = bool(cfg and cfg.anthropic_api_key.strip())

    if ia_ativa:
        try:
            resposta = _responder_com_ia(pergunta, montar_contexto(session), cfg)
            return {"resposta": resposta, "ia_generativa": True}
        except Exception as e:  # chave inválida, rede bloqueada etc. → degrada com clareza
            return {
                "resposta": _responder_deterministico(pergunta, insights)
                + f"\n\n(Falha ao chamar a IA generativa: {e})",
                "ia_generativa": False,
            }
    return {"resposta": _responder_deterministico(pergunta, insights), "ia_generativa": False}
