"use client";

import { Shield, ArrowUpRight, Zap, Clock, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { inr, type GuardianDetectResponse, type GuardianSummaryResponse, type ActionDraft } from "@/lib/api";

interface SubscriptionGuardianProps {
  guardian: GuardianDetectResponse | null;
  summary: GuardianSummaryResponse | null;
  actions: ActionDraft[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onCreateDraft: (merchant: string) => void;
  draftMerchant: string | null;
}

export function SubscriptionGuardian({
  guardian, summary, actions, onApprove, onReject, onCreateDraft, draftMerchant,
}: SubscriptionGuardianProps) {
  if (!guardian) return null;

  const changed = guardian.items.filter((i) => i.signal === "PRICE_INCREASE");
  const draftFor = (merchant: string) =>
    actions.find((a) => a.title.includes(merchant) && a.title.includes("Review"));

  return (
    <section className="mx-auto max-w-7xl px-5 pt-4">
      <div
        className="rounded-2xl p-5 sm:p-6"
        style={{
          background: "var(--color-fp-surface)",
          border: "1px solid var(--color-fp-border)",
        }}
      >
        {/* Header */}
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="border-white/[0.08] bg-white/[0.04]">
            <Shield className="mr-1 size-3" style={{ color: "var(--color-fp-amber)" }} />
            <span style={{ color: "var(--color-fp-text-muted)" }}>Subscription guardian</span>
          </Badge>
          <Badge variant="outline" className="border-white/[0.08] bg-white/[0.03]">
            <span style={{ color: "var(--color-fp-text-dim)" }}>
              finds recurring payments worth reviewing
            </span>
          </Badge>
          {summary && summary.changed_count > 0 && (
            <Badge
              variant="outline"
              className="border-white/[0.08]"
              style={{ background: "var(--color-fp-amber-dim)", color: "var(--color-fp-amber)" }}
            >
              {summary.changed_count} changed
            </Badge>
          )}
        </div>

        <p className="mt-2 max-w-2xl text-sm" style={{ color: "var(--color-fp-text-muted)" }}>
          FinPilot watches your recurring payments for price changes and flags
          them for review. Every action is a draft — FinPilot will never cancel
          or contact anyone automatically.
        </p>

        {/* No changes */}
        {changed.length === 0 && (
          <div
            className="mt-4 rounded-xl p-4 text-sm"
            style={{ background: "var(--color-fp-surface-raised)", border: "1px solid var(--color-fp-border)" }}
          >
            <p style={{ color: "var(--color-fp-text-muted)" }}>
              No subscription price changes detected. Your recurring payments look stable.
            </p>
          </div>
        )}

        {/* Changed subscriptions */}
        {changed.map((item) => {
          const existing = draftFor(item.merchant);
          const isCreating = draftMerchant === item.merchant;

          return (
            <div key={item.merchant} className="mt-4 space-y-3">
              {/* Before/After card */}
              <div
                className="rounded-xl p-4"
                style={{ background: "var(--color-fp-surface-raised)", border: "1px solid var(--color-fp-border)" }}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div
                      className="grid size-10 place-items-center rounded-xl"
                      style={{ background: "var(--color-fp-amber-dim)", border: "1px solid var(--color-fp-amber-ring)" }}
                    >
                      <Zap className="size-5" style={{ color: "var(--color-fp-amber)" }} />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">{item.merchant}</h3>
                      <p className="text-xs" style={{ color: "var(--color-fp-text-dim)" }}>
                        {item.category || "Subscription"} · {item.frequency}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className="text-[10px]"
                    style={{
                      color: existing
                        ? existing.status === "approved" ? "var(--color-fp-green)" : "var(--color-fp-amber)"
                        : "var(--color-fp-rose)",
                      borderColor: existing
                        ? existing.status === "approved" ? "var(--color-fp-green-ring)" : "var(--color-fp-amber-ring)"
                        : "var(--color-fp-rose-ring)",
                    }}
                  >
                    {existing
                      ? existing.status === "approved" ? "Approved" : existing.status === "rejected" ? "Rejected" : "Draft ready"
                      : "Price increase detected"}
                  </Badge>
                </div>

                {/* Before → After */}
                <div className="mt-4 flex flex-wrap items-baseline gap-3">
                  <div className="rounded-lg px-3 py-2" style={{ background: "var(--color-fp-bg)" }}>
                    <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Was</p>
                    <p className="text-lg font-bold" style={{ color: "var(--color-fp-text-muted)" }}>{inr(item.previous_amount)}/mo</p>
                  </div>
                  <ArrowUpRight className="size-5" style={{ color: "var(--color-fp-amber)" }} />
                  <div className="rounded-lg px-3 py-2" style={{ background: "var(--color-fp-bg)" }}>
                    <p className="text-[10px]" style={{ color: "var(--color-fp-text-dim)" }}>Now</p>
                    <p className="text-lg font-bold text-white">{inr(item.current_amount)}/mo</p>
                  </div>
                  <div className="rounded-lg px-3 py-2" style={{ background: "var(--color-fp-amber-dim)" }}>
                    <p className="text-[10px]" style={{ color: "var(--color-fp-amber)" }}>Monthly increase</p>
                    <p className="text-lg font-bold" style={{ color: "var(--color-fp-amber)" }}>+{inr(item.increase_amount)}</p>
                  </div>
                  <div className="rounded-lg px-3 py-2" style={{ background: "var(--color-fp-rose-dim)" }}>
                    <p className="text-[10px]" style={{ color: "var(--color-fp-rose)" }}>Annual impact</p>
                    <p className="text-lg font-bold" style={{ color: "var(--color-fp-rose)" }}>+{inr(item.annual_increase)}/yr</p>
                  </div>
                </div>

                {/* Why flagged */}
                <div className="mt-3 rounded-lg p-3" style={{ background: "var(--color-fp-bg)" }}>
                  <p className="fp-label-secondary" style={{ color: "var(--color-fp-text-dim)" }}>Why flagged</p>
                  <ul className="mt-1.5 space-y-1 text-xs" style={{ color: "var(--color-fp-text-muted)" }}>
                    <li>
                      <strong className="text-white">{inr(item.previous_amount)}</strong> → <strong className="text-white">{inr(item.current_amount)}</strong>/month
                      ({item.increase_percent?.toFixed(1)}% increase)
                    </li>
                    <li>That&apos;s approximately <strong className="text-white">{inr(item.annual_increase)}</strong>/year more</li>
                    <li>Current annual cost: <strong className="text-white">{inr(item.annual_cost)}</strong></li>
                  </ul>
                </div>

                {item.evidence_refs?.length > 0 && (
                  <p className="mt-2 text-[11px]" style={{ color: "var(--color-fp-text-dim)" }}>
                    Evidence: {item.evidence_refs.slice(0, 4).join(", ")}
                    {item.evidence_refs.length > 4 && ` +${item.evidence_refs.length - 4} more`}
                  </p>
                )}
              </div>

              {/* Draft action flow */}
              {existing ? (
                <div className="flex items-center gap-3 rounded-xl px-4 py-3" style={{ background: "var(--color-fp-surface-raised)", border: "1px solid var(--color-fp-border)" }}>
                  {existing.status === "draft" && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => onApprove(existing.id)}
                        className="gap-1 text-xs"
                        style={{ background: "var(--color-fp-green)", color: "var(--color-fp-bg)" }}
                      >
                        <CheckCircle2 className="size-3" /> Approve review
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onReject(existing.id)}
                        className="gap-1 text-xs"
                        style={{ color: "var(--color-fp-rose)" }}
                      >
                        <XCircle className="size-3" /> Reject
                      </Button>
                    </>
                  )}
                  {existing.status !== "draft" && (
                    <p className="text-xs" style={{ color: "var(--color-fp-text-dim)" }}>
                      {existing.status === "approved" ? "You approved this review" : "You rejected this review"}
                    </p>
                  )}
                </div>
              ) : (
                <Button
                  size="sm"
                  disabled={isCreating}
                  onClick={() => onCreateDraft(item.merchant)}
                  className="gap-1.5 text-xs"
                  style={{ background: "var(--color-fp-amber)", color: "var(--color-fp-bg)" }}
                >
                  {isCreating ? <Loader2 className="size-3 animate-spin" /> : <Clock className="size-3" />}
                  {isCreating ? "Creating draft…" : "Review subscription"}
                </Button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}