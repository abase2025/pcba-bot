#!/usr/bin/env python3
"""
Bot PC-BA 2026 — envia todos os dias, no Telegram, questões comentadas
(estilo Instituto AOCP) com dica de resolução e dica de chute.

Sem dependências externas: só Python 3.9+.

Variáveis de ambiente:
  TELEGRAM_TOKEN      token do bot (BotFather)               [obrigatório]
  TELEGRAM_CHAT_ID    seu chat id (opcional: se faltar, o bot descobre sozinho
                      a partir da última mensagem que você mandou ao @Meupcba_bot
                      e guarda em dados/chat_id.txt)
  BOT_USUARIO         usuário esperado do bot                 (padrão: Meupcba_bot)
  CARGO               investigador | escrivao | ambos         (padrão: ambos)
  QUESTOES_POR_DIA    quantas questões por dia                (padrão: 3)
  DATA_INICIO         AAAA-MM-DD do 1º envio                  (padrão: 2026-10-12)
  DATA_PROVA          AAAA-MM-DD da prova                     (padrão: 2026-12-06)
  DIA_DISCURSIVA      dia da semana da discursiva, 0=seg ... 6=dom (padrão: 5 = sábado)

Uso:
  python enviar.py              envia o lote de hoje
  python enviar.py --simular    só mostra no terminal o que seria enviado
  python enviar.py --dia 5      força o lote do 5º dia (1 = primeiro)
  python enviar.py --discursiva 3   envia só a discursiva nº 3 (teste)
"""
import argparse
import datetime as dt
import html
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
FUSO_BAHIA = dt.timezone(dt.timedelta(hours=-3))
LETRAS = "ABCDE"


# ---------------------------------------------------------------- dados
def carregar():
    ler = lambda nome: json.loads((BASE / "dados" / nome).read_text(encoding="utf-8"))
    return ler("questoes.json"), ler("dicas.json")


def carregar_discursivas():
    return json.loads((BASE / "dados" / "discursivas.json").read_text(encoding="utf-8"))


def discursiva_do_dia(inicio, hoje, dia_semana, discursivas):
    """Retorna a discursiva da semana se hoje for o dia escolhido; senão None."""
    if hoje.weekday() != dia_semana or hoje < inicio:
        return None
    n = sum(1 for k in range((hoje - inicio).days + 1)
            if (inicio + dt.timedelta(days=k)).weekday() == dia_semana)
    return discursivas[(n - 1) % len(discursivas)]


def filtrar_por_cargo(questoes, cargo):
    cargo = (cargo or "ambos").lower().replace("ã", "a")
    if cargo == "ambos":
        return list(questoes)
    return [q for q in questoes if q["cargo"] in ("ambos", cargo)]


def ordenar_misturando(questoes, semente=2026):
    """Ordem fixa e reproduzível que evita duas questões seguidas da mesma disciplina."""
    rng = random.Random(semente)
    restantes = sorted(questoes, key=lambda q: q["id"])
    rng.shuffle(restantes)
    ordem, ultima = [], None
    while restantes:
        idx = next((i for i, q in enumerate(restantes) if q["disciplina"] != ultima), 0)
        q = restantes.pop(idx)
        ordem.append(q)
        ultima = q["disciplina"]
    return ordem


def embaralhar_alternativas(q, ciclo):
    """Embaralha as alternativas (gabarito equilibrado e diferente a cada ciclo de revisão)."""
    rng = random.Random(q["id"] * 1000 + ciclo)
    correta = q["alternativas"][LETRAS.index(q["gabarito"])]
    alts = list(q["alternativas"])
    rng.shuffle(alts)
    return alts, LETRAS[alts.index(correta)]


def lote_do_dia(questoes, dia, por_dia):
    """dia começa em 1. Depois que o banco acaba, recomeça como REVISÃO."""
    total = len(questoes)
    lote = []
    for k in range(por_dia):
        pos = (dia - 1) * por_dia + k
        ciclo = pos // total + 1
        lote.append((questoes[pos % total], ciclo))
    return lote


# ---------------------------------------------------------------- mensagens
def e(txt):
    return html.escape(str(txt), quote=False)


def msg_abertura(dia, hoje, data_prova, dicas, ciclo):
    faltam = (data_prova - hoje).days
    contagem = (f"⏳ Faltam <b>{faltam} dias</b> para a prova (06/12)." if faltam > 1
                else "⏳ <b>A prova é amanhã!</b> Revise, durma cedo e confie no seu preparo." if faltam == 1
                else "")
    modo = "🔁 <b>Ciclo de REVISÃO</b> – as questões voltam com as alternativas embaralhadas." if ciclo > 1 else ""
    dica = dicas[(dia - 1) % len(dicas)]
    partes = [f"🚔 <b>PC-BA 2026 · Dia {dia}</b>", contagem, modo, f"<b>Dica de prova do dia</b>\n{e(dica)}"]
    return "\n\n".join(p for p in partes if p)


def msg_questao(n, q, alts):
    linhas = [f"<b>Questão {n}</b> · {e(q['disciplina'])}", "", e(q["enunciado"]), ""]
    linhas += [f"<b>{L})</b> {e(a)}" for L, a in zip(LETRAS, alts)]
    return "\n".join(linhas)


def msg_comentario(n, q, gab):
    return (
        f"📌 <b>Questão {n} – comentário</b> (toque para revelar)\n\n"
        f"<tg-spoiler>✅ <b>Gabarito: {gab}</b>\n\n"
        f"📖 <b>Por quê:</b> {e(q['comentario'])}\n\n"
        f"🧠 <b>Como responder:</b> {e(q['como_resolver'])}\n\n"
        f"🎲 <b>Se tiver que chutar:</b> {e(q['como_chutar'])}</tg-spoiler>"
    )


def msgs_discursiva(d):
    itens = "\n".join(f"• {e(p)}" for p in d["padrao"])
    proposta = (
        f"✍️ <b>DISCURSIVA DA SEMANA · {e(d['tema'])}</b>\n\n{e(d['enunciado'])}\n\n"
        "⏱️ Reserve 60 minutos. Escreva à mão, de 10 a 25 linhas, em folha pautada – como na prova. "
        "Só depois abra a correção abaixo e compare item por item.\n"
        "Critérios AOCP: até 15 pontos de conhecimento técnico + até 10 de Língua Portuguesa por questão; "
        "fugir do tema ou ficar fora de 10–25 linhas pode zerar."
    )
    correcao = (
        f"📋 <b>Correção – {e(d['tema'])}</b> (toque para revelar)\n\n"
        f"<tg-spoiler>🎯 <b>O que o corretor procura:</b>\n{itens}\n\n"
        f"📝 <b>Resposta-modelo:</b>\n{e(d['modelo'])}\n\n"
        f"💡 <b>Dica:</b> {e(d['dicas'])}</tg-spoiler>"
    )
    return [proposta, correcao]


def explicacao_enquete(q, gab):
    txt = f"Gabarito {gab}. {q['como_resolver']}"
    return txt if len(txt) <= 200 else txt[:197] + "..."


# ---------------------------------------------------------------- telegram
class Telegram:
    def __init__(self, token, chat_id, simular=False):
        self.url = f"https://api.telegram.org/bot{token}/"
        self.chat_id = chat_id
        self.simular = simular

    def _post(self, metodo, dados):
        if self.simular:
            print(f"\n===== {metodo} =====")
            for k, v in dados.items():
                if k != "chat_id":
                    print(f"[{k}] {v}")
            return
        corpo = urllib.parse.urlencode(
            {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in dados.items()}
        ).encode()
        for tentativa in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(self.url + metodo, data=corpo), timeout=30) as r:
                    resp = json.loads(r.read())
                    if not resp.get("ok"):
                        raise RuntimeError(resp)
                    time.sleep(1.1)  # respeita limite de envio do Telegram
                    return resp
            except urllib.error.HTTPError as erro:
                detalhe = erro.read().decode(errors="ignore")
                if erro.code == 429 and tentativa < 2:
                    time.sleep(5)
                    continue
                sys.exit(f"Erro do Telegram em {metodo}: {erro.code} {detalhe}")

    def texto(self, t):
        self._post("sendMessage", {"chat_id": self.chat_id, "text": t, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"})

    def quiz(self, pergunta, gab, explicacao):
        self._post("sendPoll", {
            "chat_id": self.chat_id, "question": pergunta, "options": list(LETRAS),
            "type": "quiz", "correct_option_id": LETRAS.index(gab),
            "explanation": explicacao, "is_anonymous": "false",
        })


# ---------------------------------------------------------------- configuração do chat
ARQ_CHAT = BASE / "dados" / "chat_id.txt"


def api_get(token, metodo):
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{metodo}", timeout=30) as r:
        return json.loads(r.read())


def conferir_bot(token, esperado):
    try:
        info = api_get(token, "getMe")["result"]
    except urllib.error.HTTPError as erro:
        sys.exit(f"Token inválido ({erro.code}). Confira o secret TELEGRAM_TOKEN copiado do @BotFather.")
    usuario = info.get("username", "")
    if esperado and usuario.lower() != esperado.lower():
        print(f"AVISO: este token é do bot @{usuario}, não de @{esperado}.")
    else:
        print(f"Bot conferido: @{usuario}")


def descobrir_chat(token):
    """Pega o chat privado mais recente que mandou mensagem ao bot."""
    chats = []
    for upd in api_get(token, "getUpdates").get("result", []):
        msg = upd.get("message") or upd.get("edited_message") or {}
        chat = msg.get("chat") or {}
        if chat.get("type") == "private":
            chats.append(chat["id"])
    return str(chats[-1]) if chats else ""


def resolver_chat_id(token, simular):
    cid = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if cid or simular:
        return cid
    if ARQ_CHAT.exists() and ARQ_CHAT.read_text().strip():
        return ARQ_CHAT.read_text().strip()
    cid = descobrir_chat(token)
    if not cid:
        usuario = os.getenv("BOT_USUARIO", "Meupcba_bot")
        sys.exit(f"Ainda não sei para quem enviar. Abra https://t.me/{usuario}, toque em Iniciar, "
                 "mande um 'oi' e rode de novo em até 24 horas.")
    ARQ_CHAT.write_text(cid + "\n")
    print(f"Chat descoberto e salvo em dados/chat_id.txt: {cid}")
    os.environ["PCBA_CHAT_NOVO"] = "1"
    return cid


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simular", action="store_true", help="não envia, só mostra")
    ap.add_argument("--dia", type=int, help="força o número do dia (1 = primeiro)")
    ap.add_argument("--discursiva", type=int, help="envia só a discursiva de número N (teste)")
    args = ap.parse_args()

    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not args.simular:
        if not token:
            sys.exit("Defina o secret TELEGRAM_TOKEN com o token do @BotFather (veja o README).")
        conferir_bot(token, os.getenv("BOT_USUARIO", "Meupcba_bot"))
    chat_id = resolver_chat_id(token, args.simular)

    por_dia = int(os.getenv("QUESTOES_POR_DIA", "3"))
    inicio = dt.date.fromisoformat(os.getenv("DATA_INICIO", "2026-10-12"))
    data_prova = dt.date.fromisoformat(os.getenv("DATA_PROVA", "2026-12-06"))
    hoje = dt.datetime.now(FUSO_BAHIA).date()

    tg = Telegram(token, chat_id, simular=args.simular)
    if os.getenv("PCBA_CHAT_NOVO"):
        tg.texto("✅ <b>@Meupcba_bot configurado!</b>\n\nA partir de agora você recebe aqui, todo dia às 06:47, "
                 "3 questões comentadas da PC-BA e, aos sábados, uma discursiva. Bons estudos! 🚔")

    if args.discursiva:
        lista = carregar_discursivas()
        for m in msgs_discursiva(lista[(args.discursiva - 1) % len(lista)]):
            tg.texto(m)
        return

    dia = args.dia or (hoje - inicio).days + 1
    if dia < 1:
        print(f"Ainda não começou: o primeiro envio é em {inicio:%d/%m/%Y}.")
        return

    if hoje >= data_prova and not args.dia:
        if hoje == data_prova:
            tg.texto("🚔 <b>Hoje é o dia!</b>\n\nLeia cada enunciado com calma, circule as palavras NÃO/EXCETO, "
                     "elimine alternativas antes de chutar e nunca deixe questão em branco. Boa prova! 💪")
        return

    questoes, dicas = carregar()
    banco = ordenar_misturando(filtrar_por_cargo(questoes, os.getenv("CARGO", "ambos")))
    lote = lote_do_dia(banco, dia, por_dia)

    tg.texto(msg_abertura(dia, hoje, data_prova, dicas, lote[0][1]))
    for i, (q, ciclo) in enumerate(lote, start=1):
        alts, gab = embaralhar_alternativas(q, ciclo)
        tg.texto(msg_questao(i, q, alts))
        tg.quiz(f"Questão {i} ({q['disciplina']}): qual a sua resposta?", gab, explicacao_enquete(q, gab))
        tg.texto(msg_comentario(i, q, gab))

    disc = discursiva_do_dia(inicio, hoje, int(os.getenv("DIA_DISCURSIVA", "5")), carregar_discursivas())
    if disc and not args.dia:
        for m in msgs_discursiva(disc):
            tg.texto(m)
    print(f"Dia {dia}: {len(lote)} questões enviadas" + (f" + discursiva ({disc['tema']})." if disc and not args.dia else "."))


if __name__ == "__main__":
    main()
