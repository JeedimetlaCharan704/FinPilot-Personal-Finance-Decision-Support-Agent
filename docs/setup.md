# Deployment Guide

## Frontend (Vercel)

### Automatic Deployment

Vercel auto-deploys on every push to `main`.

1. Connect your GitHub repo to Vercel
2. Set build command: `cd apps/web && npm run build`
3. Set output directory: `apps/web/.next`
4. Add environment variable:

```
NEXT_PUBLIC_API_BASE_URL=https://finpilot-personal-finance-decision.onrender.com
```

### Disable Deployment Protection

If visitors see "You Need Access":

1. Go to Vercel Dashboard → Your Project → **Settings**
2. Click **Deployment Protection**
3. Turn **OFF** "Vercel Authentication"
4. Save

---

## Backend (Render)

### Setup

1. Create a new **Web Service** on Render
2. Connect your GitHub repo
3. Configure:
   - **Build Command:** `cd apps/api && pip install -r requirements.txt`
   - **Start Command:** `cd apps/api && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Python Version:** 3.11

### Environment Variables

Add these in Render's Environment tab:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
LLM_PROVIDER=free
CORS_ORIGINS=https://fin-pilot-personal-finance-decision-support-agent.vercel.app
APP_ENV=production
```

### CORS Configuration

The backend must allow your frontend domain. Set `CORS_ORIGINS` to your Vercel URL.

---

## Database (Supabase)

### Setup

1. Create a free project on [supabase.com](https://supabase.com)
2. Go to **SQL Editor**
3. Run the migration files in order:
   - `supabase/migrations/202609190001_create_schema.sql`
   - `supabase/migrations/202609190002_seed_demo.sql`
4. Copy your project URL and keys to the environment variables

### Connection pooling

Supabase provides a connection pooler URL (port 6543) for serverless environments. Use the direct URL (port 5432) for local development.

---

## Local Development

```bash
# Terminal 1: Backend
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload

# Terminal 2: Frontend
cd apps/web
npm install
npm run dev
```

Frontend: http://localhost:3000
Backend API docs: http://localhost:8100/docs

---

## Production Checklist

- [ ] `.env` is not committed (gitignored)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is server-side only (never `NEXT_PUBLIC_*`)
- [ ] CORS configured for production domain only
- [ ] Deployment Protection disabled on Vercel
- [ ] Backend health check returns 200
- [ ] All 197 tests passing
- [ ] Frontend build clean (0 errors)
- [ ] Demo data seeded in Supabase
