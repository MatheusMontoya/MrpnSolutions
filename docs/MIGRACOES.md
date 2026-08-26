# Migrações de banco — como mudar o schema sem perder dado

Até 26/08/2026 o schema nascia de `SQLModel.metadata.create_all()`. Isso cria
tabela que falta, mas **nunca altera coluna que já existe**. Enquanto o banco
era descartável, tudo bem. Com dado real dentro, o primeiro "adicionar um campo"
não teria caminho seguro — era a dívida D-1 do [PRONTIDAO.md](PRONTIDAO.md).

Agora o schema é descrito por migrações do Alembic, em
`backend/migrations/versions/`. A primeira revisão é a **linha de base**: o
retrato do schema no dia em que o Alembic entrou.

---

## Os comandos

Todos rodam de `backend/`, e todos carregam o `backend/.env` sozinhos — você
nunca precisa colar a senha do Postgres na linha de comando.

| Comando | O que faz |
| --- | --- |
| `python migrar.py` | aplica o que falta (`upgrade head`) |
| `python migrar.py estado` | em que revisão o banco está |
| `python migrar.py historico` | a fila de revisões |
| `python migrar.py sql` | imprime o SQL **sem** aplicar — revise antes da produção |
| `python migrar.py nova "o que mudou"` | escreve a migração a partir da diferença dos modelos |
| `python migrar.py marcar` | marca como aplicado sem executar (schema já existe) |
| `python migrar.py voltar` | desfaz a última revisão |

### Porta 5432, não 6543

O Supabase expõe o mesmo pooler em duas portas: **6543** em modo transação (o
que a aplicação usa — muitas conexões curtas) e **5432** em modo sessão. DDL
precisa de recursos de sessão, então os comandos acima trocam a porta sozinhos
quando reconhecem uma URL do pooler. Isso também resolve um problema prático:
a 6543 costuma estar bloqueada em rede corporativa.

Para apontar para outro lugar, exporte `RUNRATE_DDL_URL`.

---

## Mudar um campo, do começo ao fim

```bash
# 1. mexa no modelo em backend/app/models.py

# 2. gere a migração a partir da diferença
cd backend
python migrar.py nova "adiciona centro de custo no consultor"

# 3. LEIA o arquivo gerado em migrations/versions/.
#    O autogenerate acerta quase sempre; ele não sabe é o que fazer com o dado
#    que já está lá. Coluna NOT NULL numa tabela cheia precisa de server_default
#    ou de um UPDATE no meio da migração.

# 4. confirme que modelo e migração batem
python -m pytest tests/test_migracoes.py -q

# 5. veja o SQL que vai rodar na produção
python migrar.py sql

# 6. aplique
python migrar.py
```

---

## O que impede a dívida de voltar

`backend/tests/test_migracoes.py` monta um banco **pelas migrações** (não pelo
`create_all`) e pergunta ao autogenerate se sobrou diferença. Sobrou = alguém
mudou um modelo e não escreveu a migração, e a CI trava o merge.

Os outros ~200 testes continuam usando `create_all` porque é rápido — e é
justamente por serem cegos a isso que este existe.

Ele roda em SQLite, então cobre estrutura (tabela, coluna, índice, nulidade),
não o tipo nativo de enum do Postgres. Para esse:

```bash
cd backend
python conferir_migracoes.py
```

Esse cria um schema temporário no Postgres de verdade, aplica `upgrade head`
nele, compara, e derruba o schema. **Nunca encosta no `public`.**

---

## A linha de base foi gerada como?

`backend/gerar_linha_de_base.py`, uma vez só. O problema que ele resolve: o
autogenerate compara os modelos com o banco apontado, então contra a produção
(que já tinha o schema) sairia uma migração vazia, e contra SQLite os 23 enums
sairiam como VARCHAR. A saída foi um schema temporário e vazio dentro do próprio
Postgres — banco vazio, dialeto certo.

A produção, que já tinha as 30 tabelas, foi **marcada** no topo
(`python migrar.py marcar`) em vez de migrada: rodar o upgrade lá tentaria criar
tabela que já existe. Antes de marcar, foi confirmado que o schema de lá batia
exatamente com os modelos — marcar sem conferir só esconderia a diferença.

---

## Quando o downgrade não serve

`python migrar.py voltar` desfaz a estrutura, não o dado. Um `drop_column` volta
com a coluna vazia. Antes de reverter qualquer coisa em produção, tenha o dump
na mão — e veja a dívida **D-3** do PRONTIDAO.md: o free tier do Supabase não
faz backup automático.
