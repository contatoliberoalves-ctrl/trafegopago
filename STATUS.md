# STATUS DO PROJETO — Tráfego Pago Dashboard

Última atualização: 2026-06-16

## Integrações

| Serviço | Status | Observações |
|---------|--------|-------------|
| Brevo (Email) | ⏳ Pendente | FASE 3 |
| Meta Ads | ⏳ Pendente | FASE 4 — precisa de App Review |
| Google/YouTube | ⏳ Pendente | FASE 5 — Developer Token pode demorar 1-5 dias |
| DevZapp (WhatsApp) | ⏳ Pendente | FASE 6 |

## Infraestrutura

| Item | Status | Endereço / Localização |
|------|--------|------------------------|
| Supabase | ⏳ Aguardando criação | — |
| Cloudflare Pages | ⏳ Pendente | FASE 8 |
| GitHub | ⏳ Pendente | FASE 8 |

## Onde ficam as chaves

| Chave | Onde fica | NUNCA vai para |
|-------|-----------|----------------|
| Supabase Anon Key | `.env` + Cloudflare Pages env vars | — |
| Brevo API Key | Supabase Secrets | front-end, Git |
| Meta App Secret | Supabase Secrets | front-end, Git |
| Google Client Secret | Supabase Secrets | front-end, Git |
| Google Developer Token | Supabase Secrets | front-end, Git |
| DevZapp Token | Supabase Secrets | front-end, Git |

## Dependências manuais pendentes

- [ ] Criar projeto no Supabase (supabase.com)
- [ ] Solicitar Developer Token no Google Ads (pode demorar 1-5 dias úteis)
- [ ] Criar App no Facebook Developers (tipo Business)
- [ ] Cadastrar conta no DevZapp
