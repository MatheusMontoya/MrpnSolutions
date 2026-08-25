# Como dar acesso a alguém no RunRate

## Antes de tudo: o RunRate não envia e-mail

Não existe "convite" que chega na caixa de entrada da pessoa. **O CEO cria a
conta definindo a senha e repassa por um canal que ele escolhe.** A pessoa entra
com essa senha e troca pela dela.

Isso é decisão de arquitetura, não esquecimento: mandar e-mail exige um serviço
externo (Resend, SendGrid), um domínio verificado e custo mensal. Enquanto a
equipe couber numa conversa, senha temporária resolve. Quando passar de umas 20
pessoas, aí vale.

---

## Passo a passo

### 1. Cadastre a pessoa como consultor (só se ela for lançar horas)

**Só para quem vai apontar hora.** RH e CEO pulam este passo.

Sidebar → **Consultores** → **Novo consultor**. Preencha nome, senioridade,
módulo SAP, custo/hora e venda/hora.

> Por que primeiro: no RunRate o *consultor* (a pessoa alocável, com taxa) e o
> *usuário* (a conta de login) são coisas separadas. A conta precisa apontar
> para o registro, senão o apontamento não sabe de quem são as horas. Se criar
> a conta antes, a pessoa não aparece na lista de vínculo.

### 2. Crie a conta de acesso

Sidebar → **Configurações** → seção **Usuários** → botão **Novo usuário**.

| Campo | O que colocar |
|---|---|
| Nome | como vai aparecer na interface e na auditoria |
| E-mail | é o login; precisa ser único |
| Senha | a temporária — mínimo 6 caracteres |
| Perfil | Consultor, RH ou CEO |
| Consultor vinculado | **só aparece se o perfil for Consultor** |

### 3. Escolha o perfil com cuidado

| Perfil | Vê | Não vê |
|---|---|---|
| **Consultor** | o próprio espaço: horas, despesas, ausências, agenda | nada de colega, nenhuma taxa |
| **RH** | equipe, utilização, agenda, fila de aprovações | receita, margem, taxas, propostas |
| **CEO** | tudo, inclusive financeiro e configurações | — |

Isso é garantido no servidor, não só na tela: o RunRate recusa (403) o que não
é do perfil, e tem 19 testes automáticos que travam qualquer regressão.

### 4. Mande a mensagem

Use o modelo da próxima seção. **Mande a senha por um canal diferente do
e-mail do login** — WhatsApp, presencial, ligação. Se a caixa de entrada da
pessoa estiver comprometida, quem invadiu não recebe login e senha juntos.

### 5. Confirme a troca de senha

A senha temporária foi digitada por você e passou por um canal de mensagem —
enquanto ela valer, existe uma cópia fora do sistema. Peça para a pessoa trocar
no primeiro acesso e confirme que ela trocou.

---

## Modelo de mensagem

> Oi, [NOME]!
>
> Seu acesso ao **RunRate** está criado — é onde a gente lança horas, despesas e
> acompanha os projetos.
>
> 🔗 **https://runrate-five.vercel.app**
> 👤 **Usuário:** [E-MAIL]
> 🔑 **Senha temporária:** [SENHA]
>
> **Troque a senha no primeiro acesso**, por favor: clique no seu avatar (canto
> superior direito) → Configurações → Trocar senha. Essa senha aí passou por
> mensagem, então ela não deve continuar valendo.
>
> O que você vai usar no dia a dia:
> • **Apontamento** — suas horas da semana. Lance com a descrição do que foi
>   feito e, na sexta, clique em *Enviar semana para aprovação*.
> • **Despesas** — reembolso, com comprovante.
> • **Ausências** — férias, folga, treinamento. Peça com antecedência: ausência
>   aprovada libera sua agenda e evita que te aloquem em cima.
> • **Agenda** — seu mês: onde você está alocado e quanto por dia.
>
> Guia completo: [link do docs/GUIA.md, se for compartilhar]
>
> Qualquer dúvida me chama.

### Variação para RH

Troque o bloco do dia a dia por:

> O que você vai usar:
> • **Aprovações** — sua tela principal. Chegam aqui as semanas de horas, as
>   despesas, os pedidos de ausência e as solicitações de alocação.
> • **Consultores** — a equipe e o mapa de utilização (quem está sobrecarregado,
>   quem está ocioso).
> • **Agenda** — o mês de cada pessoa.

---

## Depois que alguém sai da empresa

Configurações → Usuários → **Desativar**.

Não apague: desativar bloqueia o login, **derruba a sessão aberta na hora** e
preserva o histórico de apontamentos e a trilha de auditoria. Apagar levaria
junto o registro de horas que já foram faturadas.
