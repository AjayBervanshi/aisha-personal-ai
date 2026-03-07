// supabase/functions/memory_search/index.ts
// ============================================================
// Supabase Edge Function — Search Aisha's memory semantically
// Deploy: supabase functions deploy memory_search
// ============================================================

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { query, limit = 5, category = null } = await req.json();

    if (!query) {
      return new Response(
        JSON.stringify({ error: "query is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Simple keyword-based search (no embedding needed for free tier)
    let queryBuilder = supabase
      .from("aisha_memory")
      .select("id, category, title, content, importance, tags")
      .eq("is_active", true)
      .or(`title.ilike.%${query}%,content.ilike.%${query}%`)
      .order("importance", { ascending: false })
      .limit(limit);

    if (category) {
      queryBuilder = queryBuilder.eq("category", category);
    }

    const { data, error } = await queryBuilder;

    if (error) throw error;

    return new Response(
      JSON.stringify({ memories: data, count: data?.length ?? 0 }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (err) {
    return new Response(
      JSON.stringify({ error: String(err) }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
