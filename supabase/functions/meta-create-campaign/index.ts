import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type', 'Content-Type': 'application/json' };
const META_TOKEN = Deno.env.get('META_ACCESS_TOKEN')!;
const META_ACCOUNT_ID = Deno.env.get('META_ACCOUNT_ID')!;
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

async function metaPost(path: string, body: Record<string, unknown>) {
  const params = new URLSearchParams();
  params.set('access_token', META_TOKEN);
  for (const [k, v] of Object.entries(body)) {
    params.set(k, typeof v === 'object' ? JSON.stringify(v) : String(v));
  }
  const res = await fetch(`https://graph.facebook.com/v20.0/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString(),
  });
  const json = await res.json();
  if (json.error) throw new Error(json.error.message ?? JSON.stringify(json.error));
  return json;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });

  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
  const { data: { user }, error } = await supabase.auth.getUser(
    (req.headers.get('Authorization') ?? '').replace('Bearer ', '')
  );
  if (error || !user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: CORS });

  try {
    const body = await req.json();
    const { productName, campaignType = 'leads' } = body;

    if (!productName) {
      return new Response(JSON.stringify({ error: 'productName obrigatório' }), { status: 400, headers: CORS });
    }

    const objectiveMap: Record<string, string> = {
      leads: 'OUTCOME_LEADS',
      traffic: 'OUTCOME_TRAFFIC',
      engagement: 'OUTCOME_ENGAGEMENT',
    };

    const campaign = await metaPost(`act_${META_ACCOUNT_ID}/campaigns`, {
      name: `[Wizard] ${productName}`,
      objective: objectiveMap[campaignType] ?? 'OUTCOME_LEADS',
      status: 'PAUSED',
      special_ad_categories: [],
    });

    const adsManagerUrl = `https://adsmanager.facebook.com/adsmanager/manage/adsets?act=${META_ACCOUNT_ID}&selected_campaign_ids=${campaign.id}`;

    return new Response(JSON.stringify({
      ok: true,
      campaignId: campaign.id,
      adsManagerUrl,
      message: `Campanha "${productName}" criada com sucesso!`,
    }), { headers: CORS });

  } catch (err) {
    console.error('meta-create-campaign error:', err);
    return new Response(JSON.stringify({ error: String(err) }), { status: 500, headers: CORS });
  }
});
