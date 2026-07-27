# RunRate — by MRPN Solutions

> **Tudo se encaixa. Entrega com controle.**

PSA (Professional Services Automation) para consultoria SAP que fatura por
hora-homem. Tripé: **Projeto ↔ Alocação de consultores ↔ Receita**.

Identidade conforme o manual da marca: **grafite profundo `#1E2430`**, **azul
elétrico `#0A78F0`** e **cinza claro `#F7F8FA`**; símbolo de quatro peças que se
encaixam (pessoas · processos · finanças · entrega), com a peça superior-direita
sempre em azul. Tipografia Geist + JetBrains Mono para os dados — *Söhne, a fonte
do manual, exige licença comercial da Klim e entra trocando uma linha em `--fonte`
assim que os arquivos estiverem no repositório*. **Tema claro e escuro**
(Configurações → Aparência: Claro / Escuro / Sistema).

O sistema de design está documentado em [DESIGN.md](DESIGN.md) (tokens + regras)
e o registro de produto em [PRODUCT.md](PRODUCT.md).

Todo projeto segue a metodologia **SAP Activate** com 6 fases fixas
(Discover → Prepare → Explore → Realize → Deploy → Run), geradas automaticamente na
criação do projeto com datas estimadas editáveis.

## Como rodar (um comando)

```powershell
.\run.ps1          # Windows (PowerShell)
./run.sh           # Linux/macOS
```

O script instala as dependências, builda o frontend e sobe tudo em
**http://127.0.0.1:8000** (a API documentada fica em **http://127.0.0.1:8000/docs**).
O banco SQLite (`backend/psa.db`) nasce populado com o seed de demonstração:
2 clientes, 3 projetos em fases diferentes, 6 consultores (com módulo SAP),
~8 semanas de apontamentos e atividades descritas nas 2 últimas semanas.

Para desenvolvimento com hot-reload do frontend:

```bash
# terminal 1 — API
cd backend && python -m uvicorn app.main:app --reload
# terminal 2 — frontend (proxy /api → 8000)
cd frontend && npm run dev
```

Testes (motor de receita, recálculo em cascata e apontamento com descrição):

```bash
cd backend && python -m pytest tests -q
```

## Login e perfis (autenticação real)

Login com **e-mail e senha de verdade** (pbkdf2-sha256, sessões por token com
expiração deslizante — Authorization: Bearer em toda a API; logout revoga o
token na hora). Usuários demo do seed (senha `psa123`): `gestor@psa.com` e um
por consultor (`ana@psa.com`, `bruno@psa.com`, …).

- **Gestor** — visão completa; gerencia usuários e vê a trilha de auditoria.
- **Consultor** — entra no próprio espaço (apontamento, agenda, despesas,
  ausências); o RBAC bloqueia no servidor qualquer rota gerencial (403).

**Auditoria**: toda mutação da API (POST/PATCH/DELETE) é registrada por
middleware — quem, quando, o quê e o resultado — visível em Configurações.

## Telas

Navegação global numa **sidebar clara agrupada** (padrão Productive/ClickUp):
todos os ~20 destinos visíveis de uma vez em 5 grupos (Visão geral · Comercial ·
Projetos · Equipe · Financeiro), com o botão **+ Novo** (ações rápidas que já
abrem o formulário via `?novo=1`), badge ao vivo de aprovações e rodapé com o
usuário. A topbar fina traz a **busca de telas** (digite e salte, com ↑/↓ e Enter).
Responsivo estrutural: vira **rail de ícones** até 1180px e **gaveta** no mobile.

| Tela | O que faz |
|---|---|
| Copiloto (Dashboard) | **Insights determinísticos do motor** (faturas vencidas, desvios de baseline, gargalos, superalocação, riscos críticos, CRs, pendências) + **chat**: sem chave responde pelos insights; com a **chave da API Anthropic** (Configurações) usa IA generativa por cima do motor |
| Propostas (Comercial) | **Funil kanban** com **precificação por mix de senioridade** (horas jr/pl/sr × taxas da Configuração, **margem estimada pelo custo médio real**), escopo/premissas/validade; aprovada **converte em projeto** |
| Contratos (Comercial) | Vigência e situação; radar de **renovação (60 dias)** e vencidos |
| Medições (Financeiro) | **Relatório de horas do mês para aceite do cliente** ANTES de faturar: gerar → aceite emite a fatura (substituindo a prevista do mês) · contestação devolve para correção — imprimível |
| Faturamento (Financeiro) | **Plano de faturas gerado da receita prevista** mês a mês; emitir (vencimento +30d) → receber; regerar preserva emitidas |
| Contas a Receber (Financeiro) | Faturas emitidas em aberto com **aging** — vencidas destacadas ("vencida há Xd") |
| Contas a Pagar (Financeiro) | Reembolsos devidos aos consultores, com total por pessoa |
| Fluxo de Caixa (Financeiro) | Entradas (recebido + projetado) × saídas (custo das horas + despesas), com **saldo acumulado** |
| Rentabilidade (Financeiro) | Ranking de margem realizada por projeto (top/bottom) |
| Dashboard | Receita prevista×realizada, margem vs meta, utilização da semana, projetos por fase, **feed de atividades** e contadores de aprovações/pendências |
| Projetos | Lista com busca/paginação; criação gera as 6 fases Activate com entregas e Quality Gate do **modelo de projeto escolhido** (implantação padrão, rollout, ou modelos próprios editáveis nas Configurações) |
| Projeto (detalhe) | Gantt, alocações com margem, **EVM (SPI/CPI, PV/EV/AC/BAC/EAC)**, **Orçado × Realizado por rubrica** (horas e despesas automáticas do motor + terceiros/licenças/outros manuais, barras de consumo, edição inline), **TAP em 1 clique**, **solicitar alocação** (com prévia de conflitos), entregas por fase, **Quality Gate semáforo**, pendências e o recálculo em cascata com diff antes→depois |
| Quadro Ágil (por projeto) | **Híbrido estilo J.Agile**: o cronograma Activate manda no prazo/receita, a sprint organiza a execução — backlog (entregas das fases) → kanban A fazer/Em andamento/Concluída; só 1 sprint ativa; encerrar devolve pendentes ao backlog com **carry-over** medido; horas apontadas no período da sprint |
| Consultores | **Demanda × Capacidade da equipe** (gargalos em vermelho) + heatmap de utilização com **capacidade real** (ausências) e detecção de "alocado durante férias" |
| Agenda | **Calendário mensal do consultor**: alocações por dia (h/dia), ausências aprovadas, feriados e horas apontadas — consultor vê a própria, gestor escolhe quem ver |
| Clientes | Carteira com receita por cliente + detalhe com projetos |
| Apontamento | Grade semanal (salva ao sair do campo); **balão por dia** ("o que foi feito"); **enviar semana para aprovação** — trava a edição até a decisão do gestor |
| Despesas | Lançamento por projeto (inclusive **km × taxa**), aprovação e reembolso |
| Ausências | Férias/folgas/afastamentos — aprovadas reduzem a capacidade da semana |
| Aprovações (gestor) | **Fila unificada**: semanas de horas (com o detalhamento dia a dia e descrições), **solicitações de alocação com análise de conflitos do motor** (semana a semana: já alocado × pedido × capacidade; ausências no período), ausências e despesas — aprovar/reprovar com comentário; badge ao vivo na navegação |
| Pendências (gestor) | Central de ocorrências dos projetos: prioridade, responsável, resolução |
| Configurações | Perfil da consultoria, jornada, limiares, taxas por senioridade, **taxa por km**, **aparência** (tema claro/escuro/sistema), feriados, **modelos de projeto**, **Copiloto IA** (chave da API Anthropic + modelo), **usuários** (criar/vincular consultor/redefinir senha/desativar) e **trilha de auditoria** |

As telas de dados (apontamentos, faturas, despesas, propostas, pendências e
rentabilidade) têm **Exportar CSV** — separador `;`, BOM e decimal com vírgula,
prontos para o Excel pt-BR (`/api/export/{recurso}.csv`).

## Estrutura

```
backend/
  app/
    models.py            # Cliente, Projeto, Fase, Consultor, Alocação, Apontamento(+descrição), Configuração
    database.py          # SQLite via SQLModel (troque DATABASE_URL p/ Postgres)
    seed.py              # seed de demonstração (determinístico, relativo a hoje)
    services/
      receita.py         # ★ motor de receita hora-homem (funções puras)
      reagendamento.py   # ★ recálculo em cascata + diff antes→depois
      projetos.py        # criação de projeto com as 6 fases Activate
    routers/             # API REST JSON (OpenAPI em /docs)
  tests/                 # unitários do motor, da cascata e do apontamento
frontend/                # React + Vite; CSS próprio; fontes Geist/JetBrains Mono
                         # self-hosted (SEM CDN em runtime — ambiente corporativo)
  src/sessao.jsx         # sessão por perfil (gestor/consultor) + guarda de rota
  src/pages/             # todas as telas acima + Login
```

## Regras de negócio (resumo)

- **Receita prevista** = Σ (horas previstas × taxa hora-venda da alocação). A taxa da
  alocação nasce igual à do consultor, mas é editável (negociações variam por projeto).
- **Receita realizada** = Σ (horas apontadas × taxa hora-venda da alocação).
- **Margem** = receita − (horas × taxa hora-custo do consultor).
- **Utilização semanal** = horas alocadas / 40h. `>100%` superalocado, `<60%` ocioso
  (limiares editáveis em Configurações).
- **Atraso de fase**: mover a data-fim desloca as fases seguintes em cascata, estende as
  alocações da fase e recomputa a receita mensal — sempre com diff "antes → depois"
  simulado antes de aplicar.
- **Feriados** (Configurações): dias não úteis para TODO o motor — receita prevista,
  capacidade, faturas e recálculo em cascata descontam feriados automaticamente.
- **Linha de base**: fotografada na criação do projeto; a cascata mede o desvio
  ("+Xd vs baseline") por fase e no Status Report.
- **Governança**: riscos (matriz probabilidade × impacto), mudanças/CR com impacto em
  horas e valor, **Status Report em 1 clique** (imprimível — serve de termo de
  encerramento) e encerramento formal com lições aprendidas.
- **Descrição de atividade**: cada dia apontado pode ter um texto "o que foi feito";
  salvar horas nunca apaga a descrição, e o feed do gestor lista as mais recentes.

## A camada de IA (Copiloto) — plugada por cima do motor

O recálculo é **determinístico e isolado** em `backend/app/services/`:

- `receita.py` — motor de receita (funções puras, sem I/O);
- `reagendamento.py` — `simular_reagendamento()` produz o diff completo sem tocar o
  banco; `aplicar_reagendamento()` persiste;
- `evm.py` — valor agregado (PV/EV/AC → SPI/CPI/EAC) derivado do motor;
- `copiloto.py` — a camada de IA, **por cima** dos serviços acima: gera insights
  determinísticos sempre; com a chave da API Anthropic (Configurações → Copiloto IA)
  envia o contexto do motor ao modelo para respostas em linguagem natural. Nenhuma
  regra de cálculo vive em prompt — a IA interpreta, prioriza e recomenda; se a
  chamada falhar, degrada para os insights determinísticos com aviso.

## Base metodológica

As entregas padrão por fase e os checklists de Quality Gate foram adaptados dos
aceleradores oficiais do SAP Activate (PQGs, cutover, RACI fit-to-standard); o mapa
funcional de referência de PSA veio da documentação do PSOffice. Análise completa em
`docs/analise-psoffice-activate.md`.

## Fora do escopo (por decisão)

CRM de contatos/atividades comerciais (o pipeline é de **propostas de projeto**),
GMUD, integração SAP, SSO corporativo e emissão fiscal real (NF-e — o faturamento
controla o ciclo, não emite nota). Épicos restantes da Onda 4: ágil/híbrido,
portfólio executivo, construtor de relatórios e mobile (plano em docs/).
