# O que só você pode fazer

Três coisas ficaram de fora do que eu consigo executar, e não é por falta de
tentativa: as três exigem digitar credencial num painel que é da sua conta.
Eu não entro com senha, chave de API ou token em campo nenhum — nem quando você
autoriza, porque o risco não é a autorização, é o segredo passar por mim.

Tudo em volta delas já está pronto: os comandos existem, a documentação existe,
e a CI já vigia o que dá para vigiar sozinha.

---

## 1. Travar o merge quando o teste quebra (5 cliques)

A esteira já roda a cada push e a cada PR. Falta dizer ao GitHub que **um teste
vermelho impede o merge** — sem isso ela avisa, mas não segura nada.

1. https://github.com/MatheusMontoya/MrpnSolutions/settings/rules
2. **New ruleset → New branch ruleset**
3. Nome: `main protegida` · Enforcement status: **Active**
4. Target branches: **Add target → Include default branch**
5. Marque **Require status checks to pass** e adicione os três:
   `backend`, `segredos`, `frontend`
6. Marque também **Block force pushes**
7. **Create**

Se preferir a linha de comando, com o [gh](https://cli.github.com) instalado e
autenticado (`gh auth login` — a autenticação é sua, no navegador):

```bash
gh api -X POST repos/MatheusMontoya/MrpnSolutions/rulesets \
  -H "Accept: application/vnd.github+json" \
  -f name='main protegida' -f target='branch' -f enforcement='active' \
  -F 'conditions[ref_name][include][]=~DEFAULT_BRANCH' \
  -F 'rules[][type]=non_fast_forward' \
  -F 'rules[][type]=required_status_checks' \
  -F 'rules[][parameters][strict_required_status_checks_policy]=true' \
  -F 'rules[][parameters][required_status_checks][][context]=backend' \
  -F 'rules[][parameters][required_status_checks][][context]=segredos' \
  -F 'rules[][parameters][required_status_checks][][context]=frontend'
```

**Como conferir que pegou:** abra um PR com um teste quebrado de propósito. O
botão de merge tem que ficar cinza.

---

## 2. Rotacionar a senha do Postgres

Ela circulou por conversa. O repositório está limpo — varri o histórico inteiro
e agora o gitleaks olha a cada push —, mas o que passou fora do código só sai de
circulação trocando.

1. Supabase → **Project Settings → Database → Reset database password**
2. Monte a URL nova sem digitar nada arriscado à mão:
   ```bash
   cd backend
   python configurar_conexao.py
   ```
   (ele percent-encoda os caracteres reservados — foi o que quebrou da primeira
   vez, quando o `#` da senha virou início de fragmento — e apaga os arquivos
   temporários no fim)
3. Vercel → **Settings → Environment Variables → `DATABASE_URL`** → cole a nova
   em **Production, Preview e Development**
4. **Redeploy.** Variável de ambiente só passa a valer no build seguinte.
5. Confira:
   ```bash
   curl https://runrate-five.vercel.app/api/saude
   ```
   Tem que responder `{"app":"ok","banco":"ok"}`.
6. Atualize também `backend/.env`, senão os comandos de migração param de
   conectar daqui.

### Enquanto isso: dois arquivos com a senha em texto puro

`backend/senha.txt` e `backend/conexao.txt` continuam na sua máquina com a senha
atual dentro. O `configurar_conexao.py` deveria tê-los apagado e não apagou.

Estão no `.gitignore` e nunca entraram no repositório — conferi o histórico
inteiro —, então não vazaram. Mas não têm motivo para continuar existindo:

```bash
rm backend/senha.txt backend/conexao.txt
```

Deixei para você porque apagar é irreversível e a senha está lá dentro.

---

## 3. Rotacionar a chave da Anthropic

Mesmo motivo.

1. https://console.anthropic.com/settings/keys → **Create Key**
2. Revogue a antiga
3. A chave nova entra em **um** dos dois lugares:
   - Vercel → `ANTHROPIC_API_KEY` → **Redeploy**; ou
   - dentro do app: **Configurações → Copiloto**
4. Confira no app: **Copiloto** → faça uma pergunta. Se a resposta vier com
   `ia_generativa: true`, pegou. Sem chave válida ele degrada para a resposta
   determinística do motor em vez de dar erro — o que é bom, mas também quer
   dizer que a tela não denuncia sozinha uma chave errada.

---

## Ainda em aberto, mas não é permissão — é escopo

**D-3, backup.** O free tier do Supabase não faz backup automático. Agora que
existe migração isso pesa mais: `python migrar.py voltar` desfaz a *estrutura*,
nunca o dado que a estrutura levou embora. Antes de dado real de cliente, plano
pago (ou um `pg_dump` agendado).

**Lição 2, multiunidade.** Continua parada onde você deixou. É trabalho de
vários dias — schema, RBAC em toda rota, e as telas —, não um ajuste. Quando
quiser, é só dizer.

**O repositório é público.** Não tem segredo dentro dele, mas qualquer pessoa lê
a lógica de negócio da consultoria. Se a intenção era privado:
**Settings → General → Danger Zone → Change visibility.**
