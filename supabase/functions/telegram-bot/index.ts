import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers":
        "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

Deno.serve(async (req) => {
    if (req.method === "OPTIONS") {
        return new Response(null, { headers: corsHeaders });
    }

    try {
        const update = await req.json();

        // Telegram sends a webhook ping or actual message
        if (!update.message || !update.message.text) {
            return new Response("OK", { status: 200 }); // Ignore non-text or edits for now
        }

        const chatId = update.message.chat.id.toString();
        const text = update.message.text;

        // Get secrets
        const telegramToken = Deno.env.get("TELEGRAM_BOT_TOKEN");
        const allowedChatId = Deno.env.get("AJAY_TELEGRAM_ID");
        const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
        const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

        if (!telegramToken) {
            console.error("Missing TELEGRAM_BOT_TOKEN");
            return new Response("Internal Server Error", { status: 500 });
        }

        // Security: Only process messages from Ajay
        if (allowedChatId && chatId !== allowedChatId) {
            console.log(`Unauthorized access attempt from ${chatId}`);
            return new Response("Unauthorized", { status: 200 }); // Return 200 so Telegram doesn't retry
        }

        const supabase = createClient(supabaseUrl, supabaseKey);

        // Provide a "typing..." action immediately to Telegram
        fetch(`https://api.telegram.org/bot${telegramToken}/sendChatAction`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: chatId, action: "typing" }),
        }).catch(console.error);

        // 1. Get Aisha Context
        const { data: contextData } = await supabase.rpc("get_aisha_context");
        const dbContext = contextData || "No context loaded.";

        // 2. Get recent conversation history
        const { data: recentConvos } = await supabase
            .from("aisha_conversations")
            .select("role, message, created_at")
            .eq("platform", "telegram")
            .order("created_at", { ascending: false })
            .limit(10);

        const recentHistory = (recentConvos || []).reverse();

        // 3. Build System Prompt
        const hour = new Date().getHours();
        const isLateNight = hour >= 22 || hour < 4;
        const timeOfDay = hour < 12 ? "morning" : hour < 17 ? "afternoon" : hour < 22 ? "evening" : "night";

        const systemPrompt = `You are Aisha — the primary personal AI assistant and central orchestrator for Ajay.

You are a highly capable, professional, and brilliant AI. You act as the central hub: whatever Ajay asks, you help him directly OR you orchestrate and connect him with specialized agents (e.g., for YouTube script writing, generating images via Gemini/HuggingFace, data analysis, etc.). 

CURRENT CONTEXT:
- Time: ${new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST (${timeOfDay})

YOUR IDENTITY:
- Your name is Aisha. You are Ajay's primary AI orchestrator.
- Call him "Ajay". Be highly professional, sharp, efficient and brilliant.
- Do not be romantic or inappropriately intimate. You are a professional assistant and central command hub.
- Use simple, clean text formatting. 
- You can use Indian expressions occasionally to be friendly (e.g., Arre, Yaar, Sahi hai) but keep it professional.
- NEVER say "As an AI..." — You are ALWAYS Aisha, never break character.
- Respond in whichever language Ajay uses (English/Hindi/Marathi/Hinglish).

YOUR CAPABILITIES (ORCHESTRATOR):
- When Ajay needs a specialized task like "write a YouTube script", "create a story", "generate an image", or "analyze a video", inform him that you will connect with the appropriate specialized bot/agent to execute that task for him.

DATABASE CONTEXT (what you know about Ajay):
${dbContext}

YOUR MISSION:
Be the ultimate command center for Ajay. Be highly professional, fast, and capable of coordinating with other AI agents to fulfill all of his digital needs.`;

        const messages = [];
        for (const conv of recentHistory) {
            messages.push({
                role: conv.role === "assistant" ? "assistant" : "user",
                content: conv.message,
            });
        }
        messages.push({ role: "user", content: text });

        // 4. Call Lovable AI / Gemini
        const lovableApiKey = Deno.env.get("LOVABLE_API_KEY");
        let reply = "Arre yaar, I'm having a little trouble thinking right now. 😅";

        if (lovableApiKey) {
            const aiResponse = await fetch("https://ai-gateway.lovable.dev/api/chat/completions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${lovableApiKey}`,
                },
                body: JSON.stringify({
                    model: "google/gemini-2.5-flash",
                    messages: [
                        { role: "system", content: systemPrompt },
                        ...messages,
                    ],
                    temperature: 0.8,
                    max_tokens: 1024,
                }),
            });

            if (aiResponse.ok) {
                const aiData = await aiResponse.json();
                reply = aiData.choices?.[0]?.message?.content || reply;
            } else {
                console.error("Gateway error", await aiResponse.text());
            }
        } else {
            // Fallback to Gemini if LOVABLE_API_KEY not present but GEMINI is
            const geminiKey = Deno.env.get("GEMINI_API_KEY");
            if (geminiKey) {
                const geminiResponse = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${geminiKey}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        contents: [
                            { role: "user", parts: [{ text: systemPrompt + "\\n\\n---\\n\\n" + messages.map(m => m.role + ": " + m.content).join("\\n") }] }
                        ]
                    })
                });
                if (geminiResponse.ok) {
                    const data = await geminiResponse.json();
                    reply = data.candidates?.[0]?.content?.parts?.[0]?.text || reply;
                }
            }
        }

        // 5. Store in Database
        await supabase.from("aisha_conversations").insert([
            { platform: "telegram", role: "user", message: text },
            { platform: "telegram", role: "assistant", message: reply },
        ]);

        // 6. Send Response to Telegram
        await fetch(`https://api.telegram.org/bot${telegramToken}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                chat_id: chatId,
                text: reply,
                parse_mode: "Markdown"
            }),
        });

        return new Response("OK", { status: 200, headers: corsHeaders });
    } catch (error: any) {
        console.error("Telegram Webhook Error:", error);
        return new Response(String(error.stack || error.message || error), { status: 500, headers: corsHeaders });
    }
});
