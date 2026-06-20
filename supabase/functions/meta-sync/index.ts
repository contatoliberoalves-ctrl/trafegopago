import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const META_TOKEN = Deno.env.get('META_ACCESS_TOKEN')!;
const META_ACCOUNT_ID = Deno.env.get('META_ACCOUNT_ID')!;
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

const BASE = 'https://graph.facebook.com/v20.0';

async function metaGet(path: string, params: Record<string, string> = {}) {
  const url = new URL(`${BASE}/${path}`);
  url.searchParams.set('access_token', META_TOKEN);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Meta API error: ${res.status} ${await res.text()}`);
  return res.json();
}

Deno.serve(async (req) => {
  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

  // Get user from JWT
  const authHeader = req.headers.get('Authorization') ?? '';
  const { data: { user }, error: authErr } = await supabase.auth.getUser(authHeader.replace('Bearer ', ''));
  if (authErr || !user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });

  try {
    const userId = user.id;
    const accountId = META_ACCOUNT_ID;

    // Fetch campaigns + insights (last 30 days)
    const datePreset = 'last_30d';
    const campaignFields = [
      'id', 'name', 'objective', 'status', 'daily_budget', 'lifetime_budget',
      'start_time', 'stop_time',
      `insights.date_preset(${datePreset}){spend,leads,impressions,reach,clicks,ctr,cost_per_lead,purchase_roas,actions}`,
    ].join(',');

    const campaignsData = await metaGet(`act_${accountId}/campaigns`, {
      fields: campaignFields,
      limit: '100',
    });

    const campaigns = campaignsData.data ?? [];
    const upserted: string[] = [];

    for (const c of campaigns) {
      const ins = c.insights?.data?.[0] ?? {};
      const leads = parseInt(ins.leads ?? '0') || extractAction(ins.actions, 'lead');
      const spend = parseFloat(ins.spend ?? '0');
      const clicks = parseInt(ins.clicks ?? '0');
      const impressions = parseInt(ins.impressions ?? '0');
      const reach = parseInt(ins.reach ?? '0');
      const ctr = parseFloat(ins.ctr ?? '0');
      const cpl = leads > 0 ? spend / leads : null;
      const roasArr = ins.purchase_roas;
      const roas = roasArr ? parseFloat(roasArr[0]?.value ?? '0') : null;

      const statusMap: Record<string, string> = {
        ACTIVE: 'Ativo', PAUSED: 'Pausado', ARCHIVED: 'Arquivado',
        DELETED: 'Deletado', CAMPAIGN_PAUSED: 'Pausado',
      };

      const row = {
        user_id: userId,
        external_id: c.id,
        platform: 'meta',
        name: c.name,
        objective: c.objective ?? null,
        status: statusMap[c.status] ?? c.status,
        budget: parseFloat(c.daily_budget ?? c.lifetime_budget ?? '0') / 100,
        spent: spend,
        leads,
        cpl,
        roas,
        ctr,
        impressions,
        reach,
        clicks,
        start_date: c.start_time ? c.start_time.split('T')[0] : null,
        end_date: c.stop_time ? c.stop_time.split('T')[0] : null,
        synced_at: new Date().toISOString(),
      };

      const { error } = await supabase.from('campaigns').upsert(row, { onConflict: 'user_id,platform,external_id' });
      if (error) console.error('campaigns upsert error:', error.message);
      else upserted.push(c.id);
    }

    // Save daily metrics (last 30 days breakdown)
    try {
      const insightsByDay = await metaGet(`act_${accountId}/insights`, {
        fields: 'spend,impressions,clicks,actions',
        date_preset: 'last_30d',
        time_increment: '1',
        level: 'account',
        limit: '31',
      });

      for (const d of insightsByDay.data ?? []) {
        const leads = extractAction(d.actions, 'lead');
        await supabase.from('daily_metrics').upsert({
          user_id: userId,
          platform: 'meta',
          metric_date: d.date_start,
          invested: parseFloat(d.spend ?? '0'),
          leads,
          clicks: parseInt(d.clicks ?? '0'),
          impressions: parseInt(d.impressions ?? '0'),
        }, { onConflict: 'user_id,platform,metric_date' });
      }
    } catch (e) {
      console.error('daily metrics error:', e);
    }

    // Save integration record
    await supabase.from('user_integrations').upsert({
      user_id: userId,
      provider: 'meta',
      account_id: accountId,
      extra: { synced_campaigns: upserted.length, last_sync: new Date().toISOString() },
    }, { onConflict: 'user_id,provider' });

    return new Response(JSON.stringify({
      ok: true,
      synced: upserted.length,
      message: `${upserted.length} campanhas sincronizadas do Meta Ads`,
    }), { headers: { 'Content-Type': 'application/json' } });

  } catch (err) {
    console.error('meta-sync error:', err);
    return new Response(JSON.stringify({ error: String(err) }), { status: 500 });
  }
});

function extractAction(actions: Array<{ action_type: string; value: string }> | undefined, type: string): number {
  if (!actions) return 0;
  const found = actions.find(a => a.action_type === type || a.action_type.includes(type));
  return found ? parseInt(found.value) : 0;
}
