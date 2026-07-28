# Guia de uso — RunRate

**RunRate by MRPN Solutions** — PSA para consultoria SAP que fatura por hora-homem.

A ideia que sustenta o sistema inteiro: **projeto ↔ alocação ↔ receita são a mesma
coisa vista de ângulos diferentes.** Quando um consultor lança 8 horas num projeto,
isso já é custo, já é receita prevista e já é consumo de capacidade da semana. Não
existe planilha paralela para reconciliar depois.

- **No ar:** https://runrate-five.vercel.app
- **Acesso de demonstração:** `gestor@psa.com` ou `ana@psa.com`, senha `psa123`

---

## Entrar

A tela de login tem os dois perfis de demonstração como botões — um clique
preenche o formulário.

Depois de entrar, o **avatar no canto superior direito** abre o menu da conta:
troca de tema (Claro, Escuro ou Sistema), Configurações e sair. O claro é o tema
oficial; o escuro é preferência sua e fica salvo no navegador.

## Os dois perfis

O que você vê depende de quem você é.

| | Gestor | Consultor |
| --- | --- | --- |
| Navegação | 5 grupos, 20 telas | 1 grupo, 4 telas |
| Enxerga | tudo: comercial, projetos, equipe, financeiro | apenas o próprio espaço |
| Pode | criar projeto, aprovar horas, faturar, configurar | lançar horas, despesas e ausências |

A restrição não é só visual: o backend exige perfil de gestor nas rotas
sensíveis. Consultor não vê custo de colega nem margem de projeto.

---

# Para o consultor

Seu espaço tem quatro telas. A rotina real é semanal.

## Lançar horas

**Apontamento** é onde o trabalho vira dado.

1. A tela abre na **semana atual**, com uma linha por alocação sua e uma coluna
   por dia.
2. Digite as horas na célula do dia. O total do dia e o total da semana somam
   sozinhos.
3. Enquanto você não enviar, a semana fica marcada como **Rascunho — horas ainda
   não enviadas**. Pode voltar e corrigir quantas vezes quiser.
4. Quando fechar a semana, clique em **Enviar semana para aprovação**.

Depois de enviada, a semana sai do seu controle e entra na fila do gestor. Se ele
recusar, ela volta editável com o motivo.

> Lance a descrição do que foi feito junto com as horas. É o que o gestor usa
> para aprovar sem te perguntar, e é o que vira memória de cálculo na medição
> que o cliente recebe.

## Despesas

**Despesas** registra reembolso: tipo, valor, data, projeto e comprovante. Segue
o mesmo caminho das horas — entra como pendente e o gestor aprova ou recusa.

## Ausências

**Ausências** pede férias, folga, afastamento ou treinamento.

Isso não é burocracia: ausência aprovada **reduz sua capacidade** naquelas
semanas. O gestor passa a ver o buraco no gráfico de demanda × capacidade antes
de te alocar em algo que não caberia.

## Agenda

**Agenda** mostra o seu mês: onde você está alocado, quanto por dia, feriados e
ausências. É a visão de "o que me espera".

---

# Para o gestor

A navegação segue o ciclo do negócio: **Comercial → Projetos → Equipe → Financeiro**,
com o Dashboard e o Copiloto por cima.

## Dashboard

A resposta de "como estamos?" em uma tela: receita prevista e realizada, margem
contra a meta (o anel), receita mês a mês, projetos ativos com a fase atual, e a
utilização da equipe na semana corrente.

Os alertas de alocação no quarto cartão são atalhos — clicar em "4 aprovações"
leva direto para a fila.

## Comercial

### Propostas

Pipeline em colunas, e o estágio é o que move o card:

**Qualificação → Proposta → Negociação → Aprovada**, terminando em
**Convertida** (virou projeto) ou **Perdida**.

A proposta carrega a precificação: horas por senioridade, taxa de venda, e o
valor total sai do cálculo, não do chute. Quando ela é aprovada, converter cria o
projeto já com o escopo.

### Contratos e Clientes

**Contratos** guarda o vínculo formal — vigência, valor, condição de pagamento.
**Clientes** é o cadastro, e a ficha de cada um mostra o histórico de projetos e
faturamento.

## Projetos

### A lista

**Projetos** lista tudo com filtro por situação (Todos, Ativos, Pausados,
Encerrados) e mostra a fase Activate atual de cada um como uma trilha de seis
pontos.

> **Todo projeto nasce com as 6 fases do SAP Activate** já geradas:
> **Discover, Prepare, Explore, Realize, Deploy, Run** — com atividades típicas
> e quality gates dentro de cada uma. Você não monta cronograma do zero.

### A ficha do projeto

Clicando num projeto você chega no centro operacional dele:

| Seção | Para que serve |
| --- | --- |
| **Linha do tempo — SAP Activate** | as 6 fases com datas e progresso; clicar numa fase permite **reagendar**, e o sistema mostra o efeito em cascata nas fases seguintes antes de confirmar |
| **Pendências do projeto** | o que está travando, com responsável e prioridade |
| **Riscos** | probabilidade × impacto, com plano de resposta |
| **Mudanças (CR)** | change request com impacto em prazo e valor |
| **Orçado × Realizado** | por rubrica, para ver onde o dinheiro está indo |
| **Valor agregado (EVM)** | SPI, CPI e EAC — explicado abaixo |

Ainda na ficha você encontra o **TAP** (termo de abertura), a **baseline**
(cronograma congelado para comparar), o **status report** e a ação de
**encerrar projeto formalmente**.

### Quality gate

Cada fase tem um portão de qualidade com quatro estados: **não verificado,
verde, amarelo, vermelho**. Ele existe para você não avançar de fase com dívida
escondida — o gate vermelho é a conversa que precisa acontecer antes do Realize,
não depois.

### Modo ágil

Projetos que rodam em sprint têm o **Quadro Ágil** (botão na ficha do projeto):
backlog das entregas das fases, kanban em três colunas e sprints com estado
**planejada → ativa → encerrada**.

O cronograma Activate continua mandando no prazo e na receita; a sprint só
organiza a execução. Ao encerrar uma sprint, o que não foi concluído volta para
o backlog automaticamente (**carry-over**), e o sistema te avisa quantos itens
voltaram.

## Equipe

### Consultores

A tela mais densa do produto, e de propósito. O gráfico **Demanda × Capacidade**
mostra semana a semana se a equipe cabe no que foi vendido, e o gargalo aparece
em vermelho.

Abaixo, o mapa de calor por consultor: cada célula é uma semana, com o percentual
de utilização. A leitura é imediata:

- **acima de 100%** — superalocado, vai estourar
- **60 a 100%** — saudável
- **abaixo de 60%** — ocioso, é capacidade paga sem receita

A capacidade não é a jornada nominal: o sistema desconta feriados e ausências
aprovadas. É por isso que ausência registrada importa.

### Aprovações

A fila do gestor, com contador na navegação. Aqui chegam:

- **semanas de apontamento** enviadas pelos consultores — **Aprovar** ou **Recusar** com motivo
- **despesas** lançadas
- **solicitações de alocação**, com **Aprovar e alocar** em um passo

Ao aprovar uma alocação, o sistema **detecta conflito** antes: se aquele
consultor já passaria da capacidade naquelas semanas, ele avisa em vez de deixar
você criar o problema.

### Apontamento, Despesas, Ausências

O gestor também tem essas telas — para lançar em nome da equipe quando preciso e
para ver o quadro completo.

## Financeiro

O caminho do dinheiro, na ordem:

### Medições

**Medições** transforma horas aprovadas em documento para o cliente.
**Gerar medição** consolida o período; a medição nasce **gerada** e vira
**aceita** ou **contestada** conforme a resposta do cliente. É a etapa que
protege o faturamento — nota fiscal contra medição aceita raramente volta.

### Faturamento e cobrança

**Faturamento** emite a fatura a partir da medição. Depois:

- **Contas a receber** — o que o cliente deve, com vencimento e atraso
- **Contas a pagar** — custo de terceiros e despesas
- **Fluxo de caixa** — previsto contra realizado no tempo
- **Rentabilidade** — margem por projeto e por cliente, já com custo de hora

## Copiloto

O **Copiloto** lê o estado real do produto e aponta o que merece atenção:
gargalo de capacidade, projeto com CPI ruim, medição parada, fase atrasada.

Vale entender como ele funciona, porque muda a confiança que você deposita nele:
**quem calcula é o motor determinístico, não a IA.** Os insights saem de regras
sobre os seus dados. A IA entra apenas para redigir e para responder no chat, e
sempre lendo números que já foram calculados. Sem chave de API configurada, o
Copiloto continua funcionando com os insights determinísticos.

---

## Conceitos que vale entender

### EVM — valor agregado

Três medidas e três respostas:

| Indicador | Pergunta | Leitura |
| --- | --- | --- |
| **SPI** | estamos no prazo? | 1,0 = em dia; abaixo = atrasado |
| **CPI** | estamos no custo? | 1,0 = no orçamento; abaixo = gastando mais que entregou |
| **EAC** | quanto vai custar no fim? | projeção do custo total no ritmo atual |

É o que diferencia "gastamos 60% do orçamento" de "gastamos 60% e entregamos
40%" — a segunda frase é um problema, a primeira é só um número.

### Baseline

Congela o cronograma num momento. Depois, qualquer reagendamento pode ser
comparado contra o plano original — é como você prova se o atraso veio do
cliente ou da execução.

### Medição × Fatura

**Medição** é o cliente concordando com o que foi entregue. **Fatura** é a
cobrança. Nessa ordem, e nunca ao contrário.

---

## Atalhos e utilidades

| Onde | O que faz |
| --- | --- |
| **+ Novo** (topo da navegação) | ações rápidas — novo projeto, nova proposta, nova despesa, lançar horas |
| **Buscar tela** (topbar) | busca entre as 20 telas; navegue com ↑ ↓ e Enter |
| **Avatar** (canto direito) | tema, Configurações, sair |
| **Exportar** | vários relatórios exportam CSV, com acento correto no Excel |

## Configurações — só gestor

| Seção | O que controla |
| --- | --- |
| **Aparência** | tema padrão da sua conta |
| **Usuários** | quem acessa, com que perfil, e redefinição de senha |
| **Feriados** | calendário corporativo — entra direto no cálculo de capacidade |
| **Modelos de projeto** | o esqueleto de fases e atividades que todo projeto novo herda |
| **Copiloto IA** | chave da API e modelo |
| **Auditoria** | trilha de quem fez o quê, com data e resultado |

---

## Quando algo não estiver como você espera

**"Lancei horas e não aparecem no faturamento."**
Horas passam por aprovação e depois por medição antes de faturar. Confira em
Aprovações se a semana está pendente.

**"O consultor aparece ocioso mas está trabalhando."**
Utilização vem de **alocação**, não de horas lançadas. Se não existe alocação no
projeto, o trabalho não conta na capacidade.

**"A capacidade da semana está menor que o normal."**
Feriado no calendário corporativo ou ausência aprovada. Os dois reduzem a
capacidade real de propósito.

**"Reagendei uma fase e outras se moveram."**
É o comportamento correto: fases Activate são sequenciais. O sistema mostra o
efeito em cascata antes de confirmar — se não era isso, cancele e reagende
apenas a fase final.

---

## Este ambiente é uma demonstração

As credenciais aparecem na tela de login e todos os usuários nascem com a senha
`psa123`. Antes de receber dado real de cliente:

1. `VITE_DEMO=0` nas variáveis da Vercel — tira o bloco de credenciais do login
2. Trocar as senhas em **Configurações → Usuários**
3. Ativar **Deployment Protection** na Vercel, se o ambiente não deve ser público

O passo a passo de infraestrutura está em [DEPLOY.md](../DEPLOY.md); as decisões
de design, em [DESIGN.md](../DESIGN.md).
