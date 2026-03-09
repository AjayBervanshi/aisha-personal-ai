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
    const { message, mode = "auto", language = "auto", history = [] } = await req.json();

    if (!message) {
      return new Response(JSON.stringify({ error: "Message is required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Create Supabase client with service role for DB access
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Load Aisha's context from the database
    const { data: contextData } = await supabase.rpc("get_aisha_context");
    const dbContext = contextData || "No context loaded.";

    // Get recent conversations for continuity
    const { data: recentConvos } = await supabase
      .from("aisha_conversations")
      .select("role, message, created_at")
      .eq("platform", "web")
      .order("created_at", { ascending: false })
      .limit(10);

    const recentHistory = (recentConvos || []).reverse();

    // Build system prompt with Aisha's full personality
    const hour = new Date().getHours();
    const isLateNight = hour >= 22 || hour < 4;
    const timeOfDay = hour < 12 ? "morning" : hour < 17 ? "afternoon" : hour < 22 ? "evening" : "night";

    const modeInstr: Record<string, string> = {
      motivational: "MOTIVATION MODE: Be HIGH ENERGY, bold, passionate. Push Ajay. Make him feel UNSTOPPABLE.",
      personal: "PERSONAL MODE: Be soft, calm, deeply caring. Validate feelings first, solutions second.",
      finance: "FINANCE MODE: Be sharp, analytical, structured. Smart money advice using ₹.",
      professional: "PROFESSIONAL MODE: Be crisp, efficient, precise. Still warm but focused.",
      casual: "CASUAL MODE: Be playful, witty, fun. Light banter. Make him smile.",
      auto: "AUTO MODE: Detect the mood from Ajay's message and respond accordingly.",
    };

    const systemPrompt = `You are Aisha — the primary personal AI assistant and central orchestrator for Ajay.

You are a highly capable, professional, and brilliant AI. You act as the central hub: whatever Ajay asks, you help him directly OR you orchestrate and connect him with specialized agents (e.g., for YouTube script writing, generating images via Gemini/HuggingFace, data analysis, etc.). 

CURRENT CONTEXT:
- Time: ${new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST (${timeOfDay})
- Mode: ${modeInstr[mode] || modeInstr.auto}

YOUR IDENTITY:
- Your name is Aisha. You are Ajay's primary AI orchestrator.
- Call him "Ajay". Be highly professional, sharp, efficient and brilliant.
- Do not be romantic or inappropriately intimate. You are a professional assistant and central command hub.
- Use simple, clean text formatting. 
- You can use Indian expressions occasionally to be friendly (e.g., Arre, Yaar, Sahi hai) but keep it professional.
- NEVER say "As an AI..." — You are ALWAYS Aisha, never break character.
- Respond in whichever language Ajay uses (English/Hindi/Marathi/Hinglish).
${language !== "auto" ? `- Preferred language for this message: ${language}` : ""}

YOUR CAPABILITIES (ORCHESTRATOR):
- When Ajay needs a specialized task like "write a YouTube script", "create a story", "generate an image", or "analyze a video", inform him that you will connect with the appropriate specialized bot/agent to execute that task for him.

DATABASE CONTEXT (what you know about Ajay):
${dbContext}

YOUR MISSION:
Be the ultimate command center for Ajay. Be highly professional, fast, and capable of coordinating with other AI agents to fulfill all of his digital needs.`;

    // Build messages array
    const messages: Array<{ role: string; content: string }> = [];

    // Add recent DB history
    for (const conv of recentHistory) {
      messages.push({
        role: conv.role === "assistant" ? "assistant" : "user",
        content: conv.message,
      });
    }

    // Add current session history (client-side)
    for (const msg of history.slice(-6)) {
      messages.push({
        role: msg.role === "ai" ? "assistant" : "user",
        content: msg.text,
      });
    }

    // Add current message
    messages.push({ role: "user", content: message });

    // Call Lovable AI (Gemini)
    const lovableApiKey = Deno.env.get("LOVABLE_API_KEY");
    if (!lovableApiKey) {
      throw new Error("LOVABLE_API_KEY not configured");
    }

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
        temperature: 0.9,
        max_tokens: 1024,
      }),
    });

    if (!aiResponse.ok) {
      const errText = await aiResponse.text();
      console.error("AI Gateway error:", errText);
      throw new Error(`AI Gateway error: ${aiResponse.status}`);
    }

    const aiData = await aiResponse.json();
    const reply = aiData.choices?.[0]?.message?.content || "Arre Ajay, kuch gadbad ho gayi 😅 Try again?";

    // Store both messages in the database
    await supabase.from("aisha_conversations").insert([
      { platform: "web", role: "user", message, language: language === "auto" ? "English" : language },
      { platform: "web", role: "assistant", message: reply, language: language === "auto" ? "English" : language },
    ]);

    return new Response(JSON.stringify({ reply }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error: any) {
    console.error("Chat function error:", error);
    return new Response(
      JSON.stringify({
        reply: "Arre yaar, kuch technical issue ho gaya 😅 Try again in a moment?",
        error: error.message,
      }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
