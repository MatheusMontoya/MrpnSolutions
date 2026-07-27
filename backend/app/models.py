"""Modelo de dados do RunRate.

Tripé: Projeto <-> Alocação de consultores <-> Receita (hora-homem).
"""
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

# As 6 fases fixas da metodologia SAP Activate, na ordem.
FASES_ACTIVATE = ["Discover", "Prepare", "Explore", "Realize", "Deploy", "Run"]

# Duração default (em semanas) usada para gerar as datas estimadas de cada fase
# ao criar um projeto. As datas são editáveis depois.
DURACAO_DEFAULT_SEMANAS = {
    "Discover": 2,
    "Prepare": 3,
    "Explore": 6,
    "Realize": 10,
    "Deploy": 4,
    "Run": 4,
}

HORAS_SEMANA_PADRAO = 40.0  # jornada de referência para cálculo de utilização
META_MARGEM_PADRAO = 0.45  # meta de margem da consultoria (exibida no dashboard)

# Módulos SAP funcionais/técnicos usados como especialidade do consultor.
MODULOS_SAP = ["FI/CO", "MM", "SD", "PP", "ABAP", "BASIS"]


class StatusProjeto(str, Enum):
    ativo = "ativo"
    pausado = "pausado"
    encerrado = "encerrado"


class StatusFase(str, Enum):
    nao_iniciada = "nao_iniciada"
    em_andamento = "em_andamento"
    concluida = "concluida"


class Senioridade(str, Enum):
    junior = "junior"
    pleno = "pleno"
    senior = "senior"


class StatusAtividade(str, Enum):
    pendente = "pendente"
    em_andamento = "em_andamento"
    concluida = "concluida"


class StatusGate(str, Enum):
    nao_verificado = "nao_verificado"
    verde = "verde"
    amarelo = "amarelo"
    vermelho = "vermelho"


class TipoAusencia(str, Enum):
    ferias = "ferias"
    folga = "folga"
    afastamento = "afastamento"
    treinamento = "treinamento"


class StatusAprovacao(str, Enum):
    pendente = "pendente"
    aprovada = "aprovada"
    recusada = "recusada"


class StatusEnvio(str, Enum):
    enviada = "enviada"
    aprovada = "aprovada"
    reprovada = "reprovada"


class TipoDespesa(str, Enum):
    deslocamento = "deslocamento"
    alimentacao = "alimentacao"
    hospedagem = "hospedagem"
    quilometragem = "quilometragem"
    outros = "outros"


class StatusDespesa(str, Enum):
    pendente = "pendente"
    aprovada = "aprovada"
    recusada = "recusada"
    reembolsada = "reembolsada"


class StatusContrato(str, Enum):
    vigente = "vigente"
    encerrado = "encerrado"
    cancelado = "cancelado"


class GrauRisco(str, Enum):
    baixo = "baixo"
    medio = "medio"
    alto = "alto"


class StatusRisco(str, Enum):
    aberto = "aberto"
    mitigado = "mitigado"
    materializado = "materializado"


class StatusMudanca(str, Enum):
    aberta = "aberta"
    aprovada = "aprovada"
    rejeitada = "rejeitada"


class EstagioProposta(str, Enum):
    qualificacao = "qualificacao"
    proposta = "proposta"
    negociacao = "negociacao"
    aprovada = "aprovada"
    perdida = "perdida"
    convertida = "convertida"  # virou projeto


class StatusFatura(str, Enum):
    prevista = "prevista"
    emitida = "emitida"
    recebida = "recebida"
    cancelada = "cancelada"


class PrioridadePendencia(str, Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"


class StatusPendencia(str, Enum):
    aberta = "aberta"
    em_andamento = "em_andamento"
    resolvida = "resolvida"


class StatusMedicao(str, Enum):
    gerada = "gerada"  # aguardando aceite do cliente
    aceita = "aceita"  # cliente aprovou → fatura emitida vinculada
    contestada = "contestada"  # cliente questionou; pode-se gerar outra


class PerfilUsuario(str, Enum):
    gestor = "gestor"
    consultor = "consultor"


class StatusSprint(str, Enum):
    planejada = "planejada"
    ativa = "ativa"  # no máximo UMA por projeto
    encerrada = "encerrada"


class CategoriaOrcamento(str, Enum):
    horas = "horas"  # custo das horas — realizado vem do motor
    despesas = "despesas"  # reembolsáveis — realizado vem do motor
    terceiros = "terceiros"  # subcontratação — realizado manual
    licencas = "licencas"  # software/licenças — realizado manual
    outros = "outros"  # demais custos — realizado manual


class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    contato: str = ""

    projetos: list["Projeto"] = Relationship(back_populates="cliente")


class Projeto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cliente_id: int = Field(foreign_key="cliente.id")
    data_inicio: date
    status: StatusProjeto = StatusProjeto.ativo
    licoes_aprendidas: str = ""  # preenchidas no encerramento formal
    encerrado_em: Optional[date] = None
    modelo_id: Optional[int] = Field(default=None, foreign_key="modeloprojeto.id")

    cliente: Optional[Cliente] = Relationship(back_populates="projetos")
    fases: list["Fase"] = Relationship(
        back_populates="projeto",
        sa_relationship_kwargs={"order_by": "Fase.ordem", "cascade": "all, delete-orphan"},
    )


class Fase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    nome: str  # uma das FASES_ACTIVATE
    ordem: int  # 0..5, posição na sequência Activate
    data_inicio_prevista: date
    data_fim_prevista: date
    # linha de base: fotografada na criação; a cascata NÃO mexe aqui —
    # o desvio (previsto vs baseline) mede o replanejamento acumulado.
    baseline_inicio: Optional[date] = None
    baseline_fim: Optional[date] = None
    status: StatusFase = StatusFase.nao_iniciada

    projeto: Optional[Projeto] = Relationship(back_populates="fases")
    alocacoes: list["Alocacao"] = Relationship(
        back_populates="fase",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    atividades: list["Atividade"] = Relationship(
        back_populates="fase",
        sa_relationship_kwargs={"order_by": "Atividade.ordem", "cascade": "all, delete-orphan"},
    )
    itens_gate: list["ItemGate"] = Relationship(
        back_populates="fase",
        sa_relationship_kwargs={"order_by": "ItemGate.codigo", "cascade": "all, delete-orphan"},
    )


class Atividade(SQLModel, table=True):
    """Entrega/atividade dentro de uma fase Activate — editável por projeto.

    O progresso da fase passa a considerar atividades concluídas, além das horas.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    fase_id: int = Field(foreign_key="fase.id")
    titulo: str
    ordem: int = 0
    responsavel_id: Optional[int] = Field(default=None, foreign_key="consultor.id")
    data_prevista: Optional[date] = None  # data-alvo da entrega (opcional)
    status: StatusAtividade = StatusAtividade.pendente
    # modo ágil (híbrido): None = backlog; preenchido = puxada para a sprint
    sprint_id: Optional[int] = Field(default=None, foreign_key="sprint.id")

    fase: Optional[Fase] = Relationship(back_populates="atividades")
    responsavel: Optional["Consultor"] = Relationship()


class ItemGate(SQLModel, table=True):
    """Item do Quality Gate da fase (inspirado nos PQGs do SAP Activate).

    Semáforo: não verificado → verde/amarelo/vermelho. A fase só deveria ser
    concluída com o gate verde (ou aceite explícito do gestor).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    fase_id: int = Field(foreign_key="fase.id")
    codigo: str  # ex.: "EXP-01"
    pergunta: str
    risco: str = ""  # descrição do risco/porquê importa
    status: StatusGate = StatusGate.nao_verificado
    plano_acao: str = ""
    responsavel: str = ""

    fase: Optional[Fase] = Relationship(back_populates="itens_gate")


class Consultor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    senioridade: Senioridade
    modulo_sap: str = ""  # especialidade SAP (FI/CO, MM, ABAP, ...)
    skills: str = ""  # competências separadas por vírgula (ex.: "S/4HANA, Fiori, CDS")
    taxa_hora_custo: float  # R$/h de custo interno
    taxa_hora_venda: float  # R$/h default faturado ao cliente

    alocacoes: list["Alocacao"] = Relationship(back_populates="consultor")


class Alocacao(SQLModel, table=True):
    """Consultor alocado numa fase, X horas/semana entre data_inicio e data_fim.

    taxa_hora_venda é congelada na alocação (default = a do consultor) porque
    negociações variam por projeto.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    consultor_id: int = Field(foreign_key="consultor.id")
    fase_id: int = Field(foreign_key="fase.id")
    data_inicio: date
    data_fim: date
    horas_semana: float
    taxa_hora_venda: float

    consultor: Optional[Consultor] = Relationship(back_populates="alocacoes")
    fase: Optional[Fase] = Relationship(back_populates="alocacoes")
    apontamentos: list["Apontamento"] = Relationship(
        back_populates="alocacao",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Configuracao(SQLModel, table=True):
    """Parâmetros da consultoria (linha única). Editável na tela Configurações."""

    id: Optional[int] = Field(default=None, primary_key=True)
    nome_consultoria: str = "MRPN Solutions"
    cnpj: str = "00.000.000/0001-00"
    jornada_semanal: float = HORAS_SEMANA_PADRAO
    limiar_super: float = 1.0
    limiar_ocioso: float = 0.6
    meta_margem: float = META_MARGEM_PADRAO
    taxa_junior: float = 150.0
    taxa_pleno: float = 220.0
    taxa_senior: float = 350.0
    formato_data: str = "DD/MM/AAAA"
    moeda: str = "BRL"
    fuso: str = "(GMT-03:00) Brasília"
    taxa_km: float = 1.20  # R$/km para despesas de quilometragem
    # Copiloto IA (plugável): com a chave preenchida, o copiloto usa a API da
    # Anthropic; sem ela, opera com os insights determinísticos do motor.
    anthropic_api_key: str = ""
    modelo_ia: str = "claude-sonnet-5"


class Apontamento(SQLModel, table=True):
    """Lançamento manual de horas realizadas num dia, contra uma alocação.

    `descricao` registra o que foi feito nessas horas — preenchida pelo
    consultor no apontamento e exibida ao gestor no feed de atividades.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    alocacao_id: int = Field(foreign_key="alocacao.id")
    data: date
    horas: float
    descricao: str = ""

    alocacao: Optional[Alocacao] = Relationship(back_populates="apontamentos")


class Ausencia(SQLModel, table=True):
    """Férias/folga/afastamento do consultor. Quando APROVADA, reduz a
    capacidade da semana no motor de utilização (capacidade real)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    consultor_id: int = Field(foreign_key="consultor.id")
    tipo: TipoAusencia
    data_inicio: date
    data_fim: date
    motivo: str = ""
    status: StatusAprovacao = StatusAprovacao.pendente
    comentario_gestor: str = ""

    consultor: Optional[Consultor] = Relationship()


class EnvioSemana(SQLModel, table=True):
    """Envio da semana de apontamentos para aprovação do gestor.

    Sem registro = rascunho (editável). enviada → bloqueia edição;
    aprovada → definitivo; reprovada → volta a ser editável (com comentário).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    consultor_id: int = Field(foreign_key="consultor.id")
    semana: date  # segunda-feira da semana
    status: StatusEnvio = StatusEnvio.enviada
    total_horas: float = 0.0  # snapshot no momento do envio
    comentario_gestor: str = ""
    enviado_em: Optional[date] = None
    decidido_em: Optional[date] = None

    consultor: Optional[Consultor] = Relationship()


class Despesa(SQLModel, table=True):
    """Despesa de projeto lançada pelo consultor (reembolsável).

    Para tipo quilometragem, `km` é informado e o valor = km × taxa_km
    (da Configuração) no momento do lançamento.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    consultor_id: int = Field(foreign_key="consultor.id")
    projeto_id: int = Field(foreign_key="projeto.id")
    data: date
    tipo: TipoDespesa
    descricao: str = ""
    valor: float
    km: Optional[float] = None
    status: StatusDespesa = StatusDespesa.pendente
    comentario_gestor: str = ""

    consultor: Optional[Consultor] = Relationship()
    projeto: Optional[Projeto] = Relationship()


class Proposta(SQLModel, table=True):
    """Oportunidade comercial no pipeline. Precificação por mix de senioridade
    (horas × taxa padrão da Configuração) com margem estimada pelo custo médio
    real dos consultores. Aprovada → convertida em projeto."""

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    nome: str
    descricao: str = ""
    escopo: str = ""
    premissas: str = ""
    # mix de senioridade (precificação): valor = Σ horas × taxa da Configuração
    horas_junior: float = 0.0
    horas_pleno: float = 0.0
    horas_senior: float = 0.0
    valor_estimado: float = 0.0
    margem_estimada: float = 0.0  # 0..1, calculada na precificação
    horas_estimadas: float = 0.0  # total (soma do mix, ou manual)
    probabilidade: float = 0.5  # 0..1 (pondera o funil)
    validade: Optional[date] = None
    estagio: EstagioProposta = EstagioProposta.qualificacao
    criada_em: date
    decidida_em: Optional[date] = None
    projeto_id: Optional[int] = Field(default=None, foreign_key="projeto.id")

    cliente: Optional[Cliente] = Relationship()
    projeto: Optional[Projeto] = Relationship()


class Contrato(SQLModel, table=True):
    """Contrato firmado com o cliente: vigência e situação. 'A renovar' =
    vigente com fim nos próximos 60 dias."""

    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    nome: str
    data_inicio: date
    data_fim: date
    valor: float = 0.0
    status: StatusContrato = StatusContrato.vigente
    observacoes: str = ""

    cliente: Optional[Cliente] = Relationship()


class Feriado(SQLModel, table=True):
    """Feriado do calendário corporativo — dia NÃO útil para o motor
    (receita, capacidade, faturas, cascata)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    data: date
    nome: str


class Risco(SQLModel, table=True):
    """Risco do projeto: matriz probabilidade × impacto + plano de resposta."""

    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    titulo: str
    probabilidade: GrauRisco = GrauRisco.medio
    impacto: GrauRisco = GrauRisco.medio
    resposta: str = ""  # plano de mitigação/contingência
    status: StatusRisco = StatusRisco.aberto

    projeto: Optional[Projeto] = Relationship()


class MudancaCR(SQLModel, table=True):
    """Solicitação de mudança (change request) do projeto, com impacto
    estimado em horas e valor."""

    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    titulo: str
    descricao: str = ""
    impacto_horas: float = 0.0
    impacto_valor: float = 0.0
    status: StatusMudanca = StatusMudanca.aberta
    criada_em: date
    decidida_em: Optional[date] = None

    projeto: Optional[Projeto] = Relationship()


class Fatura(SQLModel, table=True):
    """Fatura do cronograma de faturamento do projeto.

    prevista (plano gerado da receita mensal) → emitida (vencimento = +30d)
    → recebida. Emitidas em aberto compõem o contas a receber.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    competencia: date  # primeiro dia do mês de referência
    valor: float
    status: StatusFatura = StatusFatura.prevista
    numero: str = ""
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    data_recebimento: Optional[date] = None

    projeto: Optional[Projeto] = Relationship()


class Sprint(SQLModel, table=True):
    """Sprint do modo ágil/híbrido: janela curta de execução DENTRO do
    cronograma Activate. O waterfall (fases/gates) segue mandando no prazo e
    na receita; a sprint organiza o dia a dia das entregas (atividades).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    numero: int  # sequencial por projeto (Sprint 1, 2, ...)
    nome: str = ""
    meta: str = ""  # objetivo da sprint (sprint goal)
    data_inicio: date
    data_fim: date
    status: StatusSprint = StatusSprint.planejada
    encerrada_em: Optional[date] = None
    carry_over: int = 0  # atividades devolvidas ao backlog no encerramento

    projeto: Optional[Projeto] = Relationship()
    atividades: list["Atividade"] = Relationship()


class Usuario(SQLModel, table=True):
    """Usuário do sistema com senha real (pbkdf2, stdlib — sem dependências).

    Perfil consultor é vinculado a um Consultor (lança as próprias horas);
    gestor vê tudo. RBAC é aplicado por middleware + guardas nos routers.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    nome: str
    senha_hash: str  # formato "salt$hash" (pbkdf2-sha256)
    perfil: PerfilUsuario
    consultor_id: Optional[int] = Field(default=None, foreign_key="consultor.id")
    ativo: bool = True

    consultor: Optional[Consultor] = Relationship()


class SessaoAcesso(SQLModel, table=True):
    """Sessão autenticada: token opaco (secrets) com expiração deslizante."""

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    usuario_id: int = Field(foreign_key="usuario.id")
    criada_em: datetime
    expira_em: datetime

    usuario: Optional[Usuario] = Relationship()


class EventoAuditoria(SQLModel, table=True):
    """Trilha de auditoria: toda mutação da API (POST/PATCH/DELETE) registra
    quem, quando, o quê e o resultado — gravada por middleware."""

    id: Optional[int] = Field(default=None, primary_key=True)
    quando: datetime
    usuario: str = ""  # nome no momento (sobrevive à remoção do usuário)
    perfil: str = ""
    metodo: str
    caminho: str
    status: int
    detalhe: str = ""  # resumo do corpo (sem senhas)


class ItemOrcamento(SQLModel, table=True):
    """Rubrica do orçamento do projeto (orçado × realizado).

    Para 'horas' e 'despesas' o REALIZADO vem do motor (custo das horas
    apontadas / despesas aprovadas) — valor_realizado fica ignorado; nas
    demais categorias o realizado é lançado manualmente.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    categoria: CategoriaOrcamento
    descricao: str = ""
    valor_orcado: float = 0.0
    valor_realizado: float = 0.0  # só usado nas categorias manuais

    projeto: Optional[Projeto] = Relationship()


class ModeloProjeto(SQLModel, table=True):
    """Modelo de projeto: as 6 fases Activate são fixas (nosso diferencial),
    mas as ENTREGAS e o QUALITY GATE de cada fase variam por tipo de trabalho
    (implantação completa, rollout, AMS...). O modelo alimenta a criação."""

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    descricao: str = ""
    padrao: bool = False  # o modelo default (templates do SAP Activate)

    atividades: list["ModeloAtividade"] = Relationship(
        back_populates="modelo",
        sa_relationship_kwargs={"order_by": "ModeloAtividade.ordem", "cascade": "all, delete-orphan"},
    )
    itens_gate: list["ModeloItemGate"] = Relationship(
        back_populates="modelo",
        sa_relationship_kwargs={"order_by": "ModeloItemGate.codigo", "cascade": "all, delete-orphan"},
    )


class ModeloAtividade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    modelo_id: int = Field(foreign_key="modeloprojeto.id")
    fase: str  # uma das FASES_ACTIVATE
    titulo: str
    ordem: int = 0

    modelo: Optional[ModeloProjeto] = Relationship(back_populates="atividades")


class ModeloItemGate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    modelo_id: int = Field(foreign_key="modeloprojeto.id")
    fase: str  # uma das FASES_ACTIVATE
    codigo: str
    pergunta: str
    risco: str = ""

    modelo: Optional[ModeloProjeto] = Relationship(back_populates="itens_gate")


class SolicitacaoAlocacao(SQLModel, table=True):
    """Pedido de alocação de consultor numa fase — aprovado, vira Alocacao.

    Governança de alocação (estilo PSOffice): em vez de alocar direto, o
    gerente solicita e a decisão passa pela fila de aprovações, onde os
    CONFLITOS (soma acima da jornada na semana, alocação durante ausência)
    são calculados pelo motor e exibidos antes do aceite.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    consultor_id: int = Field(foreign_key="consultor.id")
    fase_id: int = Field(foreign_key="fase.id")
    data_inicio: date
    data_fim: date
    horas_semana: float
    taxa_hora_venda: Optional[float] = None  # None = taxa padrão do consultor
    justificativa: str = ""
    solicitante: str = ""  # nome de quem pediu (sessão client-side; auth real é épico futuro)
    status: StatusAprovacao = StatusAprovacao.pendente
    comentario_gestor: str = ""
    criada_em: date
    decidida_em: Optional[date] = None
    alocacao_id: Optional[int] = Field(default=None, foreign_key="alocacao.id")

    consultor: Optional[Consultor] = Relationship()
    fase: Optional[Fase] = Relationship()


class Medicao(SQLModel, table=True):
    """Medição mensal do projeto: relatório de horas realizadas × taxa que o
    cliente aceita ANTES do faturamento. O aceite emite a fatura vinculada;
    contestada, permite corrigir apontamentos e gerar outra.

    total_horas/total_valor são snapshot da geração; o detalhamento por
    consultor é recalculado ao vivo dos apontamentos.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    competencia: date  # primeiro dia do mês medido
    total_horas: float = 0.0
    total_valor: float = 0.0
    status: StatusMedicao = StatusMedicao.gerada
    observacoes: str = ""
    criada_em: date
    decidida_em: Optional[date] = None
    fatura_id: Optional[int] = Field(default=None, foreign_key="fatura.id")

    projeto: Optional[Projeto] = Relationship()


class Pendencia(SQLModel, table=True):
    """Pendência/ocorrência de projeto: registro, responsável e acompanhamento."""

    id: Optional[int] = Field(default=None, primary_key=True)
    projeto_id: int = Field(foreign_key="projeto.id")
    fase_id: Optional[int] = Field(default=None, foreign_key="fase.id")
    titulo: str
    descricao: str = ""
    responsavel_id: Optional[int] = Field(default=None, foreign_key="consultor.id")
    prioridade: PrioridadePendencia = PrioridadePendencia.media
    status: StatusPendencia = StatusPendencia.aberta
    criada_em: date
    resolvida_em: Optional[date] = None

    projeto: Optional[Projeto] = Relationship()
    fase: Optional[Fase] = Relationship()
    responsavel: Optional[Consultor] = Relationship()
