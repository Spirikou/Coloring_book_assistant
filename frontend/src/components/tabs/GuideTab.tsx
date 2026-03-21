"use client";

const sections = [
  {
    title: "Prerequisites",
    text: "Phase 2 will identify onboarding prerequisites and environment checks required before first run.",
  },
  {
    title: "Configuration",
    text: "Phase 2 will include guided setup instructions for key app and integration settings.",
  },
  {
    title: "Actions",
    text: "Phase 2 will provide actionable walkthrough steps for common workflows and troubleshooting.",
  },
  {
    title: "Live Progress",
    text: "Phase 2 will surface setup and workflow progress cues directly in the guide experience.",
  },
  {
    title: "Results / History",
    text: "Phase 2 will capture completion checkpoints and quick links to previously completed guide paths.",
  },
];

export default function GuideTab() {
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
        <div className="text-lg font-semibold text-slate-900">Guide</div>
        <div className="mt-1 text-sm text-slate-600">Guide routing is available now. Rich onboarding and helper content will be delivered in later phases.</div>
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
