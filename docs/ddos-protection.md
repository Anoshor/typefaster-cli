# DDoS & abuse protection

Two independent layers. The app-layer guards ship in the code and run on the VM.
True volumetric DDoS protection has to live **upstream** of the box — the cheap,
standard answer is Cloudflare's free tier.

> **Reality check:** no amount of application code protects against a volumetric
> flood. A botnet saturating the link or CPU takes the VM down before Python
> runs. App-layer limits stop spam and amateur floods; an edge (Cloudflare)
> absorbs the real thing.

---

## Layer 1 — App-layer guards (already shipped, $0)

All per-IP, backed by the existing Redis fixed-window counter. Tunable via env
(`TYPEFASTER_*`) without code changes.

| Guard | Default | Where |
|---|---|---|
| Global HTTP requests / IP | `120` / 60s | `GlobalRateLimitMiddleware` (`server/app/abuse.py`) |
| Register + login / IP | `15` / 60s | `auth` router |
| OAuth start / IP | `20` / 60s | `oauth` router |
| OAuth poll / IP | `90` / 60s | `oauth` router |
| Lobby create / IP | `12` / 60s | `lobbies` router |
| Concurrent WS sockets / IP | `10` | `lobby_ws` + `incr_ws_connections` |
| WS messages / connection | `60` / 10s (~6/s) | `MessageRateLimiter` |
| In-flight HTTP requests (whole box) | `200` | uvicorn `--limit-concurrency` (503 over) |

Health probes (`/healthz`, `/readyz`) are exempt so monitoring isn't throttled.

The real client IP is honored because uvicorn runs with `--proxy-headers
--forwarded-allow-ips "*"`, so the reverse proxy's `X-Forwarded-For` is trusted.
**This is only safe because port 8000 is not publicly reachable** (see Layer 3).

Tune any limit on the VM, then recreate the container:
```bash
# /opt/typefaster/.env
TYPEFASTER_GLOBAL_RATE_LIMIT=240
TYPEFASTER_WS_MAX_CONNECTIONS_PER_IP=6
```
```bash
cd /opt/typefaster && sudo docker compose up -d --force-recreate server
```

---

## Layer 2 — Cloudflare free tier (the actual DDoS saviour, ~$0)

Cloudflare's free plan gives unmetered L3/L4 DDoS mitigation, a WAF, bot
filtering, caching, and an "I'm Under Attack" mode. The only cost is a domain
(~$1–12/yr) — Cloudflare can't proxy `sslip.io`, so you need a real name.

1. **Get a domain** and add it to Cloudflare (free plan). Cloudflare gives you
   two nameservers — set them at your registrar.
2. **DNS:** add an `A` record `play` → `140.245.248.113`, **proxy ON** (orange
   cloud). Now visitors hit Cloudflare, not your VM directly.
3. **Point the game at it:** issue a cert for the new host and update the client
   default (`DEFAULT_SERVER_URL` in `client/typefaster/net/token_store.py`) +
   Caddy site address to `play.yourdomain.com`.
4. **Hide the origin:** once traffic flows through Cloudflare, restrict the VM's
   firewall to accept 443 **only from Cloudflare's IP ranges**
   (https://www.cloudflare.com/ips/). Now attackers can't bypass Cloudflare by
   hitting the IP directly.
5. **Rules (free):**
   - **Rate limiting** → e.g. 100 req/min/IP to `/auth/*`.
   - **WAF managed rules** → on.
   - **Under Attack Mode** → flip on only during an active attack (adds a JS
     challenge to every visitor).

WebSockets work through Cloudflare's proxy on the free plan automatically.

---

## Layer 3 — VM firewall (do this regardless, $0)

Confirm only what's needed is open. On the Oracle security list **and** the
host firewall, allow inbound **443** (HTTPS) and **22** (SSH) only — never 8000
or 6379:

```bash
sudo ss -tlnp                     # nothing on 0.0.0.0:8000 or :6379
```
- `6379` (Redis) and `8000` (app) must stay on the internal Docker network only.
- Keep SSH key-only; `fail2ban` guards 22 (SSH brute force), not HTTP.

---

## What to do during an active attack

1. Cloudflare dashboard → **Under Attack Mode: On**.
2. Add a temporary Cloudflare rate-limit / block rule for the offending pattern.
3. If it's app-level spam from a few IPs, they're already being 429'd; tighten
   `TYPEFASTER_GLOBAL_RATE_LIMIT` and recreate the container.
