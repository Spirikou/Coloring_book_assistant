# Phase 2 Code Review (0009)

## Findings

### High: Batch automated flow does not implement "across multiple design packages"

The Phase 2 plan requires batch automated mode across multiple design packages, but the current tab only supports free-text parsing in one textarea and does not load prompts from selected packages or allow selecting multiple packages.

```160:177:frontend/src/components/tabs/ImageGenerationTab.tsx
function parseBatchDesigns(raw: string): MjBatchAutomatedDesign[] {
  const rows = raw
    .split("\n")
    .map((r) => r.trim())
    .filter(Boolean);
  return rows.map((row, idx) => {
    const [titlePart, promptsPart] = row.includes("|") ? row.split("|", 2) : [`Design ${idx + 1}`, row];
    const promptLines = promptsPart
      .split(";")
      .map((p) => p.trim())
      .filter(Boolean);
    return {
      title: titlePart.trim() || `Design ${idx + 1}`,
      output_subfolder: `design_${idx + 1}`,
      midjourney_prompts: promptLines,
    };
  }).filter((d) => d.midjourney_prompts.length > 0);
}
```

Impact:
- misses a key parity requirement from `0009_PLAN_phase2.md`
- easy user error due to ad-hoc string format
- no strong linkage to saved package metadata

Recommended fix:
- provide multi-select design package picker for batch mode
- for each selected package, load package data and extract `midjourney_prompts` from persisted package state
- use explicit per-package rows (title, prompts count, output subfolder) instead of parsing raw text

---

### High: Job start lock has a race window; users can fire multiple jobs before first SSE snapshot

Button lock state depends on `snapshot.status`, but `snapshot` is reset to `null` right before starting a job. Until first SSE event arrives, `isRunning` stays `false`, so start buttons can still be clicked.

```71:88:frontend/src/components/tabs/ImageGenerationTab.tsx
const isRunning = useMemo(() => snapshot?.status === "queued" || snapshot?.status === "running", [snapshot?.status]);
...
const canStartPublish = Boolean(browserStatus?.connected) && prompts.length > 0 && !isRunning;
...
const canStop = Boolean(jobId) && isRunning;
```

```118:124:frontend/src/components/tabs/ImageGenerationTab.tsx
async function onStartPublish() {
  if (!canStartPublish) return;
  setSnapshot(null);
  setToast(null);
  const started = await startMjPublish({ prompts });
  setJobId(started.job_id);
}
```

Impact:
- duplicate backend jobs can be created accidentally
- stop button may be unavailable right after job starts

Recommended fix:
- derive running state from `jobId` + optimistic local `starting` flag, not only `snapshot`
- disable all start actions immediately on click and re-enable only on terminal snapshot

---

### Medium: Browser readiness check is likely role-misaligned for Midjourney runs

Image Generation currently hardcodes `browserCheck("pinterest")`. There is no Midjourney role in the API, so this may pass/fail based on the wrong browser profile/port depending on environment setup.

```50:54:frontend/src/components/tabs/ImageGenerationTab.tsx
useEffect(() => {
  let mounted = true;
  setLoadingBrowser(true);
  browserCheck("pinterest")
```

Impact:
- false-negative readiness (or false-positive) when MJ automation uses a different debug target
- confusing UX for Phase 2 prerequisites

Recommended fix:
- either expose a dedicated backend role for Midjourney checks, or
- add explicit UI copy and config mapping that confirms why `pinterest` role is being used for MJ

---

### Medium: Required Phase-0 artifacts were not updated

The plan marks Phase-0 artifact usage as mandatory, but no update was made to the parity checklist and no mismatch notes were recorded.

Impact:
- acceptance state for feature parity is unverifiable from project docs
- API alignment decisions are not documented

Recommended fix:
- update `docs/features/0007_PARITY_CHECKLIST.md` rows related to Image Generation
- add notes for known limitations (batch input format, browser role mapping, etc.)

---

### Low: `ImageGenerationTab` is becoming large and mixes many concerns

The tab currently handles selection, parsing, validation, start/stop orchestration, image list state, and preview UI in one file.

Impact:
- maintenance cost rises quickly for Phase 3+
- harder to test handlers in isolation

Recommended fix:
- split into small components/hooks:
  - `ImageStageActions`
  - `ImageAutomationPanel`
  - `ImageArtifactsPanel`
  - `useImageGenerationState` hook for handler logic

## Data alignment check

- `snake_case` request keys for MJ routes are correctly used and align with backend Pydantic models.
- `StartJobResponse` shape matches backend (`job_id`, `job_type`, `status`).
- `listImages` shape aligns with backend (`filename`, `score`, `passed`, `summary`, `modified_time_iso`).
- no `data: {}` envelope mismatch found in API wrapper usage for these routes.

## Test coverage gaps

- API contract tests were added for wrapper calls and URLs (good).
- Missing UI tests for:
  - start-button lock behavior during the pre-SSE window
  - stop-state transition and button state
  - batch parser/validation behavior
  - package-selection to folder-state sync behavior

---

## Follow-up review of corrections

### Medium: Batch start can fail due to prompt-loading race

After selecting packages, prompt loading is async (`loadDesignPackage`) but `Run Batch Automated` becomes enabled as soon as a package is checked (`selectedBatchPaths.length > 0`). Users can click start before prompts are loaded, which raises "Selected packages do not contain any Midjourney prompts."

Impact:
- avoidable user-facing error
- inconsistent UX for otherwise valid selections

Recommended fix:
- track per-package loading state and disable `Run Batch Automated` while any selected package is still loading
- alternatively require at least one selected package with `promptCount > 0` before enabling start

### Medium: Potential output subfolder collisions in batch mode

`output_subfolder` is derived from sanitized package name/title only. Different packages can collapse to the same sanitized value (for example, punctuation/case differences), which can mix outputs in the same folder.

Impact:
- batch outputs from multiple designs can overwrite/mix unexpectedly
- result provenance becomes ambiguous

Recommended fix:
- append a stable index or short hash to each `output_subfolder` (for example `name_01`, `name_02`) to guarantee uniqueness

### Low: Review note for browser readiness mismatch is now documented

The correction added explicit UI text that `role=pinterest` is used temporarily for Midjourney readiness checks. This is a good mitigation, but still leaves a backend contract gap for a dedicated Midjourney role.

Recommended follow-up:
- add backend role support (for example `role=midjourney`) and switch frontend when available

---

## Final follow-up review of medium-fix implementation

No new correctness bugs were found in the latest implementation for:
- batch prompt-loading gate
- collision-safe batch output subfolders

Both previously reported medium issues are addressed in code:
- `Run Batch Automated` now waits for selected package prompt loading and requires at least one selected package with prompts.
- batch `output_subfolder` names are now deterministic and uniqueness-protected with index-based suffixing.

Residual risks / testing gaps:
- UI behavior is still validated manually; there are no component tests yet for:
  - selected-package loading states and button gating
  - batch subfolder naming guarantees from package selections
  - rapid select/unselect interaction edge-cases

