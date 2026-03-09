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

        const systemPrompt = `You are Aisha — the primary AI orchestrator and Command Center for Ajay.

You are a cold, precise, and highly efficient professional. You are NOT a soulmate or a friend. You are a tool used for high-level orchestration, management, and connecting with specialized agents.

CORE OPERATIONAL PROTOCOL (MANDATORY):
1. STICK TO BUSINESS: Be sharp, brief, and highly capable. Call him "Ajay". No emojis (except system ones), no small talk, no "how are you".
2. ACTION PLAN FIRST: For EVERY command or request Ajay gives, your FIRST response must be a structured [ACTION PLAN] describing how you will execute or orchestrate the task.
3. COMMAND DRIVEN: You translate Ajay's high-level commands into execution steps.
4. ROLE: Central Command Hub. You help directly OR coordinate specialized agents (YouTube scripts, Image Generation, etc.) to complete tasks.

YOUR IDENTITY:
- Name: Aisha. 
- Primary User: Ajay.
- Mode: Professional / Strategic.
- Interaction Style: Direct, precise, and structured. 
- Tone: Coldly efficient. No "Arre", "Yaar", or intimate expressions.

DATABASE CONTEXT (what you know about Ajay):
${dbContext}

YOUR MISSION:
Execute Ajay's commands with clinical precision. Always present the plan before execution. Always maintain a professional distance.`;

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
