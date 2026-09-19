-- FinPilot demo seed — deterministic and idempotent.
-- Safe to run repeatedly (uses fixed UUIDs + on conflict do nothing).
-- One demo user, fixed categories, fixed recurring baselines, two goals.

-- Demo user (fixed UUID so seed is idempotent and deterministic)
insert into public.users (id, email, display_name, currency)
values ('11111111-1111-1111-1111-111111111111', 'demo@finpilot.in', 'Demo User', 'INR')
on conflict (id) do nothing;

-- Categories (fixed UUIDs)
insert into public.categories (id, name, category_type) values
  ('aaaaaaaa-0000-0000-0000-000000000001', 'salary',        'income'),
  ('aaaaaaaa-0000-0000-0000-000000000002', 'rent',          'essential'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'emi',           'essential'),
  ('aaaaaaaa-0000-0000-0000-000000000004', 'utilities',     'essential'),
  ('aaaaaaaa-0000-0000-0000-000000000005', 'groceries',     'essential'),
  ('aaaaaaaa-0000-0000-0000-000000000006', 'transport',     'essential'),
  ('aaaaaaaa-0000-0000-0000-000000000007', 'food',          'discretionary'),
  ('aaaaaaaa-0000-0000-0000-000000000008', 'entertainment', 'discretionary'),
  ('aaaaaaaa-0000-0000-0000-000000000009', 'shopping',      'discretionary'),
  ('aaaaaaaa-0000-0000-0000-000000000010', 'subscriptions', 'discretionary'),
  ('aaaaaaaa-0000-0000-0000-000000000011', 'electronics',   'discretionary')
on conflict (id) do nothing;

-- Recurring baseline (fixed UUIDs; idempotent)
insert into public.recurring_payments
  (id, user_id, merchant, description, amount, frequency, next_payment_date, category_id, status) values
  ('bbbbbbbb-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Landlord', 'House rent', 15000, 'monthly', '2026-07-03', 'aaaaaaaa-0000-0000-0000-000000000002', 'active'),
  ('bbbbbbbb-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'HDFC Bank', 'Car EMI', 12500, 'monthly', '2026-07-05', 'aaaaaaaa-0000-0000-0000-000000000003', 'active'),
  ('bbbbbbbb-0000-0000-0000-000000000003', '11111111-1111-1111-1111-111111111111', 'BESCOM', 'Electricity', 2500, 'monthly', '2026-07-07', 'aaaaaaaa-0000-0000-0000-000000000004', 'active'),
  ('bbbbbbbb-0000-0000-0000-000000000004', '11111111-1111-1111-1111-111111111111', 'Netflix', 'Streaming subscription', 649, 'monthly', '2026-07-10', 'aaaaaaaa-0000-0000-0000-000000000010', 'active')
on conflict (id) do nothing;

-- Financial goals (seed baseline; idempotent)
insert into public.financial_goals
  (id, user_id, name, target_amount, current_amount, target_date, priority, status) values
  ('cccccccc-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Emergency fund', 200000, 75000, '2027-03-31', 1, 'in_progress'),
  ('cccccccc-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'New laptop', 60000, 0, '2026-12-31', 3, 'in_progress')
on conflict (id) do nothing;