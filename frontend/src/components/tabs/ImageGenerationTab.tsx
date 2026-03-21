"use client";

const sections = [
  {
    title: "Prerequisites",
    text: "Phase 2 will validate browser connectivity, Midjourney configuration, and output folder readiness.",
  },
  {
    title: "Configuration",
    text: "Phase 2 will add prompt, run-mode, and image processing options for image generation workflows.",
  },
  {
    title: "Actions",
    text: "Phase 2 will introduce typed actions for publish, upscale/vary, download, and automated pipeline starts.",
  },
  {
    title: "Live Progress",
    text: "Phase 2 will stream per-job status, stage transitions, and progress counters through SSE.",
  },
  {
    title: "Results / History",
    text: "Phase 2 will show generated outputs, job artifacts, and reusable run history.",
  },
];

export default function ImageGenerationTab() {
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
        <div className="text-lg font-semibold text-slate-900">Image Generation</div>
        <div className="mt-1 text-sm text-slate-600">Surface skeleton ready. Detailed workflow behavior lands in the next phases.</div>
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
