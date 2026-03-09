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
