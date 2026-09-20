"use client";

import { Sparkles, ArrowUpRight, Target, BadgeCheck, PieChart } from "lucide-react";
import { StatTile } from "./fp-stat-tile";
import { SpendingBars } from "./fp-spending-bars";
import { inr, pct, type MonthlyAnalytics, type RecurringAnalysis, type BudgetStatus, type Goal } from "@/lib/api";
import { useEffect, useState } from "react";
import { fetchUpcoming } from "@/lib/api";

interface SecondaryRailProps {
  monthly: MonthlyAnalytics | null;
  recurring: RecurringAnalysis | null;
  budget: BudgetStatus | null;
  goals: Goal[];
}

export function SecondaryRail({ monthly, recurring, budget, goals }: SecondaryRailProps) {
  const net = monthly?.net ?? 0;
  const savingsRate = monthly?.savings_rate ?? 0;

  return (
    <div className="space-y-4">
      {/* Stat tiles */}
      <div className="grid grid-cols-2 gap-2.5">
        <StatTile
          label="NET CASH FLOW"
          value={inr(net)}
          sub={`${pct(savingsRate)} savings rate`}
          color={net >= 0 ? "var(--color-fp-green)" : "var(--color-fp-rose)"}
        />
        <StatTile
          label="MONTHLY SPENDING"
          value={inr(monthly?.expenses ?? 0)}
          sub={monthly ? `${monthly.transactions_analyzed} transactions` : "…"}
          color="var(--color-fp-rose)"
        />
        <StatTile
          label="SAVINGS RATE"
          value={pct(savingsRate)}
          sub={monthly?.period_label ?? "…"}
          color={savingsRate > 20 ? "var(--color-fp-green)" : "var(--color-fp-amber)"}
        />
        <StatTile
          label="COMMITTED"
          value={inr(recurring?.monthly_committed ?? 0)}
          sub={`${inr(recurring?.annualized_recurring_cost ?? 0)}/yr`}
          color="var(--color-fp-amber)"
        />
      </div>

      {/* AI Insight */}
      <div
        className="rounded-xl p-4"
        style={{
          background: "linear-gradient(135deg, var(--color-fp-green-dim) 0%, var(--color-fp-surface) 100%)",
          border: "1px solid var(--color-fp-green-ring)",
        }}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="size-3.5" style={{ color: "var(--color-fp-green)" }} />
          <p className="fp-label-card" style={{ color: "var(--color-fp-green)" }}>AI INSIGHT</p>
        </div>
        <div className="mt-2">
          {monthly?.insights?.length ? (
            <ul className="space-y-1.5 text-xs" style={{ color: "var(--color-fp-text-muted)" }}>
              {monthly.insights.slice(0, 3).map((ins, i) => (
                <li key={i} className="flex gap-2">
                  <ArrowUpRight className="mt-0.5 size-3 shrink-0" style={{ color: "var(--color-fp-green)" }} />
                  {ins}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs" style={{ color: "var(--color-fp-text-dim)" }}>Loading insight…</p>
          )}
        </div>
        {budget && (
          <div className="mt-3 grid grid-cols-3 gap-2 border-t pt-3 text-center" style={{ borderColor: "var(--color-fp-border)" }}>
            <div>
              <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Committed</p>
              <p className="text-xs font-semibold" style={{ color: "var(--color-fp-amber)" }}>{inr(budget.committed)}</p>
            </div>
            <div>
              <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Spent</p>
              <p className="text-xs font-semibold" style={{ color: "var(--color-fp-rose)" }}>{inr(budget.spent)}</p>
            </div>
            <div>
              <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Discretionary</p>
              <p className="text-xs font-semibold" style={{ color: "var(--color-fp-green)" }}>{inr(budget.discretionary)}</p>
            </div>
          </div>
        )}
      </div>

      {/* Goals */}
      {goals.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Target className="size-3.5" style={{ color: "var(--color-fp-green)" }} />
            <p className="fp-label-card" style={{ color: "var(--color-fp-text-muted)" }}>GOALS</p>
          </div>
          <div className="space-y-3">
            {goals.map((g) => (
              <div key={g.id}>
                <div className="flex items-baseline justify-between text-xs">
                  <span className="font-medium text-white">{g.name}</span>
                  <span style={{ color: "var(--color-fp-text-dim)" }}>
                    {pct(g.progress_pct)}
                  </span>
                </div>
                <div className="fp-progress-track mt-1">
                  <div
                    className="fp-progress-fill"
                    style={{
                      width: `${Math.min(100, g.progress_pct)}%`,
                      background: "var(--color-fp-green)",
                    }}
                  />
                </div>
                <p className="mt-0.5 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
                  {inr(g.current_amount)} / {inr(g.target_amount)}
                  {g.required_monthly != null && ` · ${inr(g.required_monthly)}/mo required`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming obligations */}
      <UpcomingMini />

      {/* Spending breakdown */}
      {monthly && monthly.category_breakdown.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
          <div className="flex items-center gap-2 mb-3">
            <PieChart className="size-3.5" style={{ color: "var(--color-fp-violet)" }} />
            <p className="fp-label-card" style={{ color: "var(--color-fp-text-muted)" }}>
              SPENDING · {monthly.period_label}
            </p>
          </div>
          <SpendingBars categories={monthly.category_breakdown} />
        </div>
      )}
    </div>
  );
}

function UpcomingMini() {
  const [items, setItems] = useState<{ merchant: string; due_date: string; amount: number }[]>([]);
  useEffect(() => {
    (async () => {
      try {
        const res = await fetchUpcoming();
        setItems(res.upcoming.slice(0, 4).map((u) => ({
          merchant: u.merchant, due_date: u.next_payment_date, amount: u.amount,
        })));
      } catch { /* ignore */ }
    })();
  }, []);
  if (items.length === 0) return null;
  return (
    <div className="rounded-xl p-4" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
      <div className="flex items-center gap-2 mb-2">
        <BadgeCheck className="size-3.5" style={{ color: "var(--color-fp-sky)" }} />
        <p className="fp-label-card" style={{ color: "var(--color-fp-text-muted)" }}>UPCOMING</p>
      </div>
      <ul className="space-y-1.5">
        {items.map((i) => (
          <li
            key={i.merchant + i.due_date}
            className="flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5"
            style={{ background: "var(--color-fp-surface-raised)" }}
          >
            <span className="truncate text-xs text-white">{i.merchant}</span>
            <span className="shrink-0 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
              {new Date(i.due_date).toLocaleDateString()}
            </span>
            <span className="shrink-0 text-xs font-medium text-white">{inr(i.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
