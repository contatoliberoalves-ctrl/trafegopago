#!/usr/bin/env python3
import base64
import gzip
import json
import re
import os
import sys

# ── paths ──────────────────────────────────────────────────────────────────────
SRC  = '/root/.claude/uploads/26341acd-0d3c-50ee-8b02-41a608daa391/90e665a3-Trafego_Pago__Completo.html'
DEST = '/home/user/trafegopago/frontend/index.html'
HDRS = '/home/user/trafegopago/frontend/_headers'

CHUNK_DATA   = 'a43032b2-f6f3-45a7-aa98-8fe14bfeeaba'
CHUNK_BREVO  = '13470404-bf86-4cc2-98cb-f11e9abb3805'

# ── helpers ────────────────────────────────────────────────────────────────────
def decode_chunk(entry) -> str:
    """entry is either a raw base64+gz string or a dict with a 'data' key."""
    b64gz = entry['data'] if isinstance(entry, dict) else entry
    return gzip.decompress(base64.b64decode(b64gz)).decode('utf-8')

def encode_chunk(entry, text: str):
    """Re-encode text and return an updated entry (same shape as original)."""
    new_data = base64.b64encode(gzip.compress(text.encode('utf-8'))).decode('ascii')
    if isinstance(entry, dict):
        result = dict(entry)
        result['data'] = new_data
        return result
    return new_data

# ── code to inject ─────────────────────────────────────────────────────────────
SUPABASE_LOAD_FN = r"""
window.__loadSupabaseData = async function() {
  const sb = window.SUPABASE_CLIENT;
  if (!sb) return;
  try {
    const user = (await sb.auth.getUser()).data.user;
    if (!user) return;

    // Fetch email campaigns
    const { data: emailCampaigns } = await sb.from('email_campaigns').select('*').order('sent_date', { ascending: false });
    if (emailCampaigns && emailCampaigns.length > 0) {
      window.DATA.emailCampaigns = emailCampaigns.map(c => ({
        id: c.external_id || c.id,
        name: c.name,
        subject: c.subject || '',
        sent: c.sent || 0,
        opens: c.opens || 0,
        clicks: c.clicks || 0,
        bounces: c.bounces || 0,
        unsubs: c.unsubs || 0,
        date: c.sent_date ? new Date(c.sent_date).toLocaleDateString('pt-BR') : '—',
        status: c.status || 'Enviado'
      }));
    }

    // Fetch email metrics (aggregate)
    const { data: emailMeta } = await sb.from('user_integrations').select('extra').eq('provider', 'brevo').single();
    if (emailMeta?.extra) {
      Object.assign(window.DATA.emailMetrics, emailMeta.extra);
    }

    // Fetch campaigns (Meta/Google)
    const { data: campaigns } = await sb.from('campaigns').select('*').order('created_at', { ascending: false });
    if (campaigns && campaigns.length > 0) {
      window.DATA.campaigns = campaigns.map(c => ({
        id: c.external_id || c.id,
        name: c.name,
        objective: c.objective || '—',
        status: c.status || 'Ativo',
        budget: c.budget || 0,
        spent: c.spent || 0,
        leads: c.leads || 0,
        cpl: c.cpl || 0,
        roas: c.roas || 0,
        start: c.start_date ? new Date(c.start_date).toLocaleDateString('pt-BR') : '—',
        end: c.end_date ? new Date(c.end_date).toLocaleDateString('pt-BR') : '—',
      }));
    }

    // Force React to re-render by triggering a custom event
    window.dispatchEvent(new CustomEvent('supabase-data-loaded'));
  } catch(e) {
    console.warn('Supabase data load error:', e);
  }
};"""

ONCLICK_OLD = "onClick={() => { setConnected(true); toast('Brevo conectado com sucesso!', { tone:'success' }); }}"

ONCLICK_NEW = """onClick={async () => {
  if (!apiKey || !apiKey.startsWith('xkeysib-')) {
    toast('API Key inválida. Deve começar com xkeysib-', { tone:'bad' });
    return;
  }
  const sb = window.SUPABASE_CLIENT;
  if (!sb) { toast('Erro: Supabase não inicializado', { tone:'bad' }); return; }
  try {
    toast('Validando chave...', { tone:'info' });
    // Save API key to Supabase
    const { error } = await sb.from('user_integrations').upsert({
      user_id: (await sb.auth.getUser()).data.user.id,
      provider: 'brevo',
      api_key: apiKey,
      updated_at: new Date().toISOString()
    }, { onConflict: 'user_id,provider' });
    if (error) throw error;
    // Call the brevo-sync Edge Function
    const { error: fnErr } = await sb.functions.invoke('brevo-sync', { body: { api_key: apiKey } });
    if (fnErr) throw fnErr;
    setConnected(true);
    toast('Brevo conectado! Dados sendo carregados...', { tone:'success' });
    setTimeout(() => window.__loadSupabaseData?.(), 2000);
  } catch(e) {
    toast('Erro ao conectar: ' + (e.message || e), { tone:'bad' });
  }
}}"""

AUTH_SCRIPT = """<!-- Supabase Auth Layer -->
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<script>
(function() {
  const SUPABASE_URL = 'https://tvbouailesbnqdbzkkfl.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_HwAohKJ-ZTCtRGNVES9uQA_AsAUreu-';

  window.SUPABASE_CLIENT = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

  // Show login overlay if not authenticated
  window.SUPABASE_CLIENT.auth.getSession().then(({ data: { session } }) => {
    if (!session) {
      document.body.innerHTML = `
        <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#FAFBFD;font-family:'Poppins',system-ui,sans-serif;">
          <div style="width:400px;padding:40px;background:#fff;border-radius:20px;box-shadow:0 8px 32px rgba(14,31,92,0.12);border:1px solid #E6EAF2;">
            <div style="width:52px;height:52px;background:linear-gradient(135deg,#1E40AF,#3A62EC);border-radius:14px;display:flex;align-items:center;justify-content:center;margin-bottom:24px;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
            </div>
            <h1 style="font-size:22px;font-weight:600;color:#0A0A0A;margin:0 0 4px;">Tráfego Pago</h1>
            <p style="font-size:13px;color:#737373;margin:0 0 28px;">Entre na sua conta para acessar o painel</p>
            <div id="auth-error" style="display:none;background:#FEF2F2;color:#DC2626;font-size:12px;padding:10px 14px;border-radius:10px;margin-bottom:16px;"></div>
            <label style="font-size:12px;font-weight:500;color:#1F1F1F;display:block;margin-bottom:4px;">Email</label>
            <input id="auth-email" type="email" placeholder="seu@email.com" style="width:100%;height:40px;padding:0 12px;border:1.5px solid #E6EAF2;border-radius:10px;font-size:13px;font-family:inherit;outline:none;box-sizing:border-box;margin-bottom:12px;">
            <label style="font-size:12px;font-weight:500;color:#1F1F1F;display:block;margin-bottom:4px;">Senha</label>
            <input id="auth-pass" type="password" placeholder="••••••••" style="width:100%;height:40px;padding:0 12px;border:1.5px solid #E6EAF2;border-radius:10px;font-size:13px;font-family:inherit;outline:none;box-sizing:border-box;margin-bottom:20px;">
            <button id="auth-btn" style="width:100%;height:42px;background:linear-gradient(135deg,#1E40AF,#3A62EC);color:white;border:none;border-radius:12px;font-size:14px;font-weight:600;font-family:inherit;cursor:pointer;">Entrar</button>
            <div style="text-align:center;margin-top:16px;">
              <button id="auth-signup-btn" style="background:none;border:none;font-size:12px;color:#3A62EC;cursor:pointer;font-family:inherit;">Não tem conta? Criar agora</button>
            </div>
          </div>
        </div>`;

      let isSignup = false;
      document.getElementById('auth-signup-btn').onclick = () => {
        isSignup = !isSignup;
        document.getElementById('auth-btn').textContent = isSignup ? 'Criar conta' : 'Entrar';
        document.getElementById('auth-signup-btn').textContent = isSignup ? 'Já tenho conta' : 'Não tem conta? Criar agora';
      };

      document.getElementById('auth-btn').onclick = async () => {
        const email = document.getElementById('auth-email').value;
        const pass = document.getElementById('auth-pass').value;
        const errDiv = document.getElementById('auth-error');
        errDiv.style.display = 'none';

        const fn = isSignup
          ? window.SUPABASE_CLIENT.auth.signUp({ email, password: pass })
          : window.SUPABASE_CLIENT.auth.signInWithPassword({ email, password: pass });

        const { data, error } = await fn;
        if (error) {
          errDiv.textContent = error.message === 'Invalid login credentials' ? 'Email ou senha incorretos' : error.message;
          errDiv.style.display = 'block';
        } else {
          window.location.reload();
        }
      };

      document.getElementById('auth-pass').onkeydown = (e) => {
        if (e.key === 'Enter') document.getElementById('auth-btn').click();
      };
    } else {
      window.CURRENT_USER = session.user;
      // Load real data after app mounts
      setTimeout(() => window.__loadSupabaseData?.(), 1500);
    }
  });
})();
</script>"""

HEADERS_CONTENT = """/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  X-XSS-Protection: 1; mode=block
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://tvbouailesbnqdbzkkfl.supabase.co wss://tvbouailesbnqdbzkkfl.supabase.co; img-src 'self' data: https:;
"""

# ── main ───────────────────────────────────────────────────────────────────────
def main():
    print(f'Reading source: {SRC}')
    with open(SRC, 'r', encoding='utf-8') as f:
        html = f.read()
    print(f'Source size: {len(html):,} bytes')

    # ── 1. Extract the three script blocks ─────────────────────────────────────
    print('\n[1] Extracting script blocks...')

    def extract_script(stype):
        pat = re.compile(
            r'<script[^>]+type=["\']' + re.escape(stype) + r'["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE
        )
        m = pat.search(html)
        if not m:
            raise ValueError(f'Script type "{stype}" not found')
        return m.group(1).strip(), m.start(), m.end()

    manifest_raw, m_s, m_e = extract_script('__bundler/manifest')
    template_raw, t_s, t_e = extract_script('__bundler/template')
    ext_raw,      x_s, x_e = extract_script('__bundler/ext_resources')

    print(f'  manifest  : {len(manifest_raw):,} chars')
    print(f'  template  : {len(template_raw):,} chars')
    print(f'  ext_res   : {len(ext_raw):,} chars')

    # ── 2. Parse manifest ──────────────────────────────────────────────────────
    print('\n[2] Parsing manifest...')
    manifest = json.loads(manifest_raw)
    print(f'  {len(manifest)} chunks found')
    if CHUNK_DATA not in manifest:
        raise ValueError(f'Chunk {CHUNK_DATA} not in manifest')
    if CHUNK_BREVO not in manifest:
        raise ValueError(f'Chunk {CHUNK_BREVO} not in manifest')

    # ── 3. Modify CHUNK_DATA ───────────────────────────────────────────────────
    print(f'\n[3] Modifying chunk {CHUNK_DATA}...')
    data_js = decode_chunk(manifest[CHUNK_DATA])
    _data_entry = manifest[CHUNK_DATA]
    print(f'  Decompressed size: {len(data_js):,} chars')

    marker = 'window.DATA = {'
    idx = data_js.find(marker)
    if idx == -1:
        raise ValueError('window.DATA = { not found in chunk')
    print(f'  Found window.DATA at offset {idx}')

    # Walk forward counting braces to find closing };
    brace_start = data_js.index('{', idx + len(marker) - 1)
    depth = 0
    pos = brace_start
    while pos < len(data_js):
        ch = data_js[pos]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
        pos += 1

    # pos now points to the closing }
    # The statement ends with }; — find the semicolon
    semi = data_js.index(';', pos)
    insert_at = semi + 1
    print('  Closing }; of window.DATA found at offset', semi)

    data_js_new = data_js[:insert_at] + '\n' + SUPABASE_LOAD_FN + data_js[insert_at:]
    manifest[CHUNK_DATA] = encode_chunk(_data_entry, data_js_new)
    print(f'  Chunk updated. New size: {len(data_js_new):,} chars')

    # ── 4. Modify CHUNK_BREVO ──────────────────────────────────────────────────
    print(f'\n[4] Modifying chunk {CHUNK_BREVO}...')
    _brevo_entry = manifest[CHUNK_BREVO]
    brevo_js = decode_chunk(_brevo_entry)
    print(f'  Decompressed size: {len(brevo_js):,} chars')

    if ONCLICK_OLD not in brevo_js:
        raise ValueError('onClick pattern not found in brevo chunk')
    brevo_js_new = brevo_js.replace(ONCLICK_OLD, ONCLICK_NEW, 1)
    manifest[CHUNK_BREVO] = encode_chunk(_brevo_entry, brevo_js_new)
    print(f'  onClick replaced. New size: {len(brevo_js_new):,} chars')

    # ── 5. Rebuild manifest JSON ───────────────────────────────────────────────
    print('\n[5] Serialising manifest...')
    new_manifest_raw = json.dumps(manifest, separators=(',', ':'))
    print(f'  Manifest size: {len(new_manifest_raw):,} chars')

    # ── 6. Inject auth script into template ───────────────────────────────────
    print('\n[6] Modifying template...')
    template_html = json.loads(template_raw)   # JSON-encoded string → actual HTML
    body_pat = re.compile(r'(<body(?:\s[^>]*)?>)', re.IGNORECASE)
    m = body_pat.search(template_html)
    if not m:
        raise ValueError('<body> tag not found in template')
    insert_pos = m.end()
    template_html_new = template_html[:insert_pos] + '\n' + AUTH_SCRIPT + '\n' + template_html[insert_pos:]
    new_template_raw = json.dumps(template_html_new)
    print(f'  Auth script injected after {m.group(0)!r}')
    print(f'  New template JSON size: {len(new_template_raw):,} chars')

    # ── 7. Reconstruct HTML ───────────────────────────────────────────────────
    print('\n[7] Reconstructing HTML...')

    # Replace each script block content in-place, working from the end so offsets stay valid
    segments = sorted(
        [
            (m_s, m_e, f'<script type="__bundler/manifest">{new_manifest_raw}</script>'),
            (t_s, t_e, f'<script type="__bundler/template">{new_template_raw}</script>'),
            (x_s, x_e, f'<script type="__bundler/ext_resources">{ext_raw}</script>'),
        ],
        key=lambda x: x[0],
        reverse=True
    )

    out = html
    for start, end, replacement in segments:
        out = out[:start] + replacement + out[end:]

    print(f'  Output HTML size: {len(out):,} chars')

    # ── 8. Write output files ─────────────────────────────────────────────────
    os.makedirs(os.path.dirname(DEST), exist_ok=True)

    print(f'\n[8] Writing {DEST}...')
    with open(DEST, 'w', encoding='utf-8') as f:
        f.write(out)
    size = os.path.getsize(DEST)
    print(f'  Written {size:,} bytes')

    print(f'\n[9] Writing {HDRS}...')
    with open(HDRS, 'w', encoding='utf-8') as f:
        f.write(HEADERS_CONTENT)
    print(f'  Written {os.path.getsize(HDRS):,} bytes')

    print('\nDone.')

if __name__ == '__main__':
    main()
