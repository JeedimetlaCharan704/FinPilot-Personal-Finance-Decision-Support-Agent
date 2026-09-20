# FinPilot — Personal Finance Decision-Support Agent

> Your bank app tells you what you spent. **FinPilot tells you what you can do.**

Monorepo for the Agentic AI Hackathon build.

## Repository layout

```
├── apps/
│   ├── api/      FastAPI backend (agent, decisions, analytics, guardian, simulations)
│   └── web/      Next.js 15 + TypeScript + Tailwind + shadcn/ui frontend
├── data/
│   └── demo_data.csv   Synthetic 6-month INR demo transactions (60 rows, deterministic)
├── supabase/
│   └── migrations/     Schema + deterministic seed (idempotent)
├── docs/
│   └── database.md     Schema/RLS notes
├── .env.example        Environment template (placeholders only)
└── THIRD_PARTY_NOTICES.md
```

## What FinPilot does

FinPilot is a conversational finance agent that answers: **"Can I afford this?"**

- **Affordability engine** — Given a question like "Can I afford a ₹65,000 laptop next month?", FinPilot computes projected income, committed outflows, discretionary spending, free cash, and a verdict (YES / NOT_YET / NO) with a months-to-save timeline.
- **Subscription Guardian** — Monitors recurring payments and detects price increases (e.g. Netflix ₹499 → ₹649). Produces explainable analysis with percentage, annual impact, and a human-in-the-loop action draft.
- **Decision simulator** — What-if scenario engine with goal impact projections.
- **Agent trace** — Every decision shows the full reasoning chain: intent → tools → calculations → verdict.

## Quick start

### Backend (FastAPI)

```bash
cd apps/api
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# run (free LLM provider by default)
set LLM_PROVIDER=free
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100

# tests (197 total, no external services needed)
python -m pytest tests/ -q
```

### Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
```

Frontend connects to `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8100`).

### Generate demo data

```bash
cd apps/api
set PYTHONPATH=%CD%
python scripts/generate_demo_data.py   # deterministic; rewrites data/demo_data.csv
```

## API endpoints

| Route | Purpose |
|-------|---------|
| `GET /api/health` | Service health check |
| `GET /api/db/health` | DB connectivity (503 when not configured) |
| `POST /api/agent/analyze` | Main agent — intent detection, tool routing, affordability decisions |
| `GET /api/analytics/monthly` | Monthly income/spend/savings |
| `GET /api/analytics/categories` | Category breakdown |
| `GET /api/analytics/recurring` | Recurring/subscription detection |
| `GET /api/analytics/goals` | Financial goals progress |
| `GET /api/analytics/anomalies` | Spending anomalies |
| `POST /api/simulations` | What-if scenario simulation |
| `GET /api/guardian/detect` | Detect subscription price increases |
| `POST /api/guardian/draft` | Create action draft for a price increase |
| `GET /api/guardian/summary` | Guardian summary stats |
| `GET /api/actions` | List all action drafts |
| `POST /api/actions/{id}/approve` | Approve an action draft |
| `POST /api/actions/{id}/reject` | Reject an action draft |

## Database (Supabase)

Migrations under `supabase/migrations/` (in order):

1. `202609190001_create_schema.sql` — 9 tables, constraints, indexes, RLS.
2. `202609190002_seed_demo.sql` — deterministic, idempotent seed (fixed UUIDs, `on conflict do nothing`).

See `docs/database.md` for the schema map and RLS strategy.

## Security checklist

- Never commit `.env`; all secrets live in uncommitted `.env` only.
- `SUPABASE_SERVICE_ROLE_KEY` and `XAI_API_KEY` are **server-only**.
- Never place service-role keys in `NEXT_PUBLIC_*`.
- Demo data is fully synthetic; contains no real personal financial data.
- All 197 backend tests pass. Frontend builds clean (0 errors).

## Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Architecture audit | ✅ |
| 2 | Project base scaffold | ✅ |
| 3 | Database + data foundation | ✅ |
| 4 | Agent + decision simulator | ✅ |
| 5 | Subscription guardian | ✅ |
| 6 | Hero "Can I afford this?" + Phase 6 determinism | ✅ |
| 7 | Subscription guardian (price-increase detection, action drafts, approve/reject) | ✅ |
| 8 | Demo readiness, UX polish & reliability audit | ✅ |
