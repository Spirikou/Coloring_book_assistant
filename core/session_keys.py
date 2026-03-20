"""Session state keys used by the Streamlit app.

This module documents the main st.session_state keys and which module/tab owns them.
Use these when reading/writing session state so names stay consistent and cleanup is easier.

Global / app.py
---------------
- workflow_state          Current design package (dict); used by Image Gen, Canva, Pinterest, Orchestration
- generated_designs        List of design states from Design Gen concept flow (for batch image gen)
- is_running              True while any long-running task (e.g. design gen) is active
- notifications           List of notification events (core/notifications)
- notification_settings   Overrides for notification toggles (Config tab)

Design Generation (features/design_generation/ui.py)
----------------------------------------------------
- design_user_request     User idea for direct-path design
- concept_variations       List of concept variations from "Generate N Concept Variations"
- selected_concepts        Selected concepts for "Generate All Designs"
- generation_queue         Queue of concepts for batch generation
- generation_results      Results from batch (legacy / progress)
- generation_current_index, generation_step_state, generation_current_step
- generation_in_progress   True while batch design gen is running
- generation_single_insert_idx  Index for single-insert batch
- design_gen_batch_result_file  Temp file path for background batch result

Image Generation (features/image_generation/ui.py)
--------------------------------------------------
- mj_status                Midjourney progress (publish, uxd, download, batch_*)
- mj_image_job_id          Current image job id (core/jobs)
- mj_automated_process, mj_cover_automated_process, mj_publish_process, mj_cover_publish_process
- mj_batch_selected_indices  Selected design indices for batch run
- mj_confirm_delete_all    Key prefix when delete-all confirmation is shown
- mj_confirm_delete_all_folder
- mj_lightbox_open, mj_lightbox_folder, mj_lightbox_index
- mj_preview_open, mj_preview_folder, mj_preview_index
- mj_selected_images       Dict[folder_str, set of image names]
- mj_sel_<name>            Per-image selection checkbox state
- mj_design_images_folders
- browser_status           From shared_checks / image gen (BROWSER_STATUS_KEY)

Orchestration (ui/tabs/orchestration_tab.py)
--------------------------------------------
- orchestrator_config      Pipeline config (design_package_path, user_request, board_name, canva_config)
- orchestrator_design_package_path
- orchestrator_process     Subprocess running the pipeline
- orchestrator_shared       Manager dict for pipeline progress
- orchestrator_manager     Multiprocessing manager

Pinterest (ui/tabs/pinterest_tab.py, ui/components/pinterest_components.py)
---------------------------------------------------------------------------
- PINTEREST_TAB_STATE_KEY  Tab-specific state key
- pinterest_workflow       PinterestPublishingWorkflow instance
- check_browser_clicked, refresh_browser_check_pinterest

Canva (ui/tabs/canva_tab.py)
----------------------------
- CANVA_TAB_STATE_KEY      Tab-specific state key
- (browser_status shared with Image Gen / shared_checks)

Shared / components (ui/components/shared_checks.py)
-----------------------------------------------------
- browser_status           Connection status dict (when used by shared_checks)
- browser_launched_<tab>   True after launch for that tab
- refresh_browser_check_<tab>
"""

__all__: list[str] = []
