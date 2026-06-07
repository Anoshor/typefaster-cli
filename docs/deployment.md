# Deployment Guide — Single Linux VM

This deploys the TYPEFASTER online stack (Redis + FastAPI server + nginx TLS)
to one small Ubuntu VM with Docker Compose. It is intentionally minimal: no
Kubernetes, no managed database, low operating cost.

> This is documentation only — nothing here runs automatically.

## 0. Sizing
A 1 vCPU / 1 GB VM handles a small community. 2 vCPU / 2 GB is comfortable.

## 1. Provision Ubuntu & create a user
```bash
adduser deploy && usermod -aG sudo deploy
# log back in as `deploy`
```

## 2. Install Docker + Compose plugin
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER       # re-login to take effect
docker compose version              # verify the v2 plugin
```

## 3. Get the code & configure
```bash
git clone <your-repo-url> typefaster && cd typefaster
cp .env.example .env
# REQUIRED: set a strong secret
sed -i "s/^TYPEFASTER_JWT_SECRET=.*/TYPEFASTER_JWT_SECRET=$(openssl rand -hex 32)/" .env
# Lock CORS to your domain
sed -i "s|^TYPEFASTER_CORS_ORIGINS=.*|TYPEFASTER_CORS_ORIGINS=https://play.example.com|" .env
```

## 4. Firewall
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
Do **not** open 6379 (Redis) or 8000 (server) — they stay on the internal
Docker network behind nginx. For production, remove the `ports:` mapping on the
`server` service so only nginx is reachable.

## 5. TLS certificates (Let's Encrypt)
Issue a cert on the host, then mount it into nginx.
```bash
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d play.example.com   # needs :80 free briefly
mkdir -p infra/nginx/certs
sudo cp /etc/letsencrypt/live/play.example.com/fullchain.pem infra/nginx/certs/
sudo cp /etc/letsencrypt/live/play.example.com/privkey.pem  infra/nginx/certs/
sudo chown $USER infra/nginx/certs/*.pem
```
Edit `server_name` in `infra/nginx/nginx.conf` to your domain.

## 6. Launch
```bash
make up-proxy          # redis + server + nginx (TLS)
# or without the proxy (dev): make up
docker compose ps
curl -fsS https://play.example.com/healthz
```
Point your client at it:
```bash
# in ~/.config/typefaster/auth.json set "server_url": "https://play.example.com"
typefaster register alice
typefaster lobby create --name "Launch Day"
```

## 7. Certificate renewal
```bash
# crontab -e
0 3 * * * certbot renew --quiet && \
  cp /etc/letsencrypt/live/play.example.com/*.pem /home/deploy/typefaster/infra/nginx/certs/ && \
  cd /home/deploy/typefaster && docker compose --profile proxy restart nginx
```

## 8. Backups
Redis persists to the `redis-data` volume (AOF + RDB). Back it up nightly:
```bash
# crontab -e
30 3 * * * docker run --rm -v typefaster_redis-data:/data -v /home/deploy/backups:/backup \
  alpine sh -c "cd /data && tar czf /backup/redis-$(date +\%F).tar.gz ."
# prune older than 14 days
0 4 * * * find /home/deploy/backups -name 'redis-*.tar.gz' -mtime +14 -delete
```
Restore by stopping the stack and extracting the tarball back into the volume.

## 9. Monitoring & logs
- Logs are structured (key=value) on stdout: `docker compose logs -f server`.
- Health: `GET /healthz` (liveness), `GET /readyz` (Redis check) — wire these to
  an uptime monitor (e.g. UptimeRobot) hitting `https://play.example.com/healthz`.
- Optional: `docker stats` for resource usage; ship logs to your aggregator if
  desired.

## 10. Updates
```bash
cd ~/typefaster && git pull
make up-proxy          # rebuilds changed images, recreates containers
```
`restart: unless-stopped` brings everything back after a reboot.

## 11. Optional: cap leaderboard memory
A small cron can expire stale daily/weekly keys:
```bash
0 5 * * * docker compose exec -T redis sh -c \
 "redis-cli --scan --pattern 'leaderboard:daily:*' | sort | head -n -30 | xargs -r redis-cli del"
```

## Troubleshooting
| Symptom | Check |
|---------|-------|
| 502 from nginx | `docker compose logs server`; is `/readyz` green? |
| WebSocket won't connect | nginx `/ws/` block present? client using `wss://`? |
| 401 everywhere | `TYPEFASTER_JWT_SECRET` changed → tokens invalidated; log in again |
| Redis OOM | raise `maxmemory` in `infra/redis/redis.conf` or VM RAM |
