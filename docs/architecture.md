# Architecture

## Overview

FinPilot is a **multi-agent personal finance decision-support system** with a clean separation between deterministic financial computation and LLM-powered natural language understanding.

### Core Principle: Zero Hallucination on Numbers

All financial calculations (income, outflows, free cash, affordability verdicts, goal projections) are performed by **deterministic Python functions**. The LLM is used only for:
- Intent detection (classifying the user's question)
- Tool planning (deciding which financial tools to call)
- Natural language explanation (summarizing results in plain English)

This means FinPilot's financial verdicts are **auditable, reproducible, and hallucination-free**.

---

## Agent Pipeline

```
User: "Can I afford a ₹65,000 laptop next month?"
                    │
                    ▼
    ┌───────────────────────────────┐
    │     1. INTENT DETECTION       │
    │     (LLM classification)      │
    │     → PURCHASE_DECISION       │
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │     2. TOOL PLAN              │
    │     (LLM decides which tools) │
    │     → [evaluate_affordability,│
    │        project_goal_impact]   │
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │     3. DETERMINISTIC TOOLS    │
    │     (Pure Python, no LLM)     │
    │                               │
    │     compute_income()          │
    │     compute_outflows()        │
    │     compute_free_cash()       │
    │     evaluate_affordability()  │
    │     project_goal_impact()     │
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │     4. VERDICT                │
    │     AFFORDABLE / TIGHT /      │
    │     NOT_YET + months_to_save  │
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │     5. AI EXPLANATION         │
    │     (LLM grounded in numbers) │
    │     "You have ₹42,000 free    │
    │      cash. This laptop uses   │
    │      56% of your buffer..."   │
    └───────────────┬───────────────┘
                    │
                    ▼
              Full Agent Trace
         (every step is visible)
```

---

## Service Modules

| Module | Purpose |
|--------|---------|
| `intents.py` | Classifies user questions into intent categories |
| `orchestrator.py` | Routes intents to appropriate tool chains |
| `tools.py` | Tool registry and execution framework |
| `affordability.py` | Core affordability engine (income, outflows, verdict) |
| `analytics.py` | Monthly summaries, category breakdowns |
| `goals.py` | Financial goal tracking and progress |
| `guardian.py` | Subscription price-increase detection |
| `simulations.py` | What-if scenario simulation |
| `anomalies.py` | Spending anomaly detection |
| `demo_data.py` | Synthetic data generation |

---

## Database Schema (Supabase)

9 tables in PostgreSQL:

| Table | Purpose |
|-------|---------|
| `users` | Demo user identity (no passwords) |
| `categories` | Fixed category taxonomy (income/essential/discretionary/savings/transfer) |
| `transactions` | Statement-style rows with amount, category, date |
| `recurring_payments` | Subscriptions and EMIs with frequency tracking |
| `financial_goals` | Goal targets with progress tracking |
| `decision_simulations` | What-if scenario records |
| `agent_runs` | Agent conversation records |
| `agent_tool_calls` | Tool-call ledger for audit trail |
| `action_drafts` | Human-in-the-loop action drafts |

### Key Design Decisions

- **All amounts in INR** (`numeric(12,2)`) — no currency conversion
- **Deterministic seed data** — fixed UUIDs, `ON CONFLICT DO NOTHING`
- **RLS enabled** — row-level security on all tables
- **No real financial data** — everything is synthetic demo data

---

## Frontend Architecture

### Component Hierarchy

```
page.tsx (main orchestrator)
├── fp-header.tsx          (sticky brand bar)
├── fp-hero.tsx            (hero question input)
├── fp-decision-verdict.tsx (main verdict card)
├── fp-agent-trace.tsx     (collapsible reasoning chain)
├── fp-subscription-guardian.tsx (price increase cards)
├── fp-action-drafts.tsx   (grouped action drafts)
├── fp-what-if-lab.tsx     (scenario simulator)
├── fp-secondary-rail.tsx  (analytics sidebar)
│   ├── fp-stat-tile.tsx   (reusable metric block)
│   └── fp-spending-bars.tsx (horizontal bar chart)
├── fp-agent-activity.tsx  (decision history)
├── fp-agent-message-inline.tsx (inline agent replies)
├── fp-degraded-banner.tsx (error state)
└── fp-loading-sequence.tsx (loading pipeline)
```

### Design Tokens

Semantic color system in `globals.css`:

```css
/* Each color means something specific */
--color-fp-green:  #34d399;  /* positive / affordable / approved */
--color-fp-amber:  #fbbf24;  /* warning / tight / subscription */
--color-fp-rose:   #fb7185;  /* negative / not-yet / rejected */
--color-fp-violet: #a78bfa;  /* AI / scenarios / simulations */
--color-fp-sky:    #38bdf8;  /* info / traces / activity */
```

No more than two accent colors visible in any single card.

---

## LLM Integration

### Provider Abstraction

FinPilot supports multiple LLM providers through a clean abstraction:

| Provider | Use Case | API Key |
|----------|----------|---------|
| Pollinations (free) | Demo / hackathon | None needed |
| Grok (xAI) | Production quality | `XAI_API_KEY` |
| Ollama (local) | Offline development | None |

### LLM Usage Points

1. **Intent Detection** — classify user question into `PURCHASE_DECISION`, `SUBSCRIPTION_REVIEW`, `GOAL_QUERY`, `GENERAL`
2. **Tool Planning** — decide which financial tools to invoke
3. **Explanation Generation** — natural-language summary grounded in deterministic numbers

The LLM **never** touches financial calculations.

---

## Deployment

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Vercel | [fin-pilot-personal-finance-decision-support-agent.vercel.app](https://fin-pilot-personal-finance-decision-support-agent.vercel.app/) |
| Backend | Render | [finpilot-personal-finance-decision.onrender.com](https://finpilot-personal-finance-decision.onrender.com) |
| Database | Supabase | Your project URL |

### Environment Variables

| Variable | Scope | Required |
|----------|-------|----------|
| `SUPABASE_URL` | Server | Yes |
| `SUPABASE_ANON_KEY` | Server | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Server only | Yes |
| `LLM_PROVIDER` | Server | No (defaults to `free`) |
| `XAI_API_KEY` | Server | Only if using Grok |
| `NEXT_PUBLIC_API_BASE_URL` | Client + Server | Yes (frontend) |
