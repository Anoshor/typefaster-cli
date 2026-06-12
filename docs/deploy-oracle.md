# Deploy the server on an Oracle Cloud Always-Free VM ($0 forever)

A real 24/7 server on Oracle's Always-Free ARM VM. No ongoing cost.

You do the **console steps** (account + VM + open a port). Then a **single
command** on the VM deploys everything (`scripts/deploy-oracle.sh`).

---

## 1. Create the account
1. Go to <https://www.oracle.com/cloud/free/> → **Start for free**.
2. Sign up. A credit/debit card is required for identity verification — Oracle
   **does not charge** Always-Free resources. Pick your home region close to you
   (you can't change it later).

## 2. Create an Always-Free VM
1. Console → **Menu → Compute → Instances → Create instance**.
2. **Image & shape → Edit shape**:
   - Shape series: **Ampere (Arm)** → `VM.Standard.A1.Flex`
   - Set **1 OCPU / 6 GB** (well within the free allowance; plenty for this).
   - *(If Ampere shows "out of capacity", try another availability domain, or use
     the AMD `VM.Standard.E2.1.Micro` Always-Free shape instead.)*
3. **Image**: Canonical **Ubuntu 22.04** (or 24.04).
4. **Networking**: keep the default VCN; ensure **"Assign a public IPv4 address"** is on.
5. **SSH keys**: choose **Generate a key pair** and **download the private key**
   (or paste your own public key).
6. **Create**. When it's running, copy the **Public IP address**.

## 3. Open the game port (VCN Security List)
Oracle blocks inbound by default — open TCP **8000**:
1. Instance page → **Virtual cloud network** link → **Security Lists** →
   **Default Security List**.
2. **Add Ingress Rules**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: **TCP**
   - Destination Port Range: `8000`
   - **Add**.

## 4. SSH in and deploy (one command)
```bash
chmod 400 ~/Downloads/your-key.key      # the key you downloaded
ssh -i ~/Downloads/your-key.key ubuntu@<PUBLIC_IP>

# on the VM:
curl -fsSL https://raw.githubusercontent.com/Anoshor/typefaster-cli/main/scripts/deploy-oracle.sh | bash
```
The script installs Docker, builds the stack, opens the OS firewall, and prints:
```
Public: http://<PUBLIC_IP>:8000/healthz
```
Check it from your laptop:
```bash
curl http://<PUBLIC_IP>:8000/healthz     # {"status":"ok"}
```

## 5. Play
```bash
typefaster config set-server http://<PUBLIC_IP>:8000
typefaster register <name>
typefaster lobby create --name Friday --time 60
```
Multiplayer runs over `ws://` (works fine). Share the IP + `config set-server`
line with friends.

> Want the client to default to your server (so nobody needs `config set-server`)?
> Tell me the public IP/domain and I'll bake it in and ship a new release.

---

## Optional: free HTTPS + stable hostname (DuckDNS + Caddy)
Plain `http://IP` works, but for a tidy `https://you.duckdns.org`:
1. Get a free subdomain at <https://www.duckdns.org> and point it at your VM IP.
2. On the VM, run Caddy as a reverse proxy (auto Let's Encrypt):
   ```bash
   sudo docker run -d --name caddy --restart unless-stopped --network host \
     caddy caddy reverse-proxy --from you.duckdns.org --to :8000
   ```
3. Open TCP **80** and **443** in the VCN Security List too.
4. Players: `typefaster config set-server https://you.duckdns.org` (uses `wss://`).

## Updating later
```bash
ssh -i key ubuntu@<IP> 'curl -fsSL https://raw.githubusercontent.com/Anoshor/typefaster-cli/main/scripts/deploy-oracle.sh | bash'
```

## Stop / costs
Always-Free resources don't expire as long as the account stays in good standing.
To stop: `sudo docker compose down` in `/opt/typefaster`. No charges for the
Always-Free shapes.
