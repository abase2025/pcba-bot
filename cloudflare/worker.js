/**
 * @Meupcba_bot no Cloudflare Workers — responde na hora, 24h por dia.
 *
 * Comandos (mande no Telegram):
 *   estudo      → contagem regressiva + dica + 5 questões inéditas comentadas
 *   discursiva  → uma discursiva com o que o corretor procura e resposta-modelo
 *   ajuda       → lista de comandos
 *
 * Configuração no painel do Cloudflare (veja cloudflare/GUIA.md):
 *   Secret  TELEGRAM_TOKEN   token do @BotFather
 *   Secret  WEBHOOK_SECRET   uma senha qualquer inventada por você (só letras e números)
 *   KV      ESTADO           espaço de armazenamento (guarda o que você já recebeu)
 *   Variável opcional CARGO  investigador | escrivao | ambos (padrão: ambos)
 *
 * As questões são lidas do repositório público abase2025/pcba-bot (pasta dados/),
 * então questões novas adicionadas lá passam a valer sozinhas.
 */

const REPO_RAW = "https://raw.githubusercontent.com/abase2025/pcba-bot/main/dados/";
const DATA_PROVA = "2026-12-06";
const POR_PEDIDO = 5;
const LETRAS = ["A", "B", "C", "D", "E"];

const AJUDA =
  "🤖 <b>Comandos do @Meupcba_bot</b>\n\n" +
  "• <b>estudo</b>: 5 questões inéditas comentadas\n" +
  "• <b>discursiva</b>: uma discursiva com correção\n" +
  "• <b>ajuda</b>: esta mensagem\n\n" +
  "Respondo na hora. Não envio nada sozinho: as questões só chegam quando você pede.";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1) Rota de configuração: liga o Telegram a este Worker (abra uma vez no navegador)
    if (url.pathname === "/configurar") {
      if (url.searchParams.get("chave") !== env.WEBHOOK_SECRET) {
        return new Response("Chave incorreta. Use /configurar?chave=SUA_WEBHOOK_SECRET", { status: 403 });
      }
      const destino = `${url.origin}/telegram`;
      const r = await tg(env, "setWebhook", {
        url: destino,
        secret_token: env.WEBHOOK_SECRET,
        allowed_updates: ["message"],
        drop_pending_updates: false,
      });
      const info = await tg(env, "getMe", {});
      const ok = r.ok ? "✅ Pronto!" : "❌ Erro";
      return new Response(
        `${ok} Bot @${info.result?.username ?? "?"} agora entrega as mensagens em ${destino}\n\n${JSON.stringify(r)}`,
        { headers: { "content-type": "text/plain; charset=utf-8" } },
      );
    }

    // 1b) Rota para desligar o webhook (volta a permitir o bot do GitHub)
    if (url.pathname === "/desligar") {
      if (url.searchParams.get("chave") !== env.WEBHOOK_SECRET) return new Response("Chave incorreta.", { status: 403 });
      const r = await tg(env, "deleteWebhook", { drop_pending_updates: false });
      return new Response(`${r.ok ? "✅ Webhook desligado." : "❌ Erro"} Para voltar ao bot do GitHub, reative o workflow "Responder pedidos".\n\n${JSON.stringify(r)}`,
        { headers: { "content-type": "text/plain; charset=utf-8" } });
    }

    // 2) Mensagens vindas do Telegram
    if (url.pathname === "/telegram" && request.method === "POST") {
      if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
        return new Response("proibido", { status: 403 });
      }
      const update = await request.json();
      ctx.waitUntil(atender(update, env).catch((e) => console.log("erro:", e?.stack || e)));
      return new Response("ok"); // responde logo ao Telegram; o envio continua em segundo plano
    }

    return new Response("@Meupcba_bot está no ar. 🚔", { headers: { "content-type": "text/plain; charset=utf-8" } });
  },
};

// ------------------------------------------------------------------ atendimento
async function atender(update, env) {
  const msg = update.message;
  if (!msg || msg.chat?.type !== "private") return;

  const estado = await lerEstado(env);
  if (update.update_id <= (estado.ultimo_update || 0)) return; // Telegram reenviou: ignora
  estado.ultimo_update = update.update_id;

  if (!estado.chat_id) estado.chat_id = String(msg.chat.id); // primeiro a escrever vira o dono
  if (String(msg.chat.id) !== estado.chat_id) return;

  const cmd = comando(msg.text || "");
  if (!cmd) {
    await salvarEstado(env, estado);
    return;
  }
  const chat = estado.chat_id;

  if (cmd === "ajuda") {
    await enviarTexto(env, chat, AJUDA);
  } else if (cmd === "discursiva") {
    const discursivas = await baixar("discursivas.json");
    const d = discursivas[(estado.prox_discursiva || 0) % discursivas.length];
    estado.prox_discursiva = (estado.prox_discursiva || 0) + 1;
    for (const m of msgsDiscursiva(d)) await enviarTexto(env, chat, m);
  } else {
    const [questoes, dicas] = await Promise.all([baixar("questoes.json"), baixar("dicas.json")]);
    const banco = filtrarPorCargo(questoes, env.CARGO || "ambos");
    const semente = update.update_id * 31 + (msg.message_id || 0);
    const { lote, aviso } = escolherIneditas(banco, estado, POR_PEDIDO, semente);
    if (aviso) await enviarTexto(env, chat, aviso);

    estado.pacotes = (estado.pacotes || 0) + 1;
    const restantes = Math.max(banco.length - new Set(estado.enviadas).size - lote.length, 0);
    const faltam = diasAte(DATA_PROVA);
    const dica = dicas[(estado.pacotes - 1) % dicas.length];
    await enviarTexto(
      env,
      chat,
      `📚 <b>Estudo nº ${estado.pacotes}: ${lote.length} questões inéditas</b> (restam ${restantes} inéditas no banco)\n\n` +
        (faltam > 0 ? `⏳ Faltam <b>${faltam} dias</b> para a prova.\n\n` : "") +
        `<b>Dica de prova</b>\n${esc(dica)}`,
    );
    for (let i = 0; i < lote.length; i++) await enviarQuestao(env, chat, i + 1, lote[i], estado.ciclo || 1);
    marcarEnviadas(estado, lote.map((q) => q.id));
  }
  await salvarEstado(env, estado);
}

// ------------------------------------------------------------------ estado (KV)
async function lerEstado(env) {
  const salvo = await env.ESTADO.get("estado", "json");
  if (salvo) return salvo;
  // Primeira execução: aproveita o histórico do bot antigo (GitHub) para não repetir questões
  try {
    const antigo = await baixar("estado.json");
    const chat = await fetch(REPO_RAW + "chat_id.txt").then((r) => (r.ok ? r.text() : ""));
    return { enviadas: antigo.enviadas || [], ciclo: antigo.ciclo || 1, pacotes: antigo.pacotes || 0,
             prox_discursiva: antigo.prox_discursiva || 0, chat_id: chat.trim() || null, ultimo_update: 0 };
  } catch {
    return { enviadas: [], ciclo: 1, pacotes: 0, prox_discursiva: 0, chat_id: null, ultimo_update: 0 };
  }
}

async function salvarEstado(env, estado) {
  await env.ESTADO.put("estado", JSON.stringify(estado));
}

function marcarEnviadas(estado, ids) {
  const vistos = new Set(estado.enviadas);
  for (const id of ids) if (!vistos.has(id)) estado.enviadas.push(id);
}

// ------------------------------------------------------------------ lógica de questões
function normalizar(t) {
  return t.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().trim().replace(/^\//, "");
}

export function comando(texto) {
  const t = normalizar(texto);
  if (t.includes("estudo") || t.includes("estudar")) return "questoes";
  if (t.includes("discursiva")) return "discursiva";
  if (t.startsWith("start") || ["ajuda", "help", "menu", "oi", "ola"].includes(t)) return "ajuda";
  return null;
}

function filtrarPorCargo(questoes, cargo) {
  cargo = normalizar(cargo);
  return cargo === "ambos" ? questoes : questoes.filter((q) => q.cargo === "ambos" || q.cargo === cargo);
}

function rng(semente) {
  // mulberry32: gerador simples e reproduzível
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function embaralhar(lista, semente) {
  const r = rng(semente);
  const a = [...lista];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function escolherIneditas(banco, estado, n, semente) {
  const enviadas = new Set(estado.enviadas);
  let novas = banco.filter((q) => !enviadas.has(q.id));
  let aviso = "";
  if (novas.length < n) {
    estado.ciclo = (estado.ciclo || 1) + 1;
    estado.enviadas = [];
    aviso = "🔁 Você já recebeu todas as questões do banco! Começando um ciclo de REVISÃO " +
            "(alternativas embaralhadas de novo). Peça mais questões novas no chat com o Claude.";
    const idsNovas = new Set(novas.map((q) => q.id));
    novas = [...novas, ...embaralhar(banco.filter((q) => !idsNovas.has(q.id)), semente + 1)];
  }
  novas = embaralhar(novas, semente);
  const lote = [];
  const usadas = new Set();
  for (const q of novas) {
    if (lote.length === n) break;
    if (!usadas.has(q.disciplina)) { lote.push(q); usadas.add(q.disciplina); }
  }
  for (const q of novas) {
    if (lote.length === n) break;
    if (!lote.includes(q)) lote.push(q);
  }
  return { lote, aviso };
}

function embaralharAlternativas(q, ciclo) {
  const correta = q.alternativas[LETRAS.indexOf(q.gabarito)];
  const alts = embaralhar(q.alternativas, q.id * 1000 + ciclo);
  return { alts, gab: LETRAS[alts.indexOf(correta)] };
}

// ------------------------------------------------------------------ mensagens
function esc(t) {
  return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function enviarQuestao(env, chat, n, q, ciclo) {
  const { alts, gab } = embaralharAlternativas(q, ciclo);
  const texto = [`<b>Questão ${n}</b> · ${esc(q.disciplina)}`, "", esc(q.enunciado), "",
    ...alts.map((a, i) => `<b>${LETRAS[i]})</b> ${esc(a)}`)].join("\n");
  await enviarTexto(env, chat, texto);

  let expl = `Gabarito ${gab}. ${q.como_resolver}`;
  if (expl.length > 200) expl = expl.slice(0, 197) + "...";
  await chamar(env, "sendPoll", {
    chat_id: chat,
    question: `Questão ${n} (${q.disciplina}): qual a sua resposta?`.slice(0, 300),
    options: LETRAS.map((l) => ({ text: l })),
    type: "quiz",
    correct_option_id: LETRAS.indexOf(gab),
    explanation: expl,
    is_anonymous: false,
  });

  await enviarTexto(env, chat,
    `📌 <b>Questão ${n} – comentário</b> (toque para revelar)\n\n` +
    `<tg-spoiler>✅ <b>Gabarito: ${gab}</b>\n\n` +
    `📖 <b>Por quê:</b> ${esc(q.comentario)}\n\n` +
    `🧠 <b>Como responder:</b> ${esc(q.como_resolver)}\n\n` +
    `🎲 <b>Se tiver que chutar:</b> ${esc(q.como_chutar)}</tg-spoiler>`);
}

function msgsDiscursiva(d) {
  const itens = d.padrao.map((p) => `• ${esc(p)}`).join("\n");
  return [
    `✍️ <b>DISCURSIVA · ${esc(d.tema)}</b>\n\n${esc(d.enunciado)}\n\n` +
      "⏱️ Reserve 60 minutos. Escreva à mão, de 10 a 25 linhas, em folha pautada – como na prova. " +
      "Só depois abra a correção abaixo e compare item por item.\n" +
      "Critérios AOCP: até 15 pontos de conhecimento técnico + até 10 de Língua Portuguesa por questão; " +
      "fugir do tema ou ficar fora de 10–25 linhas pode zerar.",
    `📋 <b>Correção – ${esc(d.tema)}</b> (toque para revelar)\n\n` +
      `<tg-spoiler>🎯 <b>O que o corretor procura:</b>\n${itens}\n\n` +
      `📝 <b>Resposta-modelo:</b>\n${esc(d.modelo)}\n\n💡 <b>Dica:</b> ${esc(d.dicas)}</tg-spoiler>`,
  ];
}

function diasAte(dataIso) {
  const agoraBahia = new Date(Date.now() - 3 * 3600 * 1000);
  const hoje = Date.UTC(agoraBahia.getUTCFullYear(), agoraBahia.getUTCMonth(), agoraBahia.getUTCDate());
  return Math.round((Date.parse(dataIso) - hoje) / 86400000);
}

// ------------------------------------------------------------------ Telegram e GitHub
async function baixar(nome) {
  const r = await fetch(REPO_RAW + nome, { cf: { cacheTtl: 300 } });
  if (!r.ok) throw new Error(`não consegui baixar ${nome}: ${r.status}`);
  return r.json();
}

async function tg(env, metodo, corpo) {
  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/${metodo}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(corpo),
  });
  return r.json();
}

async function chamar(env, metodo, corpo) {
  for (let tentativa = 0; tentativa < 3; tentativa++) {
    const r = await tg(env, metodo, corpo);
    if (r.ok) {
      await new Promise((ok) => setTimeout(ok, 350)); // ritmo seguro para o Telegram
      return r;
    }
    if (r.error_code === 429) {
      await new Promise((ok) => setTimeout(ok, ((r.parameters?.retry_after || 2) + 0.5) * 1000));
      continue;
    }
    console.log(`Telegram ${metodo}:`, JSON.stringify(r));
    return r;
  }
}

function enviarTexto(env, chat, texto) {
  return chamar(env, "sendMessage", { chat_id: chat, text: texto, parse_mode: "HTML",
                                      link_preview_options: { is_disabled: true } });
}
