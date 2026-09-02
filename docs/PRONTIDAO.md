# Readiness check — RunRate

Lista curta e **verificável** do que precisa ter resposta antes de publicar.
Cada item traz o comando que prova, não a opinião de quem escreveu.

Regra: **item sem comando não é item.** Se não dá para verificar em 30 segundos,
ou vira comando ou sai da lista.

Estado: `AUTOMÁTICO` = coberto por teste que trava o merge · `MANUAL` = alguém confere.

---

## 1. Autenticação

| # | Pergunta | Como provar | Estado |
|---|---|---|---|
| 1.1 | Toda rota `/api/*` exige token, exceto login e saúde? | `pytest -k test_api_exige_token` | AUTOMÁTICO |
| 1.2 | Senha é guardada como hash, nunca em texto? | `select senha_hash from usuario limit 1` — tem de vir `sal$hash` | MANUAL |
| 1.3 | Cada senha tem sal próprio? | `select count(distinct split_part(senha_hash,'$',1)), count(*) from usuario` — os dois números batem | MANUAL |
| 1.4 | Logout revoga o token de verdade? | `pytest -k test_logout_revoga_token` | AUTOMÁTICO |
| 1.5 | Desativar usuário mata a sessão viva? | `pytest -k test_usuario_desativado` | AUTOMÁTICO |

## 2. Dono do recurso

O RBAC de perfil responde *"esta rota é do seu perfil?"*. Estes itens respondem a
outra pergunta, que é a que vaza dado: *"esta linha é sua?"*

| # | Pergunta | Como provar | Estado |
|---|---|---|---|
| 2.1 | Consultor lê só o próprio dado? | `pytest backend/tests/test_isolamento_consultor.py` | AUTOMÁTICO |
| 2.2 | Consultor escreve só no próprio dado? | idem — cobre lançar hora, despesa e ausência de terceiro | AUTOMÁTICO |
| 2.3 | Filtro de listagem é forçado, não confiado? | o `consultor_id` da URL é ignorado para consultor (`consultor_do_filtro`) | AUTOMÁTICO |
| 2.4 | RH não vê dinheiro? | `pytest -k test_rh_nao_ve` — margem, receita e taxas fora do payload | AUTOMÁTICO |
| 2.5 | Rota nova tem guarda de dono? | **checklist de PR**: toda rota que aceite id ou `consultor_id` declara `exigir_dono` ou `consultor_do_filtro` | MANUAL |

## 3. Segredos

| # | Pergunta | Como provar | Estado |
|---|---|---|---|
| 3.1 | Nenhum segredo no repositório? | `git log -p \| grep -iE "sk-ant-\|postgresql://.*:.*@"` sem resultado | MANUAL |
| 3.2 | `.env` bloqueado no git **e** no pacote da Vercel? | está no `.gitignore` **e** no `.vercelignore` — a CLI não usa o `.gitignore` | MANUAL |
| 3.3 | Chave de API não sai em resposta de API? | `pytest -k test_consultor_nao_recebe_a_chave` | AUTOMÁTICO |
| 3.4 | Chave rotacionada depois de qualquer exposição? | data da última rotação anotada abaixo | MANUAL |
| 3.5 | Erro de servidor não devolve credencial? | `curl /api/saude` com banco fora: a mensagem traz host, nunca senha | MANUAL |

## 4. Migrations

| # | Pergunta | Como provar | Estado |
|---|---|---|---|
| 4.1 | Schema evolui sem perder dado? | **HOJE NÃO.** É `create_all`: cria, não migra. Ver dívida D-1 | ✗ |
| 4.2 | Existe caminho de volta? | idem — sem migration não há rollback de schema | ✗ |
| 4.3 | Enum novo tem `ALTER TYPE`? | Postgres não aceita valor de enum fora do tipo; hoje é manual (`migrar_perfis.py` é o precedente) | MANUAL |

## 5. Integração contínua

| # | Pergunta | Como provar | Estado |
|---|---|---|---|
| 5.1 | Teste roda sozinho a cada push? | `.github/workflows/testes.yml` — aba Actions do repositório | AUTOMÁTICO |
| 5.2 | Teste vermelho impede o merge? | mesmo workflow em `pull_request`; falta marcar como *required* em Settings → Branches | MANUAL |
| 5.3 | Build do frontend quebra a esteira? | job `frontend` do mesmo workflow | AUTOMÁTICO |

## 6. Dados de demonstração

| # | Pergunta | Como provar | Estado |
|---|---|---|---|
| 6.1 | O ambiente tem dado real ou só seed? | ✅ **limpo em 25/08/2026** — `select count(*) from cliente` = 0. Backup do seed em `docs/backup-antes-da-limpeza.json` | FEITO |
| 6.2 | Credencial de demonstração some da tela de login? | ✅ agora é **opt-in**: só aparece com `VITE_DEMO=1`. Deploy novo nasce sem ela, mesmo se ninguém configurar nada | FEITO |
| 6.3 | Senha `psa123` trocada em todas as contas? | ✅ nenhuma conta com `psa123` existe: as 9 de demonstração foram apagadas | FEITO |
| 6.4 | Contas de demonstração desativadas? | ✅ apagadas, não só desativadas. Resta 1 conta: `michel@mrpnachbar.com` (CEO) | FEITO |
| 6.5 | O ambiente está público? | se não deve estar: Vercel → Deployment Protection | MANUAL |

---

## Dívidas abertas

**D-1 — RESOLVIDA em 26/08/2026.** Alembic no lugar do `create_all`. A linha de
base retrata as 30 tabelas com os enums nativos do Postgres, a produção foi
marcada no topo depois de conferido que o schema batia com os modelos, e
`tests/test_migracoes.py` trava o merge quando alguém muda um modelo sem
escrever a migração. Fluxo em [MIGRACOES.md](MIGRACOES.md).

**D-2 — CI criada, falta tornar obrigatória.** `.github/workflows/testes.yml`
roda os 200 testes e o build a cada push e a cada PR. Falta **um clique do dono
do repositório**: GitHub → Settings → Branches → Add rule em `main` → marcar
`backend` e `frontend` como *required status checks*. Sem isso a esteira
avisa, mas não impede o merge.

**D-3 — Backup: coberto para uso interno, não para cliente.**
`backend/backup.py` grava o instantâneo completo e restaura. O ciclo inteiro foi
exercitado num schema temporário do Postgres — gravou, apagou, restaurou, e
acento, decimal, data e sequência voltaram idênticos (`conferir_backup.py`).

O que isto **não** é: point-in-time recovery. Backup de terça, acidente na
quinta, perde-se quarta e quinta. Depende de alguém rodar o comando. Antes de
dado de cliente que a consultoria não pode perder, plano pago do Supabase.

**D-4 — Segredos que circularam fora do código.** A senha do Postgres e a chave
da Anthropic passaram por conversa. O repositório está limpo (varrido, e agora
com gitleaks na CI a cada push), mas os dois valores devem ser rotacionados nos
painéis — só quem tem a conta faz isso. Passo a passo na seção "Rotação de
segredos" do DEPLOY.md.

---

## 7. Recuperação de acesso

| # | Pergunta | Como provar | Estado |
|---|---|---|---|
| 7.1 | O CEO consegue voltar se perder a senha? | ✅ `python -m app.redefinir_senha <email>` com o `DATABASE_URL` — documentado no DEPLOY.md, coberto por `tests/test_redefinir_senha.py` | FEITO |
| 7.2 | Mudar a política de hash tranca quem já tem senha? | ✅ não: o hash grava as próprias iterações e é regravado no primeiro login. `tests/test_hash_senha.py` | FEITO |
| 7.3 | Redefinir senha pelo CEO derruba as sessões abertas? | ✅ `revogar_sessoes_do_usuario` no PATCH `/usuarios/{id}` e no comando de terminal | FEITO |

---

## Rotações e verificações

| Data | O que | Quem |
|---|---|---|
| 25/08/2026 | limpeza do seed de produção (backup antes) | Claude |
| 25/08/2026 | `VITE_DEMO=0` e remoção das 9 contas de demonstração | Claude |
| 26/08/2026 | hash de senha passa a gravar as próprias iterações (migração automática no login) | Claude |
| 26/08/2026 | bloco de credenciais de demonstração vira opt-in (`VITE_DEMO=1`) | Claude |
| — | senha temporária do CEO → definitiva | **Michel, no 1º acesso** |
| — | senha do banco Supabase | pendente |
| — | chave da API Anthropic | pendente |

## Como usar

Antes de qualquer publicação com dado real, percorrer as seis seções e registrar
data e responsável. Item `✗` é bloqueador: ou vira verde, ou vira decisão
consciente e assinada de assumir o risco.
