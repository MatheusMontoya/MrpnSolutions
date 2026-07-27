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

1. Crie um projeto novo. **Escolha a região `South America (São Paulo)`**: o
   banco perto do usuário é o que mais pesa na latência percebida.
2. Guarde a senha do banco que ele gera. Ela não é recuperável depois.
3. Vá em **Connect** (ou Project Settings → Database) e copie a string de
   **Connection Pooling / Transaction mode**, a da **porta 6543**.

> **Use a do pooler, não a conexão direta da 5432.** Cada requisição serverless é
> um processo novo; com a conexão direta você esgota o limite de conexões do
> projeto em qualquer pico. O `database.py` já está configurado com `NullPool`
> justamente porque quem faz o pool é o Supavisor, do lado do Supabase.

A string parece com isto (a senha entra no lugar de `SUA_SENHA`):

```
postgresql://postgres.abcdefgh:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
```

## 2. Criar o schema e a carga inicial — uma vez

O banco nasce vazio. Este passo cria as 29 tabelas, os tipos enum e os dados de
demonstração. Rode **da sua máquina**, apontando para o Supabase:

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL="postgresql://postgres.SEU_REF:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres" python -m app.bootstrap
```

É idempotente — rodar de novo não duplica nada.

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
   | `VITE_DEMO` | opcional — `0` esconde o bloco de credenciais no login |

4. **Deploy.**

Depois do primeiro deploy, em **Settings → Functions**, mude a região para
**São Paulo (gru1)**. Por padrão a Vercel roda em Washington, e cada consulta
faria a viagem EUA↔Brasil até o Supabase.

## 5. Conferir se subiu certo

| Verificação | Esperado |
| --- | --- |
| `https://SEU-APP.vercel.app/` | tela de login com a aurora azul |
| Entrar com `gestor@psa.com` / `psa123` | vai para o Dashboard com os números |
| `https://SEU-APP.vercel.app/api/docs` | OpenAPI do FastAPI |
| Recarregar em `/projetos/1` | continua na tela (não dá 404) |
| Lançar horas, sair e voltar | o dado **persiste** — é o teste do Postgres |

O último é o que importa: era exatamente isso que o SQLite não conseguia
entregar em serverless.

---

## Antes de virar ambiente de cliente

O deploy acima é uma **demonstração**, e por isso mostra as credenciais na tela.
Para receber dado real de cliente:

1. `VITE_DEMO=0` nas variáveis da Vercel — o bloco de credenciais sai do login.
2. Troque as senhas dos usuários semeados (todos nascem com `psa123`) em
   **Configurações → Usuários**, ou apague os de demonstração e crie os reais.
3. Ative **Deployment Protection** na Vercel se o ambiente não deve ser público.

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
