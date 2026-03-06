export function DashboardShell() {
  return (
    <section className="bg-gradient-to-br from-slate-950 via-purple-900 to-slate-800 px-8 py-10 text-white">
      <div className="rounded-2xl border border-purple-400/40 p-8 shadow-2xl backdrop-blur">
        <small className="mb-3 block uppercase tracking-[0.3em] text-purple-200">Live pulse</small>
        <h1 className="text-3xl font-semibold">Operational clarity without the clutter.</h1>
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <article className="rounded-xl border border-purple-500/30 bg-zinc-900/80 p-6 shadow-xl">
            <h2 className="text-lg font-medium text-purple-100">Open work</h2>
          </article>
          <article className="rounded-xl border border-purple-500/30 bg-zinc-900/80 p-6 shadow-xl">
            <h2 className="text-lg font-medium text-purple-100">Recent activity</h2>
          </article>
        </div>
      </div>
    </section>
  );
}
