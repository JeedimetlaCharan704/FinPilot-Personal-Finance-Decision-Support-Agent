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
          label="Net cash flow"
          value={inr(net)}
          sub={`${pct(savingsRate)} savings rate`}
          color={net >= 0 ? "var(--color-fp-green)" : "var(--color-fp-rose)"}
        />
        <StatTile
          label="Monthly spending"
          value={inr(monthly?.expenses ?? 0)}
          sub={monthly ? `${monthly.transactions_analyzed} transactions` : "…"}
          color="var(--color-fp-rose)"
        />
        <StatTile
          label="Savings rate"
          value={pct(savingsRate)}
          sub={monthly?.period_label ?? "…"}
          color={savingsRate > 20 ? "var(--color-fp-green)" : "var(--color-fp-amber)"}
        />
        <StatTile
          label="Committed"
          value={inr(recurring?.monthly_committed ?? 0)}
          sub={`${inr(recurring?.annualized_recurring_cost ?? 0)}/yr`}
          color="var(--color-fp-amber)"
        />
      </div>

      {/* AI Insight */}
      <div
        className="rounded-xl p-4"
        style={{
          background: "linear-gradient(135deg, #dce9e7 0%, #cbd8d7 100%)",
          border: "1px solid #b0c0c0",
        }}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="size-3.5" style={{ color: "#1e293b" }} />
          <p className="fp-label-card" style={{ color: "#1e293b" }}>AI Insight</p>
        </div>
        <div className="mt-2">
          {monthly?.insights?.length ? (
            <ul className="space-y-1.5 text-xs" style={{ color: "#334155" }}>
              {monthly.insights.slice(0, 3).map((ins, i) => (
                <li key={i} className="flex gap-2">
                  <ArrowUpRight className="mt-0.5 size-3 shrink-0" style={{ color: "#16a34a" }} />
                  {ins}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs" style={{ color: "#64748b" }}>Loading insight…</p>
          )}
        </div>
        {budget && (
          <div className="mt-3 grid grid-cols-3 gap-2 border-t pt-3 text-center" style={{ borderColor: "#a3b8b6" }}>
            <div>
              <p className="text-[10px]" style={{ color: "#475569" }}>Committed</p>
              <p className="text-xs font-semibold" style={{ color: "#b45309" }}>{inr(budget.committed)}</p>
            </div>
            <div>
              <p className="text-[10px]" style={{ color: "#475569" }}>Spent</p>
              <p className="text-xs font-semibold" style={{ color: "#dc2626" }}>{inr(budget.spent)}</p>
            </div>
            <div>
              <p className="text-[10px]" style={{ color: "#475569" }}>Discretionary</p>
              <p className="text-xs font-semibold" style={{ color: "#16a34a" }}>{inr(budget.discretionary)}</p>
            </div>
          </div>
        )}
      </div>

      {/* Goals */}
      {goals.length > 0 && (
        <div className="rounded-xl p-4" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Target className="size-3.5" style={{ color: "var(--color-fp-green)" }} />
            <p className="fp-label-card">Goals</p>
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
                      background: "linear-gradient(90deg, #19d3a2, #2dd4bf)",
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
            <p className="fp-label-card">
              Spending · {monthly.period_label}
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
        <p className="fp-label-card">Upcoming</p>
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
