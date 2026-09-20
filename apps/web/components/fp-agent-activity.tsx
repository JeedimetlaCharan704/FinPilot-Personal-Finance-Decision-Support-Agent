"use client";

import { useState } from "react";
import { Activity, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { type AgentRun } from "@/lib/api";

interface AgentActivityProps {
  runs: AgentRun[];
}

export function AgentActivity({ runs }: AgentActivityProps) {
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  if (runs.length === 0) {
    return (
      <div className="rounded-xl p-4" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
        <div className="flex items-center gap-2">
          <Activity className="size-3.5" style={{ color: "var(--color-fp-sky)" }} />
          <p className="text-xs" style={{ color: "var(--color-fp-text-dim)" }}>
            No agent runs yet. Ask FinPilot a question to see activity here.
          </p>
        </div>
      </div>
    );
  }

  const visibleRuns = showAll ? runs : runs.slice(0, 5);

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
      <div className="flex items-center gap-2 px-4 py-2.5">
        <Activity className="size-3.5" style={{ color: "var(--color-fp-sky)" }} />
        <p className="fp-label-card">Decision history</p>
        <Badge variant="outline" className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
          {runs.length}
        </Badge>
      </div>

      <div className="space-y-1 border-t p-2" style={{ borderColor: "var(--color-fp-border)" }}>
        {visibleRuns.map((r) => {
          let intent = "";
          let answer = r.final_response ?? "";
          try {
            const parsed = JSON.parse(r.final_response ?? "{}");
            if (parsed && typeof parsed === "object") {
              intent = parsed.intent ?? "";
              answer = parsed.answer ?? r.final_response ?? "";
            }
          } catch { /* plain string */ }

          const isOpen = expandedRun === r.id;

          return (
            <div key={r.id}>
              <button
                onClick={() => setExpandedRun(isOpen ? null : r.id)}
                className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left transition-colors hover:bg-white/[0.02]"
              >
                <div className="min-w-0">
                  <p
                    className="text-[10px] font-medium"
                    style={{
                      color: r.status === "completed" ? "var(--color-fp-green)"
                        : r.status === "failed" ? "var(--color-fp-rose)"
                        : "var(--color-fp-amber)",
                    }}
                  >
                    {r.status}
                  </p>
                  <p className="truncate text-xs text-white">{r.question || intent || "agent run"}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
                    {new Date(r.created_at).toLocaleDateString()}
                  </p>
                  <ChevronDown
                    className={cn("size-3 ml-auto transition-transform", isOpen ? "rotate-180" : "")}
                    style={{ color: "var(--color-fp-text-dim)" }}
                  />
                </div>
              </button>
              {isOpen && (
                <div className="border-t px-3 py-2.5" style={{ borderColor: "var(--color-fp-border)" }}>
                  <p className="text-xs leading-relaxed" style={{ color: "var(--color-fp-text-muted)" }}>{answer}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {runs.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="flex w-full items-center justify-center border-t px-4 py-2 text-[11px] transition-colors hover:bg-white/[0.02]"
          style={{ borderColor: "var(--color-fp-border)", color: "var(--color-fp-text-dim)" }}
        >
          {showAll ? "Show less" : `Show ${runs.length - 5} more`}
        </button>
      )}
    </div>
  );
}
