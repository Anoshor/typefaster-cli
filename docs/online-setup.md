# Going online — Cloudflare tunnel + OAuth login

How to let a friend on another machine join your races, and (optionally) enable
GitHub / Google login. Everything here is **free**.

The model: your server runs locally (Colima → `localhost:8000`). A **tunnel**
gives it a public `https://…` address. Friends point their client at that URL.

---

## 1. Start the server
```bash
cd typefaster-cli
make up                      # redis + server on localhost:8000  (Colima)
curl -s localhost:8000/healthz   # {"status":"ok"}
```

## 2. Expose it with a Cloudflare tunnel (free, no account)
```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8000
```
It prints a public URL, e.g.:
```
https://brave-otter-1234.trycloudflare.com
```
Keep this terminal open — the tunnel lives as long as it runs. WebSockets work
over it automatically (`https://` → `wss://`).

> The free `trycloudflare.com` URL changes each run. For a stable address, use a
> named tunnel (Cloudflare account, still free) or deploy to a VM (`deployment.md`).

## 3. Point clients at the tunnel
On **each** machine (yours and your friend's):
```bash
typefaster config set-server https://brave-otter-1234.trycloudflare.com
typefaster config show
```

## 4. Play
**You (host):**
```bash
typefaster register alice          # or: typefaster login --github
typefaster lobby create --name "Friday" --time 60
# waiting room shows the join code, e.g. 6AJ97X
```
**Friend (other machine):**
```bash
typefaster config set-server https://brave-otter-1234.trycloudflare.com
typefaster register bob            # or login --github / --google
typefaster lobby join 6AJ97X
```
Both: once you see each other in the room, press **R**. Server runs the
countdown and the race. After, **R** plays again, **Esc** leaves.

---

## 5. (Optional) GitHub / Google login

Username/password works out of the box. To add social login (device flow, the
`gh auth login` experience), create the apps below and put the IDs in `.env`,
then `make up` to restart.

### GitHub (client id only — free)
1. https://github.com/settings/developers → **New OAuth App**.
2. Application name: `TYPEFASTER`; Homepage URL: your repo or tunnel URL;
   Authorization callback URL: any valid URL (device flow doesn't use it, e.g.
   the homepage).
3. **Enable Device Flow** (checkbox on the app page) — required.
4. Copy the **Client ID** into `.env`:
   ```
   TYPEFASTER_GITHUB_CLIENT_ID=Iv1.xxxxxxxx
   ```
   (No client secret needed for GitHub device flow.)

### Google (client id + secret — free)
1. https://console.cloud.google.com → create/select a project.
2. **APIs & Services → OAuth consent screen** → External → fill basics → add
   your email as a test user.
3. **Credentials → Create credentials → OAuth client ID → "TVs and Limited
   Input devices"**.
4. Copy **Client ID** and **Client secret** into `.env`:
   ```
   TYPEFASTER_GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
   TYPEFASTER_GOOGLE_CLIENT_SECRET=xxxx
   ```

### Apply + use
```bash
make up                # restart server with the new env
typefaster login --github     # shows a code + opens github.com/login/device
typefaster login --google     # shows a code + opens google.com/device
```
The CLI prints a short code and opens your browser; approve there and you're in.
First social login auto-creates a TYPEFASTER account (username derived from your
GitHub login / Google email).

> Device flow needs **no public callback URL**, so it works behind the tunnel
> and on `localhost` alike. Provider login is free; the only possible cost is a
> server host if you later move off the tunnel (see `deployment.md`).

## Stop everything
```bash
# Ctrl-C the cloudflared terminal
make down            # stop redis + server
```
