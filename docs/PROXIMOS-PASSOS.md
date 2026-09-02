# RunRate — contexto e próximos passos

Cole este arquivo inteiro na primeira mensagem para o agente. Ele foi escrito
para quem está chegando agora e não acompanhou nada do que veio antes.

---

## O que é

**RunRate by MRPN Solutions** — PSA (Professional Services Automation) para uma
consultoria SAP que fatura por hora-homem. O ciclo que o sistema fecha é:

> cliente → proposta → projeto → alocação de consultor → apontamento de horas →
> aprovação → medição do mês → aceite do cliente → fatura → recebimento

```bash
git clone https://github.com/MatheusMontoya/MrpnSolutions.git
```

**Produção:** https://runrate-five.vercel.app · **CEO:** michel@mrpnachbar.com

---

## Regras da casa (não são preferências, são restrições)

1. **Nada de CDN em tempo de execução.** A rede do cliente bloqueia. Toda
   dependência é empacotada no build.
2. **Sem Tailwind e sem biblioteca de componentes.** CSS escrito à mão em
   `frontend/src/styles.css`, com tokens.
3. **Tudo em português — inclusive o código.** Nome de variável, de função, de
   classe CSS, de tabela e comentário. `exigir_dono`, `sem_dinheiro`,
   `capacidade_na_semana`. Não é estética: quem mantém isso fala português, e
   metade das regras são de negócio brasileiro.
4. **O motor de cálculo não conversa com o mundo.** `backend/app/services/` são
   funções puras, sem I/O. O copiloto de IA **lê** o que o motor calculou; nunca
   calcula nada por conta.
5. **Poluição visual é bug.** O dono do produto é sensível a isso. Na dúvida,
   tire em vez de acrescentar.

---

## Como rodar

```bash
# backend (SQLite local, semeia dados de demonstração sozinho)
cd backend
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload      # http://localhost:8000

# frontend
cd frontend
npm install
npm run dev
```

Logins de demonstração: `ceo@psa.com`, `rh@psa.com`, `ana@psa.com` — senha
`psa123` nos três. **Só existem no banco local.** A produção não tem nenhum
dado de demonstração: foi limpa de propósito.

```bash
cd backend && python -m pytest -q     # 209 testes, ~20s
```

---

## Arquitetura em cinco linhas

- **Backend:** FastAPI + SQLModel. 30 tabelas, ~119 rotas. Postgres (Supabase)
  em produção, SQLite no desenvolvimento.
- **Frontend:** React + Vite, CSS próprio.
- **Deploy:** Vercel em modo *services* — o frontend em `/` e a API em `/api`,
  mesma origem, então não existe CORS em lugar nenhum.
- **Schema:** migrações do Alembic. Detalhe em [MIGRACOES.md](MIGRACOES.md).
- **CI:** GitHub Actions roda testes, build e varredura de segredo a cada push.

### As duas camadas de permissão — leia antes de mexer em qualquer rota

Este é o ponto onde o projeto já sangrou: **22 vazamentos** de dado entre
consultores foram encontrados e corrigidos. Confundir as duas camadas recria o
problema.

| Camada | Guarda | Pergunta que responde |
| --- | --- | --- |
| Vertical | `exigir_ceo`, `exigir_gestao` | **qual rota** este perfil alcança |
| Horizontal | `exigir_dono`, `consultor_do_filtro` | **qual linha** dentro da rota |

`exigir_gestao` sozinho não protege nada de linha. Um consultor autenticado
chamando `GET /api/consultores/7/agenda` precisa de `exigir_dono` para não ler a
agenda do colega. E `consultor_do_filtro` **ignora** o `?consultor_id=` da query
quando quem pede é consultor — ele é forçado para si mesmo, porque confiar no
parâmetro é confiar no atacante.

Há ainda `sem_dinheiro(payload, usuario, campos)`, que tira taxa, custo, margem
e P&L da resposta quando quem pede não é o CEO. **O RH aprova horas e não vê
dinheiro.**

Tudo isso está em `backend/app/seguranca.py`, e
`backend/tests/test_isolamento_consultor.py` (19 testes) existe para travar a
regressão.

---

## Onde as coisas estão

```
backend/app/
  seguranca.py       ← as guardas de permissão. Comece por aqui.
  models.py          ← as 30 tabelas
  routers/           ← as rotas, uma por área
  services/          ← o motor determinístico (funções puras)
  main.py            ← middleware de autenticação e auditoria, montagem do SPA
backend/migrations/  ← Alembic
backend/tests/       ← 209 testes
frontend/src/
  pages/             ← uma por tela
  components/        ← Modal, DicaFlutuante, FalhaAoCarregar…
  styles.css         ← o sistema visual inteiro
docs/
  MIGRACOES.md            ← como mudar o schema sem perder dado
  PRONTIDAO.md            ← o que falta para produção, com as dívidas numeradas
  O-QUE-DEPENDE-DE-VOCE.md ← as três coisas que só o dono da conta faz
  GUIA.md                 ← manual de uso do produto
```

---

## Estado atual, sem maquiagem

**Funciona e está coberto por teste:** o ciclo completo de cliente até fatura
recebida; os três perfis (CEO, RH, Consultor) com isolamento verificado;
aprovação de horas, despesas e ausências; medição que **só** cobra hora
aprovada; migrações de banco; motor de capacidade, receita e EVM.

**Dívidas abertas, em ordem de urgência:**

- **D-3 — Sem backup.** O free tier do Supabase não faz backup automático.
  Bloqueante antes do primeiro dado real de cliente. Plano pago ou `pg_dump`
  agendado.
- **D-2 — A CI avisa, mas não trava o merge.** Falta marcar os checks como
  obrigatórios. É clique do dono da conta — está em `O-QUE-DEPENDE-DE-VOCE.md`.
- **D-4 — Rotacionar a senha do Postgres e a chave da Anthropic.** As duas
  circularam fora do código. O repositório está limpo (varrido, e o gitleaks
  agora olha a cada push), mas os valores precisam trocar. Também é do dono
  da conta.
- **Lição 2 — Multiunidade (filiais).** Parada de propósito. É trabalho de
  vários dias: schema, RBAC em toda rota e telas.
- **Onda 4** — portfólio executivo, construtor de relatórios, versão mobile.

---

## Duas armadilhas que já custaram caro

**Não confie no `create_all`.** Ele cria tabela que falta e **nunca altera
coluna que existe**. Mudou `models.py`? Gere a migração:

```bash
cd backend && python migrar.py nova "o que mudou"
```

A CI trava o merge se o modelo mudar sem migração — `test_migracoes.py` monta o
banco *pelas migrações* e compara com os modelos.

**Cuidado com teste que depende do calendário.** Já aconteceu: um teste lançava
hora na segunda e media a competência de *hoje*. Na semana que atravessa a
virada do mês, as horas caem de um lado e a competência do outro. Passava em 358
dias do ano. Use `segunda_estavel()` e `competencia_estavel()` do `conftest.py`
em qualquer teste que misture semana com competência mensal.

---

## O que eu quero que você faça

> **Substitua esta seção pela tarefa real antes de enviar.**

Antes de propor qualquer coisa:

1. Rode `cd backend && python -m pytest -q` e confirme os 209 passando. Se
   falhar algo no primeiro clone, me diga **antes** de mexer em código.
2. Leia `backend/app/seguranca.py` inteiro.
3. Leia `docs/PRONTIDAO.md`.

E ao trabalhar:

- Toda rota nova declara as **duas** camadas de permissão, ou justifica por que
  não precisa da horizontal.
- Toda mudança de comportamento vem com teste. Um teste que passa antes e
  depois da correção não está testando a correção.
- Mudou `models.py`, gere a migração no mesmo commit.
- Se discordar de algo aqui, diga — mas diga antes de escrever o código.
