#!/usr/bin/env python3
"""Mostra o seu chat id. Antes, mande qualquer mensagem (ex.: /start) para o seu bot no Telegram.

Uso:  TELEGRAM_TOKEN=123:ABC python descobrir_chat_id.py
"""
import json
import os
import sys
import urllib.request

token = os.getenv("TELEGRAM_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 else "")
if not token:
    sys.exit("Informe o token: TELEGRAM_TOKEN=seu_token python descobrir_chat_id.py")

with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30) as r:
    dados = json.loads(r.read())

chats = {}
for upd in dados.get("result", []):
    msg = upd.get("message") or upd.get("channel_post") or {}
    chat = msg.get("chat")
    if chat:
        chats[chat["id"]] = chat.get("first_name") or chat.get("title") or ""

if not chats:
    print("Nenhuma mensagem encontrada. Abra o seu bot no Telegram, toque em Iniciar / mande 'oi' e rode de novo.")
for cid, nome in chats.items():
    print(f"TELEGRAM_CHAT_ID = {cid}   ({nome})")
