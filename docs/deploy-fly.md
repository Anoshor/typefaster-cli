# Deploy the server to Fly.io (free-tier friendly)

Gives you a permanent `https://<app>.fly.dev` so anyone can play with **zero
config** (the client already defaults to `https://typefaster-cli.fly.dev`).

## Prereqs
```bash
brew install flyctl
fly auth signup    # or: fly auth login
```

## 1. Create the app (uses the repo's fly.toml)
```bash
cd typefaster-cli
fly launch --no-deploy --copy-config --name typefaster-cli --region bom
```
If `typefaster-cli` is taken, pick another name — then update `app` in
`fly.toml` **and** the default in `client/typefaster/net/token_store.py`, and
re-release the client so the baked-in default matches.

## 2. Redis (free Upstash)
```bash
fly redis create            # choose the free plan; copy the rediss://… URL it prints
```

## 3. Secrets
```bash
fly secrets set \
  TYPEFASTER_JWT_SECRET="$(openssl rand -hex 32)" \
  TYPEFASTER_REDIS_URL="rediss://…from step 2…" \
  TYPEFASTER_CORS_ORIGINS="*"
# Optional social login (see online-setup.md):
# fly secrets set TYPEFASTER_GITHUB_CLIENT_ID=... TYPEFASTER_GOOGLE_CLIENT_ID=... TYPEFASTER_GOOGLE_CLIENT_SECRET=...
```

## 4. Deploy
```bash
fly deploy
fly status
curl -s https://typefaster-cli.fly.dev/healthz      # {"status":"ok"}
curl -s https://typefaster-cli.fly.dev/readyz       # {"status":"ready","redis":"ok"}
```

## 5. Play (anyone, anywhere)
```bash
pipx install typefaster-cli
typefaster register alice        # uses the Fly server by default — no config needed
typefaster lobby create --name Friday --time 60
```
WebSockets work automatically over Fly's TLS (`wss://`).

## Updating the server later
- Manually: `fly deploy` from the repo.
- Automated (optional): the release workflow already builds & pushes the server
  image to `ghcr.io/anoshor/typefaster-server`; add a `fly deploy --image …`
  step (or `flyctl deploy` GitHub Action with `FLY_API_TOKEN`) to auto-deploy on
  each tag.

## Costs
Fly's free allowance covers one small always-on machine + free Upstash Redis —
$0 for a hobby server. Heavier usage may incur small charges; check Fly billing.
