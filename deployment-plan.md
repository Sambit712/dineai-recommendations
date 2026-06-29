# DineAI — Deployment Plan

> **Backend → Railway** | **Frontend → Vercel**
>
> This document covers everything needed to ship the DineAI restaurant recommendation system to production.

---

## Architecture Overview

```
┌─────────────────────────────────────┐
│           USER BROWSER              │
└──────────────┬──────────────────────┘
               │  HTTPS
               ▼
┌─────────────────────────────────────┐
│         VERCEL (Frontend)           │
│  frontend/index.html                │
│  frontend/style.css                 │
│  frontend/app.js                    │
│                                     │
│  API calls → Railway backend URL    │
└──────────────┬──────────────────────┘
               │  POST /recommend
               │  GET  /health
               ▼
┌─────────────────────────────────────┐
│         RAILWAY (Backend)           │
│  FastAPI + Uvicorn                  │
│  src/api/app.py                     │
│  Python 3.11 · Nixpacks build       │
│                                     │
│  Build: python scripts/prefetch.py  │
│  Start: uvicorn src.api.app:app     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  External Services                  │
│  • Groq API (LLM inference)         │
│  • HuggingFace Datasets (data load) │
└─────────────────────────────────────┘
```

> **IMPORTANT:** Because the frontend will be a **separate Vercel origin**, the `CORS_ORIGINS` env var on Railway **must** be set to the Vercel URL before going live. The `API_ENDPOINT` constant in `app.js` **must** also be updated from `'/recommend'` to the Railway URL.

---

## Phase 1 — Pre-deployment Checklist

Before pushing anything, verify these items locally:

- [ ] `python main.py --no-reload` starts without errors
- [ ] `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] `POST /recommend` returns valid results
- [ ] `.env` is in `.gitignore` (already is ✅)
- [ ] `data/*.pkl`, `data/*.csv`, `data/*.parquet` are in `.gitignore` (already is ✅)
- [ ] `requirements.txt` is up to date

---

## Phase 2 — Backend Deployment on Railway

### 2.1 Required Files (Already Present ✅)

| File | Purpose |
|------|---------|
| `Procfile` | Start command: `uvicorn src.api.app:app --host 0.0.0.0 --port $PORT` |
| `railway.json` | Nixpacks builder + build command (`python scripts/prefetch.py`) |
| `requirements.txt` | Python dependencies |

### 2.2 Step-by-Step

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "chore: prepare for Railway deployment"
   git push origin main
   ```

2. **Create a Railway project**
   - Go to [railway.app](https://railway.app) → **New Project**
   - Select **Deploy from GitHub repo** → connect your repository
   - Railway auto-detects Nixpacks and uses `railway.json`

3. **Set Environment Variables** in Railway dashboard → *Variables* tab:

   | Variable | Value | Notes |
   |----------|-------|-------|
   | `GROQ_API_KEY` | `gsk_...` | Your Groq API key |
   | `LLM_MODEL` | `llama3-70b-8192` | Or any Groq-supported model |
   | `LLM_TEMPERATURE` | `0.7` | |
   | `LLM_MAX_TOKENS` | `1024` | |
   | `FILTER_TOP_N` | `10` | Candidates sent to LLM |
   | `OUTPUT_TOP_K` | `5` | Final results shown |
   | `CORS_ORIGINS` | *(set after Vercel deploy — your Vercel URL)* | e.g. `https://dineai.vercel.app` |

   > **WARNING:** Leave `CORS_ORIGINS` **empty** for the first deploy so you can test the API directly. Set it to the Vercel URL **after** Phase 3 is complete.

4. **Trigger a deploy** — Railway will:
   - Install dependencies from `requirements.txt`
   - Run `python scripts/prefetch.py` (downloads + caches the dataset)
   - Start `uvicorn src.api.app:app --host 0.0.0.0 --port $PORT`

5. **Verify the backend is live**
   ```
   GET https://<your-railway-app>.up.railway.app/health
   ```
   Expected: `{"status":"ok","restaurants_loaded":XXXX}`

6. **Note your Railway URL** — you will need it in Phase 3.

### 2.3 Railway Configuration Reference

```json
// railway.json (already present)
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "python scripts/prefetch.py"
  }
}
```

```
# Procfile (already present)
web: uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
```

> **TIP:** Railway exposes logs in real time. If the build fails, check the **Build Logs** tab first — the most common issue is the dataset prefetch failing due to a missing `GROQ_API_KEY` or network timeout.

---

## Phase 3 — Frontend Deployment on Vercel

### 3.1 Required Change — Update `API_ENDPOINT` in `app.js`

Currently, `app.js` calls the API at a relative path (`/recommend`), which works when the frontend is served by the same FastAPI server. Since Vercel will serve the frontend from a **separate origin**, you must point it at the Railway URL.

**Edit `frontend/app.js`, line 12:**

```diff
- const API_ENDPOINT = '/recommend';
+ const API_ENDPOINT = 'https://<your-railway-app>.up.railway.app/recommend';
```

Replace `<your-railway-app>` with your actual Railway subdomain from Phase 2 Step 5.

### 3.2 Add a Vercel Configuration File

Create `frontend/vercel.json` to configure routing:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

> This ensures all requests fall through to `index.html` (needed for SPA-style navigation).

### 3.3 Step-by-Step

1. **Commit the changes**
   ```bash
   git add frontend/app.js frontend/vercel.json
   git commit -m "feat: point frontend at Railway backend URL"
   git push origin main
   ```

2. **Create a Vercel project**
   - Go to [vercel.com](https://vercel.com) → **New Project**
   - Import your GitHub repository
   - In **Configure Project** settings:
     - **Root Directory:** `frontend`
     - **Framework Preset:** `Other`
     - **Build Command:** *(leave blank — no build step needed)*
     - **Output Directory:** `.` *(current directory)*

3. **Deploy** — Vercel will publish the three static files:
   - `index.html`
   - `style.css`
   - `app.js`

4. **Note your Vercel URL** (e.g. `https://dineai.vercel.app`)

### 3.4 Go Back to Railway — Set CORS

Now that you have the Vercel URL, go back to Railway → *Variables* and set:

```
CORS_ORIGINS=https://dineai.vercel.app
```

Railway will automatically redeploy. After it's live, your frontend and backend will be properly connected.

---

## Phase 4 — Post-Deployment Verification

### 4.1 End-to-End Test Checklist

- [ ] `GET https://<railway>.up.railway.app/health` → `{"status":"ok"}`
- [ ] `GET https://<railway>.up.railway.app/docs` → Swagger UI loads
- [ ] Open Vercel URL → DineAI homepage loads correctly
- [ ] Select a location → submit form → recommendations appear
- [ ] Check browser DevTools → Network tab → `/recommend` returns 200

### 4.2 Quick API Smoke Test

```bash
curl -X POST https://<your-railway-app>.up.railway.app/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "location": "bangalore",
    "budget": "medium",
    "cuisine": "indian",
    "min_rating": 3.5,
    "extras": "good ambience"
  }'
```

Expected: `{"recommendations":[...],"total_found":N,...}`

### 4.3 CORS Verification

Open browser DevTools on the Vercel URL → Console. If you see CORS errors like:

```
Access to fetch at 'https://...' has been blocked by CORS policy
```

Double-check that `CORS_ORIGINS` in Railway exactly matches your Vercel URL (no trailing slash).

---

## Phase 5 — Environment Variables Summary

### Railway (Backend)

| Variable | Required | Example |
|----------|----------|---------|
| `GROQ_API_KEY` | ✅ Yes | `gsk_xxxxxxxxxxxx` |
| `LLM_MODEL` | ✅ Yes | `llama3-70b-8192` |
| `LLM_TEMPERATURE` | Optional | `0.7` |
| `LLM_MAX_TOKENS` | Optional | `1024` |
| `FILTER_TOP_N` | Optional | `10` |
| `OUTPUT_TOP_K` | Optional | `5` |
| `CORS_ORIGINS` | ✅ Yes (prod) | `https://dineai.vercel.app` |

### Vercel (Frontend)

No environment variables needed — the Railway URL is hardcoded in `app.js`.

> **TIP:** If you want to avoid hardcoding the URL, you can use a build step (e.g., a simple Node.js script) to inject it from a Vercel environment variable at deploy time.

---

## Phase 6 — Custom Domains (Optional)

### Railway Custom Domain
1. Railway Dashboard → your project → **Settings** → **Domains**
2. Add your domain (e.g. `api.dineai.com`)
3. Update your DNS with the CNAME provided by Railway
4. Update `CORS_ORIGINS` to include the new domain

### Vercel Custom Domain
1. Vercel Dashboard → your project → **Settings** → **Domains**
2. Add your domain (e.g. `dineai.com`)
3. Update your DNS with the records Vercel provides

After setting both custom domains, update `CORS_ORIGINS` to:
```
CORS_ORIGINS=https://dineai.com,https://dineai.vercel.app
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Railway build fails at `prefetch.py` | Dataset download timeout or missing network access | Re-trigger deploy; check Railway logs |
| `503 Service Unavailable` from `/health` | Dataset failed to load on startup | Check Railway **Runtime Logs** for exception details |
| CORS error in browser | `CORS_ORIGINS` not set or wrong URL | Set `CORS_ORIGINS=https://<your-vercel>.vercel.app` on Railway |
| Frontend shows no results | `API_ENDPOINT` still set to `/recommend` | Update `app.js` line 12 with the full Railway URL |
| Groq API errors | `GROQ_API_KEY` missing or invalid | Verify the key in Railway Variables; note the app falls back to local scoring |
| Vercel shows 404 on page refresh | Missing `vercel.json` rewrite rule | Add `frontend/vercel.json` as shown in Phase 3.2 |

---

## File Changes Required

| File | Action | Change |
|------|--------|--------|
| `frontend/app.js` | **Modify** line 12 | Replace `/recommend` with full Railway URL |
| `frontend/vercel.json` | **Create** | Add SPA rewrite rules for Vercel |

All other files (`Procfile`, `railway.json`, `requirements.txt`) are already correctly configured for Railway deployment. No backend code changes are needed.
