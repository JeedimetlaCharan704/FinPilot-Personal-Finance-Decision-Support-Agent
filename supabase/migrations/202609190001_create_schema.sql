-- FinPilot Phase 3 schema (storage foundation only).
-- Design decisions:
--   * Money is NUMERIC(12,2) — never float.
--   * transaction.amount is always positive; type distinguishes income/expense.
--   * All user-owned tables enable RLS. Demo strategy documented in docs/database.md.
--   * No destructive DROP statements. Deterministic, order-safe for re-runs.
--   * No financial calculations anywhere in Phase 3.

-- ---------------------------------------------------------------------------
-- 1. users
-- ---------------------------------------------------------------------------
create table if not exists public.users (
  id          uuid primary key,
  email       text unique not null,
  display_name text not null,
  currency    text not null default 'INR' check (currency = 'INR'),
  created_at  timestamptz not null default now()
);

alter table public.users enable row level security;

-- ---------------------------------------------------------------------------
-- 2. categories
-- ---------------------------------------------------------------------------
create table if not exists public.categories (
  id            uuid primary key,
  name          text unique not null,
  category_type text not null check (category_type in ('income','essential','discretionary','savings','transfer')),
  created_at    timestamptz not null default now()
);

alter table public.categories enable row level security;

-- ---------------------------------------------------------------------------
-- 3. transactions
-- ---------------------------------------------------------------------------
create table if not exists public.transactions (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references public.users(id) on delete cascade,
  category_id      uuid not null references public.categories(id),
  transaction_date date not null,
  amount           numeric(12,2) not null check (amount > 0),
  transaction_type text not null check (transaction_type in ('income','expense')),
  description      text,
  merchant         text,
  is_recurring     boolean not null default false,
  created_at       timestamptz not null default now()
);

create index if not exists idx_transactions_user_date
  on public.transactions (user_id, transaction_date desc);
create index if not exists idx_transactions_category
  on public.transactions (category_id);
create index if not exists idx_transactions_type
  on public.transactions (transaction_type);

alter table public.transactions enable row level security;

-- ---------------------------------------------------------------------------
-- 4. recurring_payments
-- ---------------------------------------------------------------------------
create table if not exists public.recurring_payments (
  id                        uuid primary key default gen_random_uuid(),
  user_id                   uuid not null references public.users(id) on delete cascade,
  merchant                  text not null,
  description               text,
  amount                    numeric(12,2) not null check (amount > 0),
  frequency                 text not null check (frequency in ('weekly','monthly','quarterly','yearly')),
  next_payment_date         date not null,
  category_id               uuid references public.categories(id),
  status                    text not null default 'active' check (status in ('active','paused','cancelled')),
  detected_from_transaction_id uuid references public.transactions(id) on delete set null,
  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now()
);

create index if not exists idx_recurring_user_next
  on public.recurring_payments (user_id, next_payment_date);

alter table public.recurring_payments enable row level security;

-- ---------------------------------------------------------------------------
-- 5. financial_goals
-- ---------------------------------------------------------------------------
create table if not exists public.financial_goals (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.users(id) on delete cascade,
  name           text not null,
  target_amount  numeric(12,2) not null check (target_amount > 0),
  current_amount numeric(12,2) not null default 0 check (current_amount >= 0),
  target_date    date,
  priority       int not null default 3 check (priority between 1 and 5),
  status         text not null default 'in_progress' check (status in ('in_progress','achieved','abandoned')),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index if not exists idx_goals_user on public.financial_goals (user_id);

alter table public.financial_goals enable row level security;

-- ---------------------------------------------------------------------------
-- 6. decision_simulations (storage only in Phase 3 — no engine)
-- ---------------------------------------------------------------------------
create table if not exists public.decision_simulations (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references public.users(id) on delete cascade,
  purchase_name        text not null,
  purchase_amount      numeric(12,2) not null check (purchase_amount > 0),
  purchase_date        date not null,
  verdict              text,
  projected_free_cash  numeric(12,2),
  goal_impact_json     jsonb,
  scenarios_json       jsonb,
  created_at           timestamptz not null default now()
);

create index if not exists idx_simulations_user on public.decision_simulations (user_id, created_at desc);

alter table public.decision_simulations enable row level security;

-- ---------------------------------------------------------------------------
-- 7. agent_runs (storage only in Phase 3 — no agent wiring)
-- ---------------------------------------------------------------------------
create table if not exists public.agent_runs (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.users(id) on delete cascade,
  question       text not null,
  status         text not null default 'pending' check (status in ('pending','running','completed','failed','cancelled')),
  started_at     timestamptz,
  completed_at   timestamptz,
  final_response text,
  created_at     timestamptz not null default now()
);

create index if not exists idx_agent_runs_user on public.agent_runs (user_id, created_at desc);

alter table public.agent_runs enable row level security;

-- ---------------------------------------------------------------------------
-- 8. agent_tool_calls (storage only in Phase 3)
-- ---------------------------------------------------------------------------
create table if not exists public.agent_tool_calls (
  id           uuid primary key default gen_random_uuid(),
  agent_run_id uuid not null references public.agent_runs(id) on delete cascade,
  tool_name    text not null,
  input_json   jsonb not null,
  output_json  jsonb,
  status       text not null default 'started' check (status in ('started','completed','failed')),
  started_at   timestamptz,
  completed_at timestamptz
);

create index if not exists idx_agent_tool_calls_run on public.agent_tool_calls (agent_run_id);

alter table public.agent_tool_calls enable row level security;

-- ---------------------------------------------------------------------------
-- 9. action_drafts (storage only in Phase 3 — NO autonomous execution)
-- ---------------------------------------------------------------------------
create table if not exists public.action_drafts (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.users(id) on delete cascade,
  action_type  text not null,
  title        text not null,
  description  text,
  payload_json jsonb,
  status       text not null default 'draft' check (status in ('draft','approved','rejected','executed')),
  approved_at  timestamptz,
  executed_at  timestamptz,
  created_at   timestamptz not null default now()
);

create index if not exists idx_action_drafts_user on public.action_drafts (user_id, status, created_at desc);

alter table public.action_drafts enable row level security;

-- ---------------------------------------------------------------------------
-- RLS policies — demo-only strategy (documented; NOT production auth).
-- No real authentication exists yet. The FastAPI backend authenticates with a
-- server-side service-role key (bypasses RLS server-side by design).
-- The app_iden placeholder below is replaced by real multi-tenant auth later.
-- ---------------------------------------------------------------------------
create policy "demo user: own users row" on public.users
  for select using (auth.uid() = id);
create policy "demo: categories readable" on public.categories
  for select using (true);
create policy "demo user: own transactions" on public.transactions
  for select using (auth.uid() = user_id);
create policy "demo user: own recurring_payments" on public.recurring_payments
  for select using (auth.uid() = user_id);
create policy "demo user: own financial_goals" on public.financial_goals
  for select using (auth.uid() = user_id);
create policy "demo user: own decision_simulations" on public.decision_simulations
  for select using (auth.uid() = user_id);
create policy "demo user: own agent_runs" on public.agent_runs
  for select using (auth.uid() = user_id);
create policy "demo user: own action_drafts" on public.action_drafts
  for select using (auth.uid() = user_id);