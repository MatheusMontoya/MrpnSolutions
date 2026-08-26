# Colocar o RunRate no ar — Supabase + GitHub + Vercel

O projeto vai para **um único projeto na Vercel**, com dois serviços no mesmo
domínio: o frontend Vite em `/` e a API FastAPI em `/api`. O banco é o Postgres
do Supabase. Sem CORS e sem duas URLs, porque tudo é mesma origem.

```
runrate.vercel.app
├── /            → serviço "frontend"  (frontend/, build Vite, servido pela CDN)
├── /api/*       → serviço "backend"   (backend/, FastAPI serverless)
└── DATABASE_URL → Postgres do Supabase (pooler)
```

Isso está declarado em [vercel.json](vercel.json). A Vercel entrega ao backend o
**path original** (`/api/auth/login` chega como `/api/auth/login`), que é
exatamente como os routers já estão prefixados — nada a mudar no código.

---

## 1. Supabase — criar o banco

1. Crie um projeto novo. A região do banco e a das funções da Vercel devem
   ficar próximas uma da outra — é o trajeto função↔banco que pesa, não o seu
   até o banco. Este ambiente usa `ca-central-1` com as funções no padrão
   `iad1`, que são vizinhas.
2. Guarde a senha do banco que ele gera. Ela não é recuperável depois.
3. Vá em **Connect** (ou Project Settings → Database) e copie a string de
   **Connection Pooling / Transaction mode**, a da **porta 6543**.

> **Use a do pooler, não a conexão direta da 5432.** Cada requisição serverless é
> um processo novo; com a conexão direta você esgota o limite de conexões do
> projeto em qualquer pico. O `database.py` já está configurado com `NullPool`
> justamente porque quem faz o pool é o Supavisor, do lado do Supabase.

A string parece com isto (a senha entra no lugar de `SUA_SENHA`):

```
postgresql://postgres.fxenxbrpsddmqupvxngn:SUA_SENHA@aws-0-ca-central-1.pooler.supabase.com:6543/postgres
```

## 2. Criar o schema e a carga inicial — uma vez

O banco nasce vazio. Este passo cria as 29 tabelas, os tipos enum e os dados de
demonstração. Rode **da sua máquina**, apontando para o Supabase:

```bash
cd backend
pip install -r requirements.txt
RUNRATE_SEM_DEMO=1 DATABASE_URL="postgresql://postgres.SEU_REF:SUA_SENHA@aws-0-ca-central-1.pooler.supabase.com:6543/postgres" python -m app.bootstrap
```

É idempotente — rodar de novo não duplica nada.

> **`RUNRATE_SEM_DEMO=1` não é opcional em produção.** Sem essa variável o
> bootstrap chama `seed_se_vazio()`, que semeia quando o banco está vazio — e
> num ambiente já limpo isso **reinjetaria os 3 projetos fictícios e 8 contas
> com senha `psa123`**. Com ela, o comando cria só o schema e o template
> Activate.

> **Por que isto não roda sozinho na subida do app?** Porque escreve. Em
> serverless, dois cold starts simultâneos correriam no `CREATE TYPE` dos 23
> enums e poderiam semear o banco duas vezes. Em SQLite local o preparo continua
> automático (um processo só, sem concorrência) — a lógica está em
> `backend/app/main.py`, na função `preparar_banco()`.

## 3. GitHub — subir o código

O repositório já está iniciado com o primeiro commit. Crie o repo vazio no
GitHub e:

```bash
git remote add origin https://github.com/SEU_USUARIO/runrate.git
git branch -M main
git push -u origin main
```

O [.gitignore](.gitignore) já mantém fora o `psa.db`, o `.env`, o `node_modules`
e o `dist`.

## 4. Vercel — importar e configurar

1. **Add New → Project** e importe o repositório do GitHub.
2. Não mexa em Build Command nem em Output Directory: o `vercel.json` em modo
   `services` manda em tudo, e esses campos vivem dentro de cada serviço.
3. Em **Settings → Environment Variables**, adicione (em Production, Preview e
   Development):

   | Variável | Valor |
   | --- | --- |
   | `DATABASE_URL` | a string do pooler do Supabase (porta 6543) |
   | `ANTHROPIC_API_KEY` | opcional — só se quiser o copiloto com IA |
   | `VITE_DEMO` | opcional — `1` **mostra** o bloco de credenciais de demonstração no login. Ausente ou qualquer outro valor: escondido, que é o certo para cliente. |

4. **Deploy.**

**Região das funções: mantenha o padrão (Washington, `iad1`).** O que importa
para a latência não é a distância até você, é a distância entre a função e o
banco — uma requisição faz várias consultas, e cada uma paga o trajeto. Com o
banco em `ca-central-1` (Montreal), a função em Washington fica a poucos
milissegundos dele. Mudar a função para São Paulo faria cada consulta cruzar o
continente e deixaria o app mais lento, não mais rápido.

Se um dia quiser o melhor dos dois, os dois têm de andar juntos: banco em
`sa-east-1` **e** funções em `gru1`.

## 5. Conferir se subiu certo

| Verificação | Esperado |
| --- | --- |
| `https://SEU-APP.vercel.app/` | tela de login com a aurora azul |
| Entrar com `ceo@psa.com` / `psa123` | vai para o Dashboard com os números |
| `https://SEU-APP.vercel.app/api/docs` | OpenAPI do FastAPI |
| Recarregar em `/projetos/1` | continua na tela (não dá 404) |
| Lançar horas, sair e voltar | o dado **persiste** — é o teste do Postgres |

O último é o que importa: era exatamente isso que o SQLite não conseguia
entregar em serverless.

---

## Mudou o schema? Migre antes do deploy

O schema é descrito por migrações do Alembic — `create_all` saiu de cena porque
não altera coluna existente. Todo deploy que mexe em `app/models.py` precisa de:

```bash
cd backend
python migrar.py sql   # revise o SQL
python migrar.py       # aplique
```

A CI trava o merge se um modelo mudar sem a migração correspondente. O fluxo
inteiro está em [docs/MIGRACOES.md](docs/MIGRACOES.md).

---

## Rotação de segredos

Estes passos são **seus** — envolvem digitar credencial nos painéis, e é a sua
conta. O repositório já é varrido por gitleaks a cada push, então o que entrar
no código é pego; o que precisa de rotação é o que circulou fora dele.

### Senha do Postgres

1. Supabase → **Project Settings → Database → Reset database password**.
2. Copie a nova. Monte a URL com `cd backend && python configurar_conexao.py`
   (ele percent-encoda os caracteres reservados, que foi o que quebrou da
   primeira vez, e apaga os arquivos temporários no fim).
3. Vercel → **Settings → Environment Variables → DATABASE_URL** → cole a nova em
   Production, Preview e Development.
4. **Redeploy** — variável de ambiente só vale a partir do próximo build.
5. Confira: `curl https://runrate-five.vercel.app/api/saude` deve responder
   `{"app":"ok","banco":"ok"}`.
6. Apague `backend/senha.txt` e `backend/conexao.txt` se ainda existirem.

### Chave da Anthropic

1. console.anthropic.com → **API Keys** → crie uma nova, revogue a antiga.
2. Vercel → `ANTHROPIC_API_KEY` → cole a nova → **Redeploy**.
3. Ou, se a chave estiver na tela: **Configurações → Copiloto** dentro do app.

---

## Antes de virar ambiente de cliente

1. **Não defina `VITE_DEMO`.** O bloco de credenciais é opt-in: só aparece com
   `VITE_DEMO=1`. Se ele estiver na tela de um cliente, é porque alguém ligou.
2. **`RUNRATE_SEM_DEMO=1` ao rodar o bootstrap.** Sem isso o `seed_se_vazio()`
   injeta 3 projetos fictícios e 8 logins com senha `psa123` em banco vazio —
   inclusive depois de uma limpeza.
3. Ative **Deployment Protection** na Vercel se o ambiente não deve ser público.

---

## Perdeu a senha do CEO

Dentro do produto quem redefine senha é o CEO, em **Configurações → Usuários**.
Só que o próprio CEO não tem a quem pedir: não há autoatendimento e não existe
outro gestor. A saída é pelo servidor, e exige o `DATABASE_URL` — ou seja, só
quem já é dono do ambiente consegue.

```bash
cd backend
DATABASE_URL="postgresql://...pooler.supabase.com:6543/postgres" \
    python -m app.redefinir_senha michel@mrpnachbar.com
```

Ele pede a senha nova no terminal (sem ecoar e sem deixar rastro no histórico),
encerra todas as sessões abertas daquela conta e reativa o usuário se ele estiver
desativado — perder a senha e ter sido invadido se parecem muito.

---

## Política de senha

O hash é PBKDF2-SHA256 e **grava o próprio número de iterações**
(`pbkdf2_sha256$600000$salt$hash`). Isso existe porque o formato antigo não
gravava: quando o custo subiu de 200k para 600k, toda senha já cadastrada
deixaria de conferir de uma vez — o CEO incluído.

Hash antigo continua valendo e é **regravado no padrão atual no primeiro login
bem-sucedido**, sem pedir nada a quem entrou. Para subir o custo de novo, basta
mudar `RUNRATE_PBKDF2_ITER`: a migração acontece sozinha, login a login.

## Limitações conhecidas deste alvo

- **Cold start.** A primeira requisição depois de um período parado paga o custo
  de subir o Python. Em uso contínuo não aparece.
- **Enums são tipos nativos no Postgres.** Adicionar valor a um enum do Python
  no futuro exige `ALTER TYPE ... ADD VALUE` no banco: o `create_all` cria, mas
  não migra. Quando isso virar rotina, vale adotar Alembic.
- **Sem tarefa agendada.** Funções serverless respondem a requisição; não há
  processo de fundo. Nada no produto depende disso hoje.

Se o cold start incomodar, o mesmo repositório roda sem alteração num container
(Render, Railway, Fly) — lá o FastAPI serve o frontend de `frontend/dist`, que é
como ele já funciona na sua máquina.
