import { useEffect, useState } from 'react';
import { loadWorkspace, subscribe } from '../lib/storage';
import type { Workspace } from '../types';

export function App() {
  const [ws, setWs] = useState<Workspace | null>(null);

  useEffect(() => {
    loadWorkspace().then(setWs);
    return subscribe(setWs);
  }, []);

  return (
    <main className="mx-auto max-w-4xl p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Triska</h1>
        <p className="text-slate-400 text-sm">
          Editor — Phase 0 scaffold. Authoring UI, recorder, and replay land
          in later phases (see <code>PLAN.md</code>).
        </p>
      </header>
      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h2 className="mb-2 font-semibold">Workspace</h2>
        {ws ? (
          <pre className="overflow-auto text-xs text-slate-300">
            {JSON.stringify(ws, null, 2)}
          </pre>
        ) : (
          <p className="text-slate-500 text-sm">Loading…</p>
        )}
      </section>
    </main>
  );
}
