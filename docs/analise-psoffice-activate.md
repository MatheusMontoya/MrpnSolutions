# Análise de base: PSOffice × SAP Activate × PSA SAP

> Fontes: `Apostila_Help_PSOffice.docx` (mapa funcional oficial), `PSOffice_Apresentacao_Mockups.pptx`
> (174 telas), `SAP Activate SAP IBP.zip` (aceleradores reais: PQG Quality Gates por fase, cutover,
> RACI fit-to-standard, config tracker). Extratos em `docs/referencias/`.

## 1. O que os documentos trazem

### SAP Activate (pacote de aceleradores IBP)
- **PQG — Project Quality Gate por fase** (`IBP_PQG_DISCOVER/PREPARE/EXPLORE/REALIZE/RUN.xlsx`):
  checklist de qualidade com `Check ID`, pergunta/tópico, descrição do risco, **status semáforo**
  (0 Não verificado · 1 Verde · amarelo · vermelho), plano de ação e responsável. É o "portão"
  que a fase precisa passar antes de avançar.
- Templates de **cutover** (estratégia + planilha), **RACI de workshops fit-to-standard**,
  **tracker de configuração**, **tracker de perguntas & respostas**, planejamento de workshops.

### PSOffice (apostila + 174 mockups)
Contextos: **Home** (horas, despesas, ausências, demandas, agenda, aprovações), **Propostas**
(pipeline/funil, clientes, contratos, precificação e margem), **Projetos** (TAP, EAP/WBS, Gantt,
linha de base, dependências, riscos, EVM/CPI/SPI, encerramento), **Alocações** (mapa, demanda ×
capacidade, fluxo de solicitação/aprovação de alocação, conflitos), **Apontamento** (timesheet,
aprovação de horas, despesas/reembolso/km), **Pendências** (central + workflow de aprovações),
**Financeiro** (cronograma de faturamento, medição, NF, contas a pagar/receber, rentabilidade,
orçado × realizado), **Relatórios**, **Administração** (perfis, permissões, campos customizados,
modelos de projeto, auditoria), **J.Agile** (híbrido waterfall+sprints), **IA copiloto**, **Mobile**.

## 2. Onde o PSA SAP já está coberto

Projetos com 6 fases Activate + Gantt + recálculo em cascata (nosso diferencial — o PSOffice não
tem cascata determinística por fase), alocação por hora com taxa negociada, timesheet com
descrição de atividade (balão) e feed do gestor, heatmap de utilização, clientes, margem vs meta,
login por perfil, configurações. ~15% do escopo PSOffice, porém com o motor de receita que é o
nosso núcleo.

## 3. Gaps priorizados (proposta em ondas)

### Onda 1 — Core Activate + capacidade (mais aderente ao embrião)
1. **Atividades/entregáveis por fase** — a spec original já previa ("entregas dentro de cada fase
   são editáveis"); nunca implementado. Lista de atividades por fase com responsável, previsto/
   realizado e % de progresso (alimenta o progresso da fase que hoje é só horas).
2. **Quality Gate por fase (PQG)** — checklist semáforo por fase, com seed real adaptado dos
   PQGs do pacote Activate; alerta na fase quando o gate não está verde; visão de gates no
   detalhe do projeto.
3. **Ausências** (férias/folgas/afastamentos) — reduzem a **capacidade** da semana; o motor de
   utilização passa a usar capacidade real (40h − ausências) em vez de 40h fixas.
4. **Demanda × Capacidade** (agregado da empresa) — gráfico semanas × (demanda alocada vs
   capacidade da equipe), antecipando gargalos. Derivável do que já temos.

### Onda 2 — Operação
5. **Aprovação de horas** — fila do gestor (semana enviada → aprovar/reprovar), estados no
   timesheet. (Hoje ficou de fora por decisão; os docs reforçam que é fluxo central de PSA.)
6. **Despesas** — lançamento por projeto (com km), conta do profissional, reembolso.
7. **Pendências/ocorrências de projeto** — registro, responsável, status, ligação à fase.

### Onda 3 — Comercial & Financeiro
8. **Propostas/Pipeline** — funil (negociação→aprovada→execução), precificação por mix de
   senioridade (usa nossas taxas), conversão proposta→projeto (gera as 6 fases).
9. **Cronograma de faturamento** — plano de faturas por fase/medição a partir da receita
   prevista; status emitida/recebida (sem NF-e — integração fiscal fica fora).
10. **Contas a receber básico** + inadimplência simples.

### Onda 4 — Além do embrião
Híbrido/ágil (Kanban sincronizado ao cronograma), construtor de relatórios, **copiloto IA**
(já planejado por cima de `services/`), mobile, auditoria/permissões finas, integrações.

## 4. Regras do Activate a absorver no motor
- Fase só "concluída" quando o **quality gate** estiver verde (ou com aceite explícito do gestor).
- Fit-to-standard (Explore) gera **backlog de adoção** → nossas atividades da fase Realize.
- Cutover (Deploy) tem checklist próprio — candidato a template de atividades da fase Deploy.
- RACI por workshop → campo "responsável" nas atividades.

## 4b. Cobertura após as Ondas 1-3.5 (2026-07-20)

**Entregue:** tripé PSA completo · atividades/entregas por fase + Quality Gates (PQG) ·
ausências/capacidade real + **feriados no motor** · Demanda×Capacidade · envio/aprovação
de semanas · despesas (km) + contas a pagar · pendências · pipeline com **precificação
por mix de senioridade e margem estimada** · contratos (renovação) · faturamento/contas a
receber (aging) · **fluxo de caixa** · **rentabilidade por projeto** · **linha de base +
desvio vs cascata** · riscos (matriz P×I) · mudanças/CR · **status report em 1 clique** ·
encerramento com lições · skills dos consultores · navegação topbar 2 níveis.

**Fica para a Onda 4:** autenticação real (senhas/SSO/RBAC), portfólio executivo
(programas/ROI/cenários), ágil/híbrido (backlog/sprints/kanban sincronizado), EAP
hierárquica com dependências/EVM formal (CPI/SPI), construtor de relatórios/exportações,
copiloto IA (planejado sobre services/), mobile, auditoria fina, integrações externas.

## 4c. Onda 4.1 entregue (2026-07-22)

**Copiloto IA plugável** (`services/copiloto.py` + página Copiloto no contexto
Dashboard): 8 famílias de insights determinísticos sobre o motor (cobrança vencida,
desvio de baseline, gargalo demanda×capacidade 6 semanas, superalocação, riscos
críticos, CRs abertas, propostas vencendo/paradas, pendências altas) + chat; com a
chave da API Anthropic em Configurações → Copiloto IA, as respostas passam a ser
generativas (modelo configurável), com degradação limpa para o determinístico.
**EVM** (`services/evm.py` + card no detalhe do projeto): PV/EV/AC a custo por fase,
SPI/CPI/SV/CV/BAC/EAC; progresso físico = atividades concluídas (fallback horas/status).
**Exportação CSV** (`routers/exportacao.py` + botões nas telas): apontamentos, faturas,
despesas, propostas, pendências e rentabilidade — `;`, BOM, decimal vírgula (Excel pt-BR).
62 testes. Restante da Onda 4: auth real, ágil/híbrido, portfólio, relatórios, mobile,
auditoria.

## 4d. Onda 4.2 entregue (2026-07-22)

Os três itens do PSOffice priorizados fora do plano original:
**Fluxo de solicitação/aprovação de alocação** (`services/alocacoes.py` +
`routers/solicitacoes.py`): pedido com justificativa → fila unificada de aprovações →
aprovado vira Alocacao; **conflitos calculados pelo motor** semana a semana (já alocado
× pedido × capacidade real com ausências) e prévia de conflito no formulário antes de
submeter. **Medição/aceite do cliente** (`routers/medicoes.py` + aba Medições):
relatório de horas do mês (por consultor/fase/taxa, imprimível) → aceite emite a fatura
vinculada substituindo a prevista do mês → contestação devolve para correção.
**TAP** (GET /projetos/{id}/tap + modal imprimível): termo de abertura com escopo/
premissas da proposta convertida, cronograma da LINHA DE BASE, equipe e riscos.
75 testes. Onda 4.3 candidata: orçado×realizado com rubricas, modelos de entregas/gates
por tipo de projeto, agenda do consultor.

## 4e. Onda 4.3 entregue (2026-07-22)

**Orçado × realizado por rubrica** (`routers/orcamento.py` + card no projeto): rubricas
'horas' e 'despesas' automáticas (realizado do motor; orçado nasce da sugestão do motor
= custo previsto) + terceiros/licenças/outros manuais; barras de consumo com farol,
edição inline, totais e saldo. **Modelos de projeto** (`routers/modelos.py` + seção nas
Configurações + select na criação): fases Activate fixas, entregas e gates por fase
editáveis por tipo (padrão materializado dos templates; novos nascem como cópia);
projeto guarda o modelo de origem. **Agenda mensal** (`GET /consultores/{id}/agenda` +
página Agenda em Equipe e Meu espaço): calendário com alocações h/dia, ausências
aprovadas (zeram o dia), feriados e horas apontadas. 84 testes.
**Restante da Onda 4:** auth real (senhas/RBAC), ágil/híbrido, portfólio executivo,
construtor de relatórios, mobile, auditoria fina.

## 4f. Onda 4.4 entregue (2026-07-22)

**Autenticação real**: Usuario (pbkdf2-sha256 da stdlib) + SessaoAcesso (token opaco,
expiração deslizante de 12h, logout revoga); login por e-mail/senha; middleware exige
Bearer em todo /api/* (exceto login). **RBAC no servidor**: routers gerenciais
(comercial, financeiro, governança, copiloto, aprovações etc.) exigem gestor (403);
consultor acessa o próprio espaço; writes de routers mistos (projetos, consultores,
decisões, configurações) têm guarda por rota. Gestão de usuários nas Configurações
(criar/vincular consultor/redefinir senha/desativar — desativar mata a sessão viva).
**Auditoria**: middleware grava toda mutação (quem, quando, método, caminho, status)
em EventoAuditoria; trilha visível nas Configurações. Export CSV passou a baixar via
fetch autenticado. 97 testes (13 de API via TestClient). Seed: gestor@psa.com +
1 usuário por consultor, senha psa123.
**Restam da Onda 4:** ágil/híbrido (J.Agile), portfólio executivo, construtor de
relatórios, mobile.

## 4g. Onda 4.5 entregue (2026-07-22)

**Modo ágil/híbrido (J.Agile)**: Sprint por projeto (numeração automática, meta,
período; no máximo UMA ativa) + Atividade.sprint_id (None = backlog). Página Quadro
Ágil (/projetos/{id}/agil, botão no detalhe): kanban A fazer/Em andamento/Concluída da
sprint em foco, backlog com as entregas abertas das 6 fases (badge da fase em cada
cartão — o vínculo com o waterfall fica visível), puxar/devolver, iniciar/encerrar
(pendentes voltam ao backlog com carry-over medido), horas apontadas no período da
sprint vindas do motor. O cronograma Activate continua dono de prazo/receita — a
sprint só organiza a execução. 105 testes.
**Restam da Onda 4:** portfólio executivo, construtor de relatórios, mobile.

## 5. Decisões em aberto
- Quais ondas entram agora (ver conversa de priorização).
- Aprovação de horas: reverte a decisão anterior de deixar fora?
- Pipeline: o corte original dizia "não fazer CRM" — pipeline de propostas é meio-CRM;
  se entrar, entra focado em proposta de projeto (sem gestão de contatos/atividades comerciais).

## 6. Backlog priorizado (2026-08-25)

### Lição 1 — segurança de acesso (ENTREGUE)
22 vazamentos horizontais entre consultores + excesso de acesso do RH ao
financeiro + travessia de caminho no servidor do SPA. Fechados, com 19 testes
de isolamento e CI que roda a cada push. Ver `docs/PRONTIDAO.md`.

### Lição 2 — multiunidade (filiais) — PRÓXIMA
Segmentar o produto por **unidade da consultoria**: cada filial enxerga os
próprios projetos, consultores e faturamento; o CEO enxerga o consolidado e
consegue comparar unidades.

O que isso exige, em ordem:
1. Entidade `Unidade` (nome, CNPJ, cidade) e `unidade_id` em Consultor,
   Projeto e Cliente.
2. Vínculo do `Usuario` à unidade — e um perfil de gestor de unidade, ou o RH
   passando a ser por unidade.
3. **Filtro por unidade em toda consulta** — é aqui que mora o risco: é o mesmo
   tipo de furo da Lição 1, uma escala acima. Sem um filtro central (algo como
   `unidade_do_filtro`, irmão do `consultor_do_filtro` que já existe), cada
   rota nova vira uma chance de vazar dado entre filiais.
4. Dashboard consolidado × por unidade, e rateio de custo indireto.

**Pré-requisito:** Alembic (dívida D-1). Adicionar `unidade_id` em tabelas com
dado real dentro é exatamente a migração que hoje não temos como fazer.

### Lição 3 — ambiente por branch
Preview da Vercel com banco separado do de produção. Hoje os dois apontam para
o mesmo Supabase, então testar numa branch mexe no dado de produção.

### Ainda abertos da Onda 4
Portfólio executivo, construtor de relatórios, mobile.
