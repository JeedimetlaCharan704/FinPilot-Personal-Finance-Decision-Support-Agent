# Database Design (Phase 3)

Storage-first foundation. No financial calculations or agent execution in this phase.

## Tables

| Table                  | Purpose (Phase 3) | Notes |
|------------------------|-------------------|-------|
| `users`                | Demo user identity | No passwords stored anywhere. |
| `categories`           | Fixed category taxonomy | `category_type` in income/essential/discretionary/savings/transfer |
| `transactions`         | Statement-style rows | `amount numeric(12,2) > 0`; `transaction_type` in income/expense |
| `recurring_payments`   | Subscriptions & EMIs | `frequency`, `status`, optional `detected_from_transaction_id` |
| `financial_goals`      | Goal baselines | `target_amount/current_amount`; no investing logic |
| `decision_simulations` | Purchase decision records (storage only) | No simulation engine yet |
| `agent_runs`           | Agent conversation records (storage only) | No agent wiring yet |
| `agent_tool_calls`     | Tool-call ledger (storage only) | |
| `action_drafts`        | Drafted actions (storage only) | **No autonomous execution** |

## Money

- Stored as `numeric(12,2)` — never float.
- Amounts are always positive; `transaction_type` carries income/expense semantics.

## RLS strategy (demo)

- RLS enabled on every user-owned table.
- Policies are **demo-only** placeholders (`auth.uid() = ...`) pending a real
  auth identity project; documented as such, NOT production auth.
- The FastAPI backend authenticates server-side with the service-role key
  (bypasses RLS by design, server-side only, never exposed to the browser).

## Migrations

- `202609190001_create_schema.sql` — schema + constraints + indexes + RLS.
- `202609190002_seed_demo.sql` — deterministic, idempotent seed:
  fixed UUIDs + `on conflict ... do nothing`, so re-running is safe.
- Ordering: users → categories → transactions-adjacent tables (FKs resolve top-down).

## Demo dataset

- `data/demo_data.csv` — 56 deterministic synthetic rows, 6 months, INR.
- One demo user `11111111-1111-1111-1111-111111111111`.
- Includes a subscription price increase (Netflix 499 → 649) and one anomalous
  large purchase (laptop) to support later detection demos.
- Regenerable via `apps/api/scripts/generate_demo_data.py` (seed 2026).