# Security review — TYPEFASTER

A practical review of the deployed game's security posture, what's been hardened,
and the honest limits.

## Threat model
A small, public, free-to-play terminal game. Assets worth protecting:
- The **VM** (don't let it be taken over / used to pivot to your accounts).
- **User credentials** (passwords/tokens in transit and at rest).
- **Availability** (don't let it be trivially DoS'd or abused).

## What's in place

### Transport
- **HTTPS/WSS via Caddy + Let's Encrypt** (`https://<ip>.sslip.io`). Passwords,
  tokens, and WebSocket traffic are TLS-encrypted in transit. The client default
  points at the `https://` URL.
- Plain `http://:8000` remains reachable for older clients; **recommend closing
  port 8000 at the Oracle Security List** once everyone is on the HTTPS build.

### Authentication & data
- Passwords hashed with **bcrypt** (never stored or logged in plaintext).
- **JWT** access tokens with expiry; sessions tracked server-side in Redis so
  **logout revokes** immediately.
- OAuth (GitHub/Google) uses the **device flow** — no client secret on user
  machines; Google's secret stays server-side only.
- Input validation via **Pydantic** on every request body.

### Abuse / hardening
- **Per-IP rate limiting** on `/auth/register`, `/auth/login`, OAuth start
  (Redis fixed-window) — slows brute force / spam.
- **Anti-cheat**: results re-scored server-side; implausible runs flagged and
  excluded from leaderboards.
- **Redis** is bound only to the internal Docker network — **never published** to
  the host or internet (verified: no public `:6379`).
- Server runs as a **non-root** user inside the container.

### VM hardening (Oracle Ubuntu 24.04)
- **SSH is key-only** (`PasswordAuthentication no`); no password logins.
- **fail2ban** active (bans brute-force SSH sources).
- **unattended-upgrades** enabled (auto security patches).
- **Firewall**: only 22 (SSH), 80/443 (TLS), 8000 (legacy) open; everything else
  dropped. Cloud Security List + host iptables both enforced.

### Supply chain / secrets
- `JWT secret` and any OAuth secrets live only in the VM's `.env` (git-ignored) —
  **never committed**. Generated with `openssl rand -hex 32`.
- CI runs **pip-audit**, **Dependabot**, and **CodeQL**.
- PyPI publishing uses **Trusted Publishing (OIDC)** — no long-lived tokens.

## Residual risks / recommendations
- **Close port 8000** (plain HTTP) once clients are updated, so no one can use
  the unencrypted endpoint. (Leave 443 only.)
- `sslip.io` is convenient but third-party DNS; for a "real" domain, point your
  own and re-issue the cert (one Caddy line).
- Consider lowering `permitrootlogin` to `no` (currently key-only) and adding a
  basic uptime/error monitor.
- Rotate `TYPEFASTER_JWT_SECRET` periodically (invalidates all sessions).

## "Can it be traced back to me?"
Honest answer: **not fully, and not while you also want public credit.**
- The GitHub repo is under your account, `pyproject` lists you as author, commits
  carry your email, and the TUI shows your name — all **intentional credit**.
- The server is a VM **you** own (its public IP is inherently visible to players).
- What hardening buys you: attackers **can't take over the VM or your accounts**
  from the game, and they **can't read user traffic** (TLS). That's the realistic,
  important protection.
- If you ever want true anonymity, that's a different setup: a pseudonymous
  GitHub identity, a VM under a separate account/payment, no name in the app, and
  a domain registered with WHOIS privacy. Say the word and we can plan that —
  it's mutually exclusive with public credit.

## Reporting
Vulnerabilities: see [`SECURITY.md`](../SECURITY.md) (private GitHub advisory).
