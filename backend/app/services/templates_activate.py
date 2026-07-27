"""Templates SAP Activate por fase: atividades/entregáveis padrão e itens de
Quality Gate (adaptados dos aceleradores oficiais — PQG, cutover, RACI).

Aplicados na criação do projeto; tudo editável por projeto depois.
"""

# Entregas/atividades default por fase (a spec original do embrião previa
# atividades editáveis dentro de cada fase).
ATIVIDADES_PADRAO: dict[str, list[str]] = {
    "Discover": [
        "Análise de viabilidade e escopo inicial",
        "Business case e objetivos de negócio",
        "Roadmap inicial da implementação",
    ],
    "Prepare": [
        "Plano de projeto e cronograma detalhado",
        "Reunião de kickoff com stakeholders",
        "Setup dos ambientes do projeto",
        "RACI dos workshops fit-to-standard",
    ],
    "Explore": [
        "Workshops fit-to-standard por processo",
        "Backlog de adoção atualizado",
        "Log de gaps e change requests",
        "Blueprint/desenho da solução validado",
    ],
    "Realize": [
        "Configuração (customizing) no ambiente DEV",
        "Desenvolvimentos (RICEFW) priorizados",
        "Testes unitários por módulo",
        "Ciclos de teste integrado",
        "Carga de dados de teste (mock)",
    ],
    "Deploy": [
        "Plano de cutover aprovado",
        "Treinamento dos usuários finais",
        "Execução do cutover / go-live",
        "Verificação pós-go-live",
    ],
    "Run": [
        "Hypercare (suporte assistido)",
        "Transição para o suporte contínuo",
        "Lições aprendidas e encerramento",
    ],
}

# Itens de Quality Gate por fase: (código, pergunta, risco/por que importa).
# Adaptação genérica dos PQGs (Project Quality Gates) do pacote SAP Activate.
GATES_PADRAO: dict[str, list[tuple[str, str, str]]] = {
    "Discover": [
        ("DIS-01", "O escopo e os objetivos de negócio estão documentados e aprovados pelo sponsor?",
         "Sem escopo aprovado, as fases seguintes herdam ambiguidade e retrabalho."),
        ("DIS-02", "O business case justifica o investimento (custo × benefício)?",
         "Projetos sem business case claro perdem patrocínio no meio do caminho."),
        ("DIS-03", "Os principais riscos e restrições foram identificados?",
         "Riscos não mapeados no Discover viram surpresas caras no Realize."),
    ],
    "Prepare": [
        ("PRE-01", "O plano de projeto (cronograma, marcos, papéis) está aprovado?",
         "A ausência de linha de base impede medir atraso e desvio."),
        ("PRE-02", "A equipe do projeto e o RACI dos workshops estão definidos?",
         "Workshops sem papéis claros geram decisões sem dono."),
        ("PRE-03", "Ambientes e acessos necessários estão disponíveis?",
         "Atraso de acesso/ambiente é a causa nº 1 de derrapagem no Explore."),
        ("PRE-04", "O plano de gestão de mudança organizacional (OCM) foi iniciado?",
         "Sem OCM, a adoção pelos usuários finais fica comprometida no go-live."),
    ],
    "Explore": [
        ("EXP-01", "Os workshops fit-to-standard cobriram todos os processos do escopo?",
         "Processo não coberto em workshop reaparece como gap tardio."),
        ("EXP-02", "O backlog de adoção está atualizado e priorizado?",
         "Backlog desatualizado esconde esforço real do Realize."),
        ("EXP-03", "Existe log de change requests com impacto em custo/prazo?",
         "CRs sem log corroem a margem silenciosamente."),
        ("EXP-04", "O escopo foi congelado para a fase Realize?",
         "Escopo aberto durante o Realize dilui o time e atrasa entregas."),
        ("EXP-05", "Cenários de integração foram identificados e dimensionados?",
         "Integrações subestimadas explodem no teste integrado."),
    ],
    "Realize": [
        ("REA-01", "As configurações estão documentadas no tracker de configuração?",
         "Config sem rastro dificulta suporte e auditoria pós-go-live."),
        ("REA-02", "Os ciclos de teste integrado foram concluídos com defeitos críticos zerados?",
         "Go-live com defeito crítico aberto transfere o risco para produção."),
        ("REA-03", "A migração de dados foi ensaiada com dados reais (mock/dress rehearsal)?",
         "Primeira carga real no cutover é receita para rollback."),
        ("REA-04", "Os key users foram treinados para o teste de aceitação?",
         "UAT sem key user preparado não valida nada."),
    ],
    "Deploy": [
        ("DEP-01", "O plano de cutover (atividades, janela, rollback) está aprovado?",
         "Cutover sem plano/rollback põe a operação do cliente em risco."),
        ("DEP-02", "Os usuários finais foram treinados e comunicados?",
         "Usuário despreparado gera enxurrada de chamados no hypercare."),
        ("DEP-03", "Critérios de go/no-go definidos e aceitos pelo cliente?",
         "Sem critério objetivo, a decisão de go-live vira queda de braço."),
    ],
    "Run": [
        ("RUN-01", "O plano de hypercare (equipe, SLA, horário) está ativo?",
         "Hypercare sem SLA definido frustra o cliente na fase mais sensível."),
        ("RUN-02", "A transição para o suporte contínuo foi formalizada?",
         "Sem transição formal, o time do projeto vira suporte eterno."),
        ("RUN-03", "Lições aprendidas registradas e projeto encerrado formalmente?",
         "Sem encerramento formal, horas continuam sendo lançadas no projeto."),
    ],
}
