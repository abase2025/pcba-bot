# @Meupcba_bot – questões da PC-BA 2026 no Telegram, quando você pede

**O bot só envia quando você pede.** Mande **estudo** para o @Meupcba_bot e ele responde em poucos minutos com 5 questões inéditas. Cada pacote traz:

1. **Abertura**: contagem regressiva para a prova (06/12/2026) e uma dica de estratégia de prova.
2. **5 questões** no estilo do Instituto AOCP (5 alternativas). Cada uma vem com:
   - uma **enquete-quiz** para você marcar a resposta e ver na hora se acertou;
   - um **comentário escondido** (toque para revelar) com gabarito, explicação baseada na lei, *como responder* e *como chutar com técnica*.

Mande **discursiva** para receber uma discursiva no formato da prova, com o que o corretor procura e uma resposta-modelo.

**Conteúdo**
- 86 questões objetivas inéditas, com o peso de cada matéria do edital. Inclui Legislação da Bahia (Leis 6.677/94 e 11.370/09, com situações que já caíram em provas anteriores), Atualidades até outubro de 2026, Penal, Processo Penal, Legislação Extravagante, Português, RLM, Informática, Constitucional, Administrativo, Medicina Legal, Igualdade Racial, Estatística, Arquivologia e Contabilidade.
- 8 discursivas com padrão de resposta.

**Comandos:** **estudo** envia 5 questões inéditas (que você ainda não recebeu); **discursiva** envia uma discursiva com correção; **ajuda** lista os comandos. O bot confere as mensagens a cada 5 minutos, então a resposta chega em cerca de 5 a 15 minutos. O envio automático diário está desligado.

Quando o banco acaba, ele recomeça como **ciclo de revisão**, com as alternativas embaralhadas.

**Você não precisa instalar nada.** O bot roda nos servidores do GitHub (GitHub Actions), de graça.

---

## Ativar o @Meupcba_bot (3 passos, sem instalar nada)

### 1. Fale com o bot
Abra **https://t.me/Meupcba_bot**, toque em **Iniciar** e mande um "oi".
É assim que o bot descobre para quem enviar. Você não precisa copiar nenhum número.

### 2. Cole o token no GitHub
Neste repositório: **Settings → Secrets and variables → Actions → New repository secret**

- **Name:** `TELEGRAM_TOKEN`
- **Secret:** o token que o @BotFather enviou quando você criou o @Meupcba_bot (parecido com `7123456789:AAH...`)

Esqueceu o token? No @BotFather, mande `/mybots` → escolha **@Meupcba_bot** → **API Token**.

### 3. Teste
Aba **Actions** → *Questões diárias PC-BA (@Meupcba_bot)* → **Run workflow**.
Se o GitHub pedir para habilitar o Actions, confirme.
Em menos de um minuto chega no seu Telegram a mensagem "✅ @Meupcba_bot configurado!", seguida das questões de hoje.

Faça o passo 3 em até **24 horas** depois do "oi" do passo 1. O Telegram só guarda as mensagens recentes. Se passar desse prazo, mande outro "oi" e rode de novo.
Depois do primeiro envio, o bot guarda o seu chat em `dados/chat_id.txt` e, a partir daí, roda sozinho todo dia às 06:47.

### Opcional (aba Variables)
- `CARGO` = `investigador`, `escrivao` ou `ambos` (padrão: `ambos`)
- `QUESTOES_POR_DIA` = `3` (pode subir para 5)
- `DATA_INICIO` = data do primeiro envio, `AAAA-MM-DD` (padrão: `2026-10-12`)

### Se algo der errado
Abra a execução na aba **Actions** e leia a mensagem:
- *Token inválido*: copie de novo o token no @BotFather e atualize o secret.
- *Ainda não sei para quem enviar*: mande "oi" ao @Meupcba_bot e rode de novo.
- *AVISO: este token é do bot @outro*: você colou o token de outro bot.

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
