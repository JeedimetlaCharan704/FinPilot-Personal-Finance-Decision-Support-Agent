"use client";

import { Badge } from "@/components/ui/badge";
import { CheckCircle2 } from "lucide-react";
import { type AgentAnswer } from "@/lib/api";

const VERDICT_META: Record<string, { color: string; label: string }> = {
  AFFORDABLE: { color: "var(--color-fp-green)", label: "AFFORDABLE" },
  TIGHT: { color: "var(--color-fp-amber)", label: "TIGHT" },
  NOT_YET: { color: "var(--color-fp-rose)", label: "NOT YET" },
  INSUFFICIENT_DATA: { color: "var(--color-fp-text-muted)", label: "INSUFFICIENT DATA" },
};

export function AgentMessageInline({ agent }: { agent: AgentAnswer }) {
  return (
    <div className="mt-3 space-y-2 border-t pt-3" style={{ borderColor: "var(--color-fp-border)" }}>
      {/* Badges */}
      <div className="flex flex-wrap gap-1.5">
        <Badge variant="outline" className="border-white/[0.08] text-[10px]" style={{ color: "var(--color-fp-text-muted)" }}>
          {agent.intent}
        </Badge>
        <Badge variant="outline" className="border-white/[0.08] text-[10px]" style={{
          color: agent.mode === "llm" ? "var(--color-fp-green)" : "var(--color-fp-text-dim)",
        }}>
          {agent.mode === "llm" ? `AI · ${agent.model}` : "deterministic"}
        </Badge>
        {agent.decision && (
          <Badge variant="outline" className="gap-1 text-[10px]" style={{
            color: VERDICT_META[agent.decision.verdict]?.color ?? "var(--color-fp-text-muted)",
            borderColor: (VERDICT_META[agent.decision.verdict]?.color ?? "var(--color-fp-border)") + "40",
          }}>
            <span className="inline-block size-1.5 rounded-full" style={{ background: VERDICT_META[agent.decision.verdict]?.color }} />
            {VERDICT_META[agent.decision.verdict]?.label ?? agent.decision.verdict}
          </Badge>
        )}
      </div>

      {/* Evidence */}
      {agent.evidence.length > 0 && (
        <details className="rounded-lg p-2" style={{ background: "var(--color-fp-surface-raised)" }}>
          <summary className="cursor-pointer text-[11px] font-medium text-white">Evidence</summary>
          <ul className="mt-1 space-y-1">
            {agent.evidence.map((e, i) => (
              <li key={i} className="flex gap-1.5 text-[10px]" style={{ color: "var(--color-fp-text-muted)" }}>
                <CheckCircle2 className="mt-0.5 size-2.5 shrink-0" style={{ color: "var(--color-fp-green)" }} />
                <span>
                  <span className="text-white">{e.label}:</span> {e.value}
                  {e.detail ? <span style={{ color: "var(--color-fp-text-dim)" }}> · {e.detail}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Activity trace */}
      {agent.activity.length > 0 && (
        <details className="rounded-lg p-2" style={{ background: "var(--color-fp-surface-raised)" }}>
          <summary className="cursor-pointer text-[11px] font-medium text-white">
            Activity · {agent.activity.length} steps
          </summary>
          <ol className="mt-1 space-y-0.5">
            {agent.activity.map((a, i) => (
              <li key={i} className="flex items-center justify-between gap-2 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
                <span className="truncate">{i + 1}. {a.tool} → {a.status}</span>
                {a.latency_ms > 0 && <span className="shrink-0">{a.latency_ms}ms</span>}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}
