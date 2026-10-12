# Bot PC-BA 2026 – questões diárias no Telegram

Todo dia, às 06:47 (horário da Bahia), o bot manda no seu Telegram:

1. **Abertura**: contagem regressiva para a prova (06/12/2026) e uma dica de estratégia de prova.
2. **3 questões** no estilo do Instituto AOCP (5 alternativas). Cada uma vem com:
   - uma **enquete-quiz** para você marcar a resposta e ver na hora se acertou;
   - um **comentário escondido** (toque para revelar) com gabarito, explicação baseada na lei, *como responder* e *como chutar com técnica*.
3. **Aos sábados**: uma **discursiva da semana**, com enunciado no formato da prova, o que o corretor procura e uma resposta-modelo.

**Conteúdo**
- 86 questões objetivas inéditas, com o peso de cada matéria do edital. Inclui Legislação da Bahia (Leis 6.677/94 e 11.370/09, com situações que já caíram em provas anteriores), Atualidades até outubro de 2026, Penal, Processo Penal, Legislação Extravagante, Português, RLM, Informática, Constitucional, Administrativo, Medicina Legal, Igualdade Racial, Estatística, Arquivologia e Contabilidade.
- 8 discursivas, uma por sábado até a prova.

Quando o banco acaba, ele recomeça como **ciclo de revisão**, com as alternativas embaralhadas.

**Você não precisa instalar nada.** O bot roda nos servidores do GitHub (GitHub Actions), de graça.

---

## Passo 1 – Criar o bot no Telegram (2 min)

1. No Telegram, abra **@BotFather** e mande `/newbot`.
2. Escolha um nome (ex.: `Meu PC-BA`) e um usuário terminado em `bot` (ex.: `meupcba_questoes_bot`).
3. Ele responde com um **token** parecido com `7123456789:AAH...`. Guarde: é a senha do bot, não compartilhe.
4. Abra o seu bot pelo link que o BotFather manda, toque em **Iniciar** e mande um "oi".

## Passo 2 – Descobrir o seu chat id (pelo navegador)

No navegador, abra o endereço abaixo trocando `SEU_TOKEN` pelo token do passo 1:

`https://api.telegram.org/botSEU_TOKEN/getUpdates`

Procure o trecho `"chat":{"id":123456789`. Esse número é o seu chat id.
Se aparecer `"result":[]`, mande outro "oi" ao bot e recarregue a página.

## Passo 3 – Colar os dois dados no GitHub

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Secret |
| --- | --- |
| `TELEGRAM_TOKEN` | o token do passo 1 |
| `TELEGRAM_CHAT_ID` | o número do passo 2 |

Opcional, na aba **Variables**:
- `CARGO` = `investigador`, `escrivao` ou `ambos` (padrão: `ambos`). Investigador recebe Contabilidade; escrivão recebe Arquivologia.
- `QUESTOES_POR_DIA` = `3` (pode subir para 5).
- `DATA_INICIO` = data do primeiro envio, no formato `AAAA-MM-DD` (padrão: `2026-10-12`).

## Passo 4 – Testar

Vá na aba **Actions** → *Questões diárias PC-BA* → **Run workflow**. Em menos de um minuto as questões chegam no Telegram.
Se o GitHub pedir para habilitar o Actions, clique em *I understand… enable*.

Pronto. A partir daí o bot roda sozinho todo dia. Na manhã de 06/12 ele manda a mensagem de boa prova e para.

---

## Para quem quiser rodar no próprio computador (opcional)

Requer Python 3.9+, sem bibliotecas extras.

```bash
export TELEGRAM_TOKEN=...  TELEGRAM_CHAT_ID=...  CARGO=investigador
python enviar.py                 # envia o lote de hoje
python enviar.py --simular       # só mostra na tela
python enviar.py --dia 7         # envia o lote do 7º dia
python enviar.py --discursiva 3  # envia a discursiva nº 3
```

## Adicionar questões

- **Objetivas**: `dados/questoes.json`. Campos: `id`, `disciplina`, `cargo` (`ambos`, `investigador` ou `escrivao`), `enunciado`, 5 `alternativas`, `gabarito`, `comentario`, `como_resolver`, `como_chutar`.
- **Discursivas**: `dados/discursivas.json`. Campos: `tema`, `enunciado`, `padrao`, `modelo`, `dicas`.
- **Dicas do dia**: `dados/dicas.json`.

## Importante

- As questões são **inéditas**, escritas no estilo da banca com base no edital (SAEB nº 02/2026) e em provas anteriores. Não são cópias de provas oficiais.
- Leis mudam: confira sempre o texto atualizado. Atualidades foi escrita em 12/10/2026; a PEC da Segurança Pública, por exemplo, ainda tramitava no Senado nessa data.
- Os temas das discursivas de 2022 não foram divulgados publicamente. As propostas seguem os temas mais prováveis apontados para 2026.
- "Dica de chute" ajuda quando você não sabe a resposta, mas **não substitui o estudo**. Nenhum método garante aprovação.
