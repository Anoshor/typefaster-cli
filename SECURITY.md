# Security Policy

## Supported versions
The latest released version on PyPI (`typefaster-cli`) and the `main` branch
receive security fixes.

## Reporting a vulnerability
Please **do not open a public issue** for security problems.

Report privately via GitHub's **Security advisories**:
<https://github.com/Anoshor/typefaster-cli/security/advisories/new>

(or email the maintainer listed on the GitHub profile). Include steps to
reproduce and impact. We aim to acknowledge within 72 hours and to ship a fix or
mitigation promptly, crediting reporters who wish to be named.

## Hardening notes (for self-hosters)
- Run the server only behind TLS (the bundled nginx profile, or a TLS-terminating
  platform like Fly.io). Never expose Redis publicly — keep it on the internal
  network (`docker-compose.yml` does not publish 6379).
- Set a strong `TYPEFASTER_JWT_SECRET` (e.g. `openssl rand -hex 32`); rotating it
  invalidates all existing sessions.
- Lock `TYPEFASTER_CORS_ORIGINS` to your real domain in production (default `*`).
- Credential endpoints (`/auth/register`, `/auth/login`, OAuth start) are
  per-IP rate limited; keep `--proxy-headers` enabled so the limiter sees real
  client IPs behind a proxy.
- Passwords are hashed with bcrypt; results are re-scored server-side with
  anti-cheat before leaderboard writes.
