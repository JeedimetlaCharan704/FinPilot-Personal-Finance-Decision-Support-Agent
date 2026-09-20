# FinPilot

### Your bank app tells you what you spent. **FinPilot tells you what you can do.**

![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-4-38bdf8?logo=tailwindcss)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3fcf8e?logo=supabase)
![Python](https://img.shields.io/badge/Python-3.11-3776ab?logo=python)
![License](https://img.shields.io/badge/License-MIT-yellow)

> An agentic AI finance advisor that answers **"Can I afford this?"** — with deterministic verdicts, AI explanations, and a full reasoning chain you can inspect.

**Live Demo** · [fin-pilot-personal-finance-decision-support-agent.vercel.app](https://fin-pilot-personal-finance-decision-support-agent.vercel.app/)

---

## What is FinPilot?

FinPilot is a **multi-agent personal finance decision-support system**. Ask it a natural-language question like _"Can I afford a ₹65,000 laptop next month?"_ and it:

1. **Detects your intent** — purchase decision, subscription review, savings goal, or general query
2. **Runs deterministic financial tools** — computes projected income, committed outflows, discretionary spending, free cash
3. **Delivers a verdict** — `AFFORDABLE` / `TIGHT` / `NOT_YET` with a months-to-save timeline
4. **Shows comparison scenarios** — buy now vs. wait 3 months vs. save for 6 months
5. **Measures goal impact** — how this purchase delays or accelerates your emergency fund, vacation, or down payment
6. **Explains everything** — full agent trace showing every tool call, calculation, and reasoning step

**Zero hallucination on numbers.** All financial computations are deterministic Python. The LLM provides natural-language explanations grounded in real calculations.

---

## The Problem

Bank apps show you **past transactions**. Budgeting apps show you **category limits**. Neither answers the question every person actually asks:

> _"If I buy this thing, will I be okay?"_

FinPilot bridges that gap. It combines:
- Your real income and spending patterns
- Recurring commitments (rent, EMIs, subscriptions)
- Financial goals (emergency fund, vacation, down payment)
- A deterministic affordability engine

...into a single **yes / no / tight** verdict with a full audit trail.

---

## Architecture

### Agentic Decision Pipeline

```
User Question
     │
     ▼
┌─────────────────────────────┐
│   Intent Detection (LLM)    │  "Can I afford..." → PURCHASE_DECISION
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Tool Plan (LLM)           │  Decide which financial tools to call
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Deterministic Tools (Python)│
│  ├─ compute_income()        │
│  ├─ compute_outflows()      │
│  ├─ compute_free_cash()     │
│  ├─ evaluate_affordability()│
│  └─ project_goal_impact()   │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Verdict + Scenarios        │  AFFORDABLE / TIGHT / NOT_YET
│  + Goal Impact Analysis     │  + months_to_save timeline
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  AI Explanation (LLM)       │  Natural-language summary grounded in numbers
└─────────────┬───────────────┘
              │
              ▼
        Full Agent Trace      │  Every step visible to the user
```

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | Next.js 15 + TypeScript + Tailwind v4 + shadcn/ui | Modern React, type-safe, dark premium design |
| **Backend** | FastAPI + Python 3.11 | Async, fast, auto-docs at `/docs` |
| **Database** | Supabase (PostgreSQL) | Hosted Postgres, RLS, real-time ready |
| **LLM** | Pollinations AI (free tier) | No API key needed for demo; Grok/Ollama optional |
| **Agent** | Custom orchestrator | Intent → Tools → Verdict → Explanation pipeline |
| **Hosting** | Vercel (frontend) + Render (backend) | Free tier, instant deploys |

### Monorepo Structure

```
FinPilot/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py         # FastAPI app + CORS
│   │   │   ├── config.py       # Pydantic settings
│   │   │   ├── db.py           # Supabase client (thread-safe)
│   │   │   ├── schemas.py      # Pydantic request/response models
│   │   │   ├── routers/        # 7 route modules (18 endpoints)
│   │   │   ├── services/       # 10 service modules (agent, affordability, analytics, guardian...)
│   │   │   ├── repositories/   # Data access layer
│   │   │   └── llm/            # LLM provider abstraction
│   │   ├── tests/              # 197 tests (all passing)
│   │   ├── scripts/            # Demo data generator
│   │   └── requirements.txt
│   └── web/                    # Next.js 15 frontend
│       ├── app/                # App router pages
│       ├── components/         # 14 FinPilot UI components
│       ├── lib/                # API client, types, utilities
│       └── public/
├── data/
│   └── demo_data.csv           # Synthetic 6-month INR demo data (60 transactions)
├── supabase/
│   └── migrations/             # Schema + seed SQL
├── docs/                       # Documentation
├── .env.example                # Environment template
└── THIRD_PARTY_NOTICES.md
```

---

## Features

### Affordability Engine

Ask any purchase question and get a deterministic verdict:

| Verdict | Meaning | What you see |
|---------|---------|--------------|
| `AFFORDABLE` | Free cash covers the purchase with buffer | Green card, scenarios showing impact |
| `TIGHT` | Technically possible but reduces buffer significantly | Amber card, warning on goal delays |
| `NOT_YET` | Insufficient free cash; need to save first | Red card, months-to-save timeline |

### Subscription Guardian

Monitors recurring payments for price increases:
- Detects Netflix ₹499 → ₹649 price hike
- Shows monthly and annual impact
- Generates a review draft (never auto-cancels)
- Human-in-the-loop approve/reject workflow

### What-If Simulator

Run scenario analyses:
- _"What if I buy a ₹60,000 laptop?"_
- _"What if my rent increases by ₹2,000?"_
- _"What if I cancel Netflix?"_
- Custom amount + frequency combinations

### Goal Impact Tracker

Tracks progress toward financial goals:
- Emergency fund, vacation, down payment
- Shows how each purchase delays or accelerates goals
- Visual progress bars with monthly required savings

### Agent Trace (Transparency)

Every decision shows the full reasoning chain:
1. Intent detected → `PURCHASE_DECISION`
2. Tool plan built → `evaluate_affordability, project_goal_impact`
3. Tools executed → deterministic calculations
4. Response generated → AI explanation grounded in numbers

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account (free tier works)

### 1. Clone & Install

```bash
git clone https://github.com/JeedimetlaCharan704/FinPilot-Personal-Finance-Decision-Support-Agent.git
cd FinPilot

# Backend
cd apps/api
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Mac/Linux
pip install -r requirements.txt

# Frontend
cd ../web
npm install
```

### 2. Configure Environment

```bash
cd apps/api
copy .env.example .env          # Windows
# cp .env.example .env         # Mac/Linux
```

Edit `.env` with your Supabase credentials:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...    # Server-only!
LLM_PROVIDER=free                   # No API key needed
```

### 3. Set Up Database

Run the SQL migrations in your Supabase dashboard:

1. Go to SQL Editor in Supabase
2. Run `supabase/migrations/202609190001_create_schema.sql`
3. Run `supabase/migrations/202609190002_seed_demo.sql`

### 4. Run

```bash
# Backend (port 8100)
cd apps/api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100

# Frontend (port 3000)
cd apps/web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and ask: _"Can I afford a ₹65,000 laptop next month?"_

### 5. Run Tests

```bash
cd apps/api
python -m pytest tests/ -q        # 197 tests, all passing
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/db/health` | Database connectivity |
| `POST` | `/api/agent/analyze` | Main agent — intent, tools, verdict, explanation |
| `GET` | `/api/analytics/monthly` | Monthly income/spend/savings summary |
| `GET` | `/api/analytics/categories` | Spending by category |
| `GET` | `/api/analytics/recurring` | Recurring payment detection |
| `GET` | `/api/analytics/goals` | Financial goals with progress |
| `GET` | `/api/analytics/anomalies` | Spending anomalies |
| `POST` | `/api/simulations` | What-if scenario simulation |
| `GET` | `/api/guardian/detect` | Detect subscription price increases |
| `POST` | `/api/guardian/draft` | Create action draft for review |
| `GET` | `/api/guardian/summary` | Guardian summary stats |
| `GET` | `/api/actions` | List all action drafts |
| `POST` | `/api/actions/{id}/approve` | Approve an action draft |
| `POST` | `/api/actions/{id}/reject` | Reject an action draft |

Full interactive API docs at `http://localhost:8100/docs` (Swagger UI).

---

## Design System

FinPilot uses a **dark premium** design with semantic color tokens:

| Color | Meaning |
|-------|---------|
| Green (`#34d399`) | Positive / CTAs / Affordable / Approved |
| Amber (`#fbbf24`) | Warning / Tight / Subscription alerts |
| Rose (`#fb7185`) | Negative / Not-yet / Risk / Rejected |
| Violet (`#a78bfa`) | AI agent / Scenarios / Simulations |
| Sky (`#38bdf8`) | Neutral info / Traces / Activity |

Typography hierarchy: hero numbers dominate → decision numbers support → labels identify → body explains.

---

## Testing

**197 backend tests** covering:
- Intent detection and tool routing
- Affordability calculations (income, outflows, free cash, verdict)
- Subscription guardian (price increase detection, draft creation)
- What-if simulations
- Goal impact projections
- API endpoint integration
- Database operations
- Edge cases (zero income, negative balances, missing data)

```bash
cd apps/api
python -m pytest tests/ -v       # Verbose output
python -m pytest tests/ -q       # Quick summary
```

Frontend: clean build, 0 TypeScript errors, 141 kB first load.

---

## Security

- `.env` is gitignored — never committed
- `SUPABASE_SERVICE_ROLE_KEY` is server-side only (never `NEXT_PUBLIC_*`)
- Demo data is fully synthetic (no real financial data)
- CORS configured per-environment
- RLS policies on all database tables

---

## Author

**Charan** — Built for the Agentic AI Hackathon 2026

- GitHub: [@JeedimetlaCharan704](https://github.com/JeedimetlaCharan704)
- LinkedIn: [Charan Jeedimetla](https://www.linkedin.com/in/charan-jeedimetla/)

---

## License

MIT — Built with care for the Agentic AI Hackathon.
