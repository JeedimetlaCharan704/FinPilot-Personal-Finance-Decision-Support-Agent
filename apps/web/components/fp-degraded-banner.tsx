"use client";

import { AlertTriangle, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api";
import { useState } from "react";

interface DegradedStateBannerProps {
  apiUp: boolean;
  onRetry?: () => void;
}

export function DegradedStateBanner({ apiUp, onRetry }: DegradedStateBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (apiUp || dismissed) return null;

  return (
    <div className="mx-auto max-w-7xl px-5 pt-4">
      <div
        className="flex items-start gap-3 rounded-xl px-4 py-3"
        style={{
          background: "rgba(251,113,133,0.06)",
          border: "1px solid rgba(251,113,133,0.20)",
        }}
      >
        <AlertTriangle className="mt-0.5 size-4 shrink-0" style={{ color: "var(--color-fp-rose)" }} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white">
            Decision engine unreachable
          </p>
          <p className="mt-0.5 text-xs" style={{ color: "var(--color-fp-text-muted)" }}>
            FinPilot cannot reach the backend at{" "}
            <code className="rounded bg-white/[0.05] px-1 py-0.5 font-mono text-[11px]">
              {API_BASE}
            </code>
            . Check that the backend is running and CORS is configured.
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={onRetry}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className="size-3" />
            Retry
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setDismissed(true)}
            className="size-6"
          >
            <X className="size-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
