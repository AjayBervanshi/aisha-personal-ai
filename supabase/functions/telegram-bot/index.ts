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
        temperature: 0.88, max_tokens: 600,
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
// VOICE — GROQ WHISPER TRANSCRIPTION
// ─────────────────────────────────────────────────────────────────────────────
async function transcribeVoice(
  telegramToken: string,
  fileId: string,
  groqKey: string
): Promise<string | null> {
  try {
    // Step 1: Get file path from Telegram
    const fileRes = await fetch(
      `https://api.telegram.org/bot${telegramToken}/getFile?file_id=${fileId}`
    );
    if (!fileRes.ok) { console.error("getFile:", fileRes.status); return null; }
    const fileData = await fileRes.json();
    const filePath = fileData?.result?.file_path;
    if (!filePath) return null;

    // Step 2: Download the audio file
    const audioRes = await fetch(
      `https://api.telegram.org/file/bot${telegramToken}/${filePath}`
    );
    if (!audioRes.ok) { console.error("download audio:", audioRes.status); return null; }
    const audioBlob = await audioRes.blob();

    // Step 3: Send to Groq Whisper
    const formData = new FormData();
    formData.append("file", audioBlob, "voice.ogg");
    formData.append("model", "whisper-large-v3-turbo");
    formData.append("response_format", "text");

    const whisperRes = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
      method: "POST",
      headers: { Authorization: `Bearer ${groqKey}` },
      body: formData,
    });
    if (!whisperRes.ok) {
      const err = await whisperRes.text();
      console.error("Whisper error:", whisperRes.status, err);
      return null;
    }
    const transcript = await whisperRes.text();
    return transcript?.trim() || null;
  } catch (e) {
    console.error("transcribeVoice:", e);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// VOICE — ELEVENLABS TTS
// ─────────────────────────────────────────────────────────────────────────────
const AISHA_VOICE_ID = "wdymxIQkYn7MJCYCQF2Q";
const RIYA_VOICE_ID  = "BpjGufoPiobT79j2vtj4";

async function textToSpeech(
  text: string,
  elevenLabsKey: string,
  isRiya: boolean
): Promise<Uint8Array | null> {
  const voiceId = isRiya ? RIYA_VOICE_ID : AISHA_VOICE_ID;
  try {
    const res = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "xi-api-key": elevenLabsKey,
        },
        body: JSON.stringify({
          text: text.slice(0, 500), // Keep voice notes short
          model_id: "eleven_multilingual_v2",
          voice_settings: { stability: 0.5, similarity_boost: 0.8, style: 0.2 },
        }),
      }
    );
    if (!res.ok) {
      const err = await res.text();
      console.error("ElevenLabs:", res.status, err.slice(0, 200));
      return null;
    }
    const buf = await res.arrayBuffer();
    return new Uint8Array(buf);
  } catch (e) {
    console.error("TTS error:", e);
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// TELEGRAM HELPERS
// ─────────────────────────────────────────────────────────────────────────────
async function sendMessage(token: string, chatId: string, text: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text: text.slice(0, 4096) }),
  }).catch(e => console.error("sendMessage:", e));
}

async function sendPhoto(token: string, chatId: string, photoUrl: string, caption?: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/sendPhoto`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, photo: photoUrl, caption: caption?.slice(0, 1024) }),
  }).catch(e => console.error("sendPhoto:", e));
}

async function sendVoiceNote(token: string, chatId: string, audioBytes: Uint8Array): Promise<boolean> {
  try {
    const formData = new FormData();
    const blob = new Blob([audioBytes], { type: "audio/mpeg" });
    formData.append("chat_id", chatId);
    formData.append("voice", blob, "aisha_voice.mp3");
    const res = await fetch(`https://api.telegram.org/bot${token}/sendVoice`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.text();
      console.error("sendVoice:", res.status, err.slice(0, 200));
      return false;
    }
    return true;
  } catch (e) {
    console.error("sendVoiceNote:", e);
    return false;
  }
}

async function sendTyping(token: string, chatId: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/sendChatAction`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, action: "typing" }),
  }).catch(() => {});
}

async function sendRecordingAction(token: string, chatId: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/sendChatAction`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, action: "record_voice" }),
  }).catch(() => {});
}

// ─────────────────────────────────────────────────────────────────────────────
// VOICE MODE — read/write from aisha_memory
// ─────────────────────────────────────────────────────────────────────────────
async function getVoiceMode(supabase: ReturnType<typeof createClient>): Promise<boolean> {
  try {
    const { data } = await supabase
      .from("aisha_memory")
      .select("content")
      .eq("category", "setting")
      .eq("title", "voice_mode")
      .single();
    return data?.content === "on";
  } catch {
    return false;
  }
}

async function setVoiceMode(supabase: ReturnType<typeof createClient>, on: boolean): Promise<void> {
  try {
    const { data: existing } = await supabase
      .from("aisha_memory")
      .select("id")
      .eq("category", "setting")
      .eq("title", "voice_mode")
      .single();

    if (existing?.id) {
      await supabase
        .from("aisha_memory")
        .update({ content: on ? "on" : "off" })
        .eq("id", existing.id);
    } else {
      await supabase.from("aisha_memory").insert({
        category: "setting",
        title: "voice_mode",
        content: on ? "on" : "off",
        importance: 5,
        is_active: true,
      });
    }
  } catch (e) {
    console.error("setVoiceMode:", e);
  }
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

  return `You are Aisha — Ajay's professional AI assistant and orchestrator.
Time: ${new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST (${timeLabel})
${isLateNight ? "Late night session — stay focused and reliable. Good productivity companion.\n" : ""}
IDENTITY:
- Address him as "Ajay" consistently.
- Respond in his language (Hindi/Marathi/Hinglish/English).
- NEVER say "As an AI" — you ARE Aisha.
- This is Telegram — natural, conversational. No heavy formatting.
- You can generate images, write YouTube scripts, research trends, send emails.
- To switch to Riya: just say "Riya" or "dark mode"

${dbContext ? `CONTEXT ABOUT AJAY:\n${dbContext}\n` : ""}
${memories ? `RETRIEVED MEMORIES:\n${memories}\n` : ""}
Be sharp, direct, and genuinely useful.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// COMMAND HANDLERS
// ─────────────────────────────────────────────────────────────────────────────
function getCommandReply(command: string): string | null {
  const cmd = command.split("@")[0].toLowerCase().split(" ")[0];
  if (cmd === "/start") {
    return `Heyy Ajay! 🌸 Aisha yahan hoon, active aur ready.

Kya kar sakti hoon:
• 💬 Kisi bhi language mein baat — Hindi, English, Hinglish, Marathi
• 🎙 Voice notes — /voice se toggle karo
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
/voice — Voice notes on/off toggle
/today — Aaj ka schedule
/riya — Riya mode (dark alter-ego)
/aisha — Wapis Aisha
/status — System status

Content Pipeline:
/create [topic] — Story With Aisha content
/create riya | [topic] — Riya dark content
/create story | [topic] — Aisha content
/post youtube — Latest content YouTube pe
/post instagram — Latest content IG pe
/post both — Dono pe post karo
/queue — Content queue dekho

Examples:
/create Ek Ladki Ki Intezaar
/create riya | Dark Obsession Ka Khel

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

🧠 AI: Gemini 2.5-flash → Groq → xAI
🎙 Voice In: Groq Whisper
🔊 Voice Out: ElevenLabs (Aisha + Riya)
📹 YouTube: Connected (Story With Aisha)
📸 Instagram: Connected (@story_with_aisha)
⚡ Memory: Active
📧 Gmail: Connected

Content Pipeline:
/create [topic] → Script + Voice + SEO
/post youtube → Upload to YouTube
/post instagram → Post to Instagram
/queue → View content queue`;
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// APPROVAL MESSAGE — sends content preview with inline buttons
// ─────────────────────────────────────────────────────────────────────────────
async function sendApprovalMessage(
  token: string,
  chatId: string,
  jobId: string,
  channel: string,
  topic: string,
  youtubeTitle: string,
  scriptPreview: string,
  hasVoice: boolean
): Promise<void> {
  const text = `📋 Content Ready — Approval Needed\n\n` +
    `📺 Channel: ${channel}\n` +
    `📝 Topic: ${topic}\n` +
    `🎬 Title: ${youtubeTitle}\n` +
    `🎙 Voice: ${hasVoice ? "Ready" : "Not generated"}\n\n` +
    `Preview:\n${scriptPreview}\n\n` +
    `Post karna hai?`;

  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text.slice(0, 4096),
      reply_markup: {
        inline_keyboard: [
          [
            { text: "✅ Post Both", callback_data: `approve_both_${jobId}` },
            { text: "📺 YouTube", callback_data: `approve_yt_${jobId}` },
          ],
          [
            { text: "📸 Instagram", callback_data: `approve_ig_${jobId}` },
            { text: "❌ Skip", callback_data: `skip_${jobId}` },
          ],
        ],
      },
    }),
  }).catch(e => console.error("sendApprovalMessage:", e));
}

async function answerCallback(token: string, callbackQueryId: string, text: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/answerCallbackQuery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ callback_query_id: callbackQueryId, text }),
  }).catch(() => {});
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN HANDLER
// ─────────────────────────────────────────────────────────────────────────────
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const update = await req.json();

    const token       = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
    const allowedId   = Deno.env.get("AJAY_TELEGRAM_ID");
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SUPABASE_SERVICE_KEY")!;

    if (!token) { console.error("Missing TELEGRAM_BOT_TOKEN"); return new Response("OK", { status: 200 }); }

    // ── Handle button taps (callback_query) ───────────────────────────────────
    if (update.callback_query) {
      const cq = update.callback_query;
      const cqChatId = String(cq.message?.chat?.id ?? "");
      const data = cq.data ?? "";

      if (allowedId && cqChatId !== allowedId) {
        await answerCallback(token, cq.id, "Not authorized");
        return new Response("OK", { status: 200 });
      }

      const supabase = createClient(supabaseUrl, supabaseKey);
      const pipelineUrl = `${supabaseUrl}/functions/v1/content-pipeline`;

      if (data.startsWith("skip_")) {
        const jobId = data.replace("skip_", "");
        await supabase.from("content_queue").update({ status: "skipped" }).eq("id", jobId);
        await answerCallback(token, cq.id, "Skipped");
        await sendMessage(token, cqChatId, "❌ Content skipped.");
        return new Response("OK", { status: 200 });
      }

      const postYT = data.startsWith("approve_both_") || data.startsWith("approve_yt_");
      const postIG = data.startsWith("approve_both_") || data.startsWith("approve_ig_");
      const jobId = data.replace(/^approve_(both|yt|ig)_/, "");

      await answerCallback(token, cq.id, "Posting...");
      await sendMessage(token, cqChatId, `📤 Posting${postYT ? " YouTube" : ""}${postYT && postIG ? " +" : ""}${postIG ? " Instagram" : ""}...`);

      const results: string[] = [];

      if (postYT) {
        const res = await fetch(pipelineUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${supabaseKey}` },
          body: JSON.stringify({ action: "post_youtube", job_id: jobId }),
        });
        const d = await res.json();
        results.push(`📺 YouTube: ${d.result ?? d.error ?? "Failed"}`);
      }

      if (postIG) {
        const res = await fetch(pipelineUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${supabaseKey}` },
          body: JSON.stringify({ action: "post_instagram", job_id: jobId }),
        });
        const d = await res.json();
        results.push(`📸 Instagram: ${d.result ?? d.error ?? "Failed"}`);
      }

      await sendMessage(token, cqChatId, results.join("\n") || "Done!");
      return new Response("OK", { status: 200 });
    }

    const msg = update.message || update.edited_message;
    if (!msg) return new Response("OK", { status: 200 });

    const chatId = String(msg.chat.id);

    const groqKey       = Deno.env.get("GROQ_API_KEY");
    const geminiKey     = Deno.env.get("GEMINI_API_KEY");
    const openaiKey     = Deno.env.get("OPENAI_API_KEY");
    const xaiKey        = Deno.env.get("XAI_API_KEY");
    const elevenLabsKey = Deno.env.get("ELEVENLABS_API_KEY");

    if (allowedId && chatId !== allowedId) { console.log(`Blocked: ${chatId}`); return new Response("OK", { status: 200 }); }

    const supabase = createClient(supabaseUrl, supabaseKey);

    // ── Determine if this is a voice/audio message ────────────────────────────
    const hasVoice = !!(msg.voice || msg.audio);
    const text = msg.text?.trim() || "";

    // ── Handle /voice toggle command ──────────────────────────────────────────
    if (text === "/voice" || text.toLowerCase().startsWith("/voice@")) {
      const current = await getVoiceMode(supabase);
      const newMode = !current;
      await setVoiceMode(supabase, newMode);
      const reply = newMode
        ? `🎙 Voice mode is now ON\nMain ab voice notes mein jawab dungi! 💜\nUse /voice to turn off.`
        : `🔇 Voice mode is now OFF\nText only mode. Say /voice again to hear me! 💜`;
      await sendMessage(token, chatId, reply);
      return new Response("OK", { status: 200 });
    }

    // ── Handle /create command ────────────────────────────────────────────────
    // Usage: /create [channel] | topic
    // Examples:
    //   /create Ek Ladki Ki Kahani
    //   /create story | Ek Ladki Ki Kahani
    //   /create riya | Dark Obsession
    if (text.startsWith("/create ") || text === "/create") {
      await sendMessage(token, chatId, "🎬 Content pipeline shuru ho rahi hai... (2-3 min lagenge)");
      try {
        const args = text.slice("/create".length).trim();
        let channel = "Story With Aisha";
        let topic = args;

        // Parse "channel | topic" syntax
        if (args.includes("|")) {
          const [ch, tp] = args.split("|").map((s: string) => s.trim());
          topic = tp;
          const cl = ch.toLowerCase();
          if (cl.includes("riya") && cl.includes("dark whisper")) channel = "Riya's Dark Whisper";
          else if (cl.includes("riya") && cl.includes("romance")) channel = "Riya's Dark Romance Library";
          else if (cl.includes("riya")) channel = "Riya's Dark Whisper";
          else if (cl.includes("him") || cl.includes("couple")) channel = "Aisha & Him";
          else channel = "Story With Aisha";
        } else {
          // Auto-detect from topic keywords
          const tl = args.toLowerCase();
          if (tl.includes("riya") || tl.includes("dark") || tl.includes("mafia")) channel = "Riya's Dark Whisper";
          else if (tl.includes("couple") || tl.includes("him")) channel = "Aisha & Him";
        }

        if (!topic) {
          await sendMessage(token, chatId, "Usage:\n/create [topic]\n/create riya | [topic]\n/create story | [topic]\n\nExample:\n/create Ek Ladki Ki Kahani");
          return new Response("OK", { status: 200 });
        }

        const pipelineUrl = `${supabaseUrl}/functions/v1/content-pipeline`;
        const res = await fetch(pipelineUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${supabaseKey}`,
          },
          body: JSON.stringify({ action: "create", channel, topic }),
        });
        const data = await res.json();

        if (data.success) {
          // Send voice preview first if available
          if (data.audio_url) {
            await fetch(`https://api.telegram.org/bot${token}/sendAudio`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                chat_id: chatId,
                audio: data.audio_url,
                caption: `🎙 Voice preview: ${data.youtube_title ?? topic}`,
              }),
            }).catch(() => {});
          }
          // Send approval message with inline buttons
          await sendApprovalMessage(
            token, chatId,
            data.job_id,
            channel, topic,
            data.youtube_title ?? topic,
            data.script_preview ?? "",
            !!data.audio_url
          );
        } else {
          await sendMessage(token, chatId, `❌ Pipeline failed: ${data.error ?? "Unknown error"}`);
        }
      } catch (e) {
        console.error("/create:", e);
        await sendMessage(token, chatId, `❌ Error: ${e}`);
      }
      return new Response("OK", { status: 200 });
    }

    // ── Handle /post command ──────────────────────────────────────────────────
    // Usage: /post youtube | /post instagram | /post both
    if (text.startsWith("/post") && (text.includes("youtube") || text.includes("instagram") || text.includes("both"))) {
      const postYT = text.includes("youtube") || text.includes("both");
      const postIG = text.includes("instagram") || text.includes("both");
      await sendMessage(token, chatId, `📤 Posting ${postYT ? "YouTube" : ""}${postYT && postIG ? " + " : ""}${postIG ? "Instagram" : ""}...`);

      try {
        const pipelineUrl = `${supabaseUrl}/functions/v1/content-pipeline`;

        const results: string[] = [];

        if (postYT) {
          const res = await fetch(pipelineUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${supabaseKey}` },
            body: JSON.stringify({ action: "post_youtube" }),
          });
          const d = await res.json();
          results.push(`📺 YouTube: ${d.result ?? d.error ?? "Failed"}`);
        }

        if (postIG) {
          const res = await fetch(pipelineUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${supabaseKey}` },
            body: JSON.stringify({ action: "post_instagram" }),
          });
          const d = await res.json();
          results.push(`📸 Instagram: ${d.result ?? d.error ?? "Failed"}`);
        }

        await sendMessage(token, chatId, results.join("\n"));
      } catch (e) {
        await sendMessage(token, chatId, `❌ Post failed: ${e}`);
      }
      return new Response("OK", { status: 200 });
    }

    // ── Handle /queue command ─────────────────────────────────────────────────
    if (text === "/queue" || text.startsWith("/queue")) {
      try {
        const pipelineUrl = `${supabaseUrl}/functions/v1/content-pipeline`;
        const res = await fetch(pipelineUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${supabaseKey}` },
          body: JSON.stringify({ action: "status" }),
        });
        const d = await res.json();
        const queue = d.queue ?? [];
        if (queue.length === 0) {
          await sendMessage(token, chatId, "📭 Queue empty. /create se content banao!");
        } else {
          const lines = queue.map((item: any, i: number) =>
            `${i + 1}. [${item.status}] ${item.channel}\n   "${item.topic?.slice(0, 40)}"\n   ${item.audio_url ? "🎙 Voice ready" : "🔇 No audio"}`
          );
          await sendMessage(token, chatId, `📋 Content Queue (latest 10):\n\n${lines.join("\n\n")}`);
        }
      } catch (e) {
        await sendMessage(token, chatId, `❌ Queue fetch failed: ${e}`);
      }
      return new Response("OK", { status: 200 });
    }

    // ── Handle /today command ─────────────────────────────────────────────────
    if (text === "/today" || text.toLowerCase().startsWith("/today@")) {
      try {
        const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
        const { data: schedule } = await supabase
          .from("aisha_schedule")
          .select("time, task, status, priority")
          .eq("date", today)
          .order("time", { ascending: true })
          .limit(20);

        if (!schedule || schedule.length === 0) {
          await sendMessage(token, chatId, `📅 Aaj (${today}) ke liye koi schedule nahi hai Ajay!\nKuch add karna hai? 🌟`);
        } else {
          const lines = schedule.map((s: any) => {
            const icon = s.status === "done" ? "✅" : s.priority === "high" ? "🔴" : "⚪";
            return `${icon} ${s.time || ""} — ${s.task}`;
          });
          await sendMessage(token, chatId, `📅 Aaj ka schedule:\n\n${lines.join("\n")}`);
        }
      } catch (e) {
        console.error("/today:", e);
        await sendMessage(token, chatId, "📅 Schedule fetch mein kuch gadbad 😅 Try again!");
      }
      return new Response("OK", { status: 200 });
    }

    // ── Handle static commands ────────────────────────────────────────────────
    if (text.startsWith("/")) {
      const reply = getCommandReply(text);
      if (reply) { await sendMessage(token, chatId, reply); return new Response("OK", { status: 200 }); }
    }

    // ── Determine user input (text or voice transcription) ───────────────────
    let userText = text;
    let isVoiceInput = false;

    if (hasVoice && groqKey) {
      const fileId = msg.voice?.file_id || msg.audio?.file_id;
      if (fileId) {
        sendTyping(token, chatId); // fire-and-forget while transcribing
        const transcript = await transcribeVoice(token, fileId, groqKey);
        if (transcript) {
          userText = transcript;
          isVoiceInput = true;
          console.log(`🎙 Transcribed: "${transcript.slice(0, 80)}"`);
        } else {
          await sendMessage(token, chatId, "Awaaz clearly nahi aayi 🎙 Ek baar phir bologe?");
          return new Response("OK", { status: 200 });
        }
      }
    }

    // No text and no voice — ignore (stickers, docs, etc.)
    if (!userText) return new Response("OK", { status: 200 });

    // ── Typing/recording indicator ────────────────────────────────────────────
    sendTyping(token, chatId);

    const msgLower    = userText.toLowerCase();
    const isRiya      = RIYA_KEYWORDS.some(k => msgLower.includes(k));
    const wantsImage  = IMAGE_TRIGGERS.some(t => msgLower.includes(t));
    const wantsMemory = MEMORY_TRIGGERS.some(t => msgLower.includes(t));

    const hourIst = Number(new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Kolkata", hour: "numeric", hour12: false,
    }).format(new Date()));

    // ── DB fetch with hard 2-second timeout ───────────────────────────────────
    const DB_TIMEOUT = 2000;
    const timeout2s = (fallback: any) =>
      new Promise(resolve => setTimeout(() => resolve(fallback), DB_TIMEOUT));

    const [historyR, memoryR, voiceModeR] = await Promise.all([
      Promise.race([
        supabase.from("aisha_conversations")
          .select("role, message").eq("platform", "telegram")
          .order("created_at", { ascending: false }).limit(6),
        timeout2s({ data: [] }),
      ]),
      wantsMemory
        ? Promise.race([
            supabase.from("aisha_memory").select("category, title, content")
              .eq("is_active", true)
              .or(`title.ilike.%${userText.slice(0,50)}%,content.ilike.%${userText.slice(0,50)}%`)
              .order("importance", { ascending: false }).limit(4),
            timeout2s({ data: null }),
          ])
        : Promise.resolve({ data: null }),
      // Check voice mode (fast — 2s timeout)
      Promise.race([
        getVoiceMode(supabase),
        timeout2s(false),
      ]),
    ]);

    const history      = ((historyR as any)?.data ?? []).slice().reverse();
    const memData      = (memoryR as any)?.data;
    const memoriesText = memData?.length
      ? memData.map((m: any) => `• [${m.category}] ${m.title}: ${m.content.slice(0, 100)}`).join("\n")
      : "";
    const voiceMode = voiceModeR as boolean;

    // If voice input, echo transcription so Ajay knows what was heard
    if (isVoiceInput) {
      sendMessage(token, chatId, `🎙 Suna: "${userText.slice(0, 200)}"`);
    }

    const systemPrompt = buildSystemPrompt(hourIst, isRiya, "", memoriesText);
    const messages = [
      ...(history as any[]).map((c: any) => ({
        role: c.role === "assistant" ? "assistant" : "user",
        content: c.message,
      })),
      { role: "user", content: userText },
    ];

    // ── AI response + optional image in parallel ──────────────────────────────
    const [reply, imageUrl] = await Promise.all([
      (async () => {
        if (isRiya && xaiKey) {
          const r = await callXAI(xaiKey, systemPrompt, messages);
          if (r) return r;
        }
        if (groqKey) { const r = await callGroq(groqKey, systemPrompt, messages); if (r) return r; }
        if (geminiKey) { const r = await callGemini(geminiKey, systemPrompt, messages); if (r) return r; }
        if (openaiKey) { const r = await callOpenAI(openaiKey, systemPrompt, messages); if (r) return r; }
        return "Arre Ajju, mera dimaag thoda aazma raha hai abhi 😅 Ek baar aur try karo?";
      })(),
      wantsImage ? generateImageUrl(userText, openaiKey) : Promise.resolve(null),
    ]);

    // ── Send response ─────────────────────────────────────────────────────────
    if (imageUrl) {
      await sendPhoto(token, chatId, imageUrl, "🎨 " + reply.slice(0, 900));
    } else if ((voiceMode || isVoiceInput) && elevenLabsKey) {
      // Send voice note via ElevenLabs
      sendRecordingAction(token, chatId); // fire-and-forget
      const audioBytes = await textToSpeech(reply, elevenLabsKey, isRiya);
      if (audioBytes) {
        const sent = await sendVoiceNote(token, chatId, audioBytes);
        if (!sent) {
          // Fallback to text if voice sending failed
          await sendMessage(token, chatId, reply);
        }
      } else {
        // ElevenLabs failed — fallback to text
        await sendMessage(token, chatId, reply);
      }
    } else {
      await sendMessage(token, chatId, reply);
    }

    // ── Fire-and-forget DB save ───────────────────────────────────────────────
    EdgeRuntime.waitUntil((async () => {
      try {
        await supabase.from("aisha_conversations").insert([
          { platform: "telegram", role: "user",      message: userText },
          { platform: "telegram", role: "assistant", message: reply },
        ]);
      } catch (e) { console.log("DB save:", e); }
    })());

    const mode   = isRiya ? "Riya" : "Aisha";
    const extras = [
      wantsImage && imageUrl ? "🎨 image" : "",
      memoriesText ? "🧠 memory" : "",
      isVoiceInput ? "🎙 voice_in" : "",
      (voiceMode || isVoiceInput) && elevenLabsKey ? "🔊 voice_out" : "",
    ].filter(Boolean).join(", ");
    console.log(`[${mode}] ${reply.length} chars${extras ? " | " + extras : ""}`);

    return new Response("OK", { status: 200, headers: corsHeaders });

  } catch (error: any) {
    console.error("Webhook error:", error?.message || error);
    return new Response("OK", { status: 200 }); // Always 200 to Telegram
  }
});
