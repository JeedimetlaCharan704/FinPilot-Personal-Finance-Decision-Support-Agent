"use client";

import { useState } from "react";
import { Gauge, Loader2, Scale } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const HERO_CHIPS = [
  "Can I afford a ₹65,000 laptop next month?",
  "Can I buy a 50000 phone next month?",
  "Can I spend ₹20k on a trip next month?",
  "Can I afford a ₹30,000 monitor?",
];

interface FpHeroProps {
  onAsk: (q: string) => void;
  thinking: boolean;
}

export function FpHero({ onAsk, thinking }: FpHeroProps) {
  const [heroInput, setHeroInput] = useState("");

  return (
    <section className="mx-auto max-w-7xl px-5 pt-8 pb-2 sm:pt-12">
      <div className="relative overflow-hidden rounded-2xl p-6 sm:p-8" style={{
        background: "linear-gradient(135deg, rgba(139,92,246,0.12) 0%, var(--color-fp-surface) 45%, var(--color-fp-bg) 100%)",
        border: "1px solid var(--color-fp-border)",
      }}>
        {/* Subtle accent glow */}
        <div
          className="pointer-events-none absolute -right-20 -top-20 size-60 rounded-full opacity-15 blur-3xl"
          style={{ background: "var(--color-fp-violet)" }}
        />

        <div className="relative">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="border-white/[0.08] bg-white/[0.04]">
              <Gauge className="mr-1 size-3" style={{ color: "var(--color-fp-violet)" }} />
              <span style={{ color: "var(--color-fp-text-muted)" }}>decision agent</span>
            </Badge>
            <Badge variant="outline" className="border-white/[0.08] bg-white/[0.03]">
              <span style={{ color: "var(--color-fp-text-dim)" }}>
                deterministic verdicts · AI explanations
              </span>
            </Badge>
          </div>

          <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl lg:text-5xl">
            <span className="text-white">Can I afford</span>{" "}
            <span style={{ color: "var(--color-fp-violet)" }}>this?</span>
          </h2>

          <p className="mt-3 max-w-2xl text-sm leading-relaxed" style={{ color: "var(--color-fp-text-muted)" }}>
            Your bank app tells you what you spent.{" "}
            <span className="text-white">FinPilot tells you what you can do.</span>{" "}
            Ask about a purchase, trip, subscription or any spending decision —
            you get a verdict, comparison scenarios and goal impact, grounded in
            your own transactions.
          </p>

          <form
            className="mt-5 flex flex-col gap-2 sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault();
              const q = heroInput.trim();
              if (!q || thinking) return;
              setHeroInput("");
              onAsk(q);
            }}
          >
            <input
              value={heroInput}
              onChange={(e) => setHeroInput(e.target.value)}
              placeholder="Can I afford a ₹65,000 laptop next month?"
              aria-label="Ask FinPilot about a purchase you are considering"
              className="h-12 flex-1 rounded-xl px-4 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#7c3aed]/40"
              style={{
                background: "#0b1017",
                border: "1px solid #293544",
              }}
            />
            <Button
              type="submit"
              disabled={thinking || !heroInput.trim()}
              className="h-12 px-6 sm:w-36"
              style={{
                background: thinking ? "var(--color-fp-surface-raised)" : "linear-gradient(135deg, #7c3aed, #9333ea)",
                color: thinking ? "var(--color-fp-text-muted)" : "white",
                border: "1px solid rgba(124,58,237,0.40)",
              }}
            >
              {thinking ? (
                <Loader2 className="mr-1.5 size-4 animate-spin" />
              ) : (
                <Scale className="mr-1.5 size-4" />
              )}
              {thinking ? "Analyzing…" : "Ask FinPilot"}
            </Button>
          </form>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {HERO_CHIPS.map((c) => (
              <button
                key={c}
                onClick={() => onAsk(c)}
                disabled={thinking}
                className="rounded-full px-3 py-1.5 text-[11px] transition-all hover:scale-[1.02]"
                style={{
                  background: "var(--color-fp-surface-raised)",
                  border: "1px solid #293544",
                  color: "var(--color-fp-text-muted)",
                }}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
