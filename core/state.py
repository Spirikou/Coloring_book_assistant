"""Unified workflow state schema for Coloring Book Assistant."""

from typing import TypedDict


class ColoringBookState(TypedDict, total=False):
    """State schema for the coloring book generation workflow."""
    # User input
    user_request: str

    # Concept research (optional - for concept-based design flow)
    concept: dict  # Pre-defined concept when skipping theme expansion
    concept_source: dict  # The concept used to generate this design (for rerun)
    parent_design_id: str  # If created via rerun from another design
    
    # Theme expansion with artistic style
    expanded_theme: dict  # {theme, artistic_style, signature_artist, unique_angle, etc.}
    theme_attempts: list  # [{attempt, content, evaluation, feedback}, ...]
    theme_score: int
    theme_passed: bool
    style_research: dict  # {style_research, artist_research}
    
    # Generated content
    title: str
    description: str
    midjourney_prompts: list
    seo_keywords: list
    
    # Per-component attempt history for UI visibility
    title_attempts: list  # [{attempt, content, evaluation, feedback}, ...]
    prompts_attempts: list
    keywords_attempts: list
    
    # Quality scores
    title_score: int
    prompts_score: int
    keywords_score: int
    title_passed: bool
    prompts_passed: bool
    keywords_passed: bool
    
    # Workflow state
    messages: list
    status: str
    
    # User interaction
    pending_question: str  # Question waiting for user answer
    user_answer: str  # User's answer to the pending question
    
    # Image generation state
    images_folder_path: str  # Path to folder containing generated images
    uploaded_images: list  # List of image file paths
    images_ready: bool  # Flag indicating images are ready for next step
    
    # Workflow tracking
    workflow_stage: str  # Current stage: "design", "images", "future_step_1", etc.
    completed_stages: list  # List of completed workflow stages
    
    # Step completion status for real-time progress updates
    theme_status: str  # "pending", "in_progress", "completed", "failed"
    title_status: str  # "pending", "in_progress", "completed", "failed"
    prompts_status: str  # "pending", "in_progress", "completed", "failed"
    keywords_status: str  # "pending", "in_progress", "completed", "failed"
    
    # Pinterest publishing state
    pinterest_board_name: str  # Pinterest board name
    pinterest_folder_path: str  # Prepared folder path for publishing
    pinterest_status: str  # "pending", "preparing", "publishing", "completed", "failed"
    pinterest_progress: dict  # Current progress info
    pinterest_results: dict  # Final publishing results
