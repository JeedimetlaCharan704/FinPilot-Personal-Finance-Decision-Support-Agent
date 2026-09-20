# API Reference

Base URL: `https://finpilot-personal-finance-decision.onrender.com`

For local development: `http://127.0.0.1:8100`

Interactive docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Health & Database

### `GET /api/health`

Service health check. Returns uptime, version, and LLM provider status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "llm_provider": "free",
  "uptime_seconds": 3600
}
```

### `GET /api/db/health`

Database connectivity check. Returns 503 when Supabase is not configured.

---

## Agent (Main Entry Point)

### `POST /api/agent/analyze`

The main agent endpoint. Sends a natural-language question and receives a full decision with verdict, scenarios, and explanation.

**Request:**
```json
{
  "question": "Can I afford a ₹65,000 laptop next month?",
  "user_id": "demo-user"
}
```

**Response:**
```json
{
  "intent": "PURCHASE_DECISION",
  "mode": "llm",
  "model": "pollinations",
  "answer": "You can afford this, but it will use 56% of your monthly free cash...",
  "decision": {
    "verdict": "TIGHT",
    "purchase_amount": 65000,
    "free_cash": 42000,
    "cash_after_purchase": -23000,
    "committed_outflows": 58000,
    "months_to_save": 2,
    "scenarios": [...],
    "goal_impacts": [...],
    "assumptions": [...]
  },
  "evidence": [
    {"label": "Monthly income", "value": "₹1,20,000"},
    {"label": "Free cash", "value": "₹42,000"}
  ],
  "activity": [
    {"step": "Intent detected", "tool": "PURCHASE_DECISION", "latency_ms": 120},
    {"step": "Tool executed", "tool": "evaluate_affordability", "latency_ms": 45}
  ]
}
```

---

## Analytics

### `GET /api/analytics/monthly`

Monthly income, expenses, savings rate, and AI-generated insights.

**Query Parameters:**
- `user_id` (optional, defaults to `demo-user`)

**Response:**
```json
{
  "income": 120000,
  "expenses": 78000,
  "savings": 42000,
  "savings_rate": 0.35,
  "net": 42000,
  "transactions_analyzed": 60,
  "period_label": "Sep 2026",
  "insights": [
    "Your spending on Food & Dining increased 18% this month",
    "You saved ₹8,000 more than last month"
  ]
}
```

### `GET /api/analytics/categories`

Spending breakdown by category.

**Response:**
```json
{
  "categories": [
    {"category": "Rent", "amount": 25000, "transaction_count": 1},
    {"category": "Food & Dining", "amount": 12000, "transaction_count": 18},
    {"category": "Transport", "amount": 4500, "transaction_count": 12}
  ]
}
```

### `GET /api/analytics/recurring`

Detected recurring payments and subscriptions.

**Response:**
```json
{
  "monthly_committed": 58000,
  "annualized_recurring_cost": 696000,
  "payments": [
    {
      "id": "...",
      "merchant": "Netflix",
      "amount": 649,
      "frequency": "monthly",
      "status": "active",
      "category": "Entertainment"
    }
  ]
}
```

### `GET /api/analytics/goals`

Financial goals with progress tracking.

**Response:**
```json
{
  "goals": [
    {
      "id": "...",
      "name": "Emergency Fund",
      "target_amount": 300000,
      "current_amount": 180000,
      "progress_pct": 60.0,
      "required_monthly": 15000
    }
  ]
}
```

### `GET /api/analytics/anomalies`

Spending anomalies (unusual transactions).

---

## Simulations

### `POST /api/simulations`

Run a what-if scenario simulation.

**Request:**
```json
{
  "scenario_type": "purchase",
  "name": "Laptop Purchase",
  "amount": 60000,
  "frequency": "one_time",
  "duration_months": 1,
  "reference_id": ""
}
```

**Response:**
```json
{
  "baseline": {
    "monthly_savings": 42000,
    "total_savings": 252000
  },
  "scenario": {
    "label": "Laptop Purchase",
    "monthly_savings": -18000,
    "total_savings": 192000
  },
  "difference": {
    "monthly_savings_delta": -60000,
    "total_cumulative": -60000,
    "duration_months": 1
  },
  "goal_impact": {
    "goal": "Emergency Fund",
    "delay_months": 4
  },
  "explanation": "This purchase reduces your monthly savings from ₹42,000 to -₹18,000...",
  "assumptions": ["Income remains constant", "No new expenses added"]
}
```

---

## Subscription Guardian

### `GET /api/guardian/detect`

Detect subscription price increases.

**Response:**
```json
{
  "items": [
    {
      "merchant": "Netflix",
      "category": "Entertainment",
      "frequency": "monthly",
      "previous_amount": 499,
      "current_amount": 649,
      "increase_amount": 150,
      "increase_percent": 30.1,
      "annual_increase": 1800,
      "annual_cost": 7788,
      "signal": "PRICE_INCREASE",
      "evidence_refs": ["transaction_2026_09_15", "recurring_payment.netflix"]
    }
  ]
}
```

### `POST /api/guardian/draft`

Create an action draft for a detected price increase.

**Request:**
```json
{
  "merchant": "Netflix",
  "action_type": "review_subscription"
}
```

### `GET /api/guardian/summary`

Summary stats for the guardian.

---

## Action Drafts

### `GET /api/actions`

List all action drafts with their current status.

### `POST /api/actions/{id}/approve`

Approve a draft action. Changes status from `draft` to `approved`.

### `POST /api/actions/{id}/reject`

Reject a draft action. Changes status from `draft` to `rejected`.

---

## Error Responses

All endpoints return standard HTTP status codes:

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Bad request (missing/invalid parameters) |
| `404` | Resource not found |
| `422` | Validation error |
| `500` | Internal server error |
| `503` | Service unavailable (DB not configured) |

Error response format:
```json
{
  "detail": "Human-readable error message"
}
```
