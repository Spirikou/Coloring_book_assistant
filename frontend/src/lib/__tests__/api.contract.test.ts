import {
  imageFullUrl,
  imageThumbnailUrl,
  listDesignPackages,
  listImages,
  parseJobEventEnvelope,
  startMjAutomated,
  startMjBatchAutomated,
  startMjDownload,
  startMjPublish,
  startMjUxd,
  startCanvaCreate,
  startDesignSingle,
  stopJob,
  startPinterestPublish,
} from "@/lib/api";

function mockJsonResponse(body: unknown, status = 200, statusText = "OK") {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: async () => body,
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  };
}

describe("api contract helpers", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("parses listDesignPackages response", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse([{ name: "pkg-1", path: "/tmp/pkg-1", title: "Book", image_count: 4, saved_at: "2026-01-01" }])
    );

    const packages = await listDesignPackages();
    expect(packages).toHaveLength(1);
    expect(packages[0].name).toBe("pkg-1");
  });

  it("throws rich errors for failed startDesignSingle", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse("bad payload", 400, "Bad Request"));
    await expect(startDesignSingle({ user_request: "" })).rejects.toThrow("API error 400 Bad Request: bad payload");
  });

  it("calls Canva and Pinterest start routes", async () => {
    mockFetch
      .mockResolvedValueOnce(
        mockJsonResponse({ job_id: "canva_1", job_type: "canva_create", status: "running" })
      )
      .mockResolvedValueOnce(
        mockJsonResponse({ job_id: "pin_1", job_type: "pinterest_publish", status: "running" })
      );

    const canva = await startCanvaCreate({ design_package_path: "/tmp/pkg-1" });
    const pinterest = await startPinterestPublish({ design_package_path: "/tmp/pkg-1", board_name: "books" });

    expect(canva.job_type).toBe("canva_create");
    expect(pinterest.job_type).toBe("pinterest_publish");
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("calls Midjourney stage and automation routes", async () => {
    mockFetch
      .mockResolvedValueOnce(mockJsonResponse({ job_id: "mj_pub_1", job_type: "mj_publish", status: "running" }))
      .mockResolvedValueOnce(mockJsonResponse({ job_id: "mj_uxd_1", job_type: "mj_uxd", status: "running" }))
      .mockResolvedValueOnce(mockJsonResponse({ job_id: "mj_dl_1", job_type: "mj_download", status: "running" }))
      .mockResolvedValueOnce(mockJsonResponse({ job_id: "mj_auto_1", job_type: "mj_automated", status: "running" }))
      .mockResolvedValueOnce(mockJsonResponse({ job_id: "mj_batch_1", job_type: "mj_batch_automated", status: "running" }))
      .mockResolvedValueOnce(mockJsonResponse({ job_id: "mj_auto_1", stopping: true }));

    const pub = await startMjPublish({ prompts: ["p1"] });
    const uxd = await startMjUxd({ button_keys: ["U1"], count: 1, output_folder: "/tmp/pkg-1/images" });
    const dl = await startMjDownload({ count: 4, output_folder: "/tmp/pkg-1/images" });
    const automated = await startMjAutomated({ prompts: ["p1"], output_folder: "/tmp/pkg-1/images" });
    const batch = await startMjBatchAutomated({
      output_folder: "/tmp/pkg-1/images",
      designs: [{ title: "Design A", midjourney_prompts: ["p1", "p2"] }],
    });
    const stop = await stopJob("mj_auto_1");

    expect(pub.job_type).toBe("mj_publish");
    expect(uxd.job_type).toBe("mj_uxd");
    expect(dl.job_type).toBe("mj_download");
    expect(automated.job_type).toBe("mj_automated");
    expect(batch.job_type).toBe("mj_batch_automated");
    expect(stop.stopping).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(6);
  });

  it("lists images and builds image URLs", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse([
        {
          id: "img1.png",
          filename: "img1.png",
          score: 9,
          passed: true,
          summary: "good",
          modified_time_iso: "2026-01-01T00:00:00Z",
        },
      ])
    );

    const rows = await listImages("/tmp/pkg-1/images");
    expect(rows).toHaveLength(1);
    expect(imageThumbnailUrl("/tmp/pkg-1/images", "img1.png")).toContain("/api/images/thumbnail");
    expect(imageFullUrl("/tmp/pkg-1/images", "img1.png")).toContain("/api/images/full");
  });

  it("parses and validates job event envelopes", () => {
    const parsed = parseJobEventEnvelope(
      JSON.stringify({
        type: "job_snapshot",
        ts: "2026-01-01T00:00:00Z",
        data: {
          job_id: "j1",
          job_type: "design_gen_single",
          status: "running",
          step: "design",
          message: "working",
          progress: {},
          result: {},
          error: "",
          created_at: "2026-01-01T00:00:00Z",
        },
      })
    );
    expect(parsed.type).toBe("job_snapshot");

    expect(() => parseJobEventEnvelope(JSON.stringify({ type: "unknown", data: {} }))).toThrow("Invalid job event envelope");
  });
});
