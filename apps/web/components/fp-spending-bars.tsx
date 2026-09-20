"use client";

import { inr, type CategoryRow } from "@/lib/api";

interface SpendingBarsProps {
  categories: CategoryRow[];
}

export function SpendingBars({ categories }: SpendingBarsProps) {
  if (categories.length === 0) return null;
  const sorted = [...categories].sort((a, b) => b.amount - a.amount);
  const max = sorted[0]?.amount ?? 1;

  return (
    <div className="space-y-2">
      {sorted.map((c) => (
        <div key={c.category} className="flex items-center gap-2.5 text-sm">
          <span
            className="w-28 shrink-0 truncate text-xs"
            style={{ color: "var(--color-fp-text-muted)" }}
          >
            {c.category}
          </span>
          <div className="fp-progress-track flex-1">
            <div
              className="fp-progress-fill"
              style={{
                width: `${(c.amount / max) * 100}%`,
                background: "var(--color-fp-violet)",
              }}
            />
          </div>
          <span className="w-16 shrink-0 text-right text-[11px] font-medium text-white">
            {inr(c.amount)}
          </span>
          <span className="w-5 shrink-0 text-right text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>
            {c.transaction_count}×
          </span>
        </div>
      ))}
    </div>
  );
}
