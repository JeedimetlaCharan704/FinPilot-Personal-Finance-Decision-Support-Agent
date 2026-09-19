# FinPilot — Personal Finance Decision-Support Agent

> Your bank app tells you what you spent. **FinPilot tells you what you can do.**

Monorepo for the Agentic AI Hackathon build.

## Repository layout

```
├── apps/
│   ├── api/      FastAPI backend (health, DB layer, demo-data generation)
│   └── web/      Next.js 15 + TypeScript + Tailwind + shadcn/ui frontend
├── data/
│   └── demo_data.csv   Synthetic 6-month INR demo transactions
├── supabase/
│   └── migrations/     Schema + deterministic seed (idempotent)
├── docs/
│   └── database.md     Schema/RLS notes
├── .env.example        Environment template (placeholders only)
└── THIRD_PARTY_NOTICES.md
```

## Status

- **Phase 2** (base scaffold): complete — backend `GET /api/health`, frontend dashboard shell.
- **Phase 3** (data foundation): complete — schema, migrations, seed, demo dataset, DB health endpoint, tests.
- **Phase 4** (agent + decision simulator): **NOT started** — no LangGraph, no financial calculations, no Grok wiring.

## Backend (FastAPI)

```bash
python -m venv .venv
.venv\Scripts\activate            # or source .venv/bin/activate on *nix
pip install -r apps/api/requirements.txt

# run
cd apps/api
python -m uvicorn app.main:app --reload --port 8000

# tests (no Supabase needed; integration tests auto-skip)
cd apps/api
python -m pytest
```

Endpoints

| Route               | Purpose |
|---------------------|---------|
| `GET /api/health`   | `{"status":"ok","service":"finpilot-api"}` |
| `GET /api/db/health`| DB connectivity (503 + non-secret message when not configured) |

### Generate demo data

```bash
cd apps/api
set PYTHONPATH=%CD%
python scripts/generate_demo_data.py   # deterministic; rewrites data/demo_data.csv
```

## Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
```

Health badge reads `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000`).

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

## Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Architecture audit | ✅ |
| 2 | Project base scaffold | ✅ |
| 3 | Database + data foundation | ✅ |
| 4 | Decision simulator + agent | ⏳ NOT started |