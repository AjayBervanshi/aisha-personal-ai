// trigger-maintenance/index.ts
// Called by pg_cron for all non-studio scheduled jobs.
// Usage: POST /trigger-maintenance?job=<job-name>
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RENDER_BOT_URL = Deno.env.get("RENDER_BOT_URL")!;
const TRIGGER_SECRET = Deno.env.get("TRIGGER_SECRET") ?? "";

const VALID_JOBS = new Set([
  "morning", "evening", "digest", "memory",
  "weekly-digest", "memory-cleanup", "task-poll",
  "inactivity", "self-improve", "temp-cleanup", "key-expiry",
]);

serve(async (req) => {
  const url = new URL(req.url);
  const job = url.searchParams.get("job") ?? "";

  if (!VALID_JOBS.has(job)) {
    return new Response(
      JSON.stringify({ error: `unknown job: ${job}` }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  try {
    const res = await fetch(`${RENDER_BOT_URL}/api/trigger/${job}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Trigger-Secret": TRIGGER_SECRET,
      },
      body: JSON.stringify({ source: "pg_cron" }),
    });

    const body = await res.text();
    console.log(`trigger-maintenance job=${job} → Render: ${res.status} ${body}`);

    return new Response(
      JSON.stringify({ job, status: res.status, body }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error(`trigger-maintenance job=${job} error:`, err);
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
