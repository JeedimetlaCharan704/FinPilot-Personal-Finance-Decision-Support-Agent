"use client";

import { useState } from "react";
import {
  BrainCircuit, ListChecks, Gauge, FlaskConical, AlertTriangle,
  Sparkles, CheckCircle2, ChevronDown, Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { type ActivityStep } from "@/lib/api";

interface AgentTraceStepperProps {
  activity: ActivityStep[];
}

function mapStep(a: ActivityStep) {
  const llm = a.tool.includes("llm:");
  if (a.step === "Intent detected")
    return { icon: <BrainCircuit className="size-3" />, label: "Understand intent", detail: a.tool, color: llm ? "var(--color-fp-green)" : "var(--color-fp-text-muted)" };
  if (a.step === "Tool plan built")
    return { icon: <ListChecks className="size-3" />, label: "Build tool plan", detail: a.tool, color: llm ? "var(--color-fp-green)" : "var(--color-fp-text-muted)" };
  if (a.step === "Tool executed" && a.tool === "evaluate_affordability")
    return { icon: <Gauge className="size-3" />, label: "Deterministic simulation", detail: a.detail, color: "var(--color-fp-violet)" };
  if (a.step === "Tool executed")
    return { icon: <FlaskConical className="size-3" />, label: "Run verified financial tools", detail: a.tool, color: "var(--color-fp-text-muted)" };
  if (a.step === "Tool failed")
    return { icon: <AlertTriangle className="size-3" />, label: `Tool failed — ${a.tool}`, detail: a.detail, color: "var(--color-fp-rose)" };
  if (a.step === "Response generated")
    return { icon: <Sparkles className="size-3" />, label: "Grounded AI explanation", detail: a.tool, color: llm ? "var(--color-fp-green)" : "var(--color-fp-text-muted)" };
  return { icon: <Activity className="size-3" />, label: a.step, detail: a.tool, color: "var(--color-fp-text-muted)" };
}

export function AgentTraceStepper({ activity }: AgentTraceStepperProps) {
  const [expanded, setExpanded] = useState(false);

  if (activity.length === 0) return null;

  const nodes = activity.map(mapStep);

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: "var(--color-fp-surface)",
        border: "1px solid var(--color-fp-border)",
      }}
    >
      {/* Collapsed summary */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          <Activity className="size-4" style={{ color: "var(--color-fp-sky)" }} />
          <span className="text-xs font-medium text-white">
            How FinPilot reached this decision
          </span>
          <span
            className="rounded-full px-2 py-0.5 text-[10px]"
            style={{ background: "var(--color-fp-sky-dim)", color: "var(--color-fp-sky)" }}
          >
            {activity.length} steps
          </span>
        </div>
        <ChevronDown
          className={cn(
            "size-4 transition-transform",
            expanded ? "rotate-180" : "",
          )}
          style={{ color: "var(--color-fp-text-dim)" }}
        />
      </button>

      {/* Expanded stepper */}
      {expanded && (
        <div className="border-t px-4 py-4" style={{ borderColor: "var(--color-fp-border)" }}>
          <ol className="relative ml-2 space-y-3">
            {/* Connector line */}
            <div className="fp-stepper-line" />

            {/* Starting node */}
            <li className="relative flex items-start gap-3">
              <span
                className="relative z-10 grid size-6 place-items-center rounded-full"
                style={{ background: "var(--color-fp-surface-raised)", border: "1px solid var(--color-fp-border)" }}
              >
                <span className="text-[10px] font-bold" style={{ color: "var(--color-fp-text-muted)" }}>0</span>
              </span>
              <div className="pt-0.5">
                <p className="text-xs font-medium text-white">Your question</p>
                <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>natural language input</p>
              </div>
            </li>

            {/* Step nodes */}
            {nodes.map((n, i) => (
              <li key={i} className="relative flex items-start gap-3">
                <span
                  className="relative z-10 grid size-6 place-items-center rounded-full"
                  style={{
                    background: n.color === "var(--color-fp-rose)" ? "var(--color-fp-rose-dim)" :
                      n.color === "var(--color-fp-violet)" ? "var(--color-fp-violet-dim)" :
                      n.color === "var(--color-fp-green)" ? "var(--color-fp-green-dim)" :
                      "var(--color-fp-surface-raised)",
                    border: `1px solid ${n.color === "var(--color-fp-text-muted)" ? "var(--color-fp-border)" : n.color + "40"}`,
                    color: n.color,
                  }}
                >
                  {n.icon}
                </span>
                <div className="flex-1 pt-0.5">
                  <p className="text-xs font-medium" style={{ color: n.color }}>{n.label}</p>
                  <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>{n.detail}</p>
                </div>
                {activity[i] && activity[i].latency_ms > 0 && (
                  <span className="shrink-0 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
                    {activity[i].latency_ms}ms
                  </span>
                )}
              </li>
            ))}

            {/* End node */}
            <li className="relative flex items-start gap-3">
              <span
                className="relative z-10 grid size-6 place-items-center rounded-full"
                style={{ background: "var(--color-fp-green-dim)", border: "1px solid var(--color-fp-green-ring)" }}
              >
                <CheckCircle2 className="size-3" style={{ color: "var(--color-fp-green)" }} />
              </span>
              <div className="pt-0.5">
                <p className="text-xs font-medium" style={{ color: "var(--color-fp-green)" }}>
                  Verified decision delivered
                </p>
                <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
                  grounded in deterministic evidence
                </p>
              </div>
            </li>
          </ol>
        </div>
      )}
    </div>
  );
}
