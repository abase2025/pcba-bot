#!/usr/bin/env python3
"""
Atende pedidos feitos no Telegram ao @Meupcba_bot.

Roda a cada 5 minutos (GitHub Actions). Lê as mensagens novas e:
  • "questões" (ou "questoes", "/questoes") → envia 5 questões que você ainda não recebeu
  • "discursiva" → envia uma discursiva com correção
  • "/start" ou "ajuda" → explica os comandos

Só responde ao seu chat (dados/chat_id.txt ou TELEGRAM_CHAT_ID).
"""
import os
import random
import sys
import unicodedata

import enviar as bot

POR_PEDIDO = int(os.getenv("QUESTOES_POR_PEDIDO", "5"))

AJUDA = ("🤖 <b>Comandos do @Meupcba_bot</b>\n\n"
         "• <b>questões</b>: 5 questões inéditas comentadas\n"
         "• <b>discursiva</b>: uma discursiva com correção\n"
         "• <b>ajuda</b>: esta mensagem\n\n"
         "Respondo em alguns minutos (confiro as mensagens a cada 5 min). "
         "Todo dia às 06:47 chegam 3 questões automáticas e, aos sábados, uma discursiva.")


def normalizar(txt):
    sem_acento = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    return sem_acento.lower().strip().lstrip("/")


def comando(txt):
    t = normalizar(txt)
    if "questo" in t or "questao" in t:
        return "questoes"
    if "discursiva" in t:
        return "discursiva"
    if t.startswith("start") or t in ("ajuda", "help", "menu", "oi", "ola"):
        return "ajuda"
    return None


def escolher_ineditas(banco, estado, n, semente):
    """Sorteia n questões ainda não enviadas. Esgotado o banco, começa novo ciclo de revisão."""
    enviadas = set(estado.get("enviadas", []))
    novas = [q for q in banco if q["id"] not in enviadas]
    aviso = ""
    if len(novas) < n:
        estado["ciclo"] = estado.get("ciclo", 1) + 1
        estado["enviadas"] = []
        aviso = ("🔁 Você já recebeu todas as questões do banco! Começando um ciclo de REVISÃO "
                 "(alternativas embaralhadas de novo). Peça mais questões novas no chat com o Claude.")
        complemento = [q for q in banco if q["id"] not in {x["id"] for x in novas}]
        random.Random(semente).shuffle(complemento)
        novas = novas + complemento
    rng = random.Random(semente)
    rng.shuffle(novas)
    # evita repetir disciplina dentro do mesmo pacote, quando possível
    escolhidas, usadas = [], set()
    for q in novas:
        if q["disciplina"] not in usadas:
            escolhidas.append(q)
            usadas.add(q["disciplina"])
        if len(escolhidas) == n:
            break
    for q in novas:
        if len(escolhidas) == n:
            break
        if q not in escolhidas:
            escolhidas.append(q)
    return escolhidas, aviso


def main():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        sys.exit("Defina o secret TELEGRAM_TOKEN.")
    meu_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not meu_chat and bot.ARQ_CHAT.exists():
        meu_chat = bot.ARQ_CHAT.read_text().strip()

    estado = bot.ler_estado()
    offset = estado.get("offset", 0)
    dados = bot.api_get(token, f"getUpdates?offset={offset}&timeout=0&allowed_updates=%5B%22message%22%5D")
    pedidos = []
    recebidas = len(dados.get("result", []))
    for upd in dados.get("result", []):
        offset = max(offset, upd["update_id"] + 1)
        msg = upd.get("message") or {}
        chat = msg.get("chat") or {}
        if chat.get("type") != "private":
            continue
        if not meu_chat:  # primeira vez: adota o chat de quem escreveu
            meu_chat = str(chat["id"])
            bot.ARQ_CHAT.write_text(meu_chat + "\n")
        if str(chat["id"]) != meu_chat:
            continue
        cmd = comando(msg.get("text", ""))
        if cmd:
            pedidos.append((cmd, msg.get("message_id", 0)))
    estado["offset"] = offset

    if not pedidos:
        bot.salvar_estado(estado)
        print(f"Nenhum pedido novo ({recebidas} mensagens lidas).")
        if recebidas:
            bot.registrar(f"responder: {recebidas} mensagens lidas, nenhum pedido reconhecido")
        return

    tg = bot.Telegram(token, meu_chat)
    questoes, _ = bot.carregar()
    banco = bot.filtrar_por_cargo(questoes, os.getenv("CARGO", "ambos"))
    discursivas = bot.carregar_discursivas()
    feitos = []
    for cmd, mid in pedidos[-3:]:  # no máximo 3 pedidos por rodada
        if cmd == "ajuda":
            tg.texto(AJUDA)
        elif cmd == "discursiva":
            d = discursivas[estado.get("prox_discursiva", 0) % len(discursivas)]
            estado["prox_discursiva"] = estado.get("prox_discursiva", 0) + 1
            for m in bot.msgs_discursiva(d):
                tg.texto(m)
        else:
            lote, aviso = escolher_ineditas(banco, estado, POR_PEDIDO, semente=offset * 31 + mid)
            if aviso:
                tg.texto(aviso)
            restantes = len(banco) - len(set(estado.get("enviadas", []))) - len(lote)
            tg.texto(f"📚 <b>{len(lote)} questões inéditas</b> saindo agora! "
                     f"(ainda restam {max(restantes, 0)} inéditas no banco)")
            ciclo = estado.get("ciclo", 1)
            for i, q in enumerate(lote, start=1):
                bot.enviar_questao(tg, i, q, ciclo)
            bot.marcar_enviadas(estado, [q["id"] for q in lote])
        feitos.append(cmd)
        bot.salvar_estado(estado)
    bot.salvar_estado(estado)
    bot.registrar(f"responder OK: {recebidas} mensagens lidas; atendidos: {', '.join(feitos)}")
    print("Atendidos:", ", ".join(feitos))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as fim:
        if fim.code not in (None, 0):
            bot.registrar(f"ERRO (responder): {fim.code}")
        raise
    except Exception as erro:  # noqa: BLE001
        bot.registrar(f"ERRO inesperado (responder): {type(erro).__name__}: {erro}")
        raise
