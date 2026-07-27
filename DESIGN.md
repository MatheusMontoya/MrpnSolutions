---
name: RunRate
description: PSA para consultoria SAP hora-homem — azul elétrico sobre grafite, calmo e denso onde o dado exige.
colors:
  azul-eletrico: "#0a78f0"
  azul-fundo: "#0a5cb8"
  azul-lavagem: "#e8f2fe"
  azul-borda-marca: "#b9d9fb"
  azure-assinatura: "#3fa0ff"
  grafite-profundo: "#1e2430"
  tinta: "#1e2430"
  tinta-2: "#5a6270"
  tinta-3: "#8b93a1"
  canvas: "#f7f8fa"
  superficie: "#ffffff"
  superficie-baixa: "#f2f4f7"
  linha: "#e3e6ec"
  verde-saudavel: "#07875a"
  ambar-atencao: "#a3600a"
  carmim-critico: "#d62b4f"
typography:
  display:
    fontFamily: "Figtree Variable, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Figtree Variable, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: "24px"
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Figtree Variable, system-ui, sans-serif"
    fontSize: "14.5px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Figtree Variable, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  dado:
    fontFamily: "Figtree Variable, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 500
    lineHeight: 1.4
    fontFeature: "tabular-nums"
rounded:
  controle: "12px"
  superficie: "22px"
  destaque: "30px"
  pilula: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.azul-eletrico}"
    textColor: "#ffffff"
    rounded: "{rounded.controle}"
    padding: "8px 16px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "#0968d4"
  button-secondary:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.azul-fundo}"
    rounded: "{rounded.controle}"
    padding: "8px 16px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.controle}"
  card:
    backgroundColor: "{colors.superficie}"
    rounded: "{rounded.superficie}"
    padding: "22px 24px"
  input:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.controle}"
    padding: "9px 12px"
    height: "40px"
  sidebar-item:
    backgroundColor: "transparent"
    textColor: "{colors.tinta-2}"
    rounded: "11px"
    height: "36px"
  sidebar-item-active:
    backgroundColor: "{colors.azul-lavagem}"
    textColor: "{colors.azul-fundo}"
  badge:
    backgroundColor: "{colors.azul-lavagem}"
    textColor: "{colors.azul-fundo}"
    rounded: "{rounded.pilula}"
    padding: "3px 10px"
---

# Design System: RunRate

## Overview

**Creative North Star: "Tudo se encaixa"**

O conceito vem do próprio símbolo: quatro peças — pessoas, processos, finanças e
entrega — que só formam um quadrado quando se encaixam. A interface é a prova
disso: a navegação inteira fica aberta numa coluna à esquerda (nada escondido
atrás de abas), o canvas é um cinza claro quase imperceptível, e a única cor viva
do sistema — o azul elétrico — só aparece onde existe ação ou seleção. O gestor
entra para responder "quanto isso fatura?" e "quem está livre?"; a interface
entrega o número e sai da frente.

**O tema claro é o oficial.** Quem nunca escolheu vê o claro, mesmo com o sistema
operacional no escuro — a decisão está em `tema.jsx`, não no `prefers-color-scheme`.
O escuro existe e é completo, mas é preferência do usuário (menu da conta →
Claro / Escuro / Sistema), não o rosto do produto: RunRate é visto em reunião de
status, projetado em tela e impresso em PDF, e é no claro que ele nasce.

A densidade é deliberadamente desigual: tabelas e grades de apontamento podem ser
densas porque são o trabalho; tudo ao redor respira. Superfícies são planas, com
cantos generosos e sombra quase imperceptível — a profundidade vem do espaço e da
hierarquia tipográfica, não de camadas empilhadas.

O sistema rejeita explicitamente: MAIÚSCULAS decorativas como rótulo de seção,
bordas laterais coloridas em cards, movimento que não comunica estado, e qualquer
cor saturada fora do acento único.

**Key Characteristics:**
- Navegação global sempre visível, agrupada por domínio
- Um acento só, usado com parcimônia (ação, seleção, estado)
- Números sempre com figuras tabulares (a própria sans, nunca monoespaçada)
- Cantos macios (12 / 22 / 30px) e sombras mínimas
- Dois temas com os mesmos componentes: só os valores dos tokens mudam

### Login

Coluna única centrada de 400px, fundo liso, sem card e sem painel decorativo —
o padrão de Stripe e ClickUp. Marca discreta no topo, campo e botão primário na
**mesma largura**, altura de 46px e fonte de 16px nos campos (abaixo disso o iOS
dá zoom ao focar). Não existe recuperação de senha por autoatendimento: quem
redefine é o gestor, e a tela diz isso em vez de exibir um link morto.

**A Aurora da Marca.** O topo do login recebe uma faixa pastel que viaja DENTRO
do azul — azul-fundo à esquerda, azul elétrico no centro, azure à direita — e é
apagada por máscara antes de chegar no formulário. O grafite foi testado nessa
faixa e embarra o degradê de cinza; a viagem fica só no azul. É o único degradê
da tela e vive em superfície ampla, como manda a Regra da Marca Chapada. No tema
escuro o grafite já é o fundo, então a aurora vira luz azul em vez de véu.

**A Regra do Desabilitado.** Botão inativo não é botão desbotado. Nada de
`opacity` global — ela embaça o rótulo junto com o fundo e o controle parece
quebrado. O desabilitado troca a cor de marca por um neutro sólido e mantém o
texto legível (≥4:1 nos dois temas). Overrides de tema precisam de
`:not(:disabled)` — sem isso vencem por especificidade e devolvem a cor de marca
a um controle inativo.

## Colors

Três cores oficiais e nada além: **grafite profundo** (#1E2430), **azul elétrico**
(#0A78F0) e **cinza claro** (#F7F8FA). As três semânticas de estado existem só para
comunicar situação, nunca para decorar.

### Primary
- **Azul Elétrico** (#0A78F0): a cor de marca, chapada. Botão primário, a peça
  superior-direita do símbolo, link, aba e item de navegação ativos, foco de teclado,
  série "realizada" nos gráficos. Nunca como preenchimento de badge nem como
  decoração de superfície.
- **Azure Assinatura** (#3fa0ff): existe só como fim do degradê contido
  (#0A78F0 → #3fa0ff), restrito ao hero do login e à borda do card do copiloto.
  Nunca sozinho como cor de texto ou fundo, e nunca no símbolo — a marca é chapada.

### Neutral
- **Grafite Profundo** (#1E2430): cor de marca que faz três papéis — a tinta do texto,
  as três peças do símbolo em fundo claro e o hero escuro do login. No tema escuro,
  vira a superfície dos cards.
- **Cinza Claro** (#F7F8FA): o fundo da área de trabalho, direto do manual da marca.
  Existe só para o branco puro dos cards se destacar.
- **Superfície** (#ffffff) e **Superfície Baixa** (#f2f4f7): cards e faixas internas
  (cabeçalho de tabela, hover de linha, campo de busca em repouso).
- **Tinta** (#1e2430), **Tinta 2** (#5a6270), **Tinta 3** (#8b93a1): a rampa de texto
  — conteúdo, apoio e metadado. Tinta 3 nunca carrega informação essencial.
- **Linha** (#e3e6ec): divisórias e contorno de card, sempre 1px.

### Tertiary
Semânticas, e apenas para estado: **Verde Saudável** (#07875a) para dentro da meta e
aprovado, **Âmbar Atenção** (#a3600a) para ocioso e pendente, **Carmim Crítico**
(#d62b4f) para superalocado, vencido e destrutivo.

### Named Rules
**A Regra do Acento Único.** Se um elemento não é acionável, não está selecionado e
não indica estado, ele não usa o azul da marca. Um badge informativo usa a lavagem
(#e8f2fe) com texto em #0a5cb8 — nunca o acento cheio.

**A Regra da Marca Chapada.** O símbolo, os ícones de app e o botão primário usam cor
sólida — nunca degradê. O degradê sobrevive em no máximo um lugar por tela e apenas
em superfície ampla (hero do login, borda do card do copiloto). Gradiente em texto é
proibido.

## Typography

**Família única:** Figtree Variable (fallback system-ui) — **substituta
técnica de Söhne**. Não há segunda família: os números usam as figuras tabulares
desta mesma fonte.

> A marca especifica **Söhne** (Klim Type Foundry), de licença comercial. Como o
> ambiente proíbe CDN, ela não pode ser carregada sem os arquivos licenciados. Com os
> `.woff2` em `frontend/src/fontes/`, a troca é uma linha: `--fonte: "Sohne", "Figtree
> Variable", system-ui`. Até lá, Figtree sustenta o registro (humanista de bojos circulares,
> contorno fechado, ótima em peso alto).

**Character:** Uma sans neo-grotesca de contorno fechado carrega tudo — título, rótulo,
corpo — variando só em peso e tracking. A monoespaçada não entra em lugar nenhum da interface; o token `--fonte-mono` fica reservado para
número, para que colunas de valores alinhem sozinhas. Ambas são servidas pelo bundle;
o ambiente do cliente bloqueia CDN.

### Hierarchy
- **Display** (800, 28px, 1.15, -0.025em): título de página. Um por tela.
- **Title** (700, 18px, 24px, -0.015em): título de card ou seção, sempre em
  sentence-case.
- **Body** (400, 14.5px, 1.55): texto corrente; descrições limitadas a ~70ch.
- **Label** (600, 12.5px): rótulo de campo, cabeçalho de tabela, metadado.
- **Dado** (500, 13.5px, tabular-nums): todo número — valor, hora, percentual, data,
  identificador.

### Named Rules
**A Regra do Sentence-case.** Nenhum rótulo de seção, cabeçalho de card ou coluna usa
caixa alta com tracking. A única exceção viva são as siglas das 6 fases SAP Activate
no Gantt e no heatmap, onde funcionam como código.

**A Regra do Número Tabular.** Qualquer dígito que o usuário possa comparar entre
linhas leva `font-variant-numeric: tabular-nums` na própria fonte da interface — alinha
em coluna sem o desenho quadrado de uma monoespaçada. Dinheiro, horas e datas nunca saem na
fonte de interface.

## Layout

Grade de duas colunas no nível do app: sidebar fixa de 252px + área de trabalho
rolável. O conteúdo tem largura máxima de 1240px centralizada, com respiro lateral de
32px. Dentro das telas, a composição é de blocos empilhados; grades de 2 colunas
usam sempre `minmax(0, 1fr)` — sem isso, uma tabela larga estoura a coluna e vaza a
página inteira.

O ritmo de espaçamento é base 4 (4/8/12/16/20/24/32/40). Cards têm 22–24px de padding
interno; entre blocos, 20–24px.

Responsivo estrutural, nunca tipográfico: até **1180px** a sidebar vira um rail de
ícones (rótulos ocultos, contador vira ponto); até **860px** as grades de 2 colunas
colapsam e as tabelas rolam dentro do próprio card; até **760px** a sidebar vira
gaveta sobre backdrop, acionada pelo botão da topbar.

### Named Rules
**A Regra do Zero Overflow.** Nenhuma tela pode ter rolagem horizontal no documento,
em nenhuma largura. Conteúdo largo (tabela, Gantt, heatmap, kanban) rola dentro do
seu próprio container.

## Elevation & Depth

Sistema quase plano. A profundidade vem de três coisas, nesta ordem: espaço em
branco, contraste tipográfico e uma borda de 1px. A sombra é o último recurso e
existe só para separar o que flutua de verdade.

### Shadow Vocabulary
- **Repouso** (`0 1px 2px rgba(30,36,48,0.06)`): card sobre o canvas. Praticamente
  invisível — é um assentamento, não uma elevação.
- **Levantado** (`0 8px 24px -12px rgba(30,36,48,0.12)`): resposta a hover em
  superfície clicável.
- **Flutuante** (`0 16px 40px -12px rgba(30,36,48,0.28)`): menu, popover e modal —
  o que realmente sai do plano.

### Named Rules
**A Regra do Plano em Repouso.** Superfície parada não tem sombra perceptível. Sombra
é reação a estado (hover, sobreposição), nunca decoração.

## Shapes

Retângulos de cantos macios em três degraus: **controle** (10px) para botão, campo,
chip e célula; **superfície** (20px) para card, modal e container; **destaque** (28px)
para o card do copiloto. Badges e contadores fogem da escala e usam pílula completa
(999px), o que os separa visualmente de qualquer coisa clicável.

Bordas são sempre 1px e da cor Linha. Ícones são SVG inline de traço 2px, desenhados
no grid de 24px — nunca fonte de ícone, nunca pacote externo.

### Named Rules
**A Regra da Borda Fina.** Toda borda é 1px. Se um elemento precisa de mais destaque,
ele ganha fundo tingido ou sombra — nunca borda grossa, e jamais borda colorida em um
único lado.

## Components

### Buttons
- **Shape:** cantos macios (10px), altura mínima 38px (44px na variante grande)
- **Primary:** azul elétrico chapado (#0A78F0) com texto branco;
  padding 8px 16px
- **Hover / Focus:** hover escurece o fundo; `:active` aplica `translateY(1px)
  scale(0.99)` — um clique físico de 130ms; foco sempre com anel de 2px no acento
- **Secondary:** superfície branca, texto #0a5cb8, borda #b9d9fb — a escolha padrão
  para ações não destrutivas
- **Ghost:** sem fundo até o hover; usado em ação terciária e dentro de linhas de tabela
- **Loading:** `.carregando` injeta um spinner de 13px em `currentColor` e bloqueia o
  ponteiro; o rótulo permanece

### Chips
- **Toolbar chip:** 34px de altura, transparente em repouso, fundo tingido quando
  ativo, com bolha de contagem à direita (fundo neutro; vira acento quando o filtro
  está ligado)
- **Badge:** pílula 3px/10px, fundo pastel + texto saturado do mesmo matiz, peso 600

### Cards / Containers
- **Corner Style:** 20px (28px no card de destaque do copiloto)
- **Background:** superfície branca sobre canvas frio
- **Shadow Strategy:** Repouso; Levantado apenas em `.card-clicavel`
- **Border:** 1px Linha
- **Internal Padding:** 22px vertical, 24px horizontal
- **Proibido:** card dentro de card. Listas dentro de um card são linhas separadas por
  hairline, com um chip de ícone colorido à esquerda quando precisam de estado.

### Inputs / Fields
- **Style:** altura 40px, borda 1px, cantos de 10px, fundo branco; `select` recebe
  chevron SVG embutido em vez do controle nativo
- **Focus:** borda no acento + anel de 3px `rgba(10,120,240,0.16)`
- **Disabled:** fundo Superfície Baixa, texto Tinta 2

### Navigation
- **Sidebar:** 252px, fundo branco, hairline à direita. Itens de 36px, ícone 17px +
  rótulo 13.5px; agrupados por domínio com rótulo em sentence-case. Ativo = pílula na
  lavagem do acento com texto e ícone no acento (nunca barra lateral). Contador em
  pílula carmim.
- **Topbar:** 58px, translúcida com blur, hairline inferior. Contém a busca de telas e
  ações de utilidade.
- **Mobile:** gaveta deslizante sobre backdrop navy a 40%.

### Anel de progresso (signature)
Donut de 54px em `conic-gradient` com miolo vazado na cor da superfície e o valor em
tabular no centro. Verde quando dentro da meta, âmbar quando abaixo. Usado onde
a pergunta é "estamos no alvo?" — margem no dashboard, consumo de orçamento.

### Símbolo da marca (signature)
Quatro brackets em grade 2×2 (`src/components/Marca.jsx`), formando um quadrado com um
vazio em cruz no centro: **pessoas** (superior-esquerdo), **finanças**
(superior-direito, sempre azul), **entrega** (inferior-direito) e **processos**
(inferior-esquerdo). As três peças neutras seguem `var(--texto)` — grafite no tema
claro, quase-branco no escuro, onde o #1E2430 virou superfície e a peça sumiria. A
variante `branco` é para fundos escuros fixos, como o hero do login.

### Borda em gradiente (signature)
Exclusiva do card do copiloto: pseudo-elemento com padding de 1.5px, gradiente
#0a78f0 → #3fa0ff → #6e5cff e `mask-composite: exclude`. **Estática** — a versão
animada foi removida por ser movimento decorativo.

## Do's and Don'ts

### Do:
- **Do** usar `minmax(0, 1fr)` em toda coluna de grid que possa receber tabela.
- **Do** manter todo número com `tabular-nums`.
- **Don't** trazer de volta uma monoespaçada para número da interface: quadra a tela inteira.
- **Do** escrever rótulo de seção e cabeçalho de coluna em sentence-case.
- **Do** dar aos controles os sete estados (repouso, hover, foco, ativo, desabilitado,
  carregando, erro) antes de considerar um componente pronto.
- **Do** trocar apenas VALORES de token ao mudar tema ou identidade — os componentes
  não conhecem cor.
- **Do** revelar ações de linha no `:hover`/`:focus-within`, mantendo-as sempre
  visíveis em dispositivos sem ponteiro.

### Don't:
- **Don't** usar `border-left`/`border-right` colorido como acento — em card, item de
  lista ou alerta.
- **Don't** animar largura, altura ou margem; use `transform` e `opacity`.
- **Don't** aplicar gradiente em texto (`background-clip: text`).
- **Don't** usar MAIÚSCULAS com tracking como rótulo de seção.
- **Don't** aninhar card dentro de card.
- **Don't** introduzir uma segunda cor de marca: o sistema tem um acento e três
  semânticas de estado, e nada além disso.
- **Don't** deixar movimento que não comunique estado — inclusive borda animada.
