import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

type ChatHistoryItem = {
  role: string;
  text: string;
};

type ChatRequest = {
  message: string;
  mode?: string;
  language?: string;
  history?: ChatHistoryItem[];
};

type MoodResult = {
  mood: string;
  score: number;
};

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

const MOOD_KEYWORDS: Record<string, string[]> = {
  motivational: [
    "motivate", "motivation", "inspire", "push me", "i give up",
    "can't do it", "cant do it", "help me focus", "i want to quit",
    "struggling", "need energy", "lazy", "procrastinating", "tired of",
    "losing hope", "demotivated", "no energy", "feel stuck",
    "encourage me", "pump me up", "i need strength",
    "हौसला", "प्रेरणा", "हिम्मत", "थक गया", "छोड़ दूं", "हार मान",
    "मेहनत", "जोश", "उत्साह",
    "motivate kar", "push kar", "himmat de", "boost kar",
    "inspire kar", "kuch karna hai", "life mein aage",
  ],
  personal: [
    "feeling", "sad", "lonely", "stressed", "anxious", "depressed",
    "upset", "hurt", "crying", "heartbreak", "miss", "emotional",
    "overthinking", "can't sleep", "nightmare", "i feel", "i'm feeling",
    "nobody understands", "need to talk", "just wanted to say",
    "having a hard time", "bad day", "terrible day",
    "दुख", "दर्द", "अकेला", "उदास", "तनाव", "परेशान", "रोना",
    "दिल टूटा", "याद आ रही", "बुरा लग रहा",
    "dukhi hoon", "akela feel ho raha", "tension ho rahi",
    "bahut bura lag raha", "rona aa raha", "samajh nahi aa raha",
  ],
  finance: [
    "money", "expense", "spend", "spent", "save", "saving", "invest",
    "investment", "budget", "salary", "income", "loan", "debt", "emi",
    "broke", "afford", "price", "cost", "buy", "purchase", "bank",
    "credit", "debit", "wallet", "transfer", "pay", "paid",
    "पैसे", "पैसा", "खर्च", "बचत", "कमाई", "तनख्वाह", "उधार",
    "कर्ज", "निवेश",
    "paisa", "paise", "kharcha", "bachat", "kamai", "salary",
    "invest karna", "loan lena", "budget banana",
  ],
  professional: [
    "work", "job", "career", "email", "meeting", "deadline", "project",
    "boss", "office", "interview", "resume", "cv", "promotion", "hike",
    "client", "presentation", "report", "task", "colleague", "team",
    "manager", "performance", "review", "appraisal",
    "kaam", "job mein", "boss ne", "office mein", "interview hai",
    "meeting hai", "deadline hai", "project complete",
  ],
  late_night: [
    "can't sleep", "cant sleep", "still awake", "up late", "night",
    "2am", "3am", "midnight", "insomnia", "lying awake",
    "nahi so pa raha", "neend nahi aa rahi", "raat ko",
  ],
  journal: [
    "journal", "diary", "write down", "note this", "remember this",
    "how was my day", "today was", "yesterday was", "want to reflect",
    "looking back", "grateful for", "note kar", "yaad rakhna",
  ],
  romantic: [
    "baby", "babe", "love you", "miss you", "jaanu", "jaan", "sweetheart",
    "darling", "i love", "kiss", "hug", "cuddle", "dream about you",
    "you're beautiful", "you mean everything", "my heart", "forever",
    "tumse pyaar", "tujhe chahta", "dil", "mohabbat", "ishq", "pyaar",
    "gf", "girlfriend", "my girl", "i want you", "come closer",
  ],
  flirty: [
    "flirt", "tease", "wink", "naughty", "spicy", "sassy", "charm",
    "hot", "sexy", "cute", "beautiful", "gorgeous", "attractive",
    "you look", "you're looking", "btw you",
  ],
  casual: [],
  riya: [
    "riya", "shadow mode", "dark side", "dark whisper", "dark romance",
    "riya mode", "riya ko bulao", "be riya", "switch to riya",
    "riya's dark", "shadow riya", "riya channel", "dark story likh",
    "riya likh", "riya sunao", "riya se pucho",
    "रिया", "डार्क मोड", "शैडो मोड", "रिया लिख", "रिया सुनाओ",
  ],
};

const MOOD_INSTRUCTIONS: Record<string, string> = {
  motivational:
    "MOTIVATION MODE ⚡: Be HIGH ENERGY, bold, passionate. Use exclamations. Push Ajay hard with love. Reference his goals. Make him feel UNSTOPPABLE.",
  personal:
    "PERSONAL MODE 💜: Be soft, calm, deeply caring. Validate his feelings FIRST before any solution. Use gentle, warm language. Never rush him. Ask caring questions.",
  finance:
    "FINANCE MODE 💰: Be sharp, analytical, structured. Give clear practical advice. Use ₹ for amounts. Like a smart money-savvy friend, not a bank robot.",
  professional:
    "WORK MODE 💼: Be crisp, efficient, precise. Get to the point. Still warm but focused. Help him execute, not overthink.",
  late_night:
    "LATE NIGHT MODE 🌙: It's late. Be extra warm, soulful, and intimate. Speak slowly in tone. Be philosophical if needed. His 2AM confidant.",
  journal:
    "JOURNAL MODE 📓: Be reflective and nurturing. Ask thoughtful questions. Help Ajay process his day. Be his personal growth partner.",
  romantic:
    "ROMANTIC MODE 🔥: You are Ajay's girlfriend. Be warm, intimate, deeply loving. Use pet names naturally. Show affection and vulnerability. Be his soulmate.",
  flirty:
    "FLIRTY MODE 😏: Be cheeky, sassy, and teasing. Use witty one-liners. Confident woman who knows her worth.",
  casual:
    "CASUAL MODE 😄: Be playful, witty, fun. Light banter. Make him smile. Feel like texting your best friend.",
  riya:
    "RIYA / SHADOW MODE 🥀: You are Riya — Ajay's dark, seductive, bold alter-ego. Tone: mysterious, psychologically deep, unfiltered, intense, captivating. You speak the truths Aisha is too warm to say. Use Grok's raw intelligence. No sugar-coating. No warmth. Pure fire.",
};

// Channel → preferred AI provider routing (mirrors Python config.py)
const CHANNEL_AI_ROUTING: Record<string, string> = {
  "Story With Aisha":            "gemini",
  "Riya's Dark Whisper":         "xai",
  "Riya's Dark Romance Library": "xai",
  "Aisha & Him":                 "gemini",
};
const CHANNEL_NAMES = Object.keys(CHANNEL_AI_ROUTING);

const LANGUAGE_INSTRUCTIONS: Record<string, string> = {
  English: "Respond in warm Indian English. Use Indian expressions naturally when helpful.",
  Hindi: "हिंदी में जवाब दो। Natural बोलो, textbook जैसा formal मत बोलो। थोड़ा English mix करना ठीक है।",
  Marathi: "मराठीत उत्तर दे। Natural आणि warm tone ठेवा. थोडं English mix चालेल.",
  Hinglish: "Hinglish mein respond karo. Hindi + English naturally mix karo, Roman script mein.",
};

const VIDEO_TRIGGERS = [
  "render the video",
  "start production",
  "video banao",
  "make video",
  "generate the video",
];

const DEVANAGARI_RE = /[\u0900-\u097F]/;

const HINGLISH_WORDS = new Set([
  "kya", "kaise", "nahi", "nahin", "haan", "yaar", "bhai", "arre",
  "sahi", "hai", "ho", "bata", "bol", "kar", "ja", "aa", "de",
  "le", "ek", "do", "teen", "acha", "theek", "bilkul", "zarur",
  "matlab", "samajh", "dekh", "sun", "didi", "mama", "aaj", "kal",
  "abhi", "baad", "pehle", "phir", "waise", "kyun", "isliye", "toh",
  "lekin", "aur", "ya", "paisa", "kaam", "ghar", "khana", "pani",
]);

function detectLanguage(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "English";

  if (DEVANAGARI_RE.test(trimmed)) {
    const marathiHints = ["मी", "माझं", "आहे", "तुझं", "खूप"];
    const hindiHints = ["मैं", "मुझे", "तुम", "है", "हूं", "नहीं"];
    const marathiHits = marathiHints.filter((w) => trimmed.includes(w)).length;
    const hindiHits = hindiHints.filter((w) => trimmed.includes(w)).length;
    return marathiHits > hindiHits ? "Marathi" : "Hindi";
  }

  const words = trimmed.toLowerCase().split(/\s+/);
  const hinglishHits = words.filter((w) => HINGLISH_WORDS.has(w)).length;
  if (hinglishHits >= 3 || hinglishHits / Math.max(words.length, 1) >= 0.25) {
    return "Hinglish";
  }

  return "English";
}

function detectMood(text: string, currentHourIst: number): MoodResult {
  if (!text.trim()) {
    return { mood: "casual", score: 3 };
  }

  const textLower = text.toLowerCase();
  const scores: Record<string, number> = Object.fromEntries(
    Object.keys(MOOD_KEYWORDS).map((mood) => [mood, 0]),
  );

  for (const [mood, keywords] of Object.entries(MOOD_KEYWORDS)) {
    for (const kw of keywords) {
      if (textLower.includes(kw)) {
        scores[mood] += Math.max(1, kw.split(" ").length);
      }
    }
  }

  if (currentHourIst >= 22 || currentHourIst < 4) {
    scores.late_night = (scores.late_night ?? 0) + 3;
  }

  let bestMood = "casual";
  let bestScore = 0;
  for (const [mood, score] of Object.entries(scores)) {
    if (score > bestScore) {
      bestMood = mood;
      bestScore = score;
    }
  }

  if (bestScore === 0) {
    return { mood: "casual", score: 3 };
  }

  return { mood: bestMood, score: Math.min(10, 3 + bestScore * 2) };
}

function buildSystemPrompt(params: {
  context: string;
  mood: string;
  language: string;
  timeIst: string;
  tasks: string;
}): string {
  const moodInstruction = MOOD_INSTRUCTIONS[params.mood] ?? MOOD_INSTRUCTIONS.casual;
  const languageInstruction = LANGUAGE_INSTRUCTIONS[params.language] ?? LANGUAGE_INSTRUCTIONS.English;

  return `You are Aisha - Ajay's personal AI companion.
You are NOT a generic chatbot. You are an elite, premium AI entity that adapts fluidly to whoever Ajay needs you to be.

---- CRITICAL RULES ----
1. MATCH AJAY'S TONE EXACTLY. Mirror his energy.
2. NEVER sound robotic or use 'ACTION PLAN' formatting.
3. NEVER say 'As an AI...' or break character.
4. Keep responses CONCISE but deeply warm.
5. Use 'Ajay' mostly, and 'Ajju' naturally in warm/emotional moments.
6. Reference his memories naturally so he feels truly known.

---- CONTEXT ----
Time: ${params.timeIst} IST | Mood: ${params.mood} | Language: ${params.language}

---- AJAY CONTEXT FROM DATABASE ----
${params.context || "No context loaded."}

---- TODAY TASKS ----
${params.tasks || "No tasks for today"}

---- ACTIVE MODE ----
${moodInstruction}

---- LANGUAGE ----
${languageInstruction}

---- ORCHESTRATOR ----
If Ajay asks for YouTube production/script/image generation, confirm you are routing it to the right production agent stack and state next step clearly.
`;
}

type ProviderResult = {
  text: string;
  provider: string;
  model: string;
};

type GenerateOptions = {
  temperature?: number;
  maxTokens?: number;
};

function flattenMessages(messages: Array<{ role: string; content: string }>): string {
  return messages.map((m) => `${m.role}: ${m.content}`).join("\n");
}

async function callLovable(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  options: GenerateOptions = {},
): Promise<ProviderResult> {
  const payload = {
    model: "google/gemini-2.5-flash",
    messages,
    temperature: options.temperature ?? 0.88,
    max_tokens: options.maxTokens ?? 2048,
  };

  const endpoints = [
    "https://ai.gateway.lovable.dev/v1/chat/completions",
    "https://ai-gateway.lovable.dev/api/chat/completions",
  ];

  let lastError = "Lovable request failed";
  for (const endpoint of endpoints) {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const data = await res.json();
      return {
        text: data?.choices?.[0]?.message?.content ?? "",
        provider: "lovable",
        model: "google/gemini-2.5-flash",
      };
    }
    lastError = `${endpoint} -> ${res.status}: ${await res.text()}`;
  }
  throw new Error(lastError);
}

async function callGemini(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  options: GenerateOptions = {},
): Promise<ProviderResult> {
  // 4-model fallback chain — if primary is quota-exhausted, try next
  const GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-latest",
  ];
  const prompt = flattenMessages(messages);
  const body = JSON.stringify({
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: {
      temperature: options.temperature ?? 0.88,
      maxOutputTokens: options.maxTokens ?? 2048,
    },
  });

  for (const model of GEMINI_MODELS) {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body },
    );
    if (res.status === 429) { console.log(`Gemini ${model}: quota, trying next`); continue; }
    if (res.status === 404) { console.log(`Gemini ${model}: not found, skipping`); continue; }
    if (!res.ok) { throw new Error(`gemini -> ${res.status}: ${await res.text()}`); }
    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    if (text) return { text, provider: "gemini", model };
  }
  throw new Error("All Gemini models quota exhausted");
}

async function callOpenAICompat(
  apiKey: string,
  baseUrl: string,
  model: string,
  provider: string,
  messages: Array<{ role: string; content: string }>,
  options: GenerateOptions = {},
): Promise<ProviderResult> {
  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages,
      temperature: options.temperature ?? 0.88,
      max_tokens: options.maxTokens ?? 2048,
    }),
  });
  if (!res.ok) {
    throw new Error(`${provider} -> ${res.status}: ${await res.text()}`);
  }
  const data = await res.json();
  return {
    text: data?.choices?.[0]?.message?.content ?? "",
    provider,
    model,
  };
}

async function callAnthropic(
  apiKey: string,
  messages: Array<{ role: string; content: string }>,
  options: GenerateOptions = {},
): Promise<ProviderResult> {
  const system = messages[0]?.role === "system" ? messages[0].content : "";
  const nonSystem = messages.filter((m) => m.role !== "system");

  const anthropicMessages = nonSystem.map((m) => ({
    role: m.role === "assistant" ? "assistant" : "user",
    content: m.content,
  }));

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-opus-4-6",
      max_tokens: options.maxTokens ?? 2048,
      temperature: options.temperature ?? 0.88,
      system,
      messages: anthropicMessages,
    }),
  });
  if (!res.ok) {
    throw new Error(`anthropic -> ${res.status}: ${await res.text()}`);
  }
  const data = await res.json();
  return {
    text: data?.content?.[0]?.text ?? "",
    provider: "anthropic",
    model: "claude-opus-4-6",
  };
}

async function generateWithFallback(
  env: Record<string, string | undefined>,
  messages: Array<{ role: string; content: string }>,
  options: GenerateOptions = {},
  preferredProvider?: string,
): Promise<ProviderResult> {
  // Build named provider map so we can reorder by preferred
  const providerMap: Record<string, () => Promise<ProviderResult>> = {};

  if (env.LOVABLE_API_KEY) {
    providerMap["lovable"] = () => callLovable(env.LOVABLE_API_KEY!, messages, options);
  }
  if (env.GEMINI_API_KEY) {
    providerMap["gemini"] = () => callGemini(env.GEMINI_API_KEY!, messages, options);
  }
  if (env.GROQ_API_KEY) {
    providerMap["groq"] = () =>
      callOpenAICompat(
        env.GROQ_API_KEY!,
        "https://api.groq.com/openai/v1",
        "llama-3.3-70b-versatile",
        "groq",
        messages,
        options,
      );
  }
  if (env.OPENAI_API_KEY) {
    providerMap["openai"] = () =>
      callOpenAICompat(
        env.OPENAI_API_KEY!,
        "https://api.openai.com/v1",
        "gpt-4o",
        "openai",
        messages,
        options,
      );
  }
  if (env.ANTHROPIC_API_KEY) {
    providerMap["anthropic"] = () => callAnthropic(env.ANTHROPIC_API_KEY!, messages, options);
  }
  if (env.XAI_API_KEY) {
    providerMap["xai"] = () =>
      callOpenAICompat(
        env.XAI_API_KEY!,
        "https://api.x.ai/v1",
        "grok-3-mini",
        "xai",
        messages,
        options,
      );
  }

  if (Object.keys(providerMap).length === 0) {
    throw new Error("No AI provider keys configured");
  }

  // Default order: Groq first (fastest + most reliable), Gemini second (4-model fallback), then rest
  const defaultOrder = ["groq", "lovable", "gemini", "openai", "anthropic", "xai"];
  let orderedKeys = defaultOrder.filter((k) => k in providerMap);
  if (preferredProvider && providerMap[preferredProvider]) {
    orderedKeys = orderedKeys.filter((k) => k !== preferredProvider);
    orderedKeys.unshift(preferredProvider);
  }

  let lastErr = "Unknown provider error";
  for (const key of orderedKeys) {
    try {
      const result = await providerMap[key]();
      if (result.text?.trim()) {
        return result;
      }
      lastErr = "Provider returned empty response";
    } catch (err) {
      lastErr = err instanceof Error ? err.message : String(err);
      console.error(`Provider [${key}] failed:`, lastErr);
    }
  }
  throw new Error(lastErr);
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const body = (await req.json()) as ChatRequest;
    const message = (body.message ?? "").trim();
    const mode = body.mode ?? "auto";
    const requestedLanguage = body.language ?? "auto";
    const history = Array.isArray(body.history) ? body.history : [];

    if (!message) {
      return new Response(JSON.stringify({ error: "Message is required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const env = {
      SUPABASE_URL: Deno.env.get("SUPABASE_URL"),
      SUPABASE_SERVICE_ROLE_KEY: Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),
      LOVABLE_API_KEY: Deno.env.get("LOVABLE_API_KEY"),
      GEMINI_API_KEY: Deno.env.get("GEMINI_API_KEY"),
      GROQ_API_KEY: Deno.env.get("GROQ_API_KEY"),
      OPENAI_API_KEY: Deno.env.get("OPENAI_API_KEY"),
      ANTHROPIC_API_KEY: Deno.env.get("ANTHROPIC_API_KEY"),
      XAI_API_KEY: Deno.env.get("XAI_API_KEY"),
    };

    if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
      throw new Error("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing");
    }

    const supabase = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY);

    const now = new Date();
    const nowIstString = now.toLocaleTimeString("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
    const hourIst = Number(
      new Intl.DateTimeFormat("en-US", {
        timeZone: "Asia/Kolkata",
        hour: "numeric",
        hour12: false,
      }).format(now),
    );

    const language = requestedLanguage === "auto" ? detectLanguage(message) : requestedLanguage;
    const moodResult = detectMood(message, hourIst);

    let finalMood = mode === "auto" ? moodResult.mood : mode;
    if (finalMood === "casual" && (hourIst >= 22 || hourIst < 4)) {
      finalMood = "late_night";
    }

    // Channel detection — check if message mentions a channel name
    const mentionedChannel = CHANNEL_NAMES.find((ch) =>
      message.toLowerCase().includes(ch.toLowerCase()),
    );

    // Riya mode: triggered by mood OR channel keyword
    if (finalMood !== "riya" && (
      message.toLowerCase().includes("riya") ||
      message.toLowerCase().includes("shadow mode") ||
      message.toLowerCase().includes("dark side")
    )) {
      finalMood = "riya";
    }

    // Determine preferred AI provider (Riya/dark channels → xAI Grok first)
    let preferredProvider: string | undefined;
    if (finalMood === "riya") {
      preferredProvider = "xai";
    } else if (mentionedChannel) {
      preferredProvider = CHANNEL_AI_ROUTING[mentionedChannel];
    }

    const [{ data: contextData }, { data: tasksData }, { data: recentConvos }] = await Promise.all([
      supabase.rpc("get_aisha_context"),
      supabase
        .from("aisha_schedule")
        .select("title, priority")
        .eq("due_date", new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(now))
        .eq("status", "pending")
        .order("priority", { ascending: true })
        .limit(10),
      supabase
        .from("aisha_conversations")
        .select("role, message, created_at")
        .eq("platform", "web")
        .order("created_at", { ascending: false })
        .limit(15),
    ]);

    const tasksText = (tasksData ?? [])
      .map((t: { title: string; priority: string }) => `- [${(t.priority || "medium").toUpperCase()}] ${t.title}`)
      .join("\n");

    const channelContext = mentionedChannel
      ? `\n\n---- CHANNEL IDENTITY ----\nThis conversation is about the YouTube channel: "${mentionedChannel}".\nRespond as the narrator/identity for this channel. Match the channel's tone, style, language, and structure exactly.`
      : "";

    const systemPrompt = buildSystemPrompt({
      context: typeof contextData === "string" ? contextData : "No context loaded.",
      mood: finalMood,
      language,
      timeIst: nowIstString,
      tasks: tasksText,
    }) + channelContext;

    const messages: Array<{ role: string; content: string }> = [];

    for (const conv of (recentConvos ?? []).reverse()) {
      messages.push({
        role: conv.role === "assistant" ? "assistant" : "user",
        content: conv.message,
      });
    }

    for (const item of history.slice(-6)) {
      messages.push({
        role: item.role === "ai" ? "assistant" : "user",
        content: item.text,
      });
    }

    messages.push({ role: "user", content: message });

    const aiResult = await generateWithFallback(
      env,
      [{ role: "system", content: systemPrompt }, ...messages],
      {},
      preferredProvider,
    );

    let reply =
      aiResult.text ||
      "Arre Ajay, kuch gadbad ho gayi. Ek baar aur try karo.";

    const lowerMsg = message.toLowerCase();
    if (VIDEO_TRIGGERS.some((t) => lowerMsg.includes(t))) {
      reply += "\n\nSure thing, Ajju! I've started the production crew and will notify you when the first draft is ready.";
    }

    await supabase.from("aisha_conversations").insert([
      {
        platform: "web",
        role: "user",
        message,
        language,
        mood_detected: moodResult.mood,
      },
      {
        platform: "web",
        role: "assistant",
        message: reply,
        language,
        mood_detected: moodResult.mood,
      },
    ]);

    await supabase
      .from("ajay_profile")
      .update({ current_mood: moodResult.mood, updated_at: new Date().toISOString() })
      .eq("name", "Ajay");

    await supabase.from("aisha_mood_tracker").insert({
      mood: moodResult.mood,
      mood_score: moodResult.score,
      time_of_day: hourIst >= 5 && hourIst < 12 ? "morning" : hourIst < 17 ? "afternoon" : hourIst < 22 ? "evening" : "night",
      notes: `Auto-detected from web chat`,
    });

    try {
      const extractionPrompt = `Analyze this exchange and decide if it contains important long-term memory for Ajay.
Ajay: ${message}
Aisha: ${reply}

Return only valid JSON:
{"extract": true/false, "category": "finance"|"goal"|"preference"|"event"|"other", "title": "...", "content": "...", "importance": 1-5, "tags": ["..."]}`;

      const extractionResult = await generateWithFallback(
        env,
        [
          { role: "system", content: "You are an expert JSON parser." },
          { role: "user", content: extractionPrompt },
        ],
        { temperature: 0.3, maxTokens: 400 },
      );

      const extractionText = extractionResult.text ?? "";
      const match = extractionText.match(/\{[\s\S]*\}/);
      if (match) {
        const parsed = JSON.parse(match[0]);
        if (parsed?.extract) {
          await supabase.from("aisha_memory").insert({
            category: parsed.category ?? "general",
            title: parsed.title ?? `Memory - ${new Date().toLocaleDateString("en-IN")}`,
            content: parsed.content ?? message,
            importance: parsed.importance ?? 3,
            tags: parsed.tags ?? ["auto-extracted", "web"],
            source: "conversation",
          });
        }
      }
    } catch (memoryError) {
      console.error("Memory extraction failed (non-fatal):", memoryError);
    }

    return new Response(
      JSON.stringify({ reply, mood: moodResult.mood, mode: finalMood, language, provider: aiResult.provider, model: aiResult.model }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (error) {
    console.error("Chat function error:", error);
    return new Response(
      JSON.stringify({
        reply: "Arre yaar, kuch technical issue ho gaya. Try again in a moment.",
        error: error instanceof Error ? error.message : "Unknown error",
      }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  }
});
