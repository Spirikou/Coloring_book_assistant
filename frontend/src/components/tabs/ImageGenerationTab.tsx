/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useMemo, useState } from "react";
import DesignPackagePicker from "@/components/DesignPackagePicker";
import JobProgressPanel from "@/components/JobProgressPanel";
import ToastCenter, { type Toast } from "@/components/ToastCenter";
import {
  browserCheck,
  imageFullUrl,
  imageThumbnailUrl,
  listImages,
  listDesignPackages,
  loadDesignPackage,
  startImageAnalyze,
  startMjAutomated,
  startMjBatchAutomated,
  startMjDownload,
  startMjPublish,
  startMjUxd,
  stopJob,
  type DesignPackageSummary,
  type ImageListItem,
} from "@/lib/api";
import type { JobSnapshot } from "@/lib/jobTypes";

export default function ImageGenerationTab() {
  const [designPackagePath, setDesignPackagePath] = useState("");
  const [imagesFolderPath, setImagesFolderPath] = useState("");
  const [packageTitle, setPackageTitle] = useState("");

  const [browserStatus, setBrowserStatus] = useState<{ connected: boolean; port: number; error: string | null } | null>(null);
  const [loadingBrowser, setLoadingBrowser] = useState(true);

  const [promptsText, setPromptsText] = useState("");
  const [uxdButtonsText, setUxdButtonsText] = useState("U1,U2,U3,U4");
  const [uxdCount, setUxdCount] = useState(1);
  const [downloadCount, setDownloadCount] = useState(4);
  const [quickRun7, setQuickRun7] = useState(false);
  const [batchPackages, setBatchPackages] = useState<DesignPackageSummary[]>([]);
  const [selectedBatchPaths, setSelectedBatchPaths] = useState<string[]>([]);
  const [batchPromptsByPath, setBatchPromptsByPath] = useState<Record<string, string[]>>({});
  const [loadingBatchPrompts, setLoadingBatchPrompts] = useState<Record<string, boolean>>({});
  const [loadingBatchPackages, setLoadingBatchPackages] = useState(true);

  const [jobId, setJobId] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<JobSnapshot | null>(null);
  const [startingJob, setStartingJob] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const [images, setImages] = useState<ImageListItem[]>([]);
  const [imagesLoading, setImagesLoading] = useState(false);
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoadingBrowser(true);
    browserCheck("pinterest")
      .then((s) => {
        if (!mounted) return;
        setBrowserStatus(s);
      })
      .catch((e) => {
        if (!mounted) return;
        setBrowserStatus({ connected: false, port: 0, error: e?.message || String(e) });
      })
      .finally(() => {
        if (!mounted) return;
        setLoadingBrowser(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    setLoadingBatchPackages(true);
    listDesignPackages()
      .then((rows) => {
        if (!mounted) return;
        setBatchPackages(rows);
      })
      .catch(() => {
        if (!mounted) return;
        setBatchPackages([]);
      })
      .finally(() => {
        if (!mounted) return;
        setLoadingBatchPackages(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const isTerminal = snapshot?.status === "completed" || snapshot?.status === "failed" || snapshot?.status === "cancelled" || snapshot?.status === "stopped";
  const hasActiveJob = Boolean(jobId) && !isTerminal;
  const isRunning = startingJob || hasActiveJob;
  const anySelectedBatchLoading = selectedBatchPaths.some((p) => Boolean(loadingBatchPrompts[p]));
  const selectedBatchReadyCount = selectedBatchPaths.filter((p) => (batchPromptsByPath[p] || []).length > 0).length;
  const prompts = useMemo(
    () => promptsText.split("\n").map((p) => p.trim()).filter(Boolean),
    [promptsText]
  );
  const uxdButtons = useMemo(
    () => uxdButtonsText.split(",").map((b) => b.trim()).filter(Boolean),
    [uxdButtonsText]
  );

  const canUseFolder = Boolean(imagesFolderPath);
  const canStartPublish = Boolean(browserStatus?.connected) && prompts.length > 0 && !isRunning;
  const canStartUxd = Boolean(browserStatus?.connected) && canUseFolder && uxdButtons.length > 0 && uxdCount >= 1 && !isRunning;
  const canStartDownload = Boolean(browserStatus?.connected) && canUseFolder && downloadCount >= 1 && !isRunning;
  const canStartAutomated = Boolean(browserStatus?.connected) && canUseFolder && prompts.length > 0 && !isRunning;
  const canStartBatchAutomated =
    Boolean(browserStatus?.connected) && canUseFolder && selectedBatchReadyCount > 0 && !anySelectedBatchLoading && !isRunning;
  const canStop = Boolean(jobId) && (isRunning || hasActiveJob);
  const canAnalyze = canUseFolder && !isRunning;

  async function onSelectDesignPackage(path: string) {
    setDesignPackagePath(path);
    setImages([]);
    setSelectedFilename(null);
    if (!path) {
      setImagesFolderPath("");
      setPackageTitle("");
      return;
    }
    const loaded = await loadDesignPackage(path);
    setImagesFolderPath(String(loaded.images_folder_path || ""));
    setPackageTitle(String(loaded.title || ""));
  }

  async function refreshImages() {
    if (!imagesFolderPath) return;
    setImagesLoading(true);
    try {
      const listed = await listImages(imagesFolderPath);
      setImages(listed);
      if (listed.length > 0 && !selectedFilename) {
        setSelectedFilename(listed[0].filename);
      }
    } finally {
      setImagesLoading(false);
    }
  }

  async function onStartPublish() {
    if (!canStartPublish) return;
    setStartingJob(true);
    setSnapshot(null);
    setToast(null);
    try {
      const started = await startMjPublish({ prompts });
      setJobId(started.job_id);
    } catch (e) {
      setStartingJob(false);
      throw e;
    }
  }

  async function onStartUxd() {
    if (!canStartUxd) return;
    setStartingJob(true);
    setSnapshot(null);
    setToast(null);
    try {
      const started = await startMjUxd({
        button_keys: uxdButtons,
        count: uxdCount,
        output_folder: imagesFolderPath,
      });
      setJobId(started.job_id);
    } catch (e) {
      setStartingJob(false);
      throw e;
    }
  }

  async function onStartDownload() {
    if (!canStartDownload) return;
    setStartingJob(true);
    setSnapshot(null);
    setToast(null);
    try {
      const started = await startMjDownload({
        count: downloadCount,
        output_folder: imagesFolderPath,
      });
      setJobId(started.job_id);
    } catch (e) {
      setStartingJob(false);
      throw e;
    }
  }

  async function onStartAutomated() {
    if (!canStartAutomated) return;
    setStartingJob(true);
    setSnapshot(null);
    setToast(null);
    try {
      const started = await startMjAutomated({
        prompts,
        output_folder: imagesFolderPath,
      });
      setJobId(started.job_id);
    } catch (e) {
      setStartingJob(false);
      throw e;
    }
  }

  async function onToggleBatchPackage(path: string, checked: boolean) {
    if (checked) {
      if (!selectedBatchPaths.includes(path)) {
        setSelectedBatchPaths((prev) => [...prev, path]);
      }
      if (!batchPromptsByPath[path]) {
        setLoadingBatchPrompts((prev) => ({ ...prev, [path]: true }));
        try {
          const loaded = await loadDesignPackage(path);
          const promptsFromPackage = Array.isArray(loaded.midjourney_prompts)
            ? loaded.midjourney_prompts.map((p: unknown) => String(p || "").trim()).filter(Boolean)
            : [];
          setBatchPromptsByPath((prev) => ({ ...prev, [path]: promptsFromPackage }));
        } finally {
          setLoadingBatchPrompts((prev) => ({ ...prev, [path]: false }));
        }
      }
      return;
    }
    setSelectedBatchPaths((prev) => prev.filter((p) => p !== path));
  }

  async function onStartBatchAutomated() {
    if (!canStartBatchAutomated) return;
    setStartingJob(true);
    const selected = batchPackages.filter((p) => selectedBatchPaths.includes(p.path));
    const usedSubfolders = new Set<string>();
    const designs = selected
      .map((pkg, idx) => {
        const promptsFromPackage = batchPromptsByPath[pkg.path] || [];
        const subfolderSeed = pkg.name || pkg.title || `design_${idx + 1}`;
        const sanitizedBase = (subfolderSeed.replace(/[^a-zA-Z0-9_-]/g, "_") || "design").slice(0, 64);
        let outputSubfolder = `${sanitizedBase}_${String(idx + 1).padStart(2, "0")}`;
        let dedupeN = 2;
        while (usedSubfolders.has(outputSubfolder)) {
          outputSubfolder = `${sanitizedBase}_${String(idx + 1).padStart(2, "0")}_${dedupeN}`;
          dedupeN += 1;
        }
        usedSubfolders.add(outputSubfolder);
        return {
          title: pkg.title || pkg.name || `Design ${idx + 1}`,
          output_subfolder: outputSubfolder,
          midjourney_prompts: promptsFromPackage,
        };
      })
      .filter((d) => d.midjourney_prompts.length > 0);
    if (designs.length === 0) {
      setStartingJob(false);
      throw new Error("Selected packages do not contain any Midjourney prompts.");
    }
    setSnapshot(null);
    setToast(null);
    try {
      const started = await startMjBatchAutomated({
        designs,
        output_folder: imagesFolderPath,
        quick_run_7: quickRun7,
      });
      setJobId(started.job_id);
    } catch (e) {
      setStartingJob(false);
      throw e;
    }
  }

  async function onAnalyzeImages() {
    if (!canAnalyze) return;
    setStartingJob(true);
    try {
      const started = await startImageAnalyze({ folder: imagesFolderPath });
      setJobId(started.job_id);
    } catch (e) {
      setStartingJob(false);
      throw e;
    }
  }

  async function onStopJob() {
    if (!jobId) return;
    await stopJob(jobId);
    setToast({
      type: "success",
      title: "Stop requested",
      message: "The job is transitioning to a stopped state.",
    });
  }

  const selectedImage = images.find((i) => i.filename === selectedFilename) || null;

  return (
    <div className="space-y-5">
      <ToastCenter toast={toast} onClose={() => setToast(null)} />

      <div className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-lg font-semibold text-slate-900">Image Generation (Midjourney)</div>
            <div className="mt-1 text-sm text-slate-600">
              Run publish, upscale/vary, download, automated, and batch jobs with live SSE progress and stop controls.
            </div>
            <div className="mt-1 text-xs text-slate-500">
              Browser readiness uses the existing `pinterest` debug role until a dedicated Midjourney role is exposed by the backend.
            </div>
          </div>
          <div className="text-right">
            {loadingBrowser ? (
              <div className="text-xs text-slate-500">Checking browser…</div>
            ) : browserStatus ? (
              <div className="text-xs">
                <span className={browserStatus.connected ? "font-semibold text-emerald-700" : "font-semibold text-rose-700"}>
                  {browserStatus.connected ? "Browser connected" : "Browser not connected"}
                </span>
                {browserStatus.error ? <div className="mt-1 text-rose-600">{browserStatus.error}</div> : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
          <div className="text-sm font-semibold text-slate-900">Prerequisites</div>
          <DesignPackagePicker value={designPackagePath} onChange={(value) => onSelectDesignPackage(value).catch((e) => setToast({ type: "error", title: "Could not load package", message: e?.message || String(e) }))} disabled={isRunning} />
          <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700">
            <div>Title: {packageTitle || "—"}</div>
            <div>Images folder: {imagesFolderPath || "—"}</div>
          </div>
        </div>

        <div className="space-y-3 rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
          <div className="text-sm font-semibold text-slate-900">Prompts & controls</div>
          <textarea
            className="h-32 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            value={promptsText}
            onChange={(e) => setPromptsText(e.target.value)}
            placeholder="One Midjourney prompt per line..."
            disabled={isRunning}
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-slate-600">UXD buttons (comma-separated)</label>
              <input
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                value={uxdButtonsText}
                onChange={(e) => setUxdButtonsText(e.target.value)}
                disabled={isRunning}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-600">UXD count</label>
              <input
                type="number"
                min={1}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                value={uxdCount}
                onChange={(e) => setUxdCount(Number(e.target.value))}
                disabled={isRunning}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-600">Download count</label>
              <input
                type="number"
                min={1}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                value={downloadCount}
                onChange={(e) => setDownloadCount(Number(e.target.value))}
                disabled={isRunning}
              />
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-700">
              <input type="checkbox" checked={quickRun7} onChange={(e) => setQuickRun7(e.target.checked)} disabled={isRunning} />
              Quick-run first 7 prompts in batch
            </label>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
          <div className="text-sm font-semibold text-slate-900">Stage actions</div>
          <div className="flex flex-wrap gap-2">
            <button className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!canStartPublish} onClick={() => onStartPublish().catch((e) => setToast({ type: "error", title: "Could not start publish", message: e?.message || String(e) }))}>Start Publish</button>
            <button className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!canStartUxd} onClick={() => onStartUxd().catch((e) => setToast({ type: "error", title: "Could not start UXD", message: e?.message || String(e) }))}>Start UXD</button>
            <button className="rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!canStartDownload} onClick={() => onStartDownload().catch((e) => setToast({ type: "error", title: "Could not start download", message: e?.message || String(e) }))}>Start Download</button>
            <button className="rounded-lg bg-rose-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!canStop} onClick={() => onStopJob().catch((e) => setToast({ type: "error", title: "Could not stop job", message: e?.message || String(e) }))}>Stop Job</button>
          </div>
        </div>

        <div className="space-y-3 rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
          <div className="text-sm font-semibold text-slate-900">Automated & batch automated</div>
          <div className="flex flex-wrap gap-2">
            <button className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!canStartAutomated} onClick={() => onStartAutomated().catch((e) => setToast({ type: "error", title: "Could not start automated", message: e?.message || String(e) }))}>Run Automated</button>
            <button className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!canStartBatchAutomated} onClick={() => onStartBatchAutomated().catch((e) => setToast({ type: "error", title: "Could not start batch automated", message: e?.message || String(e) }))}>Run Batch Automated</button>
          </div>
          {anySelectedBatchLoading ? <div className="text-xs text-amber-700">Loading prompts from selected packages...</div> : null}
          {!anySelectedBatchLoading && selectedBatchPaths.length > 0 && selectedBatchReadyCount === 0 ? (
            <div className="text-xs text-rose-700">Selected packages have no saved Midjourney prompts.</div>
          ) : null}
          <div className="text-xs text-slate-600">Select multiple design packages. Batch mode reads each package&apos;s saved `midjourney_prompts`.</div>
          <div className="max-h-40 space-y-2 overflow-auto rounded-lg border border-slate-200 bg-white p-2">
            {loadingBatchPackages ? (
              <div className="text-xs text-slate-500">Loading design packages...</div>
            ) : batchPackages.length === 0 ? (
              <div className="text-xs text-slate-500">No design packages found.</div>
            ) : (
              batchPackages.map((pkg) => {
                const selected = selectedBatchPaths.includes(pkg.path);
                const promptCount = (batchPromptsByPath[pkg.path] || []).length;
                return (
                  <label key={pkg.path} className="flex items-start gap-2 rounded border border-slate-200 px-2 py-1.5 text-xs">
                    <input
                      type="checkbox"
                      checked={selected}
                      disabled={isRunning}
                      onChange={(e) =>
                        onToggleBatchPackage(pkg.path, e.target.checked).catch((err) =>
                          setToast({ type: "error", title: "Could not load package prompts", message: err?.message || String(err) }),
                        )
                      }
                    />
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-800">{pkg.title || pkg.name}</div>
                      <div className="text-slate-600">{pkg.path}</div>
                      {selected ? <div className="text-slate-500">Prompts: {loadingBatchPrompts[pkg.path] ? "loading..." : promptCount}</div> : null}
                    </div>
                  </label>
                );
              })
            )}
          </div>
        </div>
      </div>

      <JobProgressPanel
        jobId={jobId}
        onSnapshot={(s) => {
          setSnapshot(s);
          setStartingJob(false);
        }}
        onCompleted={(s) => {
          setStartingJob(false);
          setToast({
            type: "success",
            title: `${s.job_type} completed`,
            message: s.message || "Job completed successfully.",
          });
          if (s.job_type === "mj_download" || s.job_type === "mj_automated" || s.job_type === "mj_batch_automated" || s.job_type === "image_analyze") {
            refreshImages().catch(() => {});
          }
        }}
        onFailed={(s) => {
          setStartingJob(false);
          setToast({
            type: "error",
            title: `${s.job_type} did not complete`,
            message: s.error || s.message || "Job failed or was stopped.",
          });
        }}
      />

      {snapshot ? (
        <div className="rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
          <div className="text-sm font-semibold text-slate-900">Result / error details</div>
          <pre className="mt-3 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
            {JSON.stringify({ status: snapshot.status, step: snapshot.step, message: snapshot.message, error: snapshot.error, result: snapshot.result }, null, 2)}
          </pre>
        </div>
      ) : null}

      <div className="space-y-3 rounded-xl border border-slate-200 bg-white/70 p-4 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-slate-900">Image list / preview / analysis</div>
          <div className="flex gap-2">
            <button className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-50" disabled={!canUseFolder || imagesLoading} onClick={() => refreshImages().catch((e) => setToast({ type: "error", title: "Could not list images", message: e?.message || String(e) }))}>
              Refresh Images
            </button>
            <button className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50" disabled={!canAnalyze} onClick={() => onAnalyzeImages().catch((e) => setToast({ type: "error", title: "Could not start analysis", message: e?.message || String(e) }))}>
              Analyze Images
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="max-h-72 space-y-2 overflow-auto rounded-lg border border-slate-200 bg-white p-2">
            {images.length === 0 ? (
              <div className="text-xs text-slate-500">{imagesLoading ? "Loading images..." : "No images loaded yet."}</div>
            ) : (
              images.map((img) => (
                <button
                  key={img.id}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-xs ${selectedFilename === img.filename ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50"}`}
                  onClick={() => setSelectedFilename(img.filename)}
                >
                  <div className="font-semibold text-slate-900">{img.filename}</div>
                  <div className="mt-1 text-slate-600">
                    Score: {img.score ?? "—"} | Passed: {img.passed == null ? "—" : img.passed ? "yes" : "no"}
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-3">
            {!selectedImage || !imagesFolderPath ? (
              <div className="text-xs text-slate-500">Select an image to preview.</div>
            ) : (
              <div className="space-y-2">
                <img
                  src={imageThumbnailUrl(imagesFolderPath, selectedImage.filename)}
                  alt={selectedImage.filename}
                  className="max-h-64 w-auto rounded-lg border border-slate-200"
                />
                <div className="text-xs text-slate-700">{selectedImage.summary || "No analysis summary available."}</div>
                <a
                  href={imageFullUrl(imagesFolderPath, selectedImage.filename)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
                >
                  Open full image
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
