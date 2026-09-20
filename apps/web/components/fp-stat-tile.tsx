"use client";

import { cn } from "@/lib/utils";

interface StatTileProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
  className?: string;
}

export function StatTile({ label, value, sub, color = "var(--color-fp-text)", className }: StatTileProps) {
  return (
    <div
      className={cn(
        "rounded-xl px-3 py-2.5",
        className,
      )}
      style={{
        background: "var(--color-fp-surface)",
        border: "1px solid var(--color-fp-border)",
      }}
    >
      <p className="fp-label-secondary">{label}</p>
      <p className="fp-number-secondary mt-0.5" style={{ color }}>{value}</p>
      {sub && (
        <p className="mt-0.5 text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>{sub}</p>
      )}
    </div>
  );
}
