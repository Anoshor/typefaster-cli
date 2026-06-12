#!/usr/bin/env bash
# One-shot TYPEFASTER server deploy for a fresh Ubuntu VM (Oracle Always-Free,
# or any Ubuntu host). Installs Docker, fetches the repo, and starts the stack.
#
# Run it on the VM (as the default user, e.g. `ubuntu`):
#   curl -fsSL https://raw.githubusercontent.com/Anoshor/typefaster-cli/main/scripts/deploy-oracle.sh | bash
#
# Re-running it safely updates to the latest code and restarts the stack.
set -euo pipefail

REPO="https://github.com/Anoshor/typefaster-cli"
DIR="/opt/typefaster"
PORT="${SERVER_PORT:-8000}"

echo "==> Installing prerequisites (git, openssl, iptables-persistent)…"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git openssl ca-certificates curl

echo "==> Installing Docker (if missing)…"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo systemctl enable --now docker

echo "==> Fetching the repo into ${DIR}…"
sudo mkdir -p "$DIR"
sudo chown "$USER" "$DIR"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only
else
  git clone "$REPO" "$DIR"
fi
cd "$DIR"

echo "==> Writing .env (random JWT secret) if absent…"
if [ ! -f .env ]; then
  cat > .env <<EOF
TYPEFASTER_JWT_SECRET=$(openssl rand -hex 32)
TYPEFASTER_CORS_ORIGINS=*
TYPEFASTER_ACCESS_TOKEN_MINUTES=1440
SERVER_PORT=${PORT}
EOF
fi

echo "==> Opening port ${PORT} on the OS firewall (Oracle Ubuntu blocks by default)…"
# Oracle's Ubuntu images ship iptables rules that REJECT inbound. Insert ACCEPT.
if sudo iptables -C INPUT -p tcp --dport "${PORT}" -j ACCEPT 2>/dev/null; then
  echo "    (rule already present)"
else
  sudo iptables -I INPUT -p tcp --dport "${PORT}" -j ACCEPT
fi
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent >/dev/null 2>&1 || true
sudo netfilter-persistent save >/dev/null 2>&1 || true

echo "==> Building & starting the stack…"
sudo docker compose up -d --build

echo "==> Waiting for health…"
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then break; fi
  sleep 2
done

IP="$(curl -fsS ifconfig.me 2>/dev/null || echo '<this-vm-public-ip>')"
echo
echo "============================================================"
echo " TYPEFASTER server is up."
echo "   Local : http://127.0.0.1:${PORT}/healthz"
echo "   Public: http://${IP}:${PORT}/healthz"
echo
echo " Players point their CLI at it with:"
echo "   typefaster config set-server http://${IP}:${PORT}"
echo
echo " IMPORTANT: also add an Ingress rule for TCP ${PORT} (source 0.0.0.0/0)"
echo " in your VCN Security List in the Oracle console, or it won't be reachable."
echo "============================================================"
