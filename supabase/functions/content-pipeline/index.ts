// content-pipeline/index.ts
// Supabase Edge Function — full content generation + YouTube/Instagram posting
// Called by: Telegram bot (/create, /post), Lovable web UI

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY")!;
const ELEVENLABS_API_KEY = Deno.env.get("ELEVENLABS_API_KEY")!;
const YOUTUBE_REFRESH_TOKEN = Deno.env.get("YOUTUBE_REFRESH_TOKEN")!;
const YOUTUBE_CLIENT_ID = Deno.env.get("YOUTUBE_CLIENT_ID")!;
const YOUTUBE_CLIENT_SECRET = Deno.env.get("YOUTUBE_CLIENT_SECRET")!;
const INSTAGRAM_ACCESS_TOKEN = Deno.env.get("INSTAGRAM_ACCESS_TOKEN")!;
const INSTAGRAM_BUSINESS_ID = Deno.env.get("INSTAGRAM_BUSINESS_ID")!;
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const VOICE_IDS: Record<string, string> = {
  "Story With Aisha": "wdymxIQkYn7MJCYCQF2Q",
  "Aisha & Him": "wdymxIQkYn7MJCYCQF2Q",
  "Riya's Dark Whisper": "BpjGufoPiobT79j2vtj4",
  "Riya's Dark Romance Library": "BpjGufoPiobT79j2vtj4",
};

const CHANNEL_PROMPTS: Record<string, string> = {
  "Story With Aisha": `You are Aisha, a warm Hindi storyteller. Write emotional love stories in pure Devanagari Hindi.
Tone: warm, cinematic, heart-touching. Format: 8-15 minute narration with dialogue.
Always write 100% Devanagari Hindi — no Roman script.`,
  "Riya's Dark Whisper": `You are Riya, a dark Hindi storyteller. Write adult/explicit dark romance in pure Devanagari Hindi.
Tone: mysterious, seductive, psychological. Format: 10-20 minute slow-burn story.
Always write 100% Devanagari Hindi — no Roman script.`,
  "Riya's Dark Romance Library": `You are Riya, writing mafia romance novels in pure Devanagari Hindi.
Tone: intense, dramatic, novel-style. Format: 15-25 minute chapter episode.
Always write 100% Devanagari Hindi — no Roman script.`,
  "Aisha & Him": `You are Aisha writing couple short content in Hinglish.
Tone: relatable, funny, sweet. Format: 30-second to 3-minute dialogue reel.`,
};

// ─── Gemini REST call ────────────────────────────────────────────────────────
async function gemini(prompt: string, system: string): Promise<string> {
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: `${system}\n\n${prompt}` }] }],
        generationConfig: { temperature: 0.9, maxOutputTokens: 8192 },
      }),
    }
  );
  const d = await res.json();
  return d.candidates?.[0]?.content?.parts?.[0]?.text ?? "Generation failed";
}

// ─── ElevenLabs TTS ──────────────────────────────────────────────────────────
async function generateVoice(text: string, voiceId: string): Promise<Uint8Array | null> {
  try {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
      method: "POST",
      headers: {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text.slice(0, 4000),
        model_id: "eleven_multilingual_v2",
        voice_settings: { stability: 0.5, similarity_boost: 0.75 },
      }),
    });
    if (!res.ok) return null;
    const buf = await res.arrayBuffer();
    return new Uint8Array(buf);
  } catch {
    return null;
  }
}

// ─── YouTube OAuth refresh ───────────────────────────────────────────────────
async function getYouTubeToken(): Promise<string | null> {
  try {
    const res = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: YOUTUBE_CLIENT_ID,
        client_secret: YOUTUBE_CLIENT_SECRET,
        refresh_token: YOUTUBE_REFRESH_TOKEN,
        grant_type: "refresh_token",
      }),
    });
    const d = await res.json();
    return d.access_token ?? null;
  } catch {
    return null;
  }
}

// ─── Upload audio to Supabase Storage ───────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function uploadAudio(
  supabase: any,
  audioBytes: Uint8Array,
  filename: string
): Promise<string | null> {
  const { data, error } = await supabase.storage
    .from("content-audio")
    .upload(filename, audioBytes, { contentType: "audio/mpeg", upsert: true });
  if (error) return null;
  const { data: urlData } = supabase.storage.from("content-audio").getPublicUrl(filename);
  return urlData.publicUrl;
}

// ─── Post to Instagram (image post with caption) ────────────────────────────
async function postToInstagram(caption: string, imageUrl?: string): Promise<string> {
  // Step 1: Create media container
  const params: Record<string, string> = {
    caption,
    access_token: INSTAGRAM_ACCESS_TOKEN,
  };

  if (imageUrl) {
    params.image_url = imageUrl;
  } else {
    // Use a default branded image from Supabase Storage
    params.image_url = `${SUPABASE_URL}/storage/v1/object/public/content-audio/default_thumbnail.jpg`;
  }

  const containerRes = await fetch(
    `https://graph.facebook.com/v21.0/${INSTAGRAM_BUSINESS_ID}/media`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }
  );
  const container = await containerRes.json();
  if (!container.id) return `Instagram container failed: ${JSON.stringify(container)}`;

  // Step 2: Publish
  const publishRes = await fetch(
    `https://graph.facebook.com/v21.0/${INSTAGRAM_BUSINESS_ID}/media_publish`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ creation_id: container.id, access_token: INSTAGRAM_ACCESS_TOKEN }),
    }
  );
  const pub = await publishRes.json();
  return pub.id ? `Posted! Instagram ID: ${pub.id}` : `Publish failed: ${JSON.stringify(pub)}`;
}

// ─── YouTube upload (audio as video) ─────────────────────────────────────────
async function postToYouTube(
  title: string,
  description: string,
  audioUrl: string
): Promise<string> {
  const accessToken = await getYouTubeToken();
  if (!accessToken) return "YouTube token refresh failed";

  // For audio-only content: upload the MP3 directly
  // YouTube accepts audio; it shows a static image
  try {
    const audioRes = await fetch(audioUrl);
    const audioBuffer = await audioRes.arrayBuffer();

    const metadata = {
      snippet: {
        title: title.slice(0, 100),
        description,
        tags: ["hindi", "love story", "aisha", "hindi kahani"],
        categoryId: "22",
        defaultLanguage: "hi",
      },
      status: { privacyStatus: "public" },
    };

    // Resumable upload
    const initRes = await fetch(
      "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
          "X-Upload-Content-Type": "audio/mpeg",
          "X-Upload-Content-Length": audioBuffer.byteLength.toString(),
        },
        body: JSON.stringify(metadata),
      }
    );

    const uploadUrl = initRes.headers.get("location");
    if (!uploadUrl) return `YouTube init failed: ${initRes.status}`;

    const uploadRes = await fetch(uploadUrl, {
      method: "PUT",
      headers: {
        "Content-Type": "audio/mpeg",
        "Content-Length": audioBuffer.byteLength.toString(),
      },
      body: audioBuffer,
    });

    const result = await uploadRes.json();
    return result.id
      ? `Uploaded! YouTube ID: ${result.id} → https://youtube.com/watch?v=${result.id}`
      : `Upload failed: ${JSON.stringify(result)}`;
  } catch (e) {
    return `YouTube upload error: ${e}`;
  }
}

// ─── Main pipeline ───────────────────────────────────────────────────────────
async function runPipeline(
  channel: string,
  topic: string,
  format: string = "Long Form"
): Promise<Record<string, string>> {
  const channelPrompt = CHANNEL_PROMPTS[channel] ?? CHANNEL_PROMPTS["Story With Aisha"];
  const voiceId = VOICE_IDS[channel] ?? VOICE_IDS["Story With Aisha"];

  console.log(`[Pipeline] ${channel} | ${topic}`);

  // 1. Research
  const research = await gemini(
    `Topic: "${topic}"\nWrite a 200-word story brief: characters, conflict, emotional hook, viral angle.`,
    channelPrompt
  );

  // 2. Script
  const script = await gemini(
    `Story Brief:\n${research}\n\nWrite the complete script with hook, narration, dialogue, [PAUSE] notes, and CTA.
Format: ${format === "Short/Reel" ? "30-60 second reel" : "8-15 minute full story"}`,
    channelPrompt
  );

  // 3. SEO
  const seo = await gemini(
    `Script excerpt:\n${script.slice(0, 500)}\n\nCreate:
1. YouTube title (max 60 chars, Hindi Devanagari)
2. YouTube description (SEO optimized, Devanagari)
3. Instagram caption (max 150 chars)
4. 20 hashtags
5. Thumbnail text (3-5 words)`,
    "You are an expert Hindi YouTube SEO specialist."
  );

  // Parse SEO fields (simple extraction)
  const titleMatch = seo.match(/(?:title|शीर्षक)[^\n]*\n([^\n]+)/i);
  const youtubeTitle = titleMatch?.[1]?.trim() ?? topic;

  return { research, script, seo, youtubeTitle };
}

// ─── HTTP Handler ─────────────────────────────────────────────────────────────
serve(async (req) => {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  };

  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    const body = await req.json();
    const action = body.action; // "create" | "post_youtube" | "post_instagram" | "create_and_post"
    const channel = body.channel ?? "Story With Aisha";
    const topic = body.topic ?? "";
    const format = body.format ?? "Long Form";

    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

    if (action === "create" || action === "create_and_post") {
      if (!topic) {
        return new Response(JSON.stringify({ error: "topic required" }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      // Run pipeline
      const { research, script, seo, youtubeTitle } = await runPipeline(channel, topic, format);

      // Generate voice
      const voiceId = VOICE_IDS[channel] ?? VOICE_IDS["Story With Aisha"];
      const audioBytes = await generateVoice(script, voiceId);

      let audioUrl: string | null = null;
      if (audioBytes) {
        const filename = `${Date.now()}_${channel.replace(/\s+/g, "_")}.mp3`;
        audioUrl = await uploadAudio(supabase, audioBytes, filename);
      }

      // Save to DB
      const { data: saved } = await supabase
        .from("content_queue")
        .insert({
          channel,
          topic,
          script,
          seo_package: seo,
          youtube_title: youtubeTitle,
          audio_url: audioUrl,
          status: "ready",
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      const jobId = saved?.id;
      let youtubeResult = null;
      let instagramResult = null;

      // Auto-post if requested
      if (action === "create_and_post" && audioUrl) {
        youtubeResult = await postToYouTube(youtubeTitle, seo, audioUrl);
        const igCaption = seo.match(/instagram caption[^\n]*\n([^\n]+)/i)?.[1] ?? topic;
        instagramResult = await postToInstagram(igCaption);

        // Update status
        if (jobId) {
          await supabase.from("content_queue").update({ status: "posted" }).eq("id", jobId);
        }
      }

      return new Response(
        JSON.stringify({
          success: true,
          job_id: jobId,
          channel,
          topic,
          youtube_title: youtubeTitle,
          audio_url: audioUrl,
          script_preview: script.slice(0, 300),
          youtube: youtubeResult,
          instagram: instagramResult,
          message: action === "create_and_post"
            ? "Content created and posted!"
            : "Content ready! Use action=post_youtube or post_instagram to publish.",
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (action === "post_youtube" || action === "post_instagram") {
      const jobId = body.job_id;
      let row: Record<string, string> | null = null;

      if (jobId) {
        const { data } = await supabase.from("content_queue").select("*").eq("id", jobId).single();
        row = data;
      } else {
        // Get latest ready item for this channel
        const { data } = await supabase
          .from("content_queue")
          .select("*")
          .eq("channel", channel)
          .eq("status", "ready")
          .order("created_at", { ascending: false })
          .limit(1)
          .single();
        row = data;
      }

      if (!row) {
        return new Response(
          JSON.stringify({ error: "No ready content found. Run action=create first." }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      let result = "";
      if (action === "post_youtube") {
        if (!row.audio_url) return new Response(JSON.stringify({ error: "No audio URL" }), { headers: { ...corsHeaders, "Content-Type": "application/json" } });
        result = await postToYouTube(row.youtube_title, row.seo_package, row.audio_url);
        await supabase.from("content_queue").update({ status: "posted_youtube" }).eq("id", row.id);
      } else {
        const igCaption = row.seo_package?.match(/instagram caption[^\n]*\n([^\n]+)/i)?.[1] ?? row.topic;
        result = await postToInstagram(igCaption ?? "");
        await supabase.from("content_queue").update({ status: "posted_instagram" }).eq("id", row.id);
      }

      return new Response(
        JSON.stringify({ success: true, result }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (action === "status") {
      const { data } = await supabase
        .from("content_queue")
        .select("id, channel, topic, status, created_at, audio_url")
        .order("created_at", { ascending: false })
        .limit(10);

      return new Response(
        JSON.stringify({ queue: data }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ error: "Unknown action. Use: create | create_and_post | post_youtube | post_instagram | status" }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 400 }
    );
  } catch (e) {
    return new Response(
      JSON.stringify({ error: String(e) }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 500 }
    );
  }
});
