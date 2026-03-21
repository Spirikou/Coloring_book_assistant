"use client";

const sections = [
  {
    title: "Prerequisites",
    text: "Phase 2 will validate required connectors, selected assets, and environment constraints before orchestration runs.",
  },
  {
    title: "Configuration",
    text: "Phase 2 will define orchestration profiles, sequencing rules, and guarded runtime options.",
  },
  {
    title: "Actions",
    text: "Phase 2 will provide start, pause/resume, and stop controls for multi-step orchestration jobs.",
  },
  {
    title: "Live Progress",
    text: "Phase 2 will present stage-level orchestration telemetry and cross-job status updates.",
  },
  {
    title: "Results / History",
    text: "Phase 2 will collect run summaries, outputs, and error traces for replay and debugging.",
  },
];

export default function OrchestrationTab() {
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
        <div className="text-lg font-semibold text-slate-900">Orchestration</div>
        <div className="mt-1 text-sm text-slate-600">Routing surface is in place. Feature-complete orchestration controls are planned for later phases.</div>
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
