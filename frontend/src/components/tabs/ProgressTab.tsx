"use client";

const sections = [
  {
    title: "Prerequisites",
    text: "Phase 2 will ensure job discovery and event subscription prerequisites are available before loading progress feeds.",
  },
  {
    title: "Configuration",
    text: "Phase 2 will add filters by job type, status, and time ranges for focused monitoring.",
  },
  {
    title: "Actions",
    text: "Phase 2 will enable progress actions such as follow, inspect details, and stop eligible jobs.",
  },
  {
    title: "Live Progress",
    text: "Phase 2 will centralize real-time SSE job snapshots and updates across all workflow surfaces.",
  },
  {
    title: "Results / History",
    text: "Phase 2 will expose completed/failed run timelines with persistent summaries.",
  },
];

export default function ProgressTab() {
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
        <div className="text-lg font-semibold text-slate-900">Progress</div>
        <div className="mt-1 text-sm text-slate-600">Tab shell is ready. Shared progress functionality will be connected in upcoming phases.</div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {sections.map((section) => (
          <div key={section.title} className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
            <div className="text-sm font-semibold text-slate-900">{section.title}</div>
            <div className="mt-2 text-sm text-slate-600">{section.text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
