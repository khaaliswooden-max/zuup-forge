# Deploy Aureon™ — Your First Platform

Deploy the **aureon** platform (Planetary-Scale Procurement Substrate) in minutes.

## From the Forge UI

1. Open [zuup-forge.vercel.app](https://zuup-forge.vercel.app/)
2. Click **Deploy** on the Aureon™ platform card
3. Choose **Render** or **Railway** and follow the one-click flow

---

## Render (Recommended)

1. Go to [dashboard.render.com](https://dashboard.render.com/select-repo?type=blueprint)
2. Connect your GitHub repo (`khaaliswooden-max/zuup-forge` or your fork)
3. Render detects `render.yaml` at repo root and creates the aureon service
4. Deploy — you’ll get a URL like `https://aureon-xxx.onrender.com`
5. Docs: `/docs` | Health: `/health`

If the repo root differs, set **Root Directory** to `zuup-forge` in Render settings.

---

## Railway

1. Go to [railway.app/new](https://railway.app/new)
2. Deploy from GitHub → select `zuup-forge` repo
3. Set **Root Directory** to `zuup-forge` (the inner folder)
4. Railway uses `platforms/aureon/Dockerfile` — no extra config needed
5. Generate a domain in Railway dashboard

---

## Local Docker

```bash
cd zuup-forge
docker build -f platforms/aureon/Dockerfile -t aureon .
docker run -p 8000:8000 aureon
```

Open http://localhost:8000/docs

---

## Fly.io

```bash
cd zuup-forge
fly launch --dockerfile platforms/aureon/Dockerfile --name aureon
fly deploy
```

---

*ZUUP FORGE — The Platform That Builds Platforms*
