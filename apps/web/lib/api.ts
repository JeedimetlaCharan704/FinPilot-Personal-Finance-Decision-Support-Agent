// FinPilot frontend API client. Server-side secrets never reach the browser;
// the FastAPI backend talks to Supabase with the service-role key.

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

// Deterministic demo user seeded by the Phase 3 migration (public uuid).
export const DEMO_USER_ID = "11111111-1111-1111-1111-111111111111";

export const inr = (v: number | undefined | null): string => {
  const n = Number(v ?? 0);
  return "₹" + new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(n);
};

export const pct = (v: number | undefined | null, digits = 1): string =>
  `${Number(v ?? 0).toFixed(digits)}%`;

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text();
    let detail = text;
    try { detail = JSON.parse(text).detail ?? text; } catch { /* keep text */ }
    throw new Error(`${r.status}: ${detail}`);
  }
  return r.json() as Promise<T>;
}

export interface CategoryRow { category: string; amount: number; transaction_count: number; }

export interface MonthlyAnalytics {
  has_data: boolean;
  year: number; month: number;
  period_label: string;
  income: number; expenses: number; net: number;
  savings_rate: number; committed: number;
  category_breakdown: CategoryRow[];
  largest_expenses: { merchant: string; amount: number; date: string }[];
  month_over_month: Record<string, { current: number; previous: number; diff: number; percentage: number | null }>;
  insights: string[];
  transactions_analyzed: number;
}

export interface RecurringAnalysis {
  monthly_committed: number;
  annualized_recurring_cost: number;
  payment_count: number;
  payments: { id: string; merchant: string; amount: number; frequency: string;
              next_payment_date: string | null; days_until_next: number | null;
              monthly_commitment: number; annualized: number }[];
}

export interface Goal {
  id: string; name: string; target_amount: number; current_amount: number;
  remaining: number; progress_pct: number; target_date: string | null;
  required_monthly: number | null; months_to_target: number | null; priority: number;
}

export interface Upcoming { upcoming: { merchant: string; amount: number; frequency: string;
                             monthly_commitment: number; next_payment_date: string; days_until: number }[];
                           days_horizon: number; count: number; }

export interface BudgetStatus {
  has_data: boolean; year: number; month: number;
  income: number; committed: number; spent: number;
  available: number; discretionary: number; monthly_savings: number;
  assumptions: string[];
}

export interface EvidenceItem { label: string; value: string; detail: string; }
export interface CalculationItem { formula: string; value: string; detail: string; }
export interface ActivityStep { step: string; tool: string; latency_ms: number; status: string; detail: string; }
export interface RecommendedAction { id: string; action_type: string; title: string; description: string; }

export interface AgentAnswer {
  run_id: string; intent: string; answer: string; latency_ms: number;
  insights: string[];
  evidence: EvidenceItem[];
  calculations: CalculationItem[];
  assumptions: string[];
  recommended_actions: RecommendedAction[];
  activity: ActivityStep[];
  mode: "llm" | "deterministic";
  model: string;
  warnings: string[];
}

export interface SimulationSnapshot {
  label: string; monthly_income: number; monthly_expenses: number;
  monthly_savings: number; savings_rate: number; committed: number;
}

export interface SimulationResult {
  simulation_id: string; scenario_type: string;
  baseline: SimulationSnapshot;
  scenario: SimulationSnapshot;
  difference: Record<string, number>;
  goal_impact: {
    goal: string | null; goal_id: string | null; remaining: number; progress_pct: number;
    months_baseline: number | null; months_scenario: number | null;
    delay_months: number | null; impact: string | null;
  };
  explanation: string;
  assumptions: string[];
}

export interface ActionDraft {
  id: string; action_type: string; title: string; description: string;
  status: "draft" | "approved" | "rejected" | "executed";
  created_at: string; approved_at: string | null; payload_json: unknown;
}

export interface AgentRun { id: string; question: string; status: string; started_at: string | null;
                            completed_at: string | null; final_response: string | null; created_at: string; }

export interface RunDetail { run: AgentRun; tool_calls: { id: string; tool_name: string; status: string;
                            started_at: string | null; completed_at: string | null; output_json: unknown }[]; }

export const fetchMonthly = (uid = DEMO_USER_ID) =>
  get<MonthlyAnalytics>(`/api/analytics/monthly?user_id=${uid}`);
export const fetchRecurring = (uid = DEMO_USER_ID) =>
  get<RecurringAnalysis>(`/api/analytics/recurring?user_id=${uid}`);
export const fetchGoals = (uid = DEMO_USER_ID) =>
  get<{ goals: Goal[] }>(`/api/analytics/goals?user_id=${uid}`);
export const fetchUpcoming = async (uid = DEMO_USER_ID): Promise<Upcoming> => {
  const r = await get<RecurringAnalysis>(`/api/analytics/recurring?user_id=${uid}`);
  const list = r.payments
    .filter((p) => p.days_until_next !== null && p.days_until_next >= 0 && p.days_until_next <= 30)
    .map((p) => ({ merchant: p.merchant, amount: p.amount, frequency: p.frequency,
                   monthly_commitment: p.monthly_commitment,
                   next_payment_date: p.next_payment_date ?? "", days_until: p.days_until_next ?? 0 }));
  return { upcoming: list, days_horizon: 30, count: list.length };
};
export const fetchBudget = (uid = DEMO_USER_ID) =>
  get<BudgetStatus>(`/api/analytics/budget?user_id=${uid}`);
export const fetchActions = (uid = DEMO_USER_ID) =>
  get<{ actions: ActionDraft[] }>(`/api/actions?user_id=${uid}`);
export const fetchRuns = (uid = DEMO_USER_ID) =>
  get<{ runs: AgentRun[] }>(`/api/agent/runs?user_id=${uid}`);
export const fetchRunDetail = (runId: string) =>
  get<RunDetail>(`/api/agent/runs/${runId}`);

export const askAgent = (question: string, uid = DEMO_USER_ID) =>
  post<AgentAnswer>(`/api/agent/analyze`, { user_id: uid, question });
export const runSimulation = (payload: {
  scenario_type: string; name: string; amount: number;
  frequency: "one_time" | "monthly"; duration_months: number; reference_id?: string;
}, uid = DEMO_USER_ID) =>
  post<SimulationResult>(`/api/simulations`, { user_id: uid, ...payload });
export const approveAction = (id: string) =>
  post<{ status: string }>(`/api/actions/${id}/approve`, {});
export const rejectAction = (id: string) =>
  post<{ status: string }>(`/api/actions/${id}/reject`, {});