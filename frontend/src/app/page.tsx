"use client";

import { useMemo, useState } from "react";
import PinterestTab from "@/components/tabs/PinterestTab";
import CanvaTab from "@/components/tabs/CanvaTab";
import DesignGenerationTab from "@/components/tabs/DesignGenerationTab";
import ImageGenerationTab from "@/components/tabs/ImageGenerationTab";
import OrchestrationTab from "@/components/tabs/OrchestrationTab";
import ProgressTab from "@/components/tabs/ProgressTab";
import ConfigTab from "@/components/tabs/ConfigTab";
import GuideTab from "@/components/tabs/GuideTab";

type AppTab = "design" | "images" | "canva" | "pinterest" | "orchestration" | "progress" | "config" | "guide";

const TAB_LABELS: Record<AppTab, string> = {
  design: "Design",
  images: "Images",
  canva: "Canva",
  pinterest: "Pinterest",
  orchestration: "Orchestration",
  progress: "Progress",
  config: "Config",
  guide: "Guide",
};

export default function Page() {
  const [tab, setTab] = useState<AppTab>("design");

  const title = useMemo(() => {
    if (tab === "design") return "Design Generation";
    if (tab === "images") return "Image Generation";
    if (tab === "canva") return "Canva";
    if (tab === "pinterest") return "Pinterest";
    if (tab === "orchestration") return "Orchestration";
    if (tab === "progress") return "Progress";
    if (tab === "config") return "Config";
    return "Guide";
  }, [tab]);

  const tabComponentByTab: Record<AppTab, JSX.Element> = {
    design: <DesignGenerationTab />,
    images: <ImageGenerationTab />,
    canva: <CanvaTab />,
    pinterest: <PinterestTab />,
    orchestration: <OrchestrationTab />,
    progress: <ProgressTab />,
    config: <ConfigTab />,
    guide: <GuideTab />,
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-white via-white to-slate-50">
      <div className="mx-auto max-w-5xl p-4 md:p-8">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-2xl font-semibold text-slate-900">{title}</div>
            <div className="mt-1 text-sm text-slate-600">
              SSE progress, modern UI, and direct job execution via the Python backend.
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {(Object.keys(TAB_LABELS) as AppTab[]).map((tabKey) => (
              <button
                key={tabKey}
                onClick={() => setTab(tabKey)}
                className={`rounded-lg px-3 py-2 text-sm font-semibold ${
                  tab === tabKey ? "bg-blue-600 text-white" : "bg-white text-slate-800 hover:bg-slate-50"
                }`}
              >
                {TAB_LABELS[tabKey]}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6">{tabComponentByTab[tab]}</div>
      </div>
    </main>
  );
}
