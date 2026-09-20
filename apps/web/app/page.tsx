"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Send, Scale, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  approveAction, askAgent, createGuardianDraft, fetchActions, fetchBudget,
  fetchGoals, fetchGuardian, fetchGuardianSummary, fetchMonthly, fetchRecurring,
  fetchRuns, rejectAction,
  type ActionDraft, type AgentAnswer, type AgentRun,
  type BudgetStatus, type Goal, type GuardianDetectResponse,
  type GuardianSummaryResponse, type MonthlyAnalytics, type RecurringAnalysis,
} from "@/lib/api";

/* ---- Components ---- */
import { FpHeader } from "@/components/fp-header";
import { DegradedStateBanner } from "@/components/fp-degraded-banner";
import { FpHero } from "@/components/fp-hero";
import { FpLoadingSequence } from "@/components/fp-loading-sequence";
import { DecisionVerdictCard } from "@/components/fp-decision-verdict";
import { AgentMessageInline } from "@/components/fp-agent-message-inline";
import { SubscriptionGuardian } from "@/components/fp-subscription-guardian";
import { ActionDrafts } from "@/components/fp-action-drafts";
import { AgentActivity } from "@/components/fp-agent-activity";
import { WhatIfLab } from "@/components/fp-what-if-lab";
import { SecondaryRail } from "@/components/fp-secondary-rail";

/* ---- Chat message type ---- */
interface Msg {
  role: "user" | "agent";
  text: string;
  agent?: AgentAnswer;
  error?: string;
}

const QUESTION_CHIPS = [
  "Where did I spend the most this month?",
  "What changed compared with last month?",
  "Can I afford a 60,000 rupee laptop?",
  "How much am I committed to?",
  "Am I on track for my emergency fund?",
  "What happens if my rent increases by ₹2,000?",
];

export default function Home() {
  /* ---- Data state ---- */
  const [monthly, setMonthly] = useState<MonthlyAnalytics | null>(null);
  const [recurring, setRecurring] = useState<RecurringAnalysis | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [actions, setActions] = useState<ActionDraft[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [guardian, setGuardian] = useState<GuardianDetectResponse | null>(null);
  const [guardianSummary, setGuardianSummary] = useState<GuardianSummaryResponse | null>(null);

  /* ---- UI state ---- */
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [draftMerchant, setDraftMerchant] = useState<string | null>(null);

  /* ---- Data loading ---- */
  const load = useCallback(async () => {
    try {
      const [m, rc, g, b, a, gd, gs] = await Promise.all([
        fetchMonthly(), fetchRecurring(), fetchGoals(), fetchBudget(), fetchActions(),
        fetchGuardian(), fetchGuardianSummary(),
      ]);
      setMonthly(m); setRecurring(rc);
      setGoals(g.goals); setBudget(b); setActions(a.actions);
      setGuardian(gd); setGuardianSummary(gs);
      setApiUp(true);
    } catch {
      setApiUp(false);
    }
  }, []);

  const loadRuns = useCallback(async () => {
    try { setRuns((await fetchRuns()).runs); } catch { /* api down */ }
  }, []);

  useEffect(() => {
    load();
    loadRuns();
    const t = setInterval(() => { load(); loadRuns(); }, 30000);
    return () => clearInterval(t);
  }, [load, loadRuns]);

  /* ---- Agent interaction ---- */
  const ask = useCallback(async (question: string) => {
    const q = question.trim();
    if (!q || thinking) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setThinking(true);
    try {
      const ans = await askAgent(q);
      setMessages((m) => [...m, { role: "agent", text: ans.answer, agent: ans }]);
      load(); loadRuns();
    } catch (e) {
      const msg = String(e);
      const friendly = msg.includes("Failed to fetch") || msg.includes("NetworkError")
        ? "Could not reach the FinPilot decision engine. Please check your connection."
        : `Sorry, something went wrong. ${msg.includes("Error") ? "" : msg}`;
      setMessages((m) => [...m, { role: "agent", text: friendly, error: msg }]);
    } finally {
      setThinking(false);
    }
  }, [thinking, load, loadRuns]);

  /* ---- Action handlers ---- */
  const onApprove = useCallback(async (id: string) => {
    await approveAction(id);
    setActions((await fetchActions()).actions);
  }, []);

  const onReject = useCallback(async (id: string) => {
    await rejectAction(id);
    setActions((await fetchActions()).actions);
  }, []);

  const onCreateGuardianDraft = useCallback(async (merchant: string) => {
    setDraftMerchant(merchant);
    try {
      await createGuardianDraft(merchant);
      setActions((await fetchActions()).actions);
    } finally {
      setDraftMerchant(null);
    }
  }, []);

  /* ---- Derived state ---- */
  const lastDecision = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].agent?.decision) return messages[i].agent;
    }
    return null;
  }, [messages]);

  const nonDecisionMessages = useMemo(
    () => messages.filter((m) => m.role === "user" || !m.agent?.decision),
    [messages],
  );

  return (
    <main className="min-h-screen" style={{ background: "var(--color-fp-bg)", color: "var(--color-fp-text)" }}>
      {/* Header */}
      <FpHeader apiUp={apiUp} />

      {/* API-down banner */}
      <DegradedStateBanner apiUp={apiUp === true} onRetry={load} />

      {/* Hero: "Can I afford this?" */}
      <FpHero onAsk={ask} thinking={thinking} />

      {/* Decision Result (dominant element) */}
      {lastDecision && <DecisionVerdictCard agent={lastDecision} />}

      {/* Subscription Guardian */}
      <SubscriptionGuardian
        guardian={guardian}
        summary={guardianSummary}
        actions={actions}
        onApprove={onApprove}
        onReject={onReject}
        onCreateDraft={onCreateGuardianDraft}
        draftMerchant={draftMerchant}
      />

      {/* Loading sequence */}
      {thinking && !lastDecision && (
        <div className="mx-auto max-w-7xl px-5 pt-4">
          <FpLoadingSequence active={thinking} />
        </div>
      )}

      {/* ================================================================
          MAIN CONTENT: Primary column + Secondary rail (desktop)
          Mobile: full vertical stack
          ================================================================ */}
      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">

        {/* Primary column */}
        <div className="space-y-5">
          {/* Inline copilot */}
          <div
            className="rounded-xl p-4"
            style={{ background: "var(--color-fp-surface)", border: "1px solid var(--color-fp-border)" }}
          >
            <div className="flex items-center gap-2 mb-3">
              <Bot className="size-3.5" style={{ color: "var(--color-fp-green)" }} />
              <p className="fp-label-card" style={{ color: "var(--color-fp-text-muted)" }}>
                CONTINUE THE CONVERSATION
              </p>
            </div>

            <div className="space-y-2.5">
              {nonDecisionMessages.length === 0 && !thinking && (
                <p className="rounded-lg p-3 text-xs" style={{
                  background: "var(--color-fp-surface-raised)",
                  border: "1px solid var(--color-fp-border)",
                  color: "var(--color-fp-text-dim)",
                }}>
                  Ask FinPilot anything about your money. Every answer is grounded in your
                  transactions — never invented.
                </p>
              )}
              {nonDecisionMessages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className="max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
                    style={{
                      background: m.role === "user" ? "var(--color-fp-green-dim)" : "var(--color-fp-surface-raised)",
                      border: `1px solid ${m.role === "user" ? "var(--color-fp-green-ring)" : "var(--color-fp-border)"}`,
                      color: "var(--color-fp-text)",
                    }}
                  >
                    <p>{m.text}</p>
                    {m.error && <p className="mt-1 text-xs" style={{ color: "var(--color-fp-rose)" }}>{m.error}</p>}
                    {m.agent && <AgentMessageInline agent={m.agent} />}
                  </div>
                </div>
              ))}
              {thinking && (
                <div className="flex items-center gap-2 text-xs" style={{ color: "var(--color-fp-text-muted)" }}>
                  <Loader2 className="size-3.5 animate-spin" style={{ color: "var(--color-fp-green)" }} />
                  <span>Analyzing your financial data…</span>
                </div>
              )}
            </div>

            {/* Quick question chips */}
            <div className="mt-3 flex flex-wrap gap-1.5">
              {QUESTION_CHIPS.map((c) => (
                <button
                  key={c}
                  onClick={() => ask(c)}
                  disabled={thinking}
                  className="rounded-full px-2.5 py-1 text-[11px] transition-all hover:scale-[1.02]"
                  style={{
                    background: "var(--color-fp-surface-raised)",
                    border: "1px solid var(--color-fp-border)",
                    color: "var(--color-fp-text-muted)",
                  }}
                >
                  {c}
                </button>
              ))}
            </div>

            {/* Ask input */}
            <form
              className="mt-3 flex items-center gap-2"
              onSubmit={(e) => { e.preventDefault(); ask(input); }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask FinPilot anything about your money…"
                className="h-10 flex-1 rounded-xl px-3 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[var(--color-fp-green)]/40"
                style={{
                  background: "var(--color-fp-bg)",
                  border: "1px solid var(--color-fp-border)",
                }}
              />
              <Button
                type="submit"
                disabled={thinking || !input.trim()}
                className="h-10 gap-1.5"
                style={{
                  background: thinking ? "var(--color-fp-surface-raised)" : "var(--color-fp-green)",
                  color: thinking ? "var(--color-fp-text-muted)" : "var(--color-fp-bg)",
                  border: "1px solid var(--color-fp-border)",
                }}
              >
                {thinking ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />}
                Ask
              </Button>
            </form>
          </div>

          {/* What-If Lab */}
          <WhatIfLab recurring={recurring} />

          {/* Action Drafts */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <p className="fp-label-card" style={{ color: "var(--color-fp-text-muted)" }}>ACTION DRAFTS</p>
            </div>
            <ActionDrafts actions={actions} onApprove={onApprove} onReject={onReject} />
          </div>

          {/* Agent Activity / Decision History */}
          <AgentActivity runs={runs} />
        </div>

        {/* Secondary rail — visually lighter, smaller, no competing shadows */}
        <div className="space-y-4">
          <SecondaryRail monthly={monthly} recurring={recurring} budget={budget} goals={goals} />
        </div>
      </div>

      {/* Sticky mobile ask bar */}
      <div className="fp-sticky-ask lg:hidden">
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => { e.preventDefault(); ask(input); }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask FinPilot…"
            className="h-10 flex-1 rounded-xl px-3 text-sm text-white placeholder:text-zinc-500 focus:outline-none"
            style={{
              background: "var(--color-fp-surface)",
              border: "1px solid var(--color-fp-border)",
            }}
          />
          <Button
            type="submit"
            disabled={thinking || !input.trim()}
            className="h-10 shrink-0 gap-1.5"
            style={{
              background: thinking ? "var(--color-fp-surface-raised)" : "var(--color-fp-green)",
              color: thinking ? "var(--color-fp-text-muted)" : "var(--color-fp-bg)",
              border: "1px solid var(--color-fp-border)",
            }}
          >
            {thinking ? <Loader2 className="size-3.5 animate-spin" /> : <Scale className="size-3.5" />}
            Ask
          </Button>
        </form>
      </div>

      {/* Footer */}
      <footer
        className="mx-auto max-w-7xl px-5 pb-8 pt-4 text-center text-[11px]"
        style={{ color: "var(--color-fp-text-dim)" }}
      >
        FinPilot · decision-support only · informational analysis, never financial advice
      </footer>
    </main>
  );
}
