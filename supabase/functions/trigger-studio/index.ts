// trigger-studio/index.ts
// Called by pg_cron every 4 hours.
// Forwards to Render bot's /api/trigger/studio endpoint.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RENDER_BOT_URL = Deno.env.get("RENDER_BOT_URL")!;
const TRIGGER_SECRET = Deno.env.get("TRIGGER_SECRET") ?? "";

serve(async (_req) => {
  try {
    const res = await fetch(`${RENDER_BOT_URL}/api/trigger/studio`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Trigger-Secret": TRIGGER_SECRET,
      },
      body: JSON.stringify({ source: "pg_cron" }),
    });

    const body = await res.text();
    console.log(`trigger-studio → Render: ${res.status} ${body}`);

    return new Response(
      JSON.stringify({ status: res.status, body }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("trigger-studio error:", err);
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
