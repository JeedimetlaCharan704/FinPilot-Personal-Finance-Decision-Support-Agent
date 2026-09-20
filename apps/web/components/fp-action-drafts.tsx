"use client";

import { useState, useMemo } from "react";
import { CheckCircle2, XCircle, ChevronDown, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { type ActionDraft } from "@/lib/api";

interface ActionDraftsProps {
  actions: ActionDraft[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

const STATUS_GROUPS = [
  { key: "draft", label: "Pending Review", color: "var(--color-fp-amber)", bg: "var(--color-fp-amber-dim)" },
  { key: "approved", label: "Approved", color: "var(--color-fp-green)", bg: "var(--color-fp-green-dim)" },
  { key: "rejected", label: "Rejected", color: "var(--color-fp-rose)", bg: "var(--color-fp-rose-dim)" },
] as const;

export function ActionDrafts({ actions, onApprove, onReject }: ActionDraftsProps) {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ draft: true });

  const grouped = useMemo(() => {
    const map: Record<string, ActionDraft[]> = { draft: [], approved: [], rejected: [], executed: [] };
    const seen = new Set<string>();
    for (const a of actions) {
      const key = a.title.trim().toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      const group = a.status === "executed" ? "approved" : a.status;
      if (map[group]) map[group].push(a);
    }
    return map;
  }, [actions]);

  const toggle = (key: string) => setOpenGroups((o) => ({ ...o, [key]: !o[key] }));

  if (actions.length === 0) {
    return (
      <div className="rounded-xl p-4" style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}>
        <div className="flex items-center gap-2">
          <Clock className="size-4" style={{ color: "var(--color-fp-text-dim)" }} />
          <p className="text-xs" style={{ color: "var(--color-fp-text-dim)" }}>
            No draft actions yet. Ask FinPilot about your goals or spending to generate suggestions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {STATUS_GROUPS.map((group) => {
        const items = grouped[group.key] ?? [];
        if (items.length === 0) return null;
        const isOpen = openGroups[group.key] ?? false;

        return (
          <div
            key={group.key}
            className="rounded-xl overflow-hidden"
            style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}
          >
            <button
              onClick={() => toggle(group.key)}
              className="flex w-full items-center justify-between px-4 py-2.5 text-left transition-colors hover:bg-white/[0.02]"
            >
              <div className="flex items-center gap-2">
                <span className="inline-block size-2 rounded-full" style={{ background: group.color }} />
                <span className="text-xs font-medium text-white">{group.label}</span>
                <span
                  className="rounded-full px-1.5 py-0.5 text-[10px]"
                  style={{ background: group.bg, color: group.color }}
                >
                  {items.length}
                </span>
              </div>
              <ChevronDown
                className={cn("size-3.5 transition-transform", isOpen ? "rotate-180" : "")}
                style={{ color: "var(--color-fp-text-dim)" }}
              />
            </button>
            {isOpen && (
              <div className="border-t space-y-1.5 p-2" style={{ borderColor: "var(--color-fp-border)" }}>
                {items.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-white/[0.02]"
                    style={{ background: "var(--color-fp-surface-raised)" }}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white">{a.title}</p>
                      {a.description && (
                        <p className="mt-0.5 truncate text-xs" style={{ color: "var(--color-fp-text-muted)" }}>
                          {a.description}
                        </p>
                      )}
                    </div>
                    {a.status === "draft" && (
                      <div className="flex shrink-0 gap-1.5">
                        <Button
                          size="sm"
                          onClick={() => onApprove(a.id)}
                          className="gap-1 text-xs"
                          style={{ background: "var(--color-fp-green)", color: "var(--color-fp-bg)" }}
                        >
                          <CheckCircle2 className="size-3" /> Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onReject(a.id)}
                          className="gap-1 text-xs"
                          style={{ color: "var(--color-fp-rose)" }}
                        >
                          <XCircle className="size-3" /> Reject
                        </Button>
                      </div>
                    )}
                    {a.status !== "draft" && (
                      <Badge
                        variant="outline"
                        className="text-[10px]"
                        style={{
                          color: group.color,
                          borderColor: group.color + "40",
                        }}
                      >
                        {a.status}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
