-- ============================================================
-- TRAFEGO PAGO DASHBOARD — Schema inicial
-- Aplicar no SQL Editor do Supabase
-- ============================================================

-- Habilitar extensões necessárias
create extension if not exists "uuid-ossp";
create extension if not exists pg_cron;
create extension if not exists pg_net;

-- ============================================================
-- TABELA: user_integrations
-- Armazena tokens/chaves de cada usuário (criptografado via RLS)
-- ============================================================
create table if not exists user_integrations (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  provider text not null, -- 'meta', 'google', 'brevo', 'devzapp'
  access_token text,
  refresh_token text,
  token_expires_at timestamptz,
  api_key text,           -- para Brevo e DevZapp
  account_id text,        -- ID da conta no provedor
  extra jsonb,            -- dados extras (ex: nome da conta)
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id, provider)
);

-- ============================================================
-- TABELA: campaigns
-- Campanhas do Meta Ads e Google Ads
-- ============================================================
create table if not exists campaigns (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  external_id text,       -- ID original da plataforma
  platform text not null, -- 'meta', 'google'
  name text not null,
  objective text,         -- Conversão, Tráfego, Alcance...
  status text,            -- Ativo, Pausado
  budget numeric(10,2),
  spent numeric(10,2) default 0,
  leads integer default 0,
  cpl numeric(10,2),
  roas numeric(10,4),
  ctr numeric(8,4),
  impressions bigint default 0,
  reach bigint default 0,
  clicks bigint default 0,
  start_date date,
  end_date date,
  synced_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, platform, external_id)
);

-- ============================================================
-- TABELA: ad_sets
-- Conjuntos de anúncios (somente Meta)
-- ============================================================
create table if not exists ad_sets (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  campaign_id uuid references campaigns(id) on delete cascade,
  external_id text,
  name text not null,
  audience text,
  spent numeric(10,2) default 0,
  leads integer default 0,
  cpl numeric(10,2),
  ctr numeric(8,4),
  status text,
  synced_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, external_id)
);

-- ============================================================
-- TABELA: creatives
-- Criativos/anúncios individuais (Meta)
-- ============================================================
create table if not exists creatives (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  ad_set_id uuid references ad_sets(id) on delete set null,
  external_id text,
  name text,
  type text,              -- vídeo, imagem, carrossel
  format text,            -- reels, feed, stories
  platform text,          -- Instagram, Facebook
  status text,
  headline text,
  body text,
  cta text,
  invested numeric(10,2) default 0,
  impressions bigint default 0,
  reach bigint default 0,
  clicks bigint default 0,
  ctr numeric(8,4),
  conversions integer default 0,
  cpl numeric(10,2),
  freq numeric(8,4),
  roas numeric(10,4),
  score text,             -- Excelente, Bom, Atenção, Pausar
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  synced_at timestamptz,
  unique(user_id, external_id)
);

-- ============================================================
-- TABELA: youtube_campaigns
-- Campanhas de vídeo do Google/YouTube Ads
-- ============================================================
create table if not exists youtube_campaigns (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  external_id text,
  name text not null,
  format text,            -- In-Stream pulável, Bumper, Discovery...
  views bigint default 0,
  vtr numeric(8,4),       -- view-through rate %
  cpv numeric(10,4),      -- cost per view
  q25 numeric(8,4),       -- % assistido até 25%
  q50 numeric(8,4),
  q75 numeric(8,4),
  q100 numeric(8,4),
  spent numeric(10,2) default 0,
  leads integer default 0,
  conversions integer default 0,
  status text,
  synced_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, external_id)
);

-- ============================================================
-- TABELA: email_campaigns
-- Campanhas do Brevo (email marketing)
-- ============================================================
create table if not exists email_campaigns (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  external_id text,       -- ID da campanha no Brevo
  name text not null,
  subject text,
  sent integer default 0,
  opens integer default 0,
  clicks integer default 0,
  bounces integer default 0,
  unsubs integer default 0,
  open_rate numeric(8,4),
  click_rate numeric(8,4),
  sent_date timestamptz,
  status text,            -- Enviado, Rascunho, Automação
  synced_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, external_id)
);

-- ============================================================
-- TABELA: email_lists
-- Listas de contatos do Brevo
-- ============================================================
create table if not exists email_lists (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  external_id text,
  name text not null,
  contacts integer default 0,
  growth numeric(8,4),
  segments integer default 0,
  synced_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, external_id)
);

-- ============================================================
-- TABELA: whatsapp_broadcasts
-- Disparos em massa do DevZapp
-- ============================================================
create table if not exists whatsapp_broadcasts (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  external_id text,
  name text,
  template_name text,
  sent integer default 0,
  delivered integer default 0,
  read_count integer default 0,
  replied integer default 0,
  status text,
  sent_at timestamptz,
  synced_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, external_id)
);

-- ============================================================
-- TABELA: whatsapp_conversations
-- Conversas individuais do DevZapp
-- ============================================================
create table if not exists whatsapp_conversations (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  external_id text,
  contact_name text,
  contact_phone text,
  last_message text,
  last_message_at timestamptz,
  unread integer default 0,
  tag text,               -- Quente, Morno, Frio
  updated_at timestamptz default now(),
  unique(user_id, external_id)
);

-- ============================================================
-- TABELA: automation_rules
-- Regras automáticas do painel
-- ============================================================
create table if not exists automation_rules (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  metric text not null,   -- CPL, CTR, ROAS...
  op text not null,       -- 'maior que', 'menor que'
  value numeric not null,
  period text,            -- '3 dias', '7 dias'...
  action text not null,   -- 'Pausar campanha', etc.
  active boolean default true,
  triggered integer default 0,
  created_at timestamptz default now()
);

-- ============================================================
-- TABELA: daily_metrics
-- Série temporal diária para os gráficos
-- ============================================================
create table if not exists daily_metrics (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade not null,
  platform text not null,
  metric_date date not null,
  invested numeric(10,2) default 0,
  leads integer default 0,
  clicks bigint default 0,
  impressions bigint default 0,
  created_at timestamptz default now(),
  unique(user_id, platform, metric_date)
);

-- ============================================================
-- ROW LEVEL SECURITY — cada usuário vê só os próprios dados
-- ============================================================

alter table user_integrations enable row level security;
alter table campaigns enable row level security;
alter table ad_sets enable row level security;
alter table creatives enable row level security;
alter table youtube_campaigns enable row level security;
alter table email_campaigns enable row level security;
alter table email_lists enable row level security;
alter table whatsapp_broadcasts enable row level security;
alter table whatsapp_conversations enable row level security;
alter table automation_rules enable row level security;
alter table daily_metrics enable row level security;

-- Políticas: usuário só lê/escreve os próprios dados
do $$
declare
  t text;
begin
  foreach t in array array[
    'user_integrations','campaigns','ad_sets','creatives',
    'youtube_campaigns','email_campaigns','email_lists',
    'whatsapp_broadcasts','whatsapp_conversations',
    'automation_rules','daily_metrics'
  ] loop
    execute format(
      'create policy "user_owns_%s" on %I
       for all using (auth.uid() = user_id)
       with check (auth.uid() = user_id)', t, t
    );
  end loop;
end $$;

-- ============================================================
-- ÍNDICES para performance
-- ============================================================
create index if not exists idx_campaigns_user on campaigns(user_id);
create index if not exists idx_campaigns_platform on campaigns(user_id, platform);
create index if not exists idx_email_campaigns_user on email_campaigns(user_id);
create index if not exists idx_daily_metrics_user_date on daily_metrics(user_id, metric_date desc);
create index if not exists idx_whatsapp_conv_updated on whatsapp_conversations(user_id, last_message_at desc);
