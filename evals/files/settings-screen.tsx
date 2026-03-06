export function SettingsScreen() {
  return (
    <main className="bg-gradient-to-b from-zinc-950 to-purple-950 px-8 py-10 text-white">
      <div className="mx-auto max-w-4xl rounded-xl border border-purple-500/40 p-8 shadow-xl">
        <small className="mb-2 block uppercase tracking-[0.3em] text-purple-200">Night shift</small>
        <h1 className="mb-6 text-3xl font-semibold">Team settings</h1>
        <label className="block text-sm font-medium text-purple-100">Workspace name</label>
        <input className="mt-3 w-full rounded-full border border-purple-400/30 bg-zinc-900 px-4 py-3 backdrop-blur" />
      </div>
    </main>
  );
}
