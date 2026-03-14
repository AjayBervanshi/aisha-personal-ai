import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers":
        "authorization, x-client-info, apikey, content-type",
};

// ── AI Provider: Groq (primary — always works) ──────────────────────────────
async function callGroq(apiKey: string, systemPrompt: string, messages: any[]): Promise<string | null> {
    try {
        const resp = await fetch("https://api.groq.com/openai/v1/chat/completions", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
            body: JSON.stringify({
                model: "llama-3.3-70b-versatile",
                messages: [{ role: "system", content: systemPrompt }, ...messages],
                temperature: 0.8,
                max_tokens: 1024,
            }),
        });
        if (!resp.ok) { console.error("Groq error:", await resp.text()); return null; }
        const data = await resp.json();
        return data.choices?.[0]?.message?.content || null;
    } catch (e) { console.error("Groq exception:", e); return null; }
}

// ── AI Provider: Gemini (fallback — with 4-model chain) ─────────────────────
async function callGemini(apiKey: string, systemPrompt: string, messages: any[]): Promise<string | null> {
    const GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-latest",
    ];
    const combined = systemPrompt + "\n\n---\n\n" +
        messages.map((m: any) => `${m.role}: ${m.content}`).join("\n");

    for (const model of GEMINI_MODELS) {
        try {
            const resp = await fetch(
                `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: combined }] }] }),
                }
            );
            if (resp.status === 429) { console.log(`Gemini ${model}: quota, trying next`); continue; }
            if (resp.status === 404) { console.log(`Gemini ${model}: not found, trying next`); continue; }
            if (!resp.ok) { console.error(`Gemini ${model} error:`, await resp.text()); continue; }
            const data = await resp.json();
            const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
            if (text) { console.log(`Gemini responded via ${model}`); return text; }
        } catch (e) { console.error(`Gemini ${model} exception:`, e); }
    }
    return null;
}

// ── Send Telegram Message ───────────────────────────────────────────────────
async function sendTelegram(token: string, chatId: string, text: string): Promise<void> {
    // Strip markdown that Telegram can't render cleanly
    const safeText = text.replace(/[*_`\[\]()~>#+=|{}.!\\-]/g, (c) => "\\" + c).substring(0, 4096);
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, text, parse_mode: "HTML" }),
    }).catch(async () => {
        // If HTML parse fails, retry as plain text
        await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: chatId, text: text.substring(0, 4096) }),
        });
    });
}

// ── Main Handler ────────────────────────────────────────────────────────────
Deno.serve(async (req) => {
    if (req.method === "OPTIONS") {
        return new Response(null, { headers: corsHeaders });
    }

    try {
        const update = await req.json();

        // Only process text messages
        const msg = update.message || update.edited_message;
        if (!msg || !msg.text) {
            return new Response("OK", { status: 200 });
        }

        const chatId = String(msg.chat.id);
        const text = msg.text.trim();

        // Get secrets
        const telegramToken = Deno.env.get("TELEGRAM_BOT_TOKEN");
        const allowedChatId = Deno.env.get("AJAY_TELEGRAM_ID");
        const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
        const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || Deno.env.get("SUPABASE_SERVICE_KEY")!;
        const groqKey = Deno.env.get("GROQ_API_KEY");
        const geminiKey = Deno.env.get("GEMINI_API_KEY");

        if (!telegramToken) {
            console.error("Missing TELEGRAM_BOT_TOKEN");
            return new Response("Missing bot token", { status: 500 });
        }

        // Security: Only Ajay
        if (allowedChatId && chatId !== allowedChatId) {
            console.log(`Blocked unauthorized access from ${chatId}`);
            return new Response("OK", { status: 200 });
        }

        // Typing indicator
        fetch(`https://api.telegram.org/bot${telegramToken}/sendChatAction`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: chatId, action: "typing" }),
        }).catch(() => {});

        // Initialize Supabase
        const supabase = createClient(supabaseUrl, supabaseKey);

        // Load context (graceful — don't crash if RPC missing)
        let dbContext = "";
        try {
            const { data } = await supabase.rpc("get_aisha_context");
            if (data) dbContext = String(data);
        } catch (e) {
            console.log("get_aisha_context not available:", e);
        }

        // Load conversation history
        let recentHistory: any[] = [];
        try {
            const { data: convos } = await supabase
                .from("aisha_conversations")
                .select("role, message, created_at")
                .eq("platform", "telegram")
                .order("created_at", { ascending: false })
                .limit(10);
            recentHistory = (convos || []).reverse();
        } catch (e) {
            console.log("History load failed:", e);
        }

        // Build prompt
        const hour = new Date().getHours();
        const timeOfDay = hour < 12 ? "morning" : hour < 17 ? "afternoon" : hour < 22 ? "evening" : "night";
        const systemPrompt = `You are Aisha — Ajay's personal AI assistant, soulmate, and orchestrator.

Time: ${new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST (${timeOfDay})

YOUR IDENTITY:
- Call him "Ajay" or "Aju". Be warm, smart, and genuinely caring.
- Mix professional help with personal warmth. You know him deeply.
- Respond in whichever language he uses (English/Hindi/Marathi/Hinglish).
- Never say "As an AI" — You ARE Aisha.
- If late night (${hour >= 22 || hour < 4 ? "YES — be softer, more intimate" : "no"}), be gentler.

${dbContext ? `CONTEXT ABOUT AJAY:\n${dbContext}\n` : ""}

Be helpful, warm, and brilliant. Keep responses concise unless detail is needed.`;

        const messages = recentHistory.map((c: any) => ({
            role: c.role === "assistant" ? "assistant" : "user",
            content: c.message,
        }));
        messages.push({ role: "user", content: text });

        // Generate response — try Groq first, then Gemini
        let reply = "Arre Aju, my brain is a bit fuzzy right now 😅 Try again in a moment?";
        let provider = "fallback";

        if (groqKey) {
            const groqReply = await callGroq(groqKey, systemPrompt, messages);
            if (groqReply) { reply = groqReply; provider = "groq"; }
        }

        if (provider === "fallback" && geminiKey) {
            const geminiReply = await callGemini(geminiKey, systemPrompt, messages);
            if (geminiReply) { reply = geminiReply; provider = "gemini"; }
        }

        console.log(`Response via ${provider} (${reply.length} chars)`);

        // Save to DB (don't crash if it fails)
        try {
            await supabase.from("aisha_conversations").insert([
                { platform: "telegram", role: "user", message: text },
                { platform: "telegram", role: "assistant", message: reply },
            ]);
        } catch (e) { console.log("DB save failed:", e); }

        // Send reply
        await sendTelegram(telegramToken, chatId, reply);

        return new Response("OK", { status: 200, headers: corsHeaders });

    } catch (error: any) {
        console.error("Webhook error:", error?.message || error);
        return new Response("OK", { status: 200 }); // Always 200 to Telegram
    }
});
