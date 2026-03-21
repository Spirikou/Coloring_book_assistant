"use client";

const sections = [
  {
    title: "Prerequisites",
    text: "Phase 2 will validate required local services, browser ports, and runtime environment settings.",
  },
  {
    title: "Configuration",
    text: "Phase 2 will add editable app settings, integration toggles, and persisted preference controls.",
  },
  {
    title: "Actions",
    text: "Phase 2 will support configuration checks, save operations, and safe reset helpers.",
  },
  {
    title: "Live Progress",
    text: "Phase 2 will provide status feedback for long-running config validation and setup actions.",
  },
  {
    title: "Results / History",
    text: "Phase 2 will show recent configuration updates, validation results, and audit breadcrumbs.",
  },
];

export default function ConfigTab() {
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
        <div className="text-lg font-semibold text-slate-900">Config</div>
        <div className="mt-1 text-sm text-slate-600">Configuration surface is scaffolded. Full controls and persistence are targeted for future phases.</div>
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
