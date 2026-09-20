"use client";

import { BrainCircuit } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function FpHeader({ apiUp }: { apiUp: boolean | null }) {
  return (
    <header
      className="sticky top-0 z-30 border-b border-white/[0.06] backdrop-blur-xl"
      style={{ background: "rgba(10,11,13,0.85)" }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div
            className="grid size-9 place-items-center rounded-xl"
            style={{
              background: "var(--color-fp-green-dim)",
              border: "1px solid var(--color-fp-green-ring)",
            }}
          >
            <BrainCircuit className="size-5" style={{ color: "var(--color-fp-green)" }} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              FinPilot
            </h1>
            <p className="text-[11px]" style={{ color: "var(--color-fp-text-dim)" }}>
              Personal Finance Decision Support Agent
            </p>
          </div>
        </div>

        {/* Status pills */}
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="gap-1.5 border-white/[0.08] bg-white/[0.03] text-[11px]"
          >
            <span
              className={`inline-block size-1.5 rounded-full ${
                apiUp === null
                  ? "bg-gray-500"
                  : apiUp
                    ? "bg-emerald-400"
                    : "bg-rose-400"
              }`}
            />
            <span style={{ color: apiUp === false ? "var(--color-fp-rose)" : "var(--color-fp-text-muted)" }}>
              {apiUp === null ? "connecting" : apiUp ? "engine online" : "engine offline"}
            </span>
          </Badge>
          <Badge
            variant="outline"
            className="hidden border-white/[0.08] bg-white/[0.03] text-[11px] sm:inline-flex"
          >
            <span style={{ color: "var(--color-fp-text-dim)" }}>decision-support</span>
          </Badge>
        </div>
      </div>
    </header>
  );
}
