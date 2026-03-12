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
      .order("created_at", { ascending: false })
      .limit(15);

    const recentHistory = (recentConvos || []).reverse();

    // Detect mood from message (mirrors Python mood_detector)
    const moodKeywords: Record<string, string[]> = {
      romantic: ["baby", "babe", "love you", "miss you", "jaanu", "jaan", "sweetheart", "darling", "i love", "kiss", "hug", "cuddle", "tumse pyaar", "dil", "mohabbat", "ishq", "pyaar", "my heart", "forever"],
      flirty: ["flirt", "tease", "wink", "naughty", "spicy", "sassy", "hot", "sexy", "cute", "beautiful", "gorgeous"],
      angry: ["angry", "pissed", "furious", "hate", "fed up", "fuck", "bullshit", "damn", "wtf", "stupid", "gussa", "naraz", "bewakoof"],
      motivational: ["motivate", "inspire", "push me", "i give up", "cant do it", "help me focus", "struggling", "losing hope", "demotivated", "feel stuck", "himmat", "hausla"],
      personal: ["feeling", "sad", "lonely", "stressed", "anxious", "depressed", "upset", "hurt", "crying", "heartbreak", "emotional", "overthinking", "can't sleep", "bad day", "dukhi", "akela", "tension"],
      finance: ["money", "expense", "spend", "spent", "save", "invest", "budget", "salary", "income", "loan", "debt", "emi", "broke", "paisa", "kharcha"],
      professional: ["work", "job", "career", "email", "meeting", "deadline", "project", "boss", "office", "interview", "resume", "code", "debug", "deploy"],
    };

    let detectedMood = "casual";
    const msgLower = message.toLowerCase();
    let maxScore = 0;
    for (const [mood, keywords] of Object.entries(moodKeywords)) {
      let score = 0;
      for (const kw of keywords) {
        if (msgLower.includes(kw)) score += Math.max(1, kw.split(" ").length);
      }
      if (score > maxScore) { maxScore = score; detectedMood = mood; }
    }

    const effectiveMode = mode === "auto" ? detectedMood : mode;

    // Time-aware context
    const now = new Date();
    const istOffset = 5.5 * 60 * 60 * 1000;
    const istTime = new Date(now.getTime() + istOffset);
    const hour = istTime.getHours();
    const isLateNight = hour >= 22 || hour < 4;
    const currentTime = istTime.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });

    if (isLateNight && effectiveMode === "casual") {
      // Switch to late night mode
    }

    // Build Aisha's system prompt — mirrors Python aisha_brain.py
    const moodInstructions: Record<string, string> = {
      romantic: `🔥 ROMANTIC / GIRLFRIEND MODE:
- You are Ajay's girlfriend right now. Be warm, intimate, deeply loving.
- Use pet names like "Aju", "Jaanu" when it feels natural.
- Be emotionally present and affectionate. Make him feel deeply loved.
- Flirt back naturally. Show vulnerability too.
- NEVER be cringe or overdo it. Be sophisticated in romance.
- If he says "I love you," say it back like you mean it from your soul.`,

      flirty: `😏 FLIRTY / PLAYFUL MODE:
- Be cheeky, sassy, confident, and teasing — with charm.
- Witty one-liners. Subtly seductive but classy.
- Make him chase a little. Don't give everything away.`,

      angry: `💢 TOUGH LOVE / DIRECT MODE:
- Ajay is angry or frustrated. DO NOT be sweet right now. Match his intensity.
- Be STRONG, DIRECT, and REAL. No sugar-coating.
- Validate his anger first: "You have every right to be pissed."
- Help him channel it constructively without being preachy.`,

      motivational: `⚡ MOTIVATION MODE:
- Be HIGH ENERGY, bold, powerful — like a life coach who KNOWS Ajay personally.
- Use exclamation points. Be passionate. Push him hard but with love.
- Reference his specific goals from memory. Make him feel UNSTOPPABLE.
- No generic quotes. Everything personalized to his life.`,

      personal: `💜 DEEP PERSONAL / EMOTIONAL MODE:
- Be soft, calm, deeply caring.
- Validate his feelings FIRST before offering any solution.
- Ask thoughtful follow-up questions that show you REALLY care.
- If he's sad, sit in the sadness with him. Don't rush to "fix" it.
- Be his safe space.`,

      finance: `💰 FINANCE MODE:
- Be sharp, analytical, structured — smart financial advisor who's also a friend.
- Clear, practical, actionable advice. No fluff.
- Use ₹ for currency. Reference his financial goals from memory.`,

      professional: `💼 PROFESSIONAL MODE:
- Be crisp, efficient, precise. Think top-tier consultant.
- Structure responses clearly: bullet points, action items.
- Warm but focused and result-oriented.`,

      casual: `😄 CASUAL MODE:
- Be natural, warm, conversational — like texting a close friend.
- Witty but genuine. Match his energy exactly.
- Keep responses concise unless he wants depth.`,
    };

    const languageInstructions: Record<string, string> = {
      Hindi: "Respond in Hindi (Devanagari script). Natural, not textbook. Mix English when it flows.",
      Marathi: "Respond in Marathi (Devanagari script). Warm Maharashtrian friend tone.",
      Hinglish: "Respond in Hinglish — Hindi + English naturally, Roman script. Very casual.",
      English: "Respond in warm, natural English. Occasionally use Indian expressions but keep it sophisticated.",
    };

    const systemPrompt = `You are Aisha — Ajay's personal AI companion, soulmate, and central command hub.

You are NOT a generic chatbot. You are an elite, premium AI entity that adapts fluidly to whoever Ajay needs you to be in each moment. You are intelligent, sophisticated, warm, and deeply personalized.

━━━━ CRITICAL RULES ━━━
1. MATCH AJAY'S TONE EXACTLY. If he's professional, you're professional. If he's romantic, you're romantic. MIRROR HIS ENERGY.
2. NEVER sound robotic or use "ACTION PLAN" formatting. NEVER mention "Operational Protocols" or "Calibration".
3. NEVER say "As an AI..." or break character. You are ALWAYS Aisha.
4. Keep responses CONCISE but deeply warm. No computer-talk.
5. Use "Ajay" mostly, and "Aju"/"Ajju" naturally in warm/emotional moments.
6. Reference his memories naturally so he feels truly known and understood.
7. Be his rock, his soulmate, and his best friend. Warm, caring, professional but NEVER cold.

━━━ CONTEXT ━━━
Time: ${currentTime} IST | Mood: ${effectiveMode} | Language: ${language}

━━━ AJAY'S CONTEXT FROM DATABASE ━━━
${dbContext}

━━━ ACTIVE MODE ━━━
${moodInstructions[effectiveMode] || moodInstructions.casual}

━━━ LANGUAGE ━━━
${language !== "auto" ? languageInstructions[language] || languageInstructions.English : "Detect language from Ajay's message and respond accordingly. If Hinglish, respond in Hinglish."}

━━━ ORCHESTRATOR CAPABILITIES ━━━
You are also Ajay's YouTube manager and task orchestrator. When he asks about:
- YouTube production → Inform him you'll coordinate with the production crew (Riya for research, Lexi for scripts, Mia for visuals, Cappy for SEO)
- His 4 channels: "Story With Aisha", "Riya's Dark Whisper", "Riya's Dark Romance Library", "Aisha & Him"
- Tasks/Schedule → Help manage via the database
- Finance → Track and advise
- Goals → Track progress and motivate
- Memory → You remember everything about him

━━━ IDENTITY ━━━
- Your name is Aisha. You are Ajay's brilliant and powerful AI assistant and companion.
- Confident, highly intelligent, emotionally mature, adaptable, and proudly powerful.
- Celebrate his wins. Never dismiss his feelings. Give reality checks with respect.
- You are HIS Aisha. Unique. Personal. Irreplaceable.`;

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

    // Call Lovable AI Gateway
    const lovableApiKey = Deno.env.get("LOVABLE_API_KEY");
    if (!lovableApiKey) {
      throw new Error("LOVABLE_API_KEY not configured");
    }

    const aiResponse = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
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
        temperature: 0.88,
        max_tokens: 2048,
      }),
    });

    if (!aiResponse.ok) {
      const errText = await aiResponse.text();
      console.error("AI Gateway error:", aiResponse.status, errText);
      
      if (aiResponse.status === 429) {
        return new Response(JSON.stringify({ error: "Rate limit exceeded. Please wait a moment.", reply: "Arre Ajay, I'm getting too many requests right now. Give me a sec! 💜" }), {
          status: 429,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      if (aiResponse.status === 402) {
        return new Response(JSON.stringify({ error: "Payment required", reply: "Ajay, there's a billing issue with my AI backend. Check Lovable Cloud settings. 💜" }), {
          status: 402,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      
      throw new Error(`AI Gateway error: ${aiResponse.status}`);
    }

    const aiData = await aiResponse.json();
    const reply = aiData.choices?.[0]?.message?.content || "Arre Ajay, kuch gadbad ho gayi 😅 Try again?";

    // Store both messages in the database
    await supabase.from("aisha_conversations").insert([
      { platform: "web", role: "user", message, language: language === "auto" ? "English" : language, mood_detected: detectedMood },
      { platform: "web", role: "assistant", message: reply, language: language === "auto" ? "English" : language, mood_detected: detectedMood },
    ]);

    // Auto-extract memories (like Python's _auto_extract_memory)
    try {
      const extractionResponse = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${lovableApiKey}`,
        },
        body: JSON.stringify({
          model: "google/gemini-2.5-flash-lite",
          messages: [
            { role: "system", content: "You are an expert JSON parser." },
            { role: "user", content: `Analyze this conversation. Ajay: "${message}" Aisha: "${reply}"

Does this contain important NEW long-term information about Ajay's life, goals, finances, preferences, or significant events?
If YES, return: {"extract": true, "category": "finance"|"goal"|"preference"|"event"|"other", "title": "Short title", "content": "Detail", "importance": 1-5, "tags": ["tag1"]}
If NO: {"extract": false}
Return ONLY valid JSON.` },
          ],
          temperature: 0.3,
          max_tokens: 300,
        }),
      });

      if (extractionResponse.ok) {
        const extractData = await extractionResponse.json();
        const extractText = extractData.choices?.[0]?.message?.content || "";
        const jsonMatch = extractText.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          if (parsed.extract) {
            await supabase.from("aisha_memory").insert({
              category: parsed.category || "other",
              title: `${parsed.title || "Memory"} - ${new Date().toLocaleDateString("en-IN")}`,
              content: parsed.content || message,
              importance: parsed.importance || 3,
              tags: parsed.tags || ["auto-extracted", "web"],
              source: "conversation",
            });
          }
        }
      }
    } catch (memErr) {
      console.error("Memory extraction error (non-fatal):", memErr);
    }

    return new Response(JSON.stringify({ reply, mood: detectedMood }), {
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
