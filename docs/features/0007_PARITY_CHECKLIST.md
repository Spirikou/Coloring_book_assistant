# Phase 0 Parity Checklist: Streamlit -> Next.js

Status enum: `implemented | partial | missing | blocked`

## Guide

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Guide tab with workflow instructions | `frontend/src/components/tabs/GuideTab.tsx` via `frontend/src/app/page.tsx` | none | partial | Phase 1 routing shell exists; instructional workflow content is still pending. |

## Design Generation

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Generate concept variations | `frontend/src/components/tabs/DesignGenerationTab.tsx` | `/api/jobs/design_gen_concept_variations/start` | implemented | Start flow + SSE already present. |
| Select/mix concepts then batch-generate | `frontend/src/components/tabs/DesignGenerationTab.tsx` (batch controls planned) | `/api/jobs/design_gen_batch_from_selected_concepts/start` | missing | API exists; wrapper/UI missing. |
| Single design generation run | `frontend/src/components/tabs/DesignGenerationTab.tsx` | `/api/jobs/design_gen_single/start` | implemented | Present in current Next.js tab. |
| Resume when agent asks question | `frontend/src/components/tabs/DesignGenerationTab.tsx` | `/api/jobs/{job_id}/resume` | implemented | Waiting-for-user UI exists. |
| Regenerate design components | `frontend/src/components/tabs/DesignGenerationTab.tsx` (regen panel planned) | `/api/jobs/design_gen_regenerate_component/start` | missing | API exists; wrapper/UI missing. |
| Save/update package edits | `frontend/src/components/tabs/DesignGenerationTab.tsx` (edit/save planned) | `/api/jobs/design_gen_save_or_update_design_package/start` | missing | API exists; wrapper/UI missing. |
| Rich attempt history/evaluator breakdown | `frontend/src/components/tabs/DesignGenerationTab.tsx` | mixed (`/api/design-packages/load`) | missing | Requires UI data model and rendering work. |

## Image Generation

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Image generation tab with full MJ pipeline | `frontend/src/components/tabs/ImageGenerationTab.tsx` via `frontend/src/app/page.tsx` | `/api/jobs/mj_publish/start`, `/api/jobs/mj_uxd/start`, `/api/jobs/mj_download/start`, `/api/jobs/mj_automated/start`, `/api/jobs/mj_batch_automated/start`, `/api/jobs/{job_id}/stop` | implemented | Stage actions, automated + batch automated (multi-package prompt sourcing), SSE progress, and stop control are wired. Browser readiness currently reuses `role=pinterest` until a dedicated MJ role exists. |
| Image analysis scoring job | `frontend/src/components/tabs/ImageGenerationTab.tsx` via `frontend/src/app/page.tsx` | `/api/jobs/image_analyze` | implemented | Analyze action is wired into the tab and runs via job/SSE model. |
| Browse/select/delete images | `frontend/src/components/tabs/ImageGenerationTab.tsx` via `frontend/src/app/page.tsx` | `/api/images`, `/api/images/full`, `/api/images/thumbnail`, `/api/images` (DELETE) | partial | List + select + thumbnail/full preview are implemented. Delete/curation UX remains pending. |

## Canva

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Single Canva create run | `frontend/src/components/tabs/CanvaTab.tsx` | `/api/jobs/canva_create/start` | implemented | Core flow + progress panel exists. |
| Bulk Canva creation | `frontend/src/components/tabs/CanvaTab.tsx` (bulk mode planned) | `/api/jobs/canva_create/start` | partial | Backend supports selected images; UX for bulk is missing. |
| Browser prerequisite checks | `frontend/src/components/tabs/CanvaTab.tsx` | `/api/browser/check?role=canva` | implemented | Basic connectivity check in place. |

## Pinterest

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Single Pinterest publish run | `frontend/src/components/tabs/PinterestTab.tsx` | `/api/jobs/pinterest_publish/start` | implemented | Core flow + progress panel exists. |
| Bulk publish / curated subset workflows | `frontend/src/components/tabs/PinterestTab.tsx` (bulk + curation planned) | `/api/jobs/pinterest_publish/start` | partial | Route can support subsets; UX/session orchestration missing. |
| Browser prerequisite checks | `frontend/src/components/tabs/PinterestTab.tsx` | `/api/browser/check?role=pinterest` | implemented | Basic connectivity check in place. |

## Orchestration

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Template-based sequential pipeline orchestration | `frontend/src/components/tabs/OrchestrationTab.tsx` via `frontend/src/app/page.tsx` | mixed existing jobs routes | partial | Phase 1 routing shell exists; orchestration logic and templates are still pending. |

## Progress

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Unified cross-workflow job/progress center | `frontend/src/components/tabs/ProgressTab.tsx` via `frontend/src/app/page.tsx` | `/api/jobs/{job_id}/events` | partial | Phase 1 routing shell exists; unified cross-workflow aggregation is still pending. |

## Config/Notifications

| Streamlit capability | Next.js target page/component | Backend endpoint dependency | Status | Notes |
|---|---|---|---|---|
| Settings/config operational page | `frontend/src/components/tabs/ConfigTab.tsx` via `frontend/src/app/page.tsx` | `/api/browser/check`, `/api/health` (+ future config routes) | partial | Phase 1 routing shell exists; operational settings workflows are still pending. |
| Notification center/toast history | `frontend/src/components/ToastCenter.tsx` + future notifications page | none (local today) | partial | Toast primitives exist; no durable notification center yet. |
