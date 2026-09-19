"use client"

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type Health = { status: string; service: string };
type DbHealth = { status: string; service: string; database?: string; message?: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [db, setDb] = useState<DbHealth | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [h, d] = await Promise.all([
          fetch(`${API_BASE}/api/health`).then((r) => r.json()),
          fetch(`${API_BASE}/api/db/health`).then((r) => r.json()).catch(() => ({ status: "unreachable" })),
        ]);
        setHealth(h);
        setDb(d);
      } catch (e) {
        setError(String(e));
      }
    })();
  }, []);

  return (
    <main className="grid min-h-screen place-items-center bg-zinc-950 p-8 text-zinc-100">
      <div className="w-full max-w-md space-y-6">
        <header className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">FinPilot</h1>
          <p className="text-sm text-zinc-400">
            Your bank app tells you what you spent. FinPilot tells you what you can do.
          </p>
        </header>

        <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Backend</h2>
          {error ? (
            <p className="mt-2 text-sm text-red-400">Unable to reach API: {error}</p>
          ) : health ? (
            <p className="mt-2 text-sm">
              Status: <span className="text-emerald-400">{health.status}</span>
              {"  "}service: <code className="text-zinc-300">{health.service}</code>
            </p>
          ) : (
            <p className="mt-2 text-sm text-zinc-400">Checking API…</p>
          )}
        </section>

        <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Database</h2>
          {db ? (
            <p className="mt-2 text-sm">
              Database: <span className={db.database === "connected" ? "text-emerald-400" : "text-amber-400"}>{db.database ?? db.status}</span>
              {db.message ? <span className="mt-1 block text-xs text-zinc-500">{db.message}</span> : null}
            </p>
          ) : (
            <p className="mt-2 text-sm text-zinc-400">Checking database…</p>
          )}
        </section>
      </div>
    </main>
  );
}