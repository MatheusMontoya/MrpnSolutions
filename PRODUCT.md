# Product

<!-- impeccable:product-schema 1 -->

> Registro escrito a partir das evidências do repositório e do histórico de
> decisões do projeto (não de entrevista — o dono pediu execução autônoma).
> Os pontos realmente indefinidos estão marcados como **em aberto**.

## Platform

web

## Users

**Gestor da consultoria (perfil `gestor`)** — sócio/diretor de uma consultoria SAP
que fatura por hora-homem. Trabalha no desktop, ao longo do dia, alternando entre
vender (propostas), planejar (alocação), cobrar (faturamento) e apagar incêndio
(aprovações, pendências, riscos). Precisa saber, a qualquer momento, se cada
projeto está dando lucro e se a equipe está sobre ou subalocada.

**Consultor (perfil `consultor`)** — quem executa nos projetos SAP. Entra no
sistema para lançar as próprias horas (com descrição do que foi feito), pedir
ausências, lançar despesas e ver a própria agenda. Não vê nada gerencial: o
RBAC bloqueia no servidor (403), não só na tela.

## Product Purpose

Rodar a operação inteira de uma consultoria SAP a partir de um **motor de cálculo
determinístico**: projeto ↔ alocação de consultores ↔ receita hora-homem. O
sistema responde "quanto isso vai faturar, quanto custou, quem está livre e o que
acontece se atrasar" sem depender de planilha paralela.

Sucesso = o gestor confia no número que a tela mostra e para de manter controles
em Excel.

## Positioning

Três coisas que um concorrente não copiaria sem refazer o núcleo:

1. **Cascata determinística por fase SAP Activate** — mover a data-fim de uma fase
   desloca as seguintes, estende as alocações e recomputa a receita mensal, sempre
   com **diff "antes → depois" simulado antes de aplicar** (`services/reagendamento.py`).
   O PSOffice, referência funcional do projeto, não tem isso.
2. **Motor puro e auditável** — todo cálculo vive em funções sem I/O
   (`services/receita.py`), com feriados, ausências e capacidade real embutidos.
   A camada de IA lê o motor; nunca calcula.
3. **Híbrido honesto** — o cronograma Activate manda em prazo e receita; a sprint
   só organiza a execução, com carry-over medido no encerramento.

## Operating Context

- **Metodologia SAP Activate** com 6 fases fixas (Discover → Prepare → Explore →
  Realize → Deploy → Run). Entregas e Quality Gates por fase vieram dos
  aceleradores oficiais (PQGs) e são editáveis por **modelo de projeto**.
- **Ciclo comercial → entrega → caixa**: proposta (mix de senioridade) → contrato →
  projeto com 6 fases → alocação → apontamento semanal → aprovação do gestor →
  medição aceita pelo cliente → fatura → recebimento.
- **Ritmos**: semana é a unidade de apontamento e de capacidade; mês é a unidade de
  receita, medição e faturamento.
- **Ambiente corporativo com bloqueio de CDN** — tudo (fontes, ícones, assets) é
  servido pelo próprio bundle.
- Referências funcionais estudadas: documentação do **PSOffice** e aceleradores do
  **SAP Activate** (extratos em `docs/referencias/`, análise em
  `docs/analise-psoffice-activate.md`).

## Capabilities and Constraints

**Entregue e funcionando** (105 testes automatizados no backend):
projetos com 6 fases + cascata com diff · alocação com taxa negociada ·
apontamento semanal com descrição por dia · envio/aprovação de semanas ·
ausências e feriados no motor de capacidade · despesas (inclusive km) ·
pendências · propostas com precificação por mix de senioridade · contratos ·
faturamento, medição com aceite do cliente, contas a receber/pagar, fluxo de
caixa, rentabilidade · orçado × realizado por rubrica · EVM (SPI/CPI/EAC) ·
linha de base e desvio · riscos (matriz P×I), CRs, Status Report e TAP
imprimíveis · encerramento com lições · modelos de projeto · agenda mensal ·
quadro ágil (sprints, backlog, kanban, carry-over) · copiloto de IA plugável ·
exportação CSV (Excel pt-BR) · autenticação real com senha, RBAC e trilha de
auditoria.

**Restrições técnicas confirmadas:**
- Backend Python/FastAPI + SQLModel sobre SQLite (trocável para Postgres via
  `DATABASE_URL`); frontend React + Vite com **CSS próprio, sem Tailwind**.
- **Proibido CDN em runtime.** Fonte self-hosted, família única (Figtree).
- Todo cálculo novo entra em `services/` como função pura e ganha teste; a IA
  consome o motor e não replica regra em prompt.
- A chave da API Anthropic é opcional: sem ela o copiloto opera com insights
  determinísticos.

**Fora de escopo por decisão:** CRM de contatos, GMUD, integração com o SAP,
SSO corporativo e emissão fiscal real (NF-e — o sistema controla o ciclo de
faturamento, não emite nota).

**Em aberto (não inventar):**
- Modelo comercial: uso interno da consultoria vs. produto vendido a terceiros.
  Isso decide se haverá multiempresa/multi-tenant, planos e cobrança. Nada no
  código pressupõe multi-tenant hoje.
- Volume real esperado (nº de consultores/projetos) — o seed é demonstração.
- Idiomas: hoje só pt-BR, sem infraestrutura de i18n.

## Brand Commitments

- Nome do produto: **RunRate**, endossado por **MRPN Solutions** (nomes anteriores
  "PSA SAP" e "MRPN Smart" estão aposentados; a pasta do repositório ainda se chama
  `psa-sap`). Site: runrate.com.br.
- Identidade visual: **azul elétrico** é obrigatório (decisão explícita do dono),
  com chrome **azul escuro**. Referências de acabamento declaradas: **Productive,
  ClickUp, Stripe, Slack, Jira**.
- Interface inteiramente em **português do Brasil**, incluindo os nomes de
  variáveis, classes CSS e comentários do código.
- Sensibilidade declarada a poluição visual: sem MAIÚSCULAS decorativas, sem
  densidade excessiva, sem cor saturada fora do acento.

## Evidence on Hand

- **Seed de demonstração determinístico** (`backend/app/seed.py`): 2 clientes,
  3 projetos em fases distintas, 6 consultores, ~8 semanas de apontamentos,
  propostas, contratos, faturas, riscos, CRs, sprints e usuários demo
  (`gestor@psa.com` e um por consultor, senha `psa123`). Nomes e números são
  fictícios e devem continuar assim.
- **105 testes** em `backend/tests/` cobrindo motor, cascata, ondas funcionais,
  autenticação/RBAC/auditoria e ágil.
- **Capturas reais das telas** em `docs/capturas/` (histórico do redesenho).
- **Análise funcional** PSOffice × SAP Activate em `docs/analise-psoffice-activate.md`,
  com matriz de cobertura por onda.
- Não existem: clientes reais, depoimentos, benchmarks, preço ou contrato de
  licenciamento. Nada disso deve ser fabricado em nenhuma superfície.

## Product Principles

1. **O motor é a fonte da verdade.** Toda tela mostra um número que veio de função
   pura e testada; nenhuma regra de cálculo nasce na UI ou dentro de um prompt.
2. **Mostrar o impacto antes de aplicar.** Mudanças que mexem em prazo ou dinheiro
   (cascata, medição, encerramento) apresentam o diff/consequência primeiro.
3. **Cada papel vê só o seu mundo** — e o bloqueio é no servidor, não na tela.
4. **Rastreabilidade por padrão**: quem fez, quando, o quê (auditoria automática),
   e linha de base preservada para medir o replanejamento.
5. **A ferramenta some na tarefa.** Densidade a serviço do dado, familiaridade
   acima de invenção: o gestor deve reconhecer os padrões dos SaaS que ele já usa.

## Accessibility & Inclusion

Sem requisito normativo declarado pelo dono. Padrão adotado pelo projeto:
contraste AA para texto, foco visível em todo elemento interativo, navegação por
teclado nos controles próprios (menus, busca, kanban) e `prefers-reduced-motion`
respeitado em todas as animações.
