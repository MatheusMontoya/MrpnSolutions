"""Seed de demonstração: 2 clientes, 3 projetos em fases diferentes, 6
consultores, alocações e ~8 semanas de apontamentos. Determinístico e relativo
à data de hoje, para o dashboard nascer sempre populado.

Cenários garantidos na semana corrente:
- Ana Souza com 50h alocadas (>100% → superalocada);
- Fábio Torres com 12h (<60% → ocioso);
- Elisa Rocha com taxa negociada abaixo da sua taxa default.
"""
from datetime import date, timedelta

from sqlmodel import Session, select

from .database import engine
from .models import (
    Alocacao,
    Apontamento,
    Ausencia,
    Cliente,
    Configuracao,
    Consultor,
    Contrato,
    Despesa,
    EnvioSemana,
    EstagioProposta,
    Fase,
    Fatura,
    Feriado,
    GrauRisco,
    MudancaCR,
    Pendencia,
    PrioridadePendencia,
    Projeto,
    Proposta,
    Risco,
    Senioridade,
    StatusAprovacao,
    StatusAtividade,
    StatusDespesa,
    StatusEnvio,
    StatusFase,
    StatusFatura,
    StatusGate,
    StatusMudanca,
    StatusPendencia,
    StatusRisco,
    TipoAusencia,
    TipoDespesa,
)
from .services.projetos import criar_projeto_com_fases
from .services.receita import eh_dia_util, segunda_da_semana


def seed_se_vazio() -> None:
    with Session(engine) as session:
        if session.exec(select(Cliente)).first():
            return
        _popular(session)


def _fase(session: Session, projeto: Projeto, nome: str) -> Fase:
    return session.exec(
        select(Fase).where(Fase.projeto_id == projeto.id, Fase.nome == nome)
    ).one()


def _alocar(session: Session, consultor: Consultor, fase: Fase, horas_semana: float,
            taxa: float | None = None) -> Alocacao:
    a = Alocacao(
        consultor_id=consultor.id,
        fase_id=fase.id,
        data_inicio=fase.data_inicio_prevista,
        data_fim=fase.data_fim_prevista,
        horas_semana=horas_semana,
        taxa_hora_venda=taxa if taxa is not None else consultor.taxa_hora_venda,
    )
    session.add(a)
    return a


# Descrições realistas de atividade por fase Activate (para o feed do gestor).
ATIVIDADES_POR_FASE = {
    "Discover": ["Análise de viabilidade e escopo", "Reunião de kickoff com stakeholders"],
    "Prepare": ["Setup do ambiente de projeto", "Plano de projeto e cronograma", "Definição da equipe e papéis"],
    "Explore": ["Workshop de processos com key users", "Levantamento de requisitos", "Documentação de gaps (fit-to-standard)", "Blueprint funcional"],
    "Realize": ["Configuração (customizing) no ambiente DEV", "Testes unitários do módulo", "Desenvolvimento de report/enhancement", "Ajustes pós-teste integrado", "Preparação de dados de teste"],
    "Deploy": ["Preparação do cutover", "Migração de dados mestre", "Treinamento de usuários finais"],
    "Run": ["Suporte pós-go-live (hypercare)", "Resolução de chamado de incidente", "Monitoramento e ajustes finos"],
}


def _apontar_historico(session: Session, alocacoes: list[Alocacao], hoje: date) -> None:
    """Lança horas realizadas nos dias úteis das últimas 8 semanas, dentro do
    intervalo de cada alocação, com variação determinística em torno do previsto.
    Os lançamentos das 2 últimas semanas ganham uma descrição do que foi feito,
    para o feed de atividades do gestor nascer populado."""
    inicio_janela = segunda_da_semana(hoje) - timedelta(weeks=8)
    janela_descricao = hoje - timedelta(days=14)
    fatores = [1.0, 0.9, 1.1, 1.0, 0.8]  # variação cíclica determinística
    for a in alocacoes:
        fase_nome = a.fase.nome if a.fase else "Realize"
        atividades = ATIVIDADES_POR_FASE.get(fase_nome, ["Atividades do projeto"])
        d = max(a.data_inicio, inicio_janela)
        fim = min(a.data_fim, hoje)
        while d <= fim:
            if eh_dia_util(d):
                fator = fatores[(a.fase_id + d.toordinal()) % len(fatores)]
                horas = round((a.horas_semana / 5.0) * fator, 1)
                if horas > 0:
                    # descrição só nos lançamentos recentes (determinística)
                    descricao = ""
                    if d >= janela_descricao:
                        descricao = atividades[(a.id + d.toordinal()) % len(atividades)]
                    session.add(Apontamento(alocacao_id=a.id, data=d, horas=horas, descricao=descricao))
            d += timedelta(days=1)


def _popular(session: Session) -> None:
    hoje = date.today()
    segunda = segunda_da_semana(hoje)

    session.add(Configuracao())  # parâmetros padrão da consultoria

    aurora = Cliente(nome="Aurora Alimentos", contato="Paulo Andrade — paulo.andrade@aurora.com.br")
    tecnomed = Cliente(nome="TecnoMed Diagnósticos", contato="Renata Campos — renata.campos@tecnomed.com.br")
    session.add(aurora)
    session.add(tecnomed)
    session.flush()

    ana = Consultor(nome="Ana Souza", senioridade=Senioridade.senior, modulo_sap="FI/CO", taxa_hora_custo=120, taxa_hora_venda=260)
    bruno = Consultor(nome="Bruno Lima", senioridade=Senioridade.senior, modulo_sap="MM", taxa_hora_custo=110, taxa_hora_venda=240)
    carla = Consultor(nome="Carla Mendes", senioridade=Senioridade.pleno, modulo_sap="SD", taxa_hora_custo=80, taxa_hora_venda=180)
    diego = Consultor(nome="Diego Ferreira", senioridade=Senioridade.pleno, modulo_sap="PP", taxa_hora_custo=75, taxa_hora_venda=170)
    elisa = Consultor(nome="Elisa Rocha", senioridade=Senioridade.junior, modulo_sap="ABAP", taxa_hora_custo=50, taxa_hora_venda=110)
    fabio = Consultor(nome="Fábio Torres", senioridade=Senioridade.junior, modulo_sap="BASIS", taxa_hora_custo=45, taxa_hora_venda=100)
    for c in (ana, bruno, carla, diego, elisa, fabio):
        session.add(c)
    session.flush()

    # usuários com senha real (demo: todos com senha "psa123")
    from .models import PerfilUsuario, Usuario
    from .services.auth import gerar_hash

    senha_demo = gerar_hash("psa123")  # mesmo hash para todos acelera o seed
    session.add(Usuario(
        email="gestor@psa.com", nome="Gestor Demo",
        perfil=PerfilUsuario.gestor, senha_hash=senha_demo,
    ))
    for c in (ana, bruno, carla, diego, elisa, fabio):
        email = c.nome.split()[0].lower()
        email = email.translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))
        session.add(Usuario(
            email=f"{email}@psa.com", nome=c.nome,
            perfil=PerfilUsuario.consultor, consultor_id=c.id, senha_hash=senha_demo,
        ))
    session.flush()

    # Modelos de projeto: o padrão (templates Activate) + um rollout enxuto.
    from .models import ModeloAtividade, ModeloItemGate, ModeloProjeto
    from .services.projetos import criar_modelo_padrao
    from .services.templates_activate import ATIVIDADES_PADRAO, GATES_PADRAO

    criar_modelo_padrao(session)
    rollout = ModeloProjeto(
        nome="Rollout / nova unidade",
        descricao="Versão enxuta para ativar uma unidade num template já implantado.",
    )
    session.add(rollout)
    session.flush()
    for fase_nome, titulos in ATIVIDADES_PADRAO.items():
        for i, titulo in enumerate(titulos[:3]):  # rollout: só as entregas essenciais
            session.add(ModeloAtividade(modelo_id=rollout.id, fase=fase_nome, titulo=titulo, ordem=i))
        session.add(ModeloAtividade(
            modelo_id=rollout.id, fase=fase_nome,
            titulo="Validar aderência da unidade ao template global", ordem=3,
        ))
    for fase_nome, gates in GATES_PADRAO.items():
        for codigo, pergunta, risco in gates[:2]:
            session.add(ModeloItemGate(modelo_id=rollout.id, fase=fase_nome, codigo=codigo, pergunta=pergunta, risco=risco))
    session.flush()

    # Datas de início escolhidas para cada projeto estar numa fase diferente hoje
    # (durações default: Discover 2s, Prepare 3s, Explore 6s, Realize 10s...).
    p1 = criar_projeto_com_fases(
        session,
        Projeto(nome="S/4HANA Greenfield", cliente_id=aurora.id, data_inicio=segunda - timedelta(weeks=15)),
    )  # semana 15 → Realize (11..21)
    p2 = criar_projeto_com_fases(
        session,
        Projeto(nome="Rollout Fiori Laboratórios", cliente_id=tecnomed.id, data_inicio=segunda - timedelta(weeks=8)),
        modelo=rollout,  # nasce do modelo enxuto de rollout
    )  # semana 8 → Explore (5..11)
    p3 = criar_projeto_com_fases(
        session,
        Projeto(nome="Migração ECC → S/4", cliente_id=aurora.id, data_inicio=segunda - timedelta(weeks=3)),
    )  # semana 3 → Prepare (2..5)

    alocacoes = [
        # Projeto 1 — fases passadas (histórico) e fase atual Realize
        _alocar(session, bruno, _fase(session, p1, "Explore"), 20),
        _alocar(session, diego, _fase(session, p1, "Explore"), 40),
        _alocar(session, ana, _fase(session, p1, "Realize"), 30),
        _alocar(session, carla, _fase(session, p1, "Realize"), 40),
        # taxa negociada: Elisa vale 110 na tabela, mas neste contrato fatura 95
        _alocar(session, elisa, _fase(session, p1, "Realize"), 40, taxa=95),
        _alocar(session, carla, _fase(session, p1, "Deploy"), 30),
        # Projeto 2 — Explore em andamento (Ana fica superalocada: 30h + 20h)
        _alocar(session, ana, _fase(session, p2, "Explore"), 20),
        _alocar(session, bruno, _fase(session, p2, "Explore"), 30),
        _alocar(session, diego, _fase(session, p2, "Explore"), 30),
        # Projeto 3 — Prepare em andamento (Fábio fica ocioso: só 12h)
        _alocar(session, bruno, _fase(session, p3, "Prepare"), 10),
        _alocar(session, diego, _fase(session, p3, "Prepare"), 8),
        _alocar(session, fabio, _fase(session, p3, "Prepare"), 12),
    ]
    session.flush()

    _apontar_historico(session, alocacoes, hoje)
    session.flush()

    # Progresso físico coerente com o calendário (alimenta fase atual e o EVM):
    # fases já encerradas ficam concluídas (com todas as entregas), a fase em
    # curso fica em andamento com metade das entregas feitas.
    for proj in (p1, p2, p3):
        for fase in proj.fases:
            if fase.data_fim_prevista < hoje:
                fase.status = StatusFase.concluida
                for atv in fase.atividades:
                    atv.status = StatusAtividade.concluida
                for item in fase.itens_gate:  # fase só conclui com gate verde
                    item.status = StatusGate.verde
            elif fase.data_inicio_prevista <= hoje:
                fase.status = StatusFase.em_andamento
                feitas = len(fase.atividades) // 2
                for atv in fase.atividades[:feitas]:
                    atv.status = StatusAtividade.concluida
            session.add(fase)
    session.flush()

    # ---- ausências: uma aprovada (afeta capacidade) e uma pendente (fila) ----
    session.add(Ausencia(
        consultor_id=fabio.id, tipo=TipoAusencia.ferias,
        data_inicio=segunda + timedelta(weeks=1), data_fim=segunda + timedelta(weeks=2, days=-3),
        motivo="Férias programadas", status=StatusAprovacao.aprovada,
    ))
    session.add(Ausencia(
        consultor_id=elisa.id, tipo=TipoAusencia.folga,
        data_inicio=segunda + timedelta(weeks=2), data_fim=segunda + timedelta(weeks=2, days=1),
        motivo="Compensação de horas do go-live", status=StatusAprovacao.pendente,
    ))

    # ---- despesas: km pendente, hospedagem aprovada, alimentação pendente ----
    session.add(Despesa(
        consultor_id=ana.id, projeto_id=p1.id, data=hoje - timedelta(days=2),
        tipo=TipoDespesa.quilometragem, descricao="Visita ao cliente (ida e volta)",
        km=120, valor=round(120 * 1.20, 2), status=StatusDespesa.pendente,
    ))
    session.add(Despesa(
        consultor_id=bruno.id, projeto_id=p2.id, data=hoje - timedelta(days=6),
        tipo=TipoDespesa.hospedagem, descricao="Hotel — workshop fit-to-standard",
        valor=480.00, status=StatusDespesa.aprovada,
    ))
    session.add(Despesa(
        consultor_id=carla.id, projeto_id=p1.id, data=hoje - timedelta(days=1),
        tipo=TipoDespesa.alimentacao, descricao="Almoço com key users",
        valor=86.50, status=StatusDespesa.pendente,
    ))

    # ---- pendências de projeto ----
    session.add(Pendencia(
        projeto_id=p1.id, fase_id=_fase(session, p1, "Realize").id,
        titulo="Ambiente QAS instável para o teste integrado",
        descricao="Quedas intermitentes bloqueando o ciclo 2 de testes.",
        responsavel_id=bruno.id, prioridade=PrioridadePendencia.alta,
        status=StatusPendencia.aberta, criada_em=hoje - timedelta(days=3),
    ))
    session.add(Pendencia(
        projeto_id=p1.id, fase_id=_fase(session, p1, "Deploy").id,
        titulo="Definir estratégia de carga para o cutover",
        responsavel_id=ana.id, prioridade=PrioridadePendencia.media,
        status=StatusPendencia.em_andamento, criada_em=hoje - timedelta(days=7),
    ))
    session.add(Pendencia(
        projeto_id=p2.id, fase_id=_fase(session, p2, "Explore").id,
        titulo="Ata do workshop de suprimentos pendente de validação",
        responsavel_id=diego.id, prioridade=PrioridadePendencia.baixa,
        status=StatusPendencia.resolvida, criada_em=hoje - timedelta(days=10),
        resolvida_em=hoje - timedelta(days=4),
    ))

    # ---- envios de semana: um aprovado (histórico) e um aguardando decisão ----
    semana_passada = segunda - timedelta(weeks=1)

    def _total_semana(consultor_id: int) -> float:
        ids = [a.id for a in alocacoes if a.consultor_id == consultor_id]
        aps = session.exec(
            select(Apontamento).where(
                Apontamento.alocacao_id.in_(ids),
                Apontamento.data >= semana_passada,
                Apontamento.data <= semana_passada + timedelta(days=6),
            )
        ).all()
        return round(sum(ap.horas for ap in aps), 2)

    session.add(EnvioSemana(
        consultor_id=carla.id, semana=semana_passada, status=StatusEnvio.aprovada,
        total_horas=_total_semana(carla.id), enviado_em=segunda - timedelta(days=3),
        decidido_em=segunda - timedelta(days=2),
    ))
    session.add(EnvioSemana(
        consultor_id=diego.id, semana=semana_passada, status=StatusEnvio.enviada,
        total_horas=_total_semana(diego.id), enviado_em=segunda - timedelta(days=1),
    ))

    # ---- Onda 4.2: solicitações de alocação (fila) e medição aguardando aceite ----
    from .models import Medicao, SolicitacaoAlocacao
    from .routers.medicoes import _apontamentos_do_mes, _linhas

    # Ana já está superalocada nesta semana → a fila mostra o conflito ao vivo
    session.add(SolicitacaoAlocacao(
        consultor_id=ana.id, fase_id=_fase(session, p3, "Explore").id,
        data_inicio=segunda, data_fim=segunda + timedelta(weeks=4, days=4),
        horas_semana=20, justificativa="Fit-to-standard de FI/CO precisa de sênior desde o início.",
        solicitante="Gestor Demo", criada_em=hoje - timedelta(days=1),
    ))
    # Fábio está ocioso (12h) → pedido sem conflito (começa DEPOIS das férias dele)
    session.add(SolicitacaoAlocacao(
        consultor_id=fabio.id, fase_id=_fase(session, p2, "Realize").id,
        data_inicio=segunda + timedelta(weeks=2), data_fim=segunda + timedelta(weeks=7, days=4),
        horas_semana=20, justificativa="Apoio BASIS na preparação dos ambientes do Realize.",
        solicitante="Gestor Demo", criada_em=hoje,
    ))

    # modo ágil no p1: sprint 1 encerrada (com carry-over) + sprint 2 ativa
    from .models import Sprint, StatusSprint

    realize_p1 = _fase(session, p1, "Realize")
    atividades_realize = sorted(realize_p1.atividades, key=lambda a: a.ordem)
    session.add(Sprint(
        projeto_id=p1.id, numero=1, meta="Configurações centrais de FI/CO no razão",
        data_inicio=segunda - timedelta(weeks=4), data_fim=segunda - timedelta(weeks=2, days=3),
        status=StatusSprint.encerrada, encerrada_em=segunda - timedelta(weeks=2, days=3),
        carry_over=1,
    ))
    sprint2 = Sprint(
        projeto_id=p1.id, numero=2, meta="Integração MM→FI e primeiros testes unitários",
        data_inicio=segunda - timedelta(weeks=2), data_fim=segunda + timedelta(days=4),
        status=StatusSprint.ativa,
    )
    session.add(sprint2)
    session.flush()
    # kanban da sprint ativa: as entregas do Realize ainda abertas, em colunas variadas
    abertas = [a for a in atividades_realize if a.status != StatusAtividade.concluida]
    for i, atv in enumerate(abertas[:3]):
        atv.sprint_id = sprint2.id
        if i == 0:
            atv.status = StatusAtividade.em_andamento
        session.add(atv)
    session.flush()

    # orçamento do p1 com rubricas manuais além das automáticas do motor
    from .models import CategoriaOrcamento, ItemOrcamento

    session.add(ItemOrcamento(
        projeto_id=p1.id, categoria=CategoriaOrcamento.terceiros,
        descricao="Consultoria de segurança (perfis e GRC)",
        valor_orcado=18_000, valor_realizado=9_500,
    ))
    session.add(ItemOrcamento(
        projeto_id=p1.id, categoria=CategoriaOrcamento.licencas,
        descricao="Ferramenta de migração de dados",
        valor_orcado=7_500, valor_realizado=7_500,
    ))

    # medição do mês passado do p2, aguardando aceite do cliente
    competencia_passada = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
    linhas_medicao = _linhas(_apontamentos_do_mes(session, p2, competencia_passada))
    if linhas_medicao:
        session.add(Medicao(
            projeto_id=p2.id, competencia=competencia_passada,
            total_horas=round(sum(x["horas"] for x in linhas_medicao), 2),
            total_valor=round(sum(x["valor"] for x in linhas_medicao), 2),
            criada_em=hoje - timedelta(days=2),
        ))

    # ---- pipeline comercial: propostas em estágios variados ----
    session.add(Proposta(
        cliente_id=tecnomed.id, nome="Implementação SAP IBP",
        descricao="Planejamento integrado (demand + supply) para a operação de diagnósticos.",
        valor_estimado=180_000, horas_estimadas=900, probabilidade=0.6,
        estagio=EstagioProposta.negociacao, criada_em=hoje - timedelta(days=21),
    ))
    session.add(Proposta(
        cliente_id=aurora.id, nome="AMS — Sustentação S/4HANA",
        descricao="Suporte contínuo pós-go-live (banco de horas mensal).",
        valor_estimado=90_000, horas_estimadas=600, probabilidade=0.4,
        estagio=EstagioProposta.proposta, criada_em=hoje - timedelta(days=10),
    ))
    session.add(Proposta(
        cliente_id=aurora.id, nome="Rollout Filial Sul",
        descricao="Extensão do template S/4 para a nova planta.",
        valor_estimado=250_000, horas_estimadas=1400, probabilidade=0.3,
        estagio=EstagioProposta.qualificacao, criada_em=hoje - timedelta(days=4),
    ))
    session.add(Proposta(
        cliente_id=tecnomed.id, nome="Upgrade BW/4HANA",
        descricao="Perdida para concorrente por prazo.",
        valor_estimado=120_000, probabilidade=0.5,
        estagio=EstagioProposta.perdida, criada_em=hoje - timedelta(days=45),
        decidida_em=hoje - timedelta(days=12),
    ))

    # ---- Onda 3.5: feriados BR, contratos, riscos, mudanças, skills ----
    ano = hoje.year
    for f_data, f_nome in [
        (date(ano, 9, 7), "Independência do Brasil"),
        (date(ano, 10, 12), "Nossa Senhora Aparecida"),
        (date(ano, 11, 2), "Finados"),
        (date(ano, 11, 15), "Proclamação da República"),
        (date(ano, 12, 25), "Natal"),
    ]:
        session.add(Feriado(data=f_data, nome=f_nome))

    session.add(Contrato(
        cliente_id=aurora.id, nome="Contrato Guarda-chuva S/4HANA 2026",
        data_inicio=hoje - timedelta(days=140), data_fim=hoje + timedelta(days=45),
        valor=600_000, observacoes="Cobre Greenfield + Migração ECC. Renovação em negociação.",
    ))
    session.add(Contrato(
        cliente_id=tecnomed.id, nome="Contrato Rollout Fiori",
        data_inicio=hoje - timedelta(days=70), data_fim=hoje + timedelta(days=180),
        valor=180_000,
    ))

    session.add(Risco(
        projeto_id=p1.id, titulo="Indisponibilidade do time do cliente no UAT",
        probabilidade=GrauRisco.medio, impacto=GrauRisco.alto,
        resposta="Congelar agenda de key users com 3 semanas de antecedência.",
    ))
    session.add(Risco(
        projeto_id=p1.id, titulo="Volumetria de migração acima do estimado",
        probabilidade=GrauRisco.alto, impacto=GrauRisco.alto,
        resposta="Dress rehearsal extra + janela de contingência no cutover.",
    ))
    session.add(Risco(
        projeto_id=p2.id, titulo="Atraso na liberação dos acessos Fiori",
        probabilidade=GrauRisco.baixo, impacto=GrauRisco.medio,
        resposta="Checklist de acessos no gate do Prepare.", status=StatusRisco.mitigado,
    ))

    session.add(MudancaCR(
        projeto_id=p1.id, titulo="Incluir relatório fiscal customizado (Reforma Tributária)",
        descricao="Cliente solicitou report adicional fora do escopo original.",
        impacto_horas=80, impacto_valor=80 * 180.0, criada_em=hoje - timedelta(days=5),
    ))
    session.add(MudancaCR(
        projeto_id=p1.id, titulo="Ampliar treinamento para 2ª turma",
        impacto_horas=24, impacto_valor=24 * 150.0,
        status=StatusMudanca.aprovada, criada_em=hoje - timedelta(days=15),
        decidida_em=hoje - timedelta(days=9),
    ))

    for c, sk in [
        (ana, "S/4HANA Finance, Fechamento contábil, Fiori"),
        (bruno, "Compras, MRP, Integração Ariba"),
        (carla, "Vendas B2B, Preços, EDI"),
        (diego, "PP/DS, Chão de fábrica"),
        (elisa, "ABAP OO, CDS Views, Fiori Elements"),
        (fabio, "HANA DB, Transporte, Monitoramento"),
    ]:
        c.skills = sk
        session.add(c)

    # ---- cronograma de faturamento do projeto 1 (histórico realista) ----
    session.flush()
    from .routers.faturas import gerar_plano_de_faturas

    faturas_p1 = gerar_plano_de_faturas(session, p1)
    for f in sorted(faturas_p1, key=lambda x: x.competencia):
        if f.competencia < hoje.replace(day=1) - timedelta(days=32):
            # meses antigos: emitidas e recebidas
            f.status = StatusFatura.recebida
            f.numero = f"NF-{f.competencia.strftime('%Y%m')}-001"
            f.data_emissao = f.competencia + timedelta(days=34)
            f.data_vencimento = f.data_emissao + timedelta(days=30)
            f.data_recebimento = f.data_vencimento - timedelta(days=3)
            session.add(f)
        elif f.competencia < hoje.replace(day=1):
            # mês passado: emitida, vencendo (contas a receber)
            f.status = StatusFatura.emitida
            f.numero = f"NF-{f.competencia.strftime('%Y%m')}-001"
            f.data_emissao = hoje - timedelta(days=40)
            f.data_vencimento = hoje - timedelta(days=10)  # vencida → inadimplência
            session.add(f)

    session.commit()


if __name__ == "__main__":
    from .database import criar_tabelas

    criar_tabelas()
    seed_se_vazio()
    print("Seed concluído.")
