# Deploy: VPS (backend + Neo4j) + Vercel (frontend)

## 1. VPS — point DNS

In your DNS, create an A record:

```
api.example.com  →  <VPS public IP>
```

## 2. VPS — install Docker & clone

```bash
ssh root@your-vps
apt update && apt install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx
systemctl enable --now docker

cd /opt
git clone https://github.com/dafesmith/graphrag-decision-trace.git
cd graphrag-decision-trace
```

## 3. VPS — env file

```bash
cp .env.production.example .env
nano .env   # set NEO4J_PASSWORD, ANTHROPIC_API_KEY, OPENAI_API_KEY, CORS_ALLOW_ORIGINS
```

`CORS_ALLOW_ORIGINS` should be your Vercel production URL, e.g. `https://your-frontend.vercel.app`. For preview deploys, also set `CORS_ALLOW_ORIGIN_REGEX=^https://.*\.vercel\.app$`.

## 4. VPS — start the stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
```

Backend is now on `127.0.0.1:8000` (not exposed publicly yet).

## 5. VPS — seed the graph

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/generate_sample_data.py
```

## 6. VPS — nginx + TLS

```bash
cp deploy/nginx/api.conf /etc/nginx/sites-available/api
sed -i 's/api.example.com/api.yourdomain.com/g' /etc/nginx/sites-available/api
ln -sf /etc/nginx/sites-available/api /etc/nginx/sites-enabled/api
nginx -t && systemctl reload nginx

certbot --nginx -d api.yourdomain.com
```

Verify: `curl https://api.yourdomain.com/health` (or whatever your health route is).

## 7. Vercel — deploy frontend

In the Vercel dashboard, **Add New → Project** → import `dafesmith/graphrag-decision-trace`:

- **Root Directory:** `frontend`
- **Framework Preset:** Next.js (auto)
- **Environment Variables:**
  - `NEXT_PUBLIC_API_URL` = `https://api.yourdomain.com`

Deploy. After it's live, copy the production URL back into the VPS `.env` `CORS_ALLOW_ORIGINS`, then:

```bash
docker compose -f docker-compose.prod.yml up -d backend
```

## 8. Firewall

Only 22, 80, 443 should be open to the internet. Neo4j Bolt (7687) and Browser (7474) are bound to `127.0.0.1` in `docker-compose.prod.yml`; reach them via SSH tunnel:

```bash
ssh -L 7474:127.0.0.1:7474 -L 7687:127.0.0.1:7687 root@your-vps
```
