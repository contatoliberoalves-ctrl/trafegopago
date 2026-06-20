import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, content-type',
  'Content-Type': 'application/json',
};

const META_TOKEN = Deno.env.get('META_ACCESS_TOKEN')!;
const META_ACCOUNT_ID = Deno.env.get('META_ACCOUNT_ID')!;
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const BASE = 'https://graph.facebook.com/v20.0';

async function metaPost(path: string, body: Record<string, unknown>) {
  const url = `${BASE}/${path}`;
  const form = new URLSearchParams();
  form.set('access_token', META_TOKEN);
  for (const [k, v] of Object.entries(body)) {
    form.set(k, typeof v === 'object' ? JSON.stringify(v) : String(v));
  }
  const res = await fetch(url, { method: 'POST', body: form });
  const json = await res.json();
  if (!res.ok || json.error) throw new Error(json.error?.message ?? `Meta error ${res.status}`);
  return json;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });

  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
  const authHeader = req.headers.get('Authorization') ?? '';
  const { data: { user }, error: authErr } = await supabase.auth.getUser(authHeader.replace('Bearer ', ''));
  if (authErr || !user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: CORS });

  try {
    const body = await req.json();
    const {
      productName,
      dailyBudget,     // R$ (number)
      startDate,       // YYYY-MM-DD
      endDate,         // YYYY-MM-DD (optional)
      ageMin = 18,
      ageMax = 65,
      locations = [],  // array of { key, name, type } from Meta geo search
      interests = [],  // array of { id, name }
      campaignType = 'leads', // 'leads' | 'traffic'
      destinationUrl = '',    // for traffic campaigns
    } = body;

    if (!productName || !dailyBudget || !startDate) {
      return new Response(JSON.stringify({ error: 'Campos obrigatórios: productName, dailyBudget, startDate' }), { status: 400, headers: CORS });
    }

    const objective = campaignType === 'traffic' ? 'OUTCOME_TRAFFIC' : 'OUTCOME_LEADS';
    const optimizationGoal = campaignType === 'traffic' ? 'LINK_CLICKS' : 'LEAD_GENERATION';
    const billingEvent = 'IMPRESSIONS';

    // 1. Create Campaign
    const campaign = await metaPost(`act_${META_ACCOUNT_ID}/campaigns`, {
      name: `[Wizard] ${productName}`,
      objective,
      status: 'PAUSED',
      special_ad_categories: [],
    });

    // 2. Build targeting
    const targeting: Record<string, unknown> = {
      age_min: ageMin,
      age_max: ageMax,
      geo_locations: locations.length > 0
        ? { cities: locations.filter((l: {type:string}) => l.type === 'city'), countries: locations.some((l: {type:string}) => l.type === 'country') ? ['BR'] : undefined, regions: locations.filter((l: {type:string}) => l.type === 'region') }
        : { countries: ['BR'] },
      facebook_positions: ['feed', 'instagram_stream', 'instagram_stories', 'instagram_reels'],
      publisher_platforms: ['facebook', 'instagram'],
    };
    if (interests.length > 0) {
      targeting.flexible_spec = [{ interests }];
    }

    // 3. Create Ad Set
    const adSetBody: Record<string, unknown> = {
      name: `[Wizard] ${productName} — Público`,
      campaign_id: campaign.id,
      billing_event: billingEvent,
      optimization_goal: optimizationGoal,
      bid_strategy: 'LOWEST_COST_WITHOUT_CAP',
      daily_budget: Math.round(dailyBudget * 100),
      start_time: new Date(startDate + 'T08:00:00-03:00').toISOString(),
      targeting,
      status: 'PAUSED',
    };
    if (endDate) {
      adSetBody.end_time = new Date(endDate + 'T23:59:00-03:00').toISOString();
    }
    if (campaignType === 'traffic' && destinationUrl) {
      adSetBody.destination_type = 'WEBSITE';
    }

    const adSet = await metaPost(`act_${META_ACCOUNT_ID}/adsets`, adSetBody);

    const adsManagerUrl = `https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${META_ACCOUNT_ID}&selected_campaign_ids=${campaign.id}`;

    return new Response(JSON.stringify({
      ok: true,
      campaignId: campaign.id,
      adSetId: adSet.id,
      adsManagerUrl,
      message: `Campanha "${productName}" criada com sucesso! Acesse o Meta Ads Manager para adicionar o criativo.`,
    }), { headers: CORS });

  } catch (err) {
    return new Response(JSON.stringify({ error: String(err) }), { status: 500, headers: CORS });
  }
});
