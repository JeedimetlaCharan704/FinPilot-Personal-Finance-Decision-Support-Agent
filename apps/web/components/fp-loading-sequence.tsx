"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

const LOADING_STAGES = [
  "Understanding your question…",
  "Checking your cash flow…",
  "Simulating the purchase…",
  "Checking goal impact…",
  "Preparing your decision…",
];

export function FpLoadingSequence({ active }: { active: boolean }) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!active) { setStage(0); return; }
    setStage(0);
    const timers = LOADING_STAGES.map((_, i) =>
      setTimeout(() => setStage(i), i * 1200),
    );
    return () => timers.forEach(clearTimeout);
  }, [active]);

  if (!active) return null;

  return (
    <div
      className="flex items-center gap-3 rounded-xl px-4 py-3"
      style={{
        background: "var(--color-fp-surface)",
        border: "1px solid var(--color-fp-border)",
      }}
    >
      <Loader2
        className="size-4 animate-spin"
        style={{ color: "var(--color-fp-green)" }}
      />
      <div className="flex-1">
        <p className="text-sm text-white">{LOADING_STAGES[stage]}</p>
        <div className="mt-2 flex gap-1">
          {LOADING_STAGES.map((_, i) => (
            <div
              key={i}
              className="h-0.5 flex-1 rounded-full transition-colors duration-300"
              style={{
                background:
                  i <= stage ? "var(--color-fp-green)" : "var(--color-fp-surface-overlay)",
              }}
            />
          ))}
        </div>
      </div>
      <span className="text-[11px]" style={{ color: "var(--color-fp-text-dim)" }}>
        {stage + 1}/{LOADING_STAGES.length}
      </span>
    </div>
  );
}
