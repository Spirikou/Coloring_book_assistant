import type { JobSnapshot, JobStatus, JobType } from "./jobTypes";

const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function apiUrl(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${p}`;
}

async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API error ${res.status} ${res.statusText}: ${body}`.trim());
  }
  return (await res.json()) as T;
}

export type DesignPackageSummary = {
  name: string;
  path: string;
  title: string;
  image_count: number;
  saved_at: string;
};

export async function listDesignPackages(): Promise<DesignPackageSummary[]> {
  return apiJson("/api/design-packages");
}

export type DesignPackageLoadState = Record<string, any> & {
  images_folder_path?: string;
  design_package_path?: string;
  title?: string;
};

export async function loadDesignPackage(folder_path: string): Promise<DesignPackageLoadState> {
  const url = `/api/design-packages/load?folder_path=${encodeURIComponent(folder_path)}`;
  return apiJson(url);
}

export type StartJobResponse = {
  job_id: string;
  job_type: JobType;
  status: JobStatus;
};

export async function startPinterestPublish(payload: {
  design_package_path: string;
  board_name: string;
  max_pins_per_design?: number;
  dry_run?: boolean;
}): Promise<StartJobResponse> {
  return apiJson("/api/jobs/pinterest_publish/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startCanvaCreate(payload: {
  design_package_path: string;
  images_folder_path?: string;
  page_size?: string;
  page_count?: number;
  margin_percent?: number;
  outline_height_percent?: number;
  blank_between?: boolean;
  selected_images?: string[] | null;
  dry_run?: boolean;
}): Promise<StartJobResponse> {
  return apiJson("/api/jobs/canva_create/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startDesignConceptVariations(payload: {
  user_idea: string;
  num_variations?: number;
  creativity_level?: "low" | "medium" | "high";
}): Promise<StartJobResponse> {
  return apiJson("/api/jobs/design_gen_concept_variations/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startDesignSingle(payload: {
  user_request: string;
}): Promise<StartJobResponse> {
  return apiJson("/api/jobs/design_gen_single/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resumeDesignJob(jobId: string, payload: { user_answer: string }): Promise<StartJobResponse> {
  return apiJson(`/api/jobs/${jobId}/resume`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startImageAnalyze(payload: { folder: string }): Promise<StartJobResponse> {
  return apiJson("/api/jobs/image_analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type ImageListItem = {
  id: string;
  filename: string;
  score: number | null;
  passed: boolean | null;
  summary: string | null;
  modified_time_iso: string | null;
};

export async function listImages(folder: string): Promise<ImageListItem[]> {
  return apiJson(`/api/images?folder=${encodeURIComponent(folder)}`);
}

export type BrowserCheckRole = "canva" | "pinterest";

export type BrowserCheckResponse = {
  connected: boolean;
  port: number;
  error: string | null;
};

export type MjPublishStartRequest = {
  prompts: string[];
  browser_port?: number;
  button_coordinates?: Record<string, [number, number]>;
  viewport?: { width: number; height: number };
  coordinates_viewport?: { width: number; height: number };
  debug_show_clicks?: boolean;
  poll_interval_sec?: number;
};

export type MjUxdStartRequest = {
  button_keys: string[];
  count: number;
  output_folder: string;
  browser_port?: number;
  button_coordinates?: Record<string, [number, number]>;
  viewport?: { width: number; height: number };
  coordinates_viewport?: { width: number; height: number };
  debug_show_clicks?: boolean;
  poll_interval_sec?: number;
};

export type MjDownloadStartRequest = {
  count: number;
  output_folder: string;
  browser_port?: number;
  button_coordinates?: Record<string, [number, number]>;
  viewport?: { width: number; height: number };
  coordinates_viewport?: { width: number; height: number };
  debug_show_clicks?: boolean;
  poll_interval_sec?: number;
};

export type MjAutomatedStartRequest = {
  prompts: string[];
  output_folder: string;
  browser_port?: number;
  button_coordinates?: Record<string, [number, number]>;
  viewport?: { width: number; height: number };
  coordinates_viewport?: { width: number; height: number };
  debug_show_clicks?: boolean;
  poll_interval_sec?: number;
};

export type MjBatchAutomatedDesign = {
  midjourney_prompts: string[];
  title?: string;
  output_subfolder?: string;
};

export type MjBatchAutomatedStartRequest = {
  designs: MjBatchAutomatedDesign[];
  output_folder: string;
  quick_run_7?: boolean;
  browser_port?: number;
  button_coordinates?: Record<string, [number, number]>;
  viewport?: { width: number; height: number };
  coordinates_viewport?: { width: number; height: number };
  debug_show_clicks?: boolean;
  poll_interval_sec?: number;
};

export type StopJobResponse = {
  job_id: string;
  stopping: boolean;
};

export async function startMjPublish(payload: MjPublishStartRequest): Promise<StartJobResponse> {
  return apiJson("/api/jobs/mj_publish/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startMjUxd(payload: MjUxdStartRequest): Promise<StartJobResponse> {
  return apiJson("/api/jobs/mj_uxd/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startMjDownload(payload: MjDownloadStartRequest): Promise<StartJobResponse> {
  return apiJson("/api/jobs/mj_download/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startMjAutomated(payload: MjAutomatedStartRequest): Promise<StartJobResponse> {
  return apiJson("/api/jobs/mj_automated/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startMjBatchAutomated(payload: MjBatchAutomatedStartRequest): Promise<StartJobResponse> {
  return apiJson("/api/jobs/mj_batch_automated/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function stopJob(jobId: string): Promise<StopJobResponse> {
  return apiJson(`/api/jobs/${encodeURIComponent(jobId)}/stop`, {
    method: "POST",
  });
}

export function imageThumbnailUrl(folder: string, filename: string): string {
  return apiUrl(`/api/images/thumbnail?folder=${encodeURIComponent(folder)}&filename=${encodeURIComponent(filename)}`);
}

export function imageFullUrl(folder: string, filename: string): string {
  return apiUrl(`/api/images/full?folder=${encodeURIComponent(folder)}&filename=${encodeURIComponent(filename)}`);
}

export async function browserCheck(role: BrowserCheckRole): Promise<BrowserCheckResponse> {
  const url = `/api/browser/check?role=${encodeURIComponent(role)}`;
  const res = await apiJson<BrowserCheckResponse>(url);
  return {
    connected: Boolean(res.connected),
    port: Number(res.port),
    error: res.error ?? null,
  };
}

export function jobEventsUrl(jobId: string) {
  return apiUrl(`/api/jobs/${jobId}/events`);
}

export type JobEventEnvelope =
  | { type: "job_snapshot"; ts: string; data: JobSnapshot }
  | { type: "job_update"; ts: string; data: JobSnapshot };

export function parseJobEventEnvelope(raw: string): JobEventEnvelope {
  const parsed = JSON.parse(raw) as Partial<JobEventEnvelope>;
  if (!parsed || (parsed.type !== "job_snapshot" && parsed.type !== "job_update") || !parsed.data) {
    throw new Error("Invalid job event envelope");
  }
  return parsed as JobEventEnvelope;
}

