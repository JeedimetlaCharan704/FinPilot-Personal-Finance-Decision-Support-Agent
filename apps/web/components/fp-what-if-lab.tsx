"use client";

import { useState } from "react";
import { TrendingUp, Sparkles, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { inr, type RecurringAnalysis, type SimulationResult } from "@/lib/api";
import { runSimulation } from "@/lib/api";

const SIM_CARDS = [
  { type: "purchase", label: "Laptop Purchase", amount: 60000, freq: "one_time" as const },
  { type: "rent_increase", label: "Rent Increase", amount: 2000, freq: "monthly" as const },
  { type: "extra_savings", label: "Extra Savings", amount: 10000, freq: "monthly" as const },
  { type: "cancel_subscription", label: "Cancel Netflix", amount: 649, freq: "monthly" as const },
  { type: "monthly_spend", label: "Custom Scenario", amount: 5000, freq: "monthly" as const },
];

interface WhatIfLabProps {
  recurring: RecurringAnalysis | null;
}

export function WhatIfLab({ recurring }: WhatIfLabProps) {
  const [simType, setSimType] = useState("purchase");
  const [simName, setSimName] = useState("Laptop");
  const [simAmount, setSimAmount] = useState(60000);
  const [simDuration, setSimDuration] = useState(12);
  const [simFreq, setSimFreq] = useState<"one_time" | "monthly">("one_time");
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [simBusy, setSimBusy] = useState(false);

  const pickSim = (s: typeof SIM_CARDS[number]) => {
    setSimType(s.type);
    setSimName(s.label);
    setSimAmount(s.amount);
    setSimFreq(s.freq);
  };

  const runSim = async () => {
    setSimBusy(true);
    try {
      const res = await runSimulation({
        scenario_type: simType,
        name: simName,
        amount: Number(simAmount),
        frequency: simFreq,
        duration_months: simType === "purchase" || simType === "cancel_subscription" ? 1 : Number(simDuration),
        reference_id: simType === "cancel_subscription"
          ? (recurring?.payments.find((p) => p.merchant === "Netflix")?.id ?? "")
          : "",
      });
      setSimResult(res);
    } catch {
      setSimResult(null);
    } finally {
      setSimBusy(false);
    }
  };

  const b = simResult?.baseline;
  const s = simResult?.scenario;
  const diff = simResult?.difference ?? {};
  const gi = simResult?.goal_impact;

  return (
    <div className="rounded-xl p-4" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp className="size-3.5" style={{ color: "var(--color-fp-violet)" }} />
        <p className="fp-label-card">What-if lab</p>
      </div>

      {/* Presets */}
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-5">
        {SIM_CARDS.map((sc) => (
          <button
            key={sc.type}
            onClick={() => pickSim(sc)}
            className={cn(
              "rounded-lg px-2.5 py-2 text-left text-[11px] transition-all",
              simType === sc.type
                ? "scale-[1.02]"
                : "hover:scale-[1.01]",
            )}
            style={{
              background: simType === sc.type ? "var(--color-fp-violet-dim)" : "var(--color-fp-surface-raised)",
              border: `1px solid ${simType === sc.type ? "var(--color-fp-violet-ring)" : "var(--color-fp-border)"}`,
              color: simType === sc.type ? "var(--color-fp-violet)" : "var(--color-fp-text-muted)",
            }}
          >
            <span className="font-medium">{sc.label}</span>
          </button>
        ))}
      </div>

      {/* Inputs */}
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <label className="block text-[11px]" style={{ color: "var(--color-fp-text-dim)" }}>
          Amount
          <input
            type="number"
            value={simAmount}
            onChange={(e) => setSimAmount(Number(e.target.value))}
            className="mt-1 h-8 w-full rounded-lg px-2 text-xs text-white focus:outline-none focus:ring-1"
            style={{
              background: "var(--color-fp-surface-raised)",
              border: "1px solid var(--color-fp-border)",
            }}
          />
        </label>
        <label className="block text-[11px]" style={{ color: "var(--color-fp-text-dim)" }}>
          Frequency
          <select
            value={simFreq}
            onChange={(e) => setSimFreq(e.target.value as "one_time" | "monthly")}
            className="mt-1 h-8 w-full rounded-lg px-2 text-xs text-white focus:outline-none"
            style={{ background: "var(--color-fp-surface-raised)", border: "1px solid var(--color-fp-border)" }}
          >
            <option value="one_time">One-time</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
        <label className="block text-[11px]" style={{ color: "var(--color-fp-text-dim)" }}>
          Duration (months)
          <input
            type="number"
            value={simDuration}
            min={1}
            onChange={(e) => setSimDuration(Number(e.target.value))}
            className="mt-1 h-8 w-full rounded-lg px-2 text-xs text-white focus:outline-none"
            style={{ background: "var(--color-fp-surface-raised)", border: "1px solid var(--color-fp-border)" }}
          />
        </label>
      </div>

      <Button
        onClick={runSim}
        disabled={simBusy}
        className="mt-3 w-full gap-1.5"
        style={{
          background: simBusy ? "var(--color-fp-surface-raised)" : "linear-gradient(135deg, #7c3aed, #9333ea)",
          color: simBusy ? "var(--color-fp-text-muted)" : "white",
          border: "1px solid var(--color-fp-border)",
        }}
      >
        {simBusy ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
        {simBusy ? "Simulating…" : "Run Simulation"}
      </Button>

      {/* Results */}
      {simResult && b && s && (
        <div className="mt-3 rounded-lg p-3" style={{ background: "var(--color-fp-violet-dim)", border: "1px solid var(--color-fp-violet-ring)" }}>
          <div className="flex items-center justify-between">
            <span className="fp-label-secondary" style={{ color: "var(--color-fp-violet)" }}>{s.label}</span>
            <Badge
              variant="outline"
              className="text-[10px]"
              style={{
                color: s.monthly_savings >= 0 ? "var(--color-fp-green)" : "var(--color-fp-rose)",
                borderColor: s.monthly_savings >= 0 ? "var(--color-fp-green-ring)" : "var(--color-fp-rose-ring)",
              }}
            >
              {s.monthly_savings >= 0 ? "feasible" : "caution"}
            </Badge>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Savings before</p>
              <p className="text-xs font-bold text-white">{inr(b.monthly_savings)}</p>
            </div>
            <div>
              <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Savings after</p>
              <p className="text-xs font-bold" style={{ color: "var(--color-fp-green)" }}>{inr(s.monthly_savings)}</p>
            </div>
            <div>
              <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Cumulative ({diff.duration_months ?? 1}mo)</p>
              <p className="text-xs font-bold" style={{ color: "var(--color-fp-amber)" }}>{inr(diff.total_cumulative ?? 0)}</p>
            </div>
          </div>
          {gi?.delay_months != null && gi.delay_months !== 0 && (
            <p className="mt-2 text-[11px]" style={{ color: gi.delay_months > 0 ? "var(--color-fp-rose)" : "var(--color-fp-green)" }}>
              {gi.delay_months > 0
                ? `Delays "${gi.goal}" goal by ${gi.delay_months} month(s)`
                : `Reaches "${gi.goal}" ${-gi.delay_months} month(s) sooner`}
            </p>
          )}
          <p className="mt-2 text-[11px] leading-relaxed" style={{ color: "var(--color-fp-text-muted)" }}>
            {simResult.explanation}
          </p>
          {simResult.assumptions.length > 0 && (
            <ul className="mt-1.5 space-y-0.5 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
              {simResult.assumptions.map((a, i) => <li key={i}>— {a}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
