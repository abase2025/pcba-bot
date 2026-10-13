# Migrar o @Meupcba_bot para o Cloudflare Workers

Com o Cloudflare, o bot responde **na hora, 24 horas por dia**, sem as trocas de turno nem os atrasos do GitHub. É grátis: o plano gratuito aceita 100 mil pedidos por dia.

**Tempo:** cerca de 15 a 20 minutos, tudo pelo navegador.
**O que continua igual:** os comandos (**estudo**, **discursiva**, **ajuda**) e as questões, que continuam sendo lidas deste repositório. O bot também lembra quais questões você já recebeu no GitHub, então nada se repete.

> As telas do Cloudflare mudam de vez em quando. Se algum nome de botão estiver diferente, procure a opção parecida ou me pergunte no chat.

---

## 1. Criar a conta
1. Acesse **https://dash.cloudflare.com/sign-up** e crie a conta com seu e-mail.
2. Confirme o e-mail. Não é preciso cadastrar cartão nem site.

## 2. Criar o Worker
1. No menu da esquerda, abra **Workers e Pages** (*Workers & Pages*).
2. Clique em **Criar** (*Create*) → **Criar Worker** (*Create Worker* / *Start with Hello World*).
3. Dê o nome **`meupcba-bot`** e clique em **Implantar** (*Deploy*).
4. Anote o endereço que aparece, parecido com `https://meupcba-bot.SEU-NOME.workers.dev`.

## 3. Colar o código
1. No Worker, clique em **Editar código** (*Edit code*).
2. Apague todo o código de exemplo.
3. Abra o arquivo [`cloudflare/worker.js`](worker.js) deste repositório, clique em **Raw**, copie tudo e cole no editor.
4. Clique em **Implantar** (*Deploy*).

## 4. Criar o armazenamento (KV)
É onde o bot guarda quais questões você já recebeu.
1. No menu da esquerda: **Armazenamento e bancos de dados** (*Storage & Databases*) → **KV** → **Criar** (*Create namespace*).
2. Nome: **`pcba-estado`** → criar.
3. Volte ao Worker `meupcba-bot` → **Configurações** (*Settings*) → **Vinculações** (*Bindings*) → **Adicionar** (*Add*) → **Namespace KV**.
   - **Nome da variável:** `ESTADO` (exatamente assim, em maiúsculas)
   - **Namespace:** `pcba-estado`
   - Salve / implante.

## 5. Guardar o token e a senha
Ainda em **Configurações → Variáveis e segredos** (*Variables and Secrets*) → **Adicionar** (*Add*):

| Tipo | Nome | Valor |
| --- | --- | --- |
| **Segredo** (*Secret*) | `TELEGRAM_TOKEN` | o token do @BotFather |
| **Segredo** (*Secret*) | `WEBHOOK_SECRET` | uma senha inventada por você, só letras e números (ex.: `estudoPCBA2026xyz`) |
| Texto (opcional) | `CARGO` | `investigador`, `escrivao` ou `ambos` |

Clique em **Implantar** (*Deploy*).

## 6. Desligar o bot antigo do GitHub
Os dois não podem funcionar ao mesmo tempo.
- No GitHub: **Actions** → **Responder pedidos (@Meupcba_bot)** → botão **⋯** → **Disable workflow**.
- Ou peça no chat com o Claude: "desliga o bot do GitHub".

## 7. Ligar o Telegram ao Cloudflare
No navegador, abra o endereço abaixo, trocando o seu endereço e a sua senha:

```
https://meupcba-bot.SEU-NOME.workers.dev/configurar?chave=SUA_WEBHOOK_SECRET
```

Deve aparecer **"✅ Pronto! Bot @Meupcba_bot agora entrega as mensagens em…"**.

## 8. Testar
Mande **estudo** para o @Meupcba_bot. As questões chegam em poucos segundos. 🎉

---

## Se algo der errado
- **"Chave incorreta"** no passo 7: a senha no endereço está diferente da salva em `WEBHOOK_SECRET`.
- **O bot não responde:** no Worker, abra **Logs** (*Observability*) e mande "estudo" de novo; os erros aparecem ali. Confira se a vinculação se chama exatamente `ESTADO`.
- **Erro sobre `questoes.json`:** o repositório precisa continuar **público**, porque o Worker lê as questões dele.

## Voltar para o GitHub
1. Abra `https://meupcba-bot.SEU-NOME.workers.dev/desligar?chave=SUA_WEBHOOK_SECRET`
2. No GitHub, reative o workflow **Responder pedidos** (*Enable workflow*).
