# In-Depth Analysis: Upscale Batch Bug (Image 10 Duplicated, Image 12 Skipped)

## Executive Summary

When upscaling 12 images in two batches (10 + 2), the observed behavior was:
- **Image 10** was upscaled twice (once in Batch 1, again in Batch 2)
- **Image 12** was never upscaled

This analysis traces the terminal logs, identifies root causes, and proposes improvements without implementing them.

---

## 1. Terminal Log Reconstruction

### Batch 1 (Images 1–10)

| Time     | Event |
|----------|-------|
| 07:50:28 | Batch 1/2: `start_index=0`, `batch_size=10`, `resuming=False` |
| 07:50:29 | First batch: click `nth(0)`, ArrowRight 0 times → image 1 |
| 07:50:33 | Before loop: `page_url=...3276541b...?index=0`, `image_job_id=3276541b`, processing images 1–10 |
| 07:50:33–53 | `upscale_subtle` images 1/10 through 10/10 |
| 07:50:54 | Batch complete: `last_url=...ada12b25...?index=1` (jobs_url=True) |
| 07:50:55 | Batch 1 done: `last_processed_url=...ada12b25...?index=1` |

**Observation:** Batch 1 ends on a different job (`ada12b25`) than it started (`3276541b`). The carousel crosses job boundaries during navigation.

### Queue Wait (07:50:55 – 07:57:05)

- Queue drains from 7 → 0 over ~257 seconds
- Finalization wait: ~110 seconds extrapolated

### Batch 2 (Images 11–12)

| Time     | Event |
|----------|-------|
| 07:57:05 | Batch 2/2: `start_index=10`, `batch_size=2`, `resuming=True`, `last_url=...ada12b25...?index=1` |
| 07:57:05 | Resume: expect image 11 |
| 07:57:08 | Resumed via URL navigation (jobId=ada12b25) |
| 07:57:08 | Resume strategy: URL navigation OK, advancing ArrowRight to image 11 |
| 07:57:13 | Before loop: `page_url=...ada12b25...?index=1`, processing images 11–12 |
| 07:57:13 | `upscale_subtle` image 1/2 |
| 07:57:15 | `upscale_subtle` image 2/2 |
| 07:57:16 | Batch complete: `last_url=...ada12b25...?index=2` |
| 07:57:17 | Batch 2 done |

**Observation:** No `[Upscale TRACE] Carousel advanced after X.Xs` log in Batch 2. That suggests either:
1. The carousel advance was not detected (same image before/after ArrowRight), or
2. `prev_img_url` was empty so `_wait_for_carousel_advance` returned early without polling

---

## 2. Root Cause Hypotheses

### Hypothesis A: Carousel Advance Not Verified (HIGH CONFIDENCE)

**Evidence:** `_wait_for_carousel_advance()` returns `True`/`False` but its return value is never checked in `click_button_first_n` (lines 770, 795). If the carousel does not advance (e.g., timeout, DOM delay, or boundary behavior), the code still proceeds to the loop.

**Scenario:**
1. Resume navigates to `ada12b25?index=1` (image 10).
2. ArrowRight is pressed.
3. Carousel does not advance (or advances slowly) within 8 seconds.
4. `_wait_for_carousel_advance` returns `False`; caller ignores it.
5. Loop runs with the view still on image 10.
6. Iteration 1: upscale image 10 (duplicate).
7. ArrowRight → image 11.
8. Iteration 2: upscale image 11.
9. Loop ends; image 12 is never reached.

**Conclusion:** This explains both symptoms: image 10 upscaled twice, image 12 skipped.

---

### Hypothesis B: `last_url` Captures Wrong Image (MEDIUM CONFIDENCE)

**Evidence:** `last_url` is taken from `page.url` after the loop (line 927). If the Midjourney SPA updates the URL asynchronously or with a delay, the captured URL might not match the last processed image.

**Scenario:** If `last_url` actually pointed to image 9 instead of 10:
1. Resume navigates to image 9.
2. ArrowRight → image 10.
3. Loop processes 2 images: 10 (duplicate) and 11.
4. Image 12 is never reached.

**Mitigation:** Prefer capturing the image URL from the detail view (`_get_image_url_from_detail_view`) instead of `page.url`, or add a short wait before capturing to allow the URL to settle.

---

### Hypothesis C: Index Semantics / Multi-Job Grid Mismatch (MEDIUM CONFIDENCE)

**Evidence:** Batch 1 starts on job `3276541b` and ends on `ada12b25?index=1`. The `index` parameter may not map 1:1 to global image position when images span multiple jobs.

**Scenario:** If `index` is per-job (e.g., 0–3 for a 4-image grid) and the global mapping is wrong, resuming at `index=1` might land on the wrong image. The current logic assumes `last_url` always points to the last processed image.

**Mitigation:** Validate that the resumed image matches the expected one (e.g., by comparing CDN image ID with a stored reference) before advancing.

---

### Hypothesis D: Race / Timing at Job Boundary (LOW–MEDIUM CONFIDENCE)

**Evidence:** Batch 1 ends on job `ada12b25`; Batch 2 resumes on the same job. The transition from image 10 to 11 may cross a job or layout boundary, causing slower DOM updates.

**Scenario:** At job boundaries, ArrowRight might trigger a heavier update (new job load, layout change). The 2.5s wait and 8s carousel timeout may be insufficient.

**Mitigation:** Increase waits at resume, or add retries for the ArrowRight + advance verification step.

---

### Hypothesis E: `prev_img_url` Empty on Resume (LOW CONFIDENCE)

**Evidence:** If `_get_image_url_from_detail_view(0)` returns `None` after navigation, `prev_img_url` is empty. `_wait_for_carousel_advance("", ...)` returns `True` immediately (line 298) without verifying the advance.

**Scenario:** Detail view not fully loaded; no previous URL to compare. Advance is assumed without verification.

**Mitigation:** Require a non-empty `prev_img_url` before trusting the advance, or add a fallback verification (e.g., compare with expected next image).

---

## 3. Code Flow Summary

### Batch 1 End → `last_url` Capture

```
Loop i=0..9: upscale, ArrowRight (except last)
→ After i=9: still on image 10, no ArrowRight
→ page_url = self.page.url
→ last_url = page_url (if jobs URL) else CDN URL from detail view
→ Escape, return last_url
```

### Batch 2 Resume

```
last_processed_url = ada12b25?index=1
→ _navigate_to_image_by_url(last_processed_url)  # opens image 10
→ prev_img_url = _get_image_url_from_detail_view(0)
→ ArrowRight
→ _wait_for_carousel_advance(prev_img_url)  # return value IGNORED
→ Loop i=0..1: upscale 2 images
```

If the advance failed, the loop would still run on image 10, causing the observed bug.

---

## 4. Proposed Improvements

### 4.1 Verify Carousel Advance Before Proceeding (Critical)

**Change:** Check the return value of `_wait_for_carousel_advance` after the resume ArrowRight. If it returns `False`:
- Retry ArrowRight + advance verification (e.g., up to 2 retries with increased wait).
- If still failing, log a clear error and optionally abort or fall back to a different resume strategy.

**Location:** `midjourney_web_controller.py`, around lines 768–770 and 793–795.

---

### 4.2 Prefer Detail-View URL for `last_url` When Resuming

**Change:** When capturing `last_url` at batch end, prefer the CDN URL from the detail view over `page.url` when both are available. This reduces dependence on SPA URL update timing. Optionally, add a short wait before capture to allow the URL to stabilize.

**Location:** `midjourney_web_controller.py`, lines 927–932.

---

### 4.3 Extract and Preserve Index from `last_url` for Resume

**Change:** Parse the `index` from the jobs URL (e.g., `?index=N`) and use it when building the resume URL. Ensure `_build_jobs_nav_url` preserves the index for jobs URLs (it already does). Add logging of the parsed index for debugging.

**Location:** `midjourney_web_controller.py`, `_build_jobs_nav_url` and resume logic.

---

### 4.4 Add Post-Resume Verification

**Change:** After advancing ArrowRight on resume, verify that the current image is not the same as the one at `last_processed_url` (e.g., by comparing normalized CDN IDs). If they match, treat it as a failed advance and retry or abort.

**Location:** `midjourney_web_controller.py`, resume block after `_wait_for_carousel_advance`.

---

### 4.5 Configurable Resume Waits

**Change:** Make resume-related waits configurable (e.g., `resume_arrow_right_wait_sec`, `carousel_advance_max_wait_sec`) so they can be increased for slower networks or multi-job boundaries.

**Location:** `config.py` and `midjourney_web_controller.py` `_w()` calls.

---

### 4.6 Optional: Position-Based Resume Fallback

**Change:** When URL-based resume fails or advance verification fails, fall back to position-based resume: click the first grid image, then press ArrowRight `start_index` times to reach the correct image. This is already partially implemented for grid lookup; ensure it is used when URL resume + advance fails.

**Location:** `midjourney_web_controller.py`, resume strategy logic.

---

### 4.7 Improved Logging

**Change:** Add logs for:
- `_wait_for_carousel_advance` result (success/failure)
- `prev_img_url` and `current_url` when advance fails
- Parsed `index` from `last_url` when resuming

**Location:** `midjourney_web_controller.py`, resume and carousel advance paths.

---

## 5. Recommended Implementation Order

1. **4.1** – Verify carousel advance (highest impact, addresses primary failure mode).
2. **4.7** – Improved logging (low risk, aids future debugging).
3. **4.4** – Post-resume verification (defense in depth).
4. **4.2** – Prefer detail-view URL for `last_url` (reduces timing issues).
5. **4.5** – Configurable waits (operational flexibility).
6. **4.3** – Index extraction (if index semantics are confirmed).
7. **4.6** – Position-based fallback (only if URL-based resume remains unreliable).

---

## 6. Files Involved

| File | Role |
|------|------|
| `integrations/midjourney/automation/midjourney_web_controller.py` | `click_button_first_n`, resume logic, `_wait_for_carousel_advance`, `_build_jobs_nav_url` |
| `features/image_generation/midjourney_runner.py` | Batch orchestration, `start_index`, `last_processed_url` passing |
| `config.py` | Wait configuration (`resume_arrow_right_wait_sec`, etc.) |

---

## 7. Summary

The most likely cause is **Hypothesis A**: the carousel advance after resume is not verified, so when it fails (e.g., at a job boundary or due to timing), the code proceeds as if it succeeded and upscales the wrong images. Implementing **4.1** (verify advance) and **4.7** (logging) should prevent this class of bug and make future issues easier to diagnose.
