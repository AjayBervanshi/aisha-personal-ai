const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

type SyncRequest = {
  secret_names?: string[];
  only_known_prefixes?: boolean;
};

const DEFAULT_NAME_FILTER = /(KEY|SECRET|TOKEN|PASS|PWD|API)/;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: CORS_HEADERS });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Only POST supported" }), {
      status: 405,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }

  try {
    const authHeader = req.headers.get("authorization") ?? "";
    const bearer = authHeader.replace(/^Bearer\s+/i, "");
    const adminToken = Deno.env.get("API_KEYS_SYNC_TOKEN") ?? "";

    if (!adminToken || bearer !== adminToken) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    const body = (await req.json().catch(() => ({}))) as SyncRequest;
    const env = Deno.env.toObject();

    let names: string[];
    if (Array.isArray(body.secret_names) && body.secret_names.length > 0) {
      names = body.secret_names.filter((n) => typeof env[n] === "string" && env[n].length > 0);
    } else {
      names = Object.keys(env).filter((name) => DEFAULT_NAME_FILTER.test(name));
      if (body.only_known_prefixes !== false) {
        names = names.filter((name) =>
          [
            "GEMINI_",
            "OPENAI_",
            "GROQ_",
            "ANTHROPIC_",
            "XAI_",
            "HUGGINGFACE_",
            "ELEVENLABS_",
            "TELEGRAM_",
            "YOUTUBE_",
            "INSTAGRAM_",
            "GITHUB_",
            "SUPABASE_",
            "GMAIL_",
            "JULES_",
            "RAILWAY_",
            "AJAY_",
          ].some((p) => name.startsWith(p))
        );
      }
    }

    if (names.length === 0) {
      return new Response(JSON.stringify({ error: "No matching secrets found" }), {
        status: 400,
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!supabaseUrl || !serviceRoleKey) {
      return new Response(JSON.stringify({ error: "Missing Supabase runtime env vars" }), {
        status: 500,
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    const result: Array<{ id: string; name: string }> = [];
    for (const name of names) {
      const existingRes = await fetch(
        `${supabaseUrl}/rest/v1/api_keys?select=id,name&name=eq.${encodeURIComponent(name)}&order=created_at.desc&limit=1`,
        {
          headers: {
            apikey: serviceRoleKey,
            Authorization: `Bearer ${serviceRoleKey}`,
            "Content-Type": "application/json",
          },
        }
      );
      if (!existingRes.ok) {
        const detail = await existingRes.text();
        return new Response(JSON.stringify({ error: "DB lookup failed", detail, name }), {
          status: 500,
          headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
        });
      }
      const existing = (await existingRes.json()) as Array<{ id: string; name: string }>;

      if (existing.length > 0) {
        const id = existing[0].id;
        const updateRes = await fetch(`${supabaseUrl}/rest/v1/api_keys?id=eq.${id}`, {
          method: "PATCH",
          headers: {
            apikey: serviceRoleKey,
            Authorization: `Bearer ${serviceRoleKey}`,
            "Content-Type": "application/json",
            Prefer: "return=representation",
          },
          body: JSON.stringify({
            secret: env[name],
          }),
        });
        if (!updateRes.ok) {
          const detail = await updateRes.text();
          return new Response(JSON.stringify({ error: "DB update failed", detail, name }), {
            status: 500,
            headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
          });
        }
        const updated = (await updateRes.json()) as Array<{ id: string; name: string }>;
        if (updated.length > 0) {
          result.push({ id: updated[0].id, name: updated[0].name });
        }
      } else {
        const insertRes = await fetch(`${supabaseUrl}/rest/v1/api_keys`, {
          method: "POST",
          headers: {
            apikey: serviceRoleKey,
            Authorization: `Bearer ${serviceRoleKey}`,
            "Content-Type": "application/json",
            Prefer: "return=representation",
          },
          body: JSON.stringify([
            {
              name,
              secret: env[name],
            },
          ]),
        });
        if (!insertRes.ok) {
          const detail = await insertRes.text();
          return new Response(JSON.stringify({ error: "DB insert failed", detail, name }), {
            status: 500,
            headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
          });
        }
        const inserted = (await insertRes.json()) as Array<{ id: string; name: string }>;
        if (inserted.length > 0) {
          result.push({ id: inserted[0].id, name: inserted[0].name });
        }
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        stored_count: result.length,
        target_host: new URL(supabaseUrl).host,
        rows: result,
      }),
      {
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      }
    );
  } catch (err) {
    return new Response(JSON.stringify({ error: err instanceof Error ? err.message : "Unknown error" }), {
      status: 500,
      headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
    });
  }
});
