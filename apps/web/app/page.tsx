"use client"

import { useCallback, useEffect, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowUpRight, BadgeCheck, BrainCircuit, Bot,
  CheckCircle2, CircleDollarSign, FlaskConical, Landmark, Loader2, PieChart,
  Send, Sparkles, Target, TrendingUp, Wallet, XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  API_BASE, approveAction, askAgent, fetchActions, fetchBudget, fetchGoals,
  fetchMonthly, fetchRecurring, fetchRuns, fetchUpcoming, inr, pct, rejectAction,
  runSimulation,
  type ActionDraft, type AgentAnswer, type AgentRun, type BudgetStatus,
  type Goal, type MonthlyAnalytics,
  type RecurringAnalysis, type SimulationResult,
} from "@/lib/api";

const QUESTION_CHIPS = [
  "Where did I spend the most this month?",
  "What changed compared with last month?",
  "Can I afford a 60,000 rupee laptop?",
  "How much am I committed to?",
  "Am I on track for my emergency fund?",
  "What happens if my rent increases by ₹2,000?",
];

const SIM_CARDS = [
  { type: "purchase", label: "Laptop Purchase" },
  { type: "rent_increase", label: "Rent Increase" },
  { type: "extra_savings", label: "Extra Savings" },
  { type: "cancel_subscription", label: "Cancel Netflix" },
  { type: "monthly_spend", label: "Custom Scenario" },
];
interface Msg {
  role: "user" | "agent";
  text: string;
  agent?: AgentAnswer;
  error?: string;
}

export default function Home() {
  const [monthly, setMonthly] = useState<MonthlyAnalytics | null>(null);
  const [recurring, setRecurring] = useState<RecurringAnalysis | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [actions, setActions] = useState<ActionDraft[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);

  const [simType, setSimType] = useState("purchase");
  const [simName, setSimName] = useState("Laptop");
  const [simAmount, setSimAmount] = useState(60000);
  const [simDuration, setSimDuration] = useState(12);
  const [simFreq, setSimFreq] = useState<"one_time" | "monthly">("one_time");
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [simBusy, setSimBusy] = useState(false);

  const [expandedRun, setExpandedRun] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, rc, g, b, a] = await Promise.all([
        fetchMonthly(), fetchRecurring(), fetchGoals(), fetchBudget(), fetchActions(),
      ]);
      setMonthly(m); setRecurring(rc);
      setGoals(g.goals); setBudget(b); setActions(a.actions);
      setApiUp(true);
    } catch {
      setApiUp(false);
    }
  }, []);

  const loadRuns = useCallback(async () => {
    try { setRuns((await fetchRuns()).runs); } catch { /* api down */ }
  }, []);

  useEffect(() => {
    load();
    loadRuns();
    const t = setInterval(() => { load(); loadRuns(); }, 30000);
    return () => clearInterval(t);
  }, [load, loadRuns]);

  const ask = useCallback(async (question: string) => {
    const q = question.trim();
    if (!q || thinking) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setThinking(true);
    try {
      const ans = await askAgent(q);
      setMessages((m) => [...m, { role: "agent", text: ans.answer, agent: ans }]);
      load(); loadRuns();
    } catch (e) {
      setMessages((m) => [...m, { role: "agent", text: "I could not reach the decision engine.", error: String(e) }]);
    } finally {
      setThinking(false);
    }
  }, [thinking, load, loadRuns]);
  const onApprove = useCallback(async (id: string) => {
    await approveAction(id);
    setActions((await fetchActions()).actions);
  }, []);

  const onReject = useCallback(async (id: string) => {
    await rejectAction(id);
    setActions((await fetchActions()).actions);
  }, []);

  const runSim = useCallback(async () => {
    setSimBusy(true);
    try {
      const res = await runSimulation({
        scenario_type: simType,
        name: simName,
        amount: Number(simAmount),
        frequency: simFreq,
        duration_months: simType === "purchase" || simType === "cancel_subscription" ? 1 : Number(simDuration),
        reference_id: simType === "cancel_subscription" ? (recurring?.payments.find(p => p.merchant === "Netflix")?.id ?? "") : "",
      });
      setSimResult(res);
    } catch (e) {
      setSimResult(null);
      alert(`Simulation failed: ${e}`);
    } finally {
      setSimBusy(false);
    }
  }, [simType, simName, simAmount, simFreq, simDuration, recurring]);

  const pickSim = (t: string, label: string, amt: number, freq: "one_time" | "monthly") => {
    setSimType(t); setSimName(label); setSimAmount(amt); setSimFreq(freq);
  };

  const net = monthly?.net ?? 0;
  const savingsRate = monthly?.savings_rate ?? 0;

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="sticky top-0 z-20 border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-xl bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30">
              <BrainCircuit className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">FinPilot</h1>
              <p className="text-xs text-zinc-500">Your Financial Intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={apiUp === null ? "outline" : apiUp ? "default" : "destructive"}>
              <span className={`mr-1 inline-block size-1.5 rounded-full ${apiUp === null ? "bg-zinc-500" : apiUp ? "bg-emerald-400" : "bg-red-400"}`} />
              {apiUp === null ? "connecting" : apiUp ? "API live" : "API down"}
            </Badge>
            <Badge variant="secondary">decision-support</Badge>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <div className="space-y-5">
          {/* ---- Copilot ---- */}
          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="size-4 text-emerald-400" /> AI Copilot
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-3">
                {messages.length === 0 && (
                  <p className="rounded-lg border border-dashed border-zinc-700 p-3 text-xs text-zinc-400">
                    Ask FinPilot anything about your money. Every answer is grounded in your
                    transactions — never invented. Evidence and calculations are shown with each reply.
                    {" "}An AI model enhances explanations when configured; otherwise you get the
                    same answers from the built-in deterministic engine.
                  </p>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                      m.role === "user"
                        ? "bg-emerald-500/15 text-emerald-50 ring-1 ring-emerald-500/30"
                        : "bg-zinc-800/80 text-zinc-100 ring-1 ring-zinc-700"
                    }`}>
                      <p>{m.text}</p>
                      {m.error && <p className="mt-1 text-xs text-red-400">{m.error}</p>}
                      {m.agent && <AgentDetailBlock agent={m.agent} />}
                    </div>
                  </div>
                ))}
                {thinking && (
                  <div className="flex items-center gap-2 text-xs text-zinc-400">
                    <Loader2 className="size-3.5 animate-spin text-emerald-400" />
                    <span>Detecting intent · calling tools · reasoning over data…</span>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-1.5">
                {QUESTION_CHIPS.map((c) => (
                  <button
                    key={c}
                    onClick={() => ask(c)}
                    className="rounded-full border border-zinc-700 bg-zinc-800/60 px-2.5 py-1 text-[11px] text-zinc-300 transition hover:border-emerald-500/50 hover:text-emerald-300"
                  >
                    {c}
                  </button>
                ))}
              </div>

              <form
                className="flex items-center gap-2"
                onSubmit={(e) => { e.preventDefault(); ask(input); }}
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask FinPilot anything about your money…"
                  className="h-10 flex-1 rounded-xl border border-zinc-700 bg-zinc-900 px-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-emerald-500/60 focus:outline-none"
                />
                <Button type="submit" disabled={thinking || !input.trim()} className="h-10">
                  {thinking ? <Loader2 className="mr-1 size-4 animate-spin" /> : <Send className="mr-1 size-4" />}
                  Ask
                </Button>
              </form>
            </CardContent>
          </Card>
          {/* ---- What-If Lab ---- */}
          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FlaskConical className="size-4 text-violet-400" /> What-If Lab
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                {SIM_CARDS.map((s) => (
                  <button
                    key={s.type}
                    onClick={() => pickSim(s.type, s.label, s.type === "purchase" ? 60000 : s.type === "rent_increase" ? 2000 : s.type === "extra_savings" ? 10000 : s.type === "cancel_subscription" ? 649 : 5000, s.type === "purchase" ? "one_time" : "monthly")}
                    className={`rounded-xl border p-2.5 text-left text-xs transition ${
                      simType === s.type
                        ? "border-violet-500/60 bg-violet-500/10 text-violet-200"
                        : "border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:border-zinc-500"
                    }`}
                  >
                    <div className="mb-1 text-violet-300"><TrendingUp className="size-4" /></div>
                    <div className="font-medium">{s.label}</div>
                  </button>
                ))}
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <label className="block text-xs text-zinc-400">
                  Amount (₹)
                  <input
                    type="number"
                    value={simAmount}
                    onChange={(e) => setSimAmount(Number(e.target.value))}
                    className="mt-1 h-9 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-2 text-sm text-zinc-100 focus:border-violet-500/60 focus:outline-none"
                  />
                </label>
                <label className="block text-xs text-zinc-400">
                  Frequency
                  <select
                    value={simFreq}
                    onChange={(e) => setSimFreq(e.target.value as "one_time" | "monthly")}
                    className="mt-1 h-9 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-2 text-sm text-zinc-100 focus:border-violet-500/60 focus:outline-none"
                  >
                    <option value="one_time">One-time</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </label>
                <label className="block text-xs text-zinc-400">
                  Duration (months)
                  <input
                    type="number"
                    value={simDuration}
                    min={1}
                    onChange={(e) => setSimDuration(Number(e.target.value))}
                    className="mt-1 h-9 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-2 text-sm text-zinc-100 focus:border-violet-500/60 focus:outline-none"
                  />
                </label>
              </div>

              <Button onClick={runSim} disabled={simBusy} className="w-full bg-violet-600 hover:bg-violet-500">
                {simBusy ? <Loader2 className="mr-1 size-4 animate-spin" /> : <Sparkles className="mr-1 size-4" />}
                Run Simulation
              </Button>

              {simResult && <SimulationBlock sim={simResult} />}
            </CardContent>
          </Card>

          {/* ---- Action drafts ---- */}
          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-amber-400" /> Action Drafts
                <Badge variant="outline" className="ml-1">{actions.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {actions.length === 0 && (
                <p className="text-xs text-zinc-500">No draft actions yet. Ask the copilot about your goals or spending to generate suggestions.</p>
              )}
              {actions.map((a) => (
                <div key={a.id} className="flex items-center justify-between gap-3 rounded-xl border border-zinc-700/70 bg-zinc-800/40 p-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-zinc-100">{a.title}</p>
                    {a.description && <p className="mt-0.5 truncate text-xs text-zinc-400">{a.description}</p>}
                    <Badge variant={a.status === "draft" ? "outline" : a.status === "approved" ? "default" : "secondary"} className="mt-1.5">
                      {a.status}
                    </Badge>
                  </div>
                  {a.status === "draft" && (
                    <div className="flex shrink-0 gap-1.5">
                      <Button size="sm" variant="secondary" onClick={() => onApprove(a.id)}>
                        <CheckCircle2 className="mr-1 size-3.5 text-emerald-400" /> Approve
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => onReject(a.id)}>
                        <XCircle className="mr-1 size-3.5 text-red-400" /> Reject
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
          {/* ---- Agent Activity ---- */}
          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="size-4 text-sky-400" /> Agent Activity
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {runs.length === 0 && <p className="text-xs text-zinc-500">No agent runs yet.</p>}
              {runs.map((r) => (
                <RunRow key={r.id} run={r} expanded={expandedRun === r.id}
                  onToggle={() => setExpandedRun(expandedRun === r.id ? null : r.id)} />
              ))}
            </CardContent>
          </Card>
        </div>

        {/* ============ RIGHT COLUMN ============ */}
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <KpiCard icon={<Wallet className="size-4 text-emerald-400" />} label="Net Cash Flow" value={inr(net)}
              sub={`${pct(savingsRate)} savings rate`} up={net >= 0} />
            <KpiCard icon={<CircleDollarSign className="size-4 text-rose-400" />} label="Monthly Spending" value={inr(monthly?.expenses ?? 0)}
              sub={monthly ? `${monthly.transactions_analyzed} transactions` : "…"} up={false} />
            <KpiCard icon={<TrendingUp className="size-4 text-sky-400" />} label="Savings Rate" value={pct(savingsRate)}
              sub={monthly?.period_label ?? "…"} up={savingsRate > 20} />
            <KpiCard icon={<Landmark className="size-4 text-amber-400" />} label="Committed" value={inr(recurring?.monthly_committed ?? 0)}
              sub={`${inr(recurring?.annualized_recurring_cost ?? 0)}/yr`} up={false} />
          </div>

          <Card className="border-emerald-500/25 bg-gradient-to-br from-emerald-500/10 to-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-300">
                <Sparkles className="size-4" /> AI Insight
              </CardTitle>
            </CardHeader>
            <CardContent>
              {monthly?.insights?.length ? (
                <ul className="space-y-1.5 text-sm text-zinc-200">
                  {monthly.insights.slice(0, 3).map((ins, i) => (
                    <li key={i} className="flex gap-2"><ArrowUpRight className="mt-0.5 size-3.5 shrink-0 text-emerald-400" />{ins}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-zinc-400">Loading insight…</p>
              )}
              {budget && (
                <div className="mt-3 grid grid-cols-3 gap-2 border-t border-zinc-700/60 pt-3 text-center">
                  <div>
                    <p className="text-[11px] text-zinc-500">Committed</p>
                    <p className="text-sm font-semibold text-amber-300">{inr(budget.committed)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] text-zinc-500">Spent</p>
                    <p className="text-sm font-semibold text-rose-300">{inr(budget.spent)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] text-zinc-500">Discretionary</p>
                    <p className="text-sm font-semibold text-emerald-300">{inr(budget.discretionary)}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="size-4 text-emerald-400" /> Goals
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {goals.map((g) => (
                <div key={g.id}>
                  <div className="mb-1 flex items-baseline justify-between text-sm">
                    <span className="font-medium text-zinc-200">{g.name}</span>
                    <span className="text-xs text-zinc-400">{inr(g.current_amount)} / {inr(g.target_amount)} · {pct(g.progress_pct)}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-zinc-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400"
                      style={{ width: `${Math.min(100, g.progress_pct)}%` }}
                    />
                  </div>
                  {g.required_monthly !== null && (
                    <p className="mt-1 text-[11px] text-zinc-500">
                      {inr(g.required_monthly)}/mo required{g.target_date ? ` · target ${g.target_date}` : ""}
                    </p>
                  )}
                </div>
              ))}
              {goals.length === 0 && <p className="text-xs text-zinc-500">No goals set up.</p>}
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BadgeCheck className="size-4 text-sky-400" /> Upcoming Obligations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <UpcomingList />
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="size-4 text-violet-400" /> Spending Mix · {monthly?.period_label ?? ""}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {monthly?.category_breakdown.map((c) => (
                <div key={c.category} className="flex items-center gap-2 text-sm">
                  <span className="w-28 shrink-0 truncate text-zinc-300">{c.category}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-800">
                    <div
                      className="h-full rounded-full bg-violet-500/70"
                      style={{ width: `${monthly.expenses > 0 ? (c.amount / monthly.expenses) * 100 : 0}%` }}
                    />
                  </div>
                  <span className="w-20 shrink-0 text-right text-xs text-zinc-400">{inr(c.amount)}</span>
                  <span className="w-6 shrink-0 text-right text-[10px] text-zinc-600">{c.transaction_count}×</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      <footer className="mx-auto max-w-7xl px-5 pb-8 text-center text-[11px] text-zinc-600">
        FinPilot · decision-support only · informational analysis, never financial advice · API {API_BASE}
      </footer>
    </main>
  );
}
function KpiCard({ icon, label, value, sub, up }: {
  icon: React.ReactNode; label: string; value: string; sub: string; up: boolean;
}) {
  return (
    <Card className="border-zinc-800 bg-zinc-900/60">
      <CardContent className="pt-4">
        <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">{icon}{label}</div>
        <p className="mt-1 text-lg font-bold tracking-tight text-zinc-50">{value}</p>
        <p className={`flex items-center gap-1 text-[11px] ${up ? "text-emerald-400" : "text-zinc-500"}`}>
          {up ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}{sub}
        </p>
      </CardContent>
    </Card>
  );
}

function UpcomingList() {
  const [items, setItems] = useState<{ merchant: string; due_date: string; amount: number }[]>([]);
  useEffect(() => {
    (async () => {
      try {
        const res = await fetchUpcoming();
        const list = res.upcoming.map((u) => ({
          merchant: u.merchant, due_date: u.next_payment_date, amount: u.amount,
        }));
        setItems(list.slice(0, 4));
      } catch { /* ignore */ }
    })();
  }, []);
  if (items.length === 0) return <p className="text-xs text-zinc-500">Nothing scheduled ahead.</p>;
  return (
    <ul className="space-y-1.5 text-sm">
      {items.map((i) => (
        <li key={i.merchant + i.due_date} className="flex items-center justify-between gap-2 rounded-lg bg-zinc-800/50 px-3 py-2">
          <span className="truncate text-zinc-200">{i.merchant}</span>
          <span className="shrink-0 text-xs text-zinc-400">{new Date(i.due_date).toLocaleDateString()}</span>
          <span className="shrink-0 font-medium text-zinc-100">{inr(i.amount)}</span>
        </li>
      ))}
    </ul>
  );
}

function SimulationBlock({ sim }: { sim: SimulationResult }) {
  const b = sim.baseline, s = sim.scenario;
  const diff = sim.difference ?? {};
  const gi = sim.goal_impact ?? {};
  const delayMonths = gi.delay_months as number | null;
  const delayTxt = delayMonths === null || delayMonths === undefined
    ? null
    : delayMonths > 0
      ? `delays '${gi.goal}' goal by about ${delayMonths} month(s)`
      : delayMonths < 0
        ? `reaches '${gi.goal}' about ${-delayMonths} month(s) sooner`
        : `'${gi.goal}' timeline unchanged`;
  return (
    <div className="space-y-2 rounded-xl border border-violet-500/25 bg-violet-500/5 p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-violet-300">{s.label}</span>
        <Badge variant={s.monthly_savings >= 0 ? "default" : "secondary"}>
          {s.monthly_savings >= 0 ? "feasible" : "caution"}
        </Badge>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-[11px] text-zinc-500">Savings now</p>
          <p className="font-semibold text-zinc-100">{inr(b.monthly_savings)}</p>
        </div>
        <div>
          <p className="text-[11px] text-zinc-500">Savings after</p>
          <p className="font-semibold text-emerald-300">{inr(s.monthly_savings)}</p>
        </div>
        <div>
          <p className="text-[11px] text-zinc-500">Cumulative ({diff.duration_months ?? 1} mo)</p>
          <p className="font-semibold text-amber-300">{inr(diff.total_cumulative ?? 0)}</p>
        </div>
      </div>
      {delayTxt && <p className="text-xs text-amber-300">— {delayTxt}</p>}
      <p className="text-xs leading-relaxed text-zinc-300">{sim.explanation}</p>
      {sim.assumptions.length > 0 && (
        <ul className="space-y-0.5 text-[10px] text-zinc-500">
          {sim.assumptions.map((a, i) => <li key={i}>— {a}</li>)}
        </ul>
      )}
      <p className="text-[11px] text-zinc-600">deterministic run · decision-support only</p>
    </div>
  );
}
function AgentDetailBlock({ agent }: { agent: AgentAnswer }) {
  return (
    <div className="mt-2 space-y-2 border-t border-zinc-700/60 pt-2 text-xs">
      <div className="flex flex-wrap gap-1.5">
        <Badge variant="outline" className="text-[10px]">{agent.intent}</Badge>
        <Badge variant={agent.mode === "llm" ? "default" : "secondary"} className="text-[10px]">
          {agent.mode === "llm" ? `AI-assisted · ${agent.model || "llm"}` : "deterministic engine"}
        </Badge>
        {agent.warnings?.map((w, i) => (
          <Badge key={i} variant="destructive" className="text-[10px]">{w.slice(0, 60)}</Badge>
        ))}
        {agent.recommended_actions
          .filter((r) => r.action_type !== "none")
          .map((r) => (
            <Badge key={r.id || r.title} variant="secondary" className="bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30">
              action: {r.title}
            </Badge>
          ))}
      </div>

      {agent.evidence.length > 0 && (
        <details className="rounded-lg bg-zinc-900/80 p-2" open>
          <summary className="cursor-pointer font-medium text-zinc-300">Evidence</summary>
          <ul className="mt-1.5 space-y-1">
            {agent.evidence.map((e, i) => (
              <li key={i} className="flex items-center gap-1.5 text-zinc-400">
                <CheckCircle2 className="size-3 shrink-0 text-emerald-500" />
                <span>
                  <span className="text-zinc-300">{e.label}:</span> {e.value}
                  {e.detail ? <span className="text-zinc-500"> · {e.detail}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {agent.calculations.length > 0 && (
        <details className="rounded-lg bg-zinc-900/80 p-2">
          <summary className="cursor-pointer font-medium text-zinc-300">Calculations</summary>
          <ul className="mt-1.5 space-y-1">
            {agent.calculations.map((c, i) => (
              <li key={i} className="text-zinc-400">
                <span className="text-zinc-300">{c.formula}:</span> {c.value}
                {c.detail ? <span className="text-zinc-500"> · {c.detail}</span> : null}
              </li>
            ))}
          </ul>
        </details>
      )}

      {agent.activity.length > 0 && (
        <details className="rounded-lg bg-zinc-900/80 p-2">
          <summary className="cursor-pointer font-medium text-zinc-300">Activity · {agent.activity.length} steps</summary>
          <ol className="mt-1.5 space-y-1">
            {agent.activity.map((a, i) => (
              <li key={i} className="flex items-center justify-between gap-2 text-zinc-400">
                <span className="truncate">{i + 1}. {a.tool} → {a.status}</span>
                {a.latency_ms !== undefined && <span className="shrink-0 text-[10px] text-zinc-600">{a.latency_ms}ms</span>}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function RunRow({ run, expanded, onToggle }: {
  run: AgentRun; expanded: boolean; onToggle: () => void;
}) {
  let intent = "";
  let answer = run.final_response ?? "";
  try {
    const parsed = JSON.parse(run.final_response ?? "{}");
    if (parsed && typeof parsed === "object") {
      intent = parsed.intent ?? "";
      answer = parsed.answer ?? run.final_response ?? "";
    }
  } catch { /* final_response is a plain string */ }
  const label = intent ? `${intent}` : "agent run";
  return (
    <div className="rounded-xl border border-zinc-700/70 bg-zinc-800/40">
      <button onClick={onToggle} className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left">
        <div className="min-w-0">
          <p className={`text-[11px] font-medium ${run.status === "completed" ? "text-emerald-300" : run.status === "failed" ? "text-red-300" : "text-amber-300"}`}>
            {run.status}
          </p>
          <p className="truncate text-sm text-zinc-100">{run.question || label}</p>
        </div>
        <div className="shrink-0 text-right">
          <Badge variant="outline" className="text-[10px]">{label}</Badge>
          <p className="mt-1 text-[10px] text-zinc-500">{new Date(run.created_at).toLocaleString()}</p>
        </div>
      </button>
      {expanded && (
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap border-t border-zinc-700/60 px-3 py-2 text-[10px] leading-relaxed text-zinc-400">
          {answer}
        </pre>
      )}
    </div>
  );
}