"use client";

import { useState } from "react";
import { Gauge, ChevronDown, Target, CheckCircle2, BrainCircuit } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { inr, type AgentAnswer, type DecisionScenario, type DecisionGoalImpact } from "@/lib/api";

/* ---- Verdict metadata ---- */
const VERDICT_META: Record<string, {
  color: string; dimColor: string; ringColor: string;
  label: string; emoji: string;
}> = {
  AFFORDABLE: { color: "var(--color-fp-green)", dimColor: "var(--color-fp-green-dim)", ringColor: "var(--color-fp-green-ring)", label: "AFFORDABLE", emoji: "" },
  TIGHT: { color: "var(--color-fp-amber)", dimColor: "var(--color-fp-amber-dim)", ringColor: "var(--color-fp-amber-ring)", label: "TIGHT", emoji: "" },
  NOT_YET: { color: "var(--color-fp-rose)", dimColor: "var(--color-fp-rose-dim)", ringColor: "var(--color-fp-rose-ring)", label: "NOT YET", emoji: "" },
  INSUFFICIENT_DATA: { color: "var(--color-fp-text-muted)", dimColor: "rgba(139,141,149,0.12)", ringColor: "rgba(139,141,149,0.30)", label: "INSUFFICIENT DATA", emoji: "" },
};

const fmtCash = (v: number | null | undefined): string => {
  const n = Number(v ?? 0);
  return n < 0 ? `\u2212${inr(Math.abs(n))}` : inr(n);
};

/* ---- Main Verdict Card ---- */
export function DecisionVerdictCard({ agent }: { agent: AgentAnswer }) {
  const d = agent.decision!;
  const meta = VERDICT_META[d.verdict] ?? VERDICT_META.INSUFFICIENT_DATA;
  const [showEvidence, setShowEvidence] = useState(false);

  return (
    <section className="mx-auto max-w-7xl px-5 pt-6">
      <div
        className="overflow-hidden rounded-2xl"
        style={{
          background: "var(--color-fp-surface)",
          border: "1px solid var(--color-fp-border)",
          boxShadow: `0 0 0 1px ${meta.ringColor}, 0 0 40px -12px ${meta.color}30`,
        }}
      >
        {/* Verdict header */}
        <div
          className="flex items-center justify-between gap-4 px-6 py-4"
          style={{ background: meta.dimColor }}
        >
          <div className="flex items-center gap-3">
            <div
              className="grid size-10 place-items-center rounded-xl"
              style={{ background: `${meta.color}20`, border: `1px solid ${meta.ringColor}` }}
            >
              <Gauge className="size-5" style={{ color: meta.color }} />
            </div>
            <div>
              <p className="fp-label-secondary">DECISION</p>
              <p className="text-xs" style={{ color: "var(--color-fp-text-muted)" }}>
                {agent.intent} · {agent.mode === "llm" ? `AI-assisted` : "deterministic"}
              </p>
            </div>
          </div>
          <Badge
            variant="outline"
            className="gap-1.5 border-white/[0.1] px-3 py-1 text-xs font-bold"
            style={{ color: meta.color, borderColor: meta.ringColor }}
          >
            <span className="inline-block size-2 rounded-full" style={{ background: meta.color }} />
            {meta.label}
          </Badge>
        </div>

        <div className="space-y-6 px-6 py-6">
          {/* Purchase amount + verdict */}
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="fp-label-card">PURCHASE AMOUNT</p>
              <p className="fp-number-decision mt-1">{inr(d.purchase_amount)}</p>
            </div>
            <p
              className="max-w-lg text-sm leading-relaxed"
              style={{ color: "var(--color-fp-text-muted)" }}
            >
              {agent.answer}
            </p>
          </div>

          {/* Key numbers grid — 4 most important numbers */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <NumberCell label="FREE CASH" value={inr(d.free_cash)} color="var(--color-fp-green)" />
            <NumberCell
              label="CASH AFTER"
              value={fmtCash(d.cash_after_purchase)}
              color={d.cash_after_purchase < 0 ? "var(--color-fp-rose)" : "var(--color-fp-green)"}
            />
            <NumberCell label="COMMITTED" value={inr(d.committed_outflows)} color="var(--color-fp-amber)" />
            <NumberCell
              label="MONTHS TO SAVE"
              value={d.months_to_save != null ? `${d.months_to_save}` : "—"}
              color="var(--color-fp-sky)"
            />
          </div>

          {/* Scenarios */}
          {d.scenarios.length > 0 && <ScenarioRow scenarios={d.scenarios} />}

          {/* Goal impacts */}
          {d.goal_impacts.length > 0 && <GoalImpactBlock impacts={d.goal_impacts} />}

          {/* Agent trace */}
          {agent.activity.length > 0 && <AgentTraceInline activity={agent.activity} />}

          {/* Evidence & assumptions — collapsed */}
          <details
            className="group overflow-hidden rounded-xl"
            style={{ background: "var(--color-fp-bg)", border: "1px solid var(--color-fp-border)" }}
          >
            <summary
              className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-medium text-white"
              onClick={(e) => { e.preventDefault(); setShowEvidence(!showEvidence); }}
            >
              <span>Evidence & assumptions</span>
              <ChevronDown
                className={cn(
                  "size-3.5 transition-transform",
                  showEvidence ? "rotate-180" : "",
                )}
                style={{ color: "var(--color-fp-text-dim)" }}
              />
            </summary>
            {showEvidence && (
              <div className="grid gap-4 border-t px-4 py-3 lg:grid-cols-2" style={{ borderColor: "var(--color-fp-border)" }}>
                <ul className="space-y-1.5 text-xs" style={{ color: "var(--color-fp-text-muted)" }}>
                  {agent.evidence.map((e, i) => (
                    <li key={i} className="flex gap-1.5">
                      <CheckCircle2 className="mt-0.5 size-3 shrink-0" style={{ color: "var(--color-fp-green)" }} />
                      <span>
                        <span className="text-white">{e.label}:</span> {e.value}
                        {e.detail ? <span style={{ color: "var(--color-fp-text-dim)" }}> · {e.detail}</span> : null}
                      </span>
                    </li>
                  ))}
                </ul>
                <ul className="space-y-1 text-xs" style={{ color: "var(--color-fp-text-dim)" }}>
                  {d.assumptions.map((a, i) => <li key={i}>— {a}</li>)}
                </ul>
              </div>
            )}
          </details>
        </div>
      </div>
    </section>
  );
}

/* ---- Number cell used in the key metrics grid ---- */
function NumberCell({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div
      className="rounded-xl px-3.5 py-3"
      style={{ background: "var(--color-fp-bg)", border: "1px solid var(--color-fp-border)" }}
    >
      <p className="fp-label-secondary">{label}</p>
      <p className="fp-number-evidence mt-1" style={{ color }}>{value}</p>
    </div>
  );
}

/* ---- Scenario comparison row ---- */
function ScenarioRow({ scenarios }: { scenarios: DecisionScenario[] }) {
  if (!scenarios || scenarios.length === 0) return null;
  return (
    <div>
      <p className="mb-3 flex items-center gap-1.5 fp-label-card" style={{ color: "var(--color-fp-violet)" }}>
        <Target className="size-3" /> SCENARIOS
      </p>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {scenarios.map((s, i) => (
          <div
            key={i}
            className="rounded-xl px-3.5 py-3 transition-all hover:scale-[1.01]"
            style={{ background: "var(--color-fp-violet-dim)", border: "1px solid var(--color-fp-violet-ring)" }}
          >
            <p className="text-[11px] font-semibold" style={{ color: "var(--color-fp-violet)" }}>
              {s.label}
            </p>
            <p className="mt-1 text-lg font-bold text-white">{inr(s.amount)}</p>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {s.cash_after_purchase != null && (
                <span className="rounded-md bg-white/[0.05] px-1.5 py-0.5 text-[10px]" style={{ color: s.cash_after_purchase < 0 ? "var(--color-fp-rose)" : "var(--color-fp-green)" }}>
                  cash: {fmtCash(s.cash_after_purchase)}
                </span>
              )}
              {s.months_to_save != null && (
                <span className="rounded-md bg-white/[0.05] px-1.5 py-0.5 text-[10px] text-white">
                  {s.months_to_save}mo to save
                </span>
              )}
              {s.goal_delay_months != null && s.goal_delay_months !== 0 && (
                <span
                  className="rounded-md px-1.5 py-0.5 text-[10px]"
                  style={{
                    background: s.goal_delay_months > 0 ? "var(--color-fp-rose-dim)" : "var(--color-fp-green-dim)",
                    color: s.goal_delay_months > 0 ? "var(--color-fp-rose)" : "var(--color-fp-green)",
                  }}
                >
                  goal {s.goal_delay_months > 0 ? `+${s.goal_delay_months}mo` : `${s.goal_delay_months}mo`}
                </span>
              )}
            </div>
            {s.detail && (
              <p className="mt-1.5 text-[10px] leading-relaxed" style={{ color: "var(--color-fp-text-dim)" }}>
                {s.detail}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Goal impact block ---- */
function GoalImpactBlock({ impacts }: { impacts: DecisionGoalImpact[] }) {
  if (!impacts || impacts.length === 0) return null;
  return (
    <div>
      <p className="mb-3 flex items-center gap-1.5 fp-label-card" style={{ color: "var(--color-fp-green)" }}>
        <Target className="size-3" /> GOAL IMPACT
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {impacts.map((g, i) => {
          const delayColor =
            g.delay_months != null && g.delay_months > 0 ? "var(--color-fp-rose)" :
            g.delay_months != null && g.delay_months < 0 ? "var(--color-fp-green)" :
            "var(--color-fp-text-dim)";
          return (
            <div
              key={i}
              className="rounded-xl px-3.5 py-3"
              style={{ background: "var(--color-fp-bg)", border: "1px solid var(--color-fp-border)" }}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-white">{g.goal}</span>
                <span className="text-[11px] font-semibold" style={{ color: delayColor }}>
                  {g.delay_months == null ? "timeline unavailable" :
                   g.delay_months > 0 ? `delayed ${g.delay_months}mo` :
                   g.delay_months < 0 ? `accelerated ${-g.delay_months}mo` :
                   "unchanged"}
                </span>
              </div>
              <p className="mt-1 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
                {g.months_baseline != null
                  ? `${g.months_baseline}mo → ${g.months_after_purchase ?? "—"}mo`
                  : "no baseline"}{" "}
                · {inr(g.remaining)} remaining
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- Inline agent trace (within decision card) ---- */
function AgentTraceInline({ activity }: { activity: AgentAnswer["activity"] }) {
  return (
    <div>
      <p className="mb-3 flex items-center gap-1.5 fp-label-card" style={{ color: "var(--color-fp-sky)" }}>
        <BrainCircuit className="size-3" /> AGENT TRACE
      </p>
      <ol className="space-y-1.5">
        {activity.map((a, i) => (
          <li key={i} className="flex items-center gap-2 text-xs">
            <span
              className="grid size-5 place-items-center rounded-full"
              style={{ background: "var(--color-fp-surface-raised)" }}
            >
              <span className="text-[10px] font-bold" style={{ color: "var(--color-fp-sky)" }}>{i + 1}</span>
            </span>
            <span className="text-white">{a.step}</span>
            <span className="ml-auto truncate max-w-[40%] text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
              {a.tool}
            </span>
            {a.latency_ms > 0 && (
              <span className="shrink-0 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
                {a.latency_ms}ms
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
