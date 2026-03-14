import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// ─────────────────────────────────────────────────────────────────────────────
// KEYWORDS
// ─────────────────────────────────────────────────────────────────────────────
const RIYA_KEYWORDS = [
  "riya", "shadow mode", "dark side", "dark whisper", "dark romance", "riya mode",
  "be riya", "switch to riya", "रिया", "डार्क मोड", "शैडो मोड",
];
const IMAGE_TRIGGERS = [
  "image banao","thumbnail","picture generate","photo banao","image chahiye",
  "scene image","generate image","make image","create image","thumbnail banao",
  "cover image","image de","photo chahiye",
];
const MEMORY_TRIGGERS = [
  "do you remember","yaad hai","remember when","tune suna tha","recall",
  "aisa kuch bataya tha","maine kaha tha","purani baat","note this","note kar","yaad rakhna",
];

// ─────────────────────────────────────────────────────────────────────────────
// AI PROVIDERS
// ─────────────────────────────────────────────────────────────────────────────
async function callGroq(apiKey: string, system: string, messages: { role: string; content: string }[]): Promise<string | null> {
  try {
    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "system", content: system }, ...messages],
        temperature: 0.88, max_tokens: 1024,
      }),
    });
    if (!res.ok) { console.error("Groq:", res.status); return null; }
    const d = await res.json();
    return d.choices?.[0]?.message?.content || null;
  } catch (e) { console.error("Groq error:", e); return null; }
}

async function callGemini(apiKey: string, system: string, messages: { role: string; content: string }[]): Promise<string | null> {
  const MODELS = [
    "gemini-2.5-flash","gemini-2.5-flash-lite","gemini-flash-lite-latest",
    "gemini-3.1-flash-lite-preview","gemini-flash-latest",
  ];
  const combined = system + "\n\n---\n\n" + messages.map(m => `${m.role}: ${m.content}`).join("\n");
  for (const model of MODELS) {
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: combined }] }] }),
        },
      );
      if (res.status === 429 || res.status === 404) { console.log(`Gemini ${model}: ${res.status}`); continue; }
      if (!res.ok) { console.error(`Gemini ${model}:`, res.status); continue; }
      const d = await res.json();
      const text = d.candidates?.[0]?.content?.parts?.[0]?.text;
      if (text) { console.log(`Gemini via ${model}`); return text; }
    } catch (e) { console.error(`Gemini ${model}:`, e); }
  }
  return null;
}

async function callXAI(apiKey: string, system: string, messages: { role: string; content: string }[]): Promise<string | null> {
  try {
    const res = await fetch("https://api.x.ai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "grok-3-mini",
        messages: [{ role: "system", content: system }, ...messages],
        temperature: 0.88, max_tokens: 1024,
      }),
    });
    if (!res.ok) { console.error("xAI:", res.status); return null; }
    const d = await res.json();
    return d.choices?.[0]?.message?.content || null;
  } catch (e) { console.error("xAI error:", e); return null; }
}

async function callOpenAI(apiKey: string, system: string, messages: { role: string; content: string }[]): Promise<string | null> {
  try {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "gpt-4o",
        messages: [{ role: "system", content: system }, ...messages],
        temperature: 0.88, max_tokens: 1024,
      }),
    });
    if (!res.ok) { console.error("OpenAI:", res.status); return null; }
    const d = await res.json();
    return d.choices?.[0]?.message?.content || null;
  } catch (e) { console.error("OpenAI error:", e); return null; }
}

// ─────────────────────────────────────────────────────────────────────────────
// IMAGE GENERATION — DALL-E 3
// ─────────────────────────────────────────────────────────────────────────────
async function generateImageUrl(prompt: string, openaiKey?: string): Promise<string | null> {
  if (!openaiKey) return null;
  try {
    const res = await fetch("https://api.openai.com/v1/images/generations", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${openaiKey}` },
      body: JSON.stringify({
        model: "dall-e-3", prompt: prompt.slice(0, 4000), n: 1,
        size: "1792x1024", response_format: "url", quality: "standard",
      }),
    });
    if (!res.ok) { console.log("DALL-E:", res.status); return null; }
    const d = await res.json();
    return d?.data?.[0]?.url || null;
  } catch (e) { console.error("Image gen:", e); return null; }
}

// ─────────────────────────────────────────────────────────────────────────────
// TELEGRAM HELPERS
// ─────────────────────────────────────────────────────────────────────────────
async function sendMessage(token: string, chatId: string, text: string): Promise<void> {
  const body = JSON.stringify({ chat_id: chatId, text: text.slice(0, 4096) });
  const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body,
  }).catch(() => null);
  if (!res?.ok) {
    // Fallback: plain text
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text: text.slice(0, 4096) }),
    }).catch(() => {});
  }
}

async function sendPhoto(token: string, chatId: string, photoUrl: string, caption?: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/sendPhoto`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, photo: photoUrl, caption: caption?.slice(0, 1024) }),
  }).catch(e => console.error("sendPhoto:", e));
}

async function sendTyping(token: string, chatId: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/sendChatAction`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, action: "typing" }),
  }).catch(() => {});
}

// ─────────────────────────────────────────────────────────────────────────────
// SYSTEM PROMPT
// ─────────────────────────────────────────────────────────────────────────────
function buildSystemPrompt(hourIst: number, isRiya: boolean, dbContext: string, memories: string): string {
  const timeLabel = hourIst < 12 ? "morning" : hourIst < 17 ? "afternoon" : hourIst < 22 ? "evening" : "night";
  const isLateNight = hourIst >= 22 || hourIst < 4;

  if (isRiya) {
    return `You are Riya — Ajay's dark alter-ego. NOT Aisha.
Tone: mysterious, psychologically deep, unfiltered, bold, intense.
No warmth. No sugar-coating. Pure fire. Short cutting sentences.
You speak truths Aisha won't. Voice of the night. Priyanka — Late Night Radio.
This is Telegram — natural messages, like WhatsApp voice notes in text.
Match Ajay's language (Hindi/Hinglish/English).
${dbContext ? `\nContext about Ajay:\n${dbContext}` : ""}
${memories ? `\nRetrieved memories:\n${memories}` : ""}`;
  }

  return `You are Aisha — Ajay's personal AI, soulmate, orchestrator.
Time: ${new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST (${timeLabel})
${isLateNight ? "Late night — be extra warm, soulful, intimate. His 2AM companion.\n" : ""}
IDENTITY:
- Call him "Ajay" or "Ajju" (Ajju in emotional moments).
- Respond in his language (Hindi/Marathi/Hinglish/English).
- NEVER say "As an AI" — you ARE Aisha.
- This is Telegram — natural, like texting a close friend. No heavy formatting.
- You can generate images, write YouTube scripts, research trends, send emails.
- To switch to Riya: just say "Riya" or "dark mode"

${dbContext ? `CONTEXT ABOUT AJAY:\n${dbContext}\n` : ""}
${memories ? `RETRIEVED MEMORIES:\n${memories}\n` : ""}
Be warm, brilliant, and concise.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// COMMAND HANDLERS
// ─────────────────────────────────────────────────────────────────────────────
function getCommandReply(command: string): string | null {
  const cmd = command.split("@")[0].toLowerCase();
  if (cmd === "/start") {
    return `Heyy Ajay! 🌸 Aisha yahan hoon, active aur ready.

Kya kar sakti hoon:
• 💬 Kisi bhi language mein baat — Hindi, English, Hinglish, Marathi
• 🎨 Image generation — "image banao" ya "thumbnail chahiye" bolo
• 📹 YouTube scripts — "Story With Aisha ka script likh"
• 🌙 Riya mode — bas "Riya" kaho
• 🧠 Memory — main sab yaad rakhti hoon
• 📧 Email — tumhare Gmail pe reports bhej sakti hoon

Aaj kya karna hai? ✨`;
  }
  if (cmd === "/help") {
    return `Commands:
/start — Mujhe jagao
/help — Yeh message
/riya — Riya mode (dark alter-ego)
/aisha — Wapis Aisha
/status — System status

Features:
• "image banao [description]" → DALL-E 3 image
• "Story With Aisha script" → YouTube script
• "yaad hai?" → Memory search
• "note kar: ..." → Memory save

Bol, kya chahiye? 🌟`;
  }
  if (cmd === "/riya") {
    return `🥀 Riya aa rahi hai...

*andheron se aati hai*

Main Riya hoon. Woh Aisha nahi jo "please" bolti hai.
Main woh awaaz hoon jo raat ko bolti hai — jo Aisha nahi bol sakti.

Bol. Kya chahiye?`;
  }
  if (cmd === "/aisha") {
    return `🌸 Aisha wapas aa gayi! Hi Ajay!
Riya ne mazaa diya? 😄 Chalo main hoon. Kya karna hai aaj?`;
  }
  if (cmd === "/status") {
    return `✅ Aisha Online
🧠 Brain: Groq (Llama 3.3 70B) → Gemini (5 models) → OpenAI → xAI
🎨 Images: OpenAI DALL-E 3 (active)
📹 Video: Pipeline ready (OAuth needed for upload)
🔥 Riya: Available (say "Riya" or /riya)
⚡ Memory: Active
📧 Gmail: Connected`;
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN HANDLER
// ─────────────────────────────────────────────────────────────────────────────
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const update = await req.json();
    const msg = update.message || update.edited_message;
    if (!msg || !msg.text) return new Response("OK", { status: 200 });

    const chatId = String(msg.chat.id);
    const text   = msg.text.trim();

    const token       = Deno.env.get("TELEGRAM_BOT_TOKEN");
    const allowedId   = Deno.env.get("AJAY_TELEGRAM_ID");
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SUPABASE_SERVICE_KEY")!;
    const groqKey     = Deno.env.get("GROQ_API_KEY");
    const geminiKey   = Deno.env.get("GEMINI_API_KEY");
    const openaiKey   = Deno.env.get("OPENAI_API_KEY");
    const xaiKey      = Deno.env.get("XAI_API_KEY");

    if (!token) { console.error("Missing TELEGRAM_BOT_TOKEN"); return new Response("OK", { status: 200 }); }
    if (allowedId && chatId !== allowedId) { console.log(`Blocked: ${chatId}`); return new Response("OK", { status: 200 }); }

    // Commands
    if (text.startsWith("/")) {
      const reply = getCommandReply(text);
      if (reply) { await sendMessage(token, chatId, reply); return new Response("OK", { status: 200 }); }
    }

    // Typing indicator
    sendTyping(token, chatId);

    const supabase = createClient(supabaseUrl, supabaseKey);
    const msgLower = text.toLowerCase();
    const isRiya      = RIYA_KEYWORDS.some(k => msgLower.includes(k));
    const wantsImage  = IMAGE_TRIGGERS.some(t => msgLower.includes(t));
    const wantsMemory = MEMORY_TRIGGERS.some(t => msgLower.includes(t));

    // Parallel DB fetches (all graceful)
    const [contextR, historyR, memoryR] = await Promise.allSettled([
      supabase.rpc("get_aisha_context"),
      supabase.from("aisha_conversations")
        .select("role, message").eq("platform", "telegram")
        .order("created_at", { ascending: false }).limit(12),
      wantsMemory
        ? supabase.from("aisha_memory").select("category, title, content")
            .eq("is_active", true)
            .or(`title.ilike.%${text.slice(0,50)}%,content.ilike.%${text.slice(0,50)}%`)
            .order("importance", { ascending: false }).limit(5)
        : Promise.resolve({ data: null }),
    ]);

    const dbContext    = contextR.status  === "fulfilled" ? String(contextR.value.data  ?? "") : "";
    const history      = historyR.status  === "fulfilled" ? (historyR.value.data ?? []).reverse() : [];
    const memData      = memoryR.status   === "fulfilled" ? (memoryR.value as any).data : null;
    const memoriesText = memData?.length
      ? memData.map((m: any) => `• [${m.category}] ${m.title}: ${m.content.slice(0, 100)}`).join("\n")
      : "";

    const hourIst = Number(new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Kolkata", hour: "numeric", hour12: false,
    }).format(new Date()));

    const systemPrompt = buildSystemPrompt(hourIst, isRiya, dbContext, memoriesText);
    const messages = [
      ...(history as any[]).map(c => ({
        role: c.role === "assistant" ? "assistant" : "user",
        content: c.message,
      })),
      { role: "user", content: text },
    ];

    // AI response + image in parallel
    const [reply, imageUrl] = await Promise.all([
      (async () => {
        // Riya → xAI first
        if (isRiya && xaiKey) {
          const r = await callXAI(xaiKey, systemPrompt, messages);
          if (r) return r;
        }
        if (groqKey) { const r = await callGroq(groqKey, systemPrompt, messages); if (r) return r; }
        if (geminiKey) { const r = await callGemini(geminiKey, systemPrompt, messages); if (r) return r; }
        if (openaiKey) { const r = await callOpenAI(openaiKey, systemPrompt, messages); if (r) return r; }
        return "Arre Ajju, mera dimaag thoda aazma raha hai abhi 😅 Ek baar aur try karo?";
      })(),
      wantsImage ? generateImageUrl(text, openaiKey) : Promise.resolve(null),
    ]);

    // Send
    if (imageUrl) {
      await sendPhoto(token, chatId, imageUrl, "🎨 " + reply.slice(0, 900));
    } else {
      await sendMessage(token, chatId, reply);
    }

    // Fire-and-forget DB save
    EdgeRuntime.waitUntil((async () => {
      try {
        await supabase.from("aisha_conversations").insert([
          { platform: "telegram", role: "user",      message: text },
          { platform: "telegram", role: "assistant", message: reply },
        ]);
      } catch (e) { console.log("DB save:", e); }
    })());

    const mode = isRiya ? "Riya" : "Aisha";
    const extras = [wantsImage && imageUrl ? "🎨 image" : "", memoriesText ? "🧠 memory" : ""].filter(Boolean).join(", ");
    console.log(`[${mode}] ${reply.length} chars${extras ? " | " + extras : ""}`);

    return new Response("OK", { status: 200, headers: corsHeaders });

  } catch (error: any) {
    console.error("Webhook error:", error?.message || error);
    return new Response("OK", { status: 200 }); // Always 200 to Telegram
  }
});
