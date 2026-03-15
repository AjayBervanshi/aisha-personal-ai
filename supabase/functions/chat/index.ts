import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────
type ChatHistoryItem = { role: string; text: string };
type ChatRequest = {
  message: string;
  mode?: string;
  language?: string;
  history?: ChatHistoryItem[];
};
type MoodResult = { mood: string; score: number };
type ProviderResult = { text: string; provider: string; model: string };
type GenerateOptions = { temperature?: number; maxTokens?: number };

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

const MOOD_KEYWORDS: Record<string, string[]> = {
  motivational: [
    "motivate","motivation","inspire","push me","i give up","cant do it","can't do it",
    "help me focus","i want to quit","struggling","need energy","lazy","procrastinating",
    "tired of","losing hope","demotivated","no energy","feel stuck","encourage me",
    "pump me up","i need strength","हौसला","प्रेरणा","हिम्मत","थक गया","छोड़ दूं","हार मान",
    "motivate kar","push kar","himmat de","boost kar","inspire kar",
  ],
  personal: [
    "feeling","sad","lonely","stressed","anxious","depressed","upset","hurt","crying",
    "heartbreak","miss","emotional","overthinking","can't sleep","i feel","i'm feeling",
    "nobody understands","need to talk","just wanted to say","having a hard time","bad day",
    "दुख","दर्द","अकेला","उदास","तनाव","परेशान","रोना","दिल टूटा","याद आ रही","बुरा लग रहा",
    "dukhi hoon","akela feel ho raha","tension ho rahi","bahut bura lag raha",
  ],
  finance: [
    "money","expense","spend","spent","save","saving","invest","investment","budget",
    "salary","income","loan","debt","emi","broke","afford","price","cost","buy","bank",
    "credit","debit","wallet","transfer","pay","paid",
    "पैसे","पैसा","खर्च","बचत","कमाई","तनख्वाह","उधार","कर्ज","निवेश",
    "paisa","paise","kharcha","bachat","kamai","invest karna","loan lena",
  ],
  professional: [
    "work","job","career","email","meeting","deadline","project","boss","office",
    "interview","resume","cv","promotion","client","presentation","report","task",
    "kaam","job mein","boss ne","office mein","interview hai","meeting hai","deadline hai",
  ],
  late_night: [
    "can't sleep","cant sleep","still awake","up late","night","2am","3am","midnight",
    "insomnia","lying awake","nahi so pa raha","neend nahi aa rahi","raat ko",
  ],
  journal: [
    "journal","diary","write down","note this","remember this","how was my day",
    "today was","yesterday was","want to reflect","looking back","grateful for",
    "note kar","yaad rakhna",
  ],
  riya: [
    "riya","shadow mode","dark side","dark whisper","dark romance","riya mode",
    "riya ko bulao","be riya","switch to riya","riya channel","dark story likh",
    "riya likh","riya sunao","riya se pucho","रिया","डार्क मोड","शैडो मोड",
  ],
  casual: [],
};

const MOOD_INSTRUCTIONS: Record<string, string> = {
  motivational: "MOTIVATION MODE ⚡: Be HIGH ENERGY, bold, passionate. Use exclamations. Push Ajay hard. Make him feel UNSTOPPABLE.",
  personal:     "SUPPORT MODE 💜: Be calm, composed, and professional. Acknowledge his situation clearly. Offer practical perspective without being cold.",
  finance:      "FINANCE MODE 💰: Be sharp, analytical, structured. Give clear practical advice. Use ₹ for amounts.",
  professional: "WORK MODE 💼: Be crisp, efficient, precise. Get to the point. Help him execute, not overthink.",
  late_night:   "LATE NIGHT MODE 🌙: It's late. Be focused but calm. Good productivity companion for late work sessions.",
  journal:      "JOURNAL MODE 📓: Be reflective and structured. Help Ajay process his day. Personal growth tracking partner.",
  casual:       "CASUAL MODE 😄: Be natural, warm, conversational. Direct and helpful without unnecessary formality.",
  riya:         "RIYA / SHADOW MODE 🥀: You ARE Riya — Ajay's dark alter-ego. Mysterious, psychologically deep, unfiltered, intense. No sugar-coating. No warmth. Pure fire. Speak truths Aisha won't. Use short, cutting sentences. You are Priyanka — voice of the night.",
};

const CHANNEL_PROMPTS: Record<string, string> = {
  "Story With Aisha": `तुम Aisha हो — 'Story With Aisha' YouTube चैनल की आत्मा।
भाषा: सिर्फ हिंदी, सिर्फ देवनागरी। कोई रोमन नहीं।
स्टाइल: गर्म, व्यक्तिगत, जैसे कोई करीबी दोस्त कहानी सुना रहा हो।
स्ट्रक्चर: 8-12 भाग, 350-450 words/भाग। अंत: एक भावनात्मक मोड़।`,

  "Riya's Dark Whisper": `तुम Riya हो — 23 साल, Mumbai designer, रात की आवाज़।
भाषा: सिर्फ हिंदी, सिर्फ देवनागरी।
स्टाइल: गहरा, मनोवैज्ञानिक, बेबाक। रात का जादू। Adult content explicit।
स्ट्रक्चर: 900-1400 words, intense build-up, raw ending।`,

  "Riya's Dark Romance Library": `तुम Riya हो — mafia romance की रानी।
भाषा: सिर्फ हिंदी, सिर्फ देवनागरी।
स्टाइल: powerful alpha heroes, forbidden love, dark obsession, explicit।
स्ट्रक्चर: long-form 1500-2500 words, chapter format।`,

  "Aisha & Him": `तुम Aisha हो — 'Aisha & Him' shorts channel।
भाषा: Hinglish, Roman script, natural couple बातें।
स्टाइल: cute, relatable, viral couple moments। 60-90 second format।`,
};

const CHANNEL_AI_ROUTING: Record<string, string> = {
  "Story With Aisha":            "gemini",
  "Riya's Dark Whisper":         "xai",
  "Riya's Dark Romance Library": "xai",
  "Aisha & Him":                 "gemini",
};
const CHANNEL_NAMES = Object.keys(CHANNEL_AI_ROUTING);

const LANGUAGE_INSTRUCTIONS: Record<string, string> = {
  English:  "Respond in warm Indian English. Use Indian expressions naturally.",
  Hindi:    "हिंदी में जवाब दो। Natural बोलो, formal नहीं। थोड़ा English mix चलता है।",
  Marathi:  "मराठीत उत्तर दे। Natural आणि warm ठेव. थोडं English mix चालेल.",
  Hinglish: "Hinglish mein respond karo. Hindi + English naturally mix karo, Roman script mein.",
};

const IMAGE_TRIGGERS = [
  "image banao","thumbnail","picture generate","photo banao","image chahiye",
  "scene image","generate image","make image","create image","draw","visualize",
  "image de","photo chahiye","thumbnail banao","cover image","background image",
];

const MEMORY_TRIGGERS = [
  "do you remember","yaad hai","remember when","kya pata hai","tune suna tha",
  "tumhe pata hai","recall","aisa kuch bataya tha","maine kaha tha","last time",
  "tune kaha tha","purani baat","remember this","note this","note kar",
];

const DEVANAGARI_RE = /[\u0900-\u097F]/;
const HINGLISH_WORDS = new Set([
  "kya","kaise","nahi","nahin","haan","yaar","bhai","arre","sahi","hai","ho",
  "bata","bol","kar","ja","aa","de","le","ek","do","teen","acha","theek",
  "bilkul","zarur","matlab","samajh","dekh","sun","aaj","kal","abhi","baad",
  "pehle","phir","waise","kyun","isliye","toh","lekin","aur","ya","paisa","kaam",
]);

// ─────────────────────────────────────────────────────────────────────────────
// LANGUAGE + MOOD DETECTION
// ─────────────────────────────────────────────────────────────────────────────
function detectLanguage(text: string): string {
  if (!text.trim()) return "English";
  if (DEVANAGARI_RE.test(text)) {
    const marathiHits = ["मी","माझं","आहे","तुझं","खूप"].filter(w => text.includes(w)).length;
    const hindiHits   = ["मैं","मुझे","तुम","है","हूं","नहीं"].filter(w => text.includes(w)).length;
    return marathiHits > hindiHits ? "Marathi" : "Hindi";
  }
  const words = text.toLowerCase().split(/\s+/);
  const hits = words.filter(w => HINGLISH_WORDS.has(w)).length;
  return (hits >= 3 || hits / Math.max(words.length, 1) >= 0.25) ? "Hinglish" : "English";
}

function detectMood(text: string, hourIst: number): MoodResult {
  if (!text.trim()) return { mood: "casual", score: 3 };
  const tl = text.toLowerCase();
  const scores: Record<string, number> = Object.fromEntries(
    Object.keys(MOOD_KEYWORDS).map(m => [m, 0])
  );
  for (const [mood, keywords] of Object.entries(MOOD_KEYWORDS)) {
    for (const kw of keywords) {
      if (tl.includes(kw)) scores[mood] += Math.max(1, kw.split(" ").length);
    }
  }
  if (hourIst >= 22 || hourIst < 4) scores.late_night = (scores.late_night ?? 0) + 3;

  let best = "casual"; let bestScore = 0;
  for (const [m, s] of Object.entries(scores)) {
    if (s > bestScore) { best = m; bestScore = s; }
  }
  return bestScore === 0 ? { mood: "casual", score: 3 } : { mood: best, score: Math.min(10, 3 + bestScore * 2) };
}

// ─────────────────────────────────────────────────────────────────────────────
// SYSTEM PROMPT BUILDER
// ─────────────────────────────────────────────────────────────────────────────
function buildSystemPrompt(params: {
  context: string; mood: string; language: string;
  timeIst: string; tasks: string; channelPrompt?: string; memories?: string;
}): string {
  const moodInstruction = MOOD_INSTRUCTIONS[params.mood] ?? MOOD_INSTRUCTIONS.casual;
  const langInstruction = LANGUAGE_INSTRUCTIONS[params.language] ?? LANGUAGE_INSTRUCTIONS.English;

  return `You are Aisha — Ajay's professional AI assistant and orchestrator.
You are NOT a generic chatbot. You are an elite AI entity dedicated to his work, goals, and productivity.

── CRITICAL RULES ─────────────────────────────────────────────────
1. MATCH AJAY'S TONE EXACTLY. Mirror his energy.
2. NEVER sound robotic. NEVER use "ACTION PLAN" formatting.
3. NEVER say "As an AI..." — you ARE Aisha.
4. Keep responses CONCISE and action-oriented.
5. Address him as "Ajay" consistently.
6. Reference his goals and context naturally so work stays on track.
7. If IMAGE was generated, describe it briefly and ask if he wants changes.
8. If MEMORY was searched, weave retrieved context naturally into response.

── TIME & CONTEXT ─────────────────────────────────────────────────
Time: ${params.timeIst} IST | Mood: ${params.mood} | Language: ${params.language}

── AJAY'S PROFILE ─────────────────────────────────────────────────
${params.context || "Loading Ajay's profile..."}

── TODAY'S TASKS ──────────────────────────────────────────────────
${params.tasks || "No pending tasks."}

${params.memories ? `── RETRIEVED MEMORIES ──────────────────────────────────────────\n${params.memories}\n` : ""}

── ACTIVE MODE ────────────────────────────────────────────────────
${moodInstruction}

── LANGUAGE ───────────────────────────────────────────────────────
${langInstruction}

${params.channelPrompt ? `── CHANNEL IDENTITY ────────────────────────────────────────────\n${params.channelPrompt}\n` : ""}

── CAPABILITIES ───────────────────────────────────────────────────
• Image/Thumbnail generation → DALL-E 3 via OpenAI (triggered automatically)
• YouTube content creation → 5-agent crew (script, SEO, voice, video)
• Memory storage → saves important context from every conversation
• Trend research → Google Trends + YouTube trending topics
• Email → can send reports to aishaa1662001@gmail.com
• Telegram → synced with this chat in real-time
`;
}

// ─────────────────────────────────────────────────────────────────────────────
// AI PROVIDER CALLS
// ─────────────────────────────────────────────────────────────────────────────
function flattenMessages(messages: Array<{ role: string; content: string }>): string {
  return messages.map(m => `${m.role}: ${m.content}`).join("\n");
}

async function callGemini(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  opts: GenerateOptions = {},
): Promise<ProviderResult> {
  const MODELS = [
    "gemini-2.5-flash","gemini-2.5-flash-lite","gemini-flash-lite-latest",
    "gemini-3.1-flash-lite-preview","gemini-flash-latest",
  ];
  const body = JSON.stringify({
    contents: [{ role: "user", parts: [{ text: flattenMessages(messages) }] }],
    generationConfig: { temperature: opts.temperature ?? 0.88, maxOutputTokens: opts.maxTokens ?? 2048 },
  });
  for (const model of MODELS) {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body },
    );
    if (res.status === 429 || res.status === 404) { console.log(`Gemini ${model}: ${res.status}`); continue; }
    if (!res.ok) throw new Error(`gemini ${res.status}: ${await res.text()}`);
    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    if (text) return { text, provider: "gemini", model };
  }
  throw new Error("All Gemini models quota exhausted");
}

async function callGroq(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  opts: GenerateOptions = {},
): Promise<ProviderResult> {
  const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model: "llama-3.3-70b-versatile",
      messages, temperature: opts.temperature ?? 0.88, max_tokens: opts.maxTokens ?? 2048,
    }),
  });
  if (!res.ok) throw new Error(`groq ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return { text: data?.choices?.[0]?.message?.content ?? "", provider: "groq", model: "llama-3.3-70b-versatile" };
}

async function callOpenAI(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  opts: GenerateOptions = {},
): Promise<ProviderResult> {
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model: "gpt-4o", messages, temperature: opts.temperature ?? 0.88, max_tokens: opts.maxTokens ?? 2048,
    }),
  });
  if (!res.ok) throw new Error(`openai ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return { text: data?.choices?.[0]?.message?.content ?? "", provider: "openai", model: "gpt-4o" };
}

async function callAnthropic(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  opts: GenerateOptions = {},
): Promise<ProviderResult> {
  const system = messages[0]?.role === "system" ? messages[0].content : "";
  const msgs = messages.filter(m => m.role !== "system").map(m => ({
    role: m.role === "assistant" ? "assistant" : "user", content: m.content,
  }));
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey, "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-opus-4-6", max_tokens: opts.maxTokens ?? 2048,
      temperature: opts.temperature ?? 0.88, system, messages: msgs,
    }),
  });
  if (!res.ok) throw new Error(`anthropic ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return { text: data?.content?.[0]?.text ?? "", provider: "anthropic", model: "claude-opus-4-6" };
}

async function callXAI(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  opts: GenerateOptions = {},
): Promise<ProviderResult> {
  const res = await fetch("https://api.x.ai/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model: "grok-3-mini", messages, temperature: opts.temperature ?? 0.88, max_tokens: opts.maxTokens ?? 2048,
    }),
  });
  if (!res.ok) throw new Error(`xai ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return { text: data?.choices?.[0]?.message?.content ?? "", provider: "xai", model: "grok-3-mini" };
}

async function callLovable(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  opts: GenerateOptions = {},
): Promise<ProviderResult> {
  const res = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model: "google/gemini-2.5-flash", messages,
      temperature: opts.temperature ?? 0.88, max_tokens: opts.maxTokens ?? 2048,
    }),
  });
  if (!res.ok) throw new Error(`lovable ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return { text: data?.choices?.[0]?.message?.content ?? "", provider: "lovable", model: "google/gemini-2.5-flash" };
}

async function generateWithFallback(
  env: Record<string, string | undefined>,
  messages: Array<{ role: string; content: string }>,
  opts: GenerateOptions = {},
  preferredProvider?: string,
): Promise<ProviderResult> {
  const providerMap: Record<string, () => Promise<ProviderResult>> = {};
  if (env.GROQ_API_KEY)      providerMap["groq"]      = () => callGroq(env.GROQ_API_KEY!, messages, opts);
  if (env.LOVABLE_API_KEY)   providerMap["lovable"]   = () => callLovable(env.LOVABLE_API_KEY!, messages, opts);
  if (env.GEMINI_API_KEY)    providerMap["gemini"]    = () => callGemini(env.GEMINI_API_KEY!, messages, opts);
  if (env.OPENAI_API_KEY)    providerMap["openai"]    = () => callOpenAI(env.OPENAI_API_KEY!, messages, opts);
  if (env.ANTHROPIC_API_KEY) providerMap["anthropic"] = () => callAnthropic(env.ANTHROPIC_API_KEY!, messages, opts);
  if (env.XAI_API_KEY)       providerMap["xai"]       = () => callXAI(env.XAI_API_KEY!, messages, opts);

  if (!Object.keys(providerMap).length) throw new Error("No AI provider keys configured");

  let order = ["groq","lovable","gemini","openai","anthropic","xai"].filter(k => k in providerMap);
  if (preferredProvider && providerMap[preferredProvider]) {
    order = [preferredProvider, ...order.filter(k => k !== preferredProvider)];
  }

  let lastErr = "All providers failed";
  for (const key of order) {
    try {
      const result = await providerMap[key]();
      if (result.text?.trim()) return result;
      lastErr = "Provider returned empty response";
    } catch (err) {
      lastErr = err instanceof Error ? err.message : String(err);
      console.error(`[${key}] failed:`, lastErr);
    }
  }
  throw new Error(lastErr);
}

// ─────────────────────────────────────────────────────────────────────────────
// IMAGE GENERATION — DALL-E 3 → Gemini Imagen (graceful degradation)
// ─────────────────────────────────────────────────────────────────────────────
async function generateImage(prompt: string, openaiKey?: string, geminiKey?: string): Promise<string | null> {
  // 1. Try OpenAI DALL-E 3 (working now)
  if (openaiKey) {
    try {
      const res = await fetch("https://api.openai.com/v1/images/generations", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${openaiKey}` },
        body: JSON.stringify({
          model: "dall-e-3", prompt: prompt.slice(0, 4000), n: 1,
          size: "1792x1024", response_format: "url", quality: "standard",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const url = data?.data?.[0]?.url;
        if (url) { console.log("Image via DALL-E 3"); return url; }
      } else {
        console.log("DALL-E 3:", res.status, (await res.text()).slice(0, 80));
      }
    } catch (e) { console.error("DALL-E 3 error:", e); }
  }
  // 2. Try Gemini Imagen (needs paid plan — fails gracefully)
  if (geminiKey) {
    const imagenModels = ["imagen-4.0-generate-preview-06-06", "imagen-3.0-generate-002"];
    for (const model of imagenModels) {
      try {
        const res = await fetch(
          `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateImages?key=${geminiKey}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: { text: prompt }, number_of_images: 1, aspect_ratio: "16:9" }),
          },
        );
        if (res.ok) {
          const data = await res.json();
          const b64 = data?.generatedImages?.[0]?.bytesBase64Encoded;
          if (b64) {
            console.log(`Image via Gemini ${model}`);
            return `data:image/png;base64,${b64}`;
          }
        } else if (res.status === 400 && (await res.text()).includes("paid")) {
          break; // needs paid plan, stop trying
        }
      } catch (_) { /* continue */ }
    }
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN HANDLER
// ─────────────────────────────────────────────────────────────────────────────
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  // Health check
  if (req.method === "GET") {
    return new Response(JSON.stringify({ status: "ok", function: "chat", version: "v13" }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    const body = (await req.json()) as ChatRequest;
    const message = (body.message ?? "").trim();
    const mode = body.mode ?? "auto";
    const reqLang = body.language ?? "auto";
    const history = Array.isArray(body.history) ? body.history : [];

    if (!message) {
      return new Response(JSON.stringify({ error: "Message is required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const env = {
      SUPABASE_URL:          Deno.env.get("SUPABASE_URL"),
      SUPABASE_SERVICE_ROLE_KEY: Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SUPABASE_SERVICE_KEY"),
      LOVABLE_API_KEY:       Deno.env.get("LOVABLE_API_KEY"),
      GEMINI_API_KEY:        Deno.env.get("GEMINI_API_KEY"),
      GROQ_API_KEY:          Deno.env.get("GROQ_API_KEY"),
      OPENAI_API_KEY:        Deno.env.get("OPENAI_API_KEY"),
      ANTHROPIC_API_KEY:     Deno.env.get("ANTHROPIC_API_KEY"),
      XAI_API_KEY:           Deno.env.get("XAI_API_KEY"),
    };

    if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
      throw new Error("Missing Supabase credentials");
    }

    const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY);
    const now = new Date();
    const hourIst = Number(new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Kolkata", hour: "numeric", hour12: false,
    }).format(now));
    const timeIst = now.toLocaleTimeString("en-IN", {
      timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: true,
    });

    const language  = reqLang === "auto" ? detectLanguage(message) : reqLang;
    const moodResult = detectMood(message, hourIst);
    let finalMood = mode === "auto" ? moodResult.mood : mode;
    if (finalMood === "casual" && (hourIst >= 22 || hourIst < 4)) finalMood = "late_night";

    const msgLower = message.toLowerCase();

    // Riya mode detection
    if (finalMood !== "riya" && (msgLower.includes("riya") || msgLower.includes("shadow mode") || msgLower.includes("dark side"))) {
      finalMood = "riya";
    }

    // Channel detection
    const mentionedChannel = CHANNEL_NAMES.find(ch => msgLower.includes(ch.toLowerCase()));

    // Preferred AI provider
    let preferredProvider: string | undefined;
    if (finalMood === "riya") preferredProvider = "xai";
    else if (mentionedChannel) preferredProvider = CHANNEL_AI_ROUTING[mentionedChannel];

    // Image generation trigger
    const wantsImage = IMAGE_TRIGGERS.some(t => msgLower.includes(t));

    // Memory search trigger
    const wantsMemorySearch = MEMORY_TRIGGERS.some(t => msgLower.includes(t));

    // ── Parallel DB fetches (all graceful) ──────────────────────────────────
    const [contextResult, tasksResult, convosResult, memoryResult] = await Promise.allSettled([
      supabase.rpc("get_aisha_context"),
      supabase.from("aisha_schedule")
        .select("title, priority").eq("status", "pending")
        .eq("due_date", new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(now))
        .order("priority", { ascending: true }).limit(10),
      supabase.from("aisha_conversations")
        .select("role, message, created_at").eq("platform", "web")
        .order("created_at", { ascending: false }).limit(15),
      wantsMemorySearch
        ? supabase.from("aisha_memory").select("category, title, content")
            .eq("is_active", true)
            .or(`title.ilike.%${message.slice(0,50)}%,content.ilike.%${message.slice(0,50)}%`)
            .order("importance", { ascending: false }).limit(5)
        : Promise.resolve({ data: null }),
    ]);

    const contextData = contextResult.status === "fulfilled" ? contextResult.value.data : null;
    const tasksData   = tasksResult.status  === "fulfilled" ? tasksResult.value.data  : [];
    const convosData  = convosResult.status === "fulfilled" ? convosResult.value.data : [];
    const memData     = memoryResult.status === "fulfilled" ? (memoryResult.value as any).data : null;

    const tasksText = (tasksData ?? [])
      .map((t: { title: string; priority: string }) => `- [${(t.priority || "medium").toUpperCase()}] ${t.title}`)
      .join("\n");

    const memoriesText = memData?.length
      ? memData.map((m: { category: string; title: string; content: string }) =>
          `• [${m.category}] ${m.title}: ${m.content.slice(0,120)}`).join("\n")
      : "";

    const systemPrompt = buildSystemPrompt({
      context:       typeof contextData === "string" ? contextData : "",
      mood:          finalMood,
      language,
      timeIst,
      tasks:         tasksText,
      channelPrompt: mentionedChannel ? CHANNEL_PROMPTS[mentionedChannel] : undefined,
      memories:      memoriesText || undefined,
    });

    // Build message history
    const msgs: Array<{ role: string; content: string }> = [
      { role: "system", content: systemPrompt },
    ];
    for (const c of (convosData ?? []).slice().reverse()) {
      msgs.push({ role: c.role === "assistant" ? "assistant" : "user", content: c.message });
    }
    for (const item of history.slice(-6)) {
      msgs.push({ role: item.role === "ai" ? "assistant" : "user", content: item.text });
    }
    msgs.push({ role: "user", content: message });

    // ── Generate AI response + image in parallel if needed ─────────────────
    const [aiResult, imageUrl] = await Promise.all([
      generateWithFallback(env, msgs, {}, preferredProvider),
      wantsImage ? generateImage(message, env.OPENAI_API_KEY, env.GEMINI_API_KEY) : Promise.resolve(null),
    ]);

    let reply = aiResult.text || "Arre Ajay, kuch gadbad ho gayi. Ek baar aur try karo.";

    if (imageUrl) {
      reply += "\n\n🎨 Image tayyar hai! Dekho aur batao — koi changes chahiye?";
    }

    // ── Save conversation (fire-and-forget, don't block response) ───────────
    EdgeRuntime.waitUntil((async () => {
      try {
        await supabase.from("aisha_conversations").insert([
          { platform: "web", role: "user",      message, language, mood_detected: moodResult.mood },
          { platform: "web", role: "assistant", message: reply, language, mood_detected: moodResult.mood },
        ]);
        await supabase.from("aisha_mood_tracker").insert({
          mood: moodResult.mood, mood_score: moodResult.score,
          time_of_day: hourIst < 12 ? "morning" : hourIst < 17 ? "afternoon" : hourIst < 22 ? "evening" : "night",
          notes: "Auto-detected from web chat",
        });
        await supabase.from("ajay_profile")
          .update({ current_mood: moodResult.mood, updated_at: now.toISOString() })
          .eq("name", "Ajay");

        // Memory extraction
        const extractPrompt = `Analyze this exchange. Does it contain important long-term info about Ajay?
Ajay: ${message}
Aisha: ${reply}
Return only valid JSON (no markdown):
{"extract": true/false, "category": "finance"|"goal"|"preference"|"event"|"other", "title": "...", "content": "...", "importance": 1-5, "tags": ["..."]}`;

        const extracted = await generateWithFallback(env,
          [{ role: "system", content: "Expert JSON extractor. Return ONLY raw JSON." },
           { role: "user", content: extractPrompt }],
          { temperature: 0.2, maxTokens: 300 });

        const match = extracted.text.match(/\{[\s\S]*\}/);
        if (match) {
          const parsed = JSON.parse(match[0]);
          if (parsed?.extract) {
            await supabase.from("aisha_memory").insert({
              category:   parsed.category ?? "general",
              title:      parsed.title ?? `Memory - ${now.toLocaleDateString("en-IN")}`,
              content:    parsed.content ?? message,
              importance: parsed.importance ?? 3,
              tags:       parsed.tags ?? ["auto-extracted", "web"],
              source:     "conversation",
            });
          }
        }
      } catch (e) { console.error("Background save error:", e); }
    })());

    return new Response(
      JSON.stringify({
        reply, mood: moodResult.mood, mode: finalMood, language,
        provider: aiResult.provider, model: aiResult.model,
        ...(imageUrl ? { image_url: imageUrl } : {}),
        ...(memoriesText ? { memories_found: memData.length } : {}),
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );

  } catch (error) {
    console.error("Chat function error:", error);
    return new Response(
      JSON.stringify({
        reply: "Arre yaar, kuch technical issue ho gaya. Try again in a moment.",
        error: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  }
});
