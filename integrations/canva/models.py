"""
Pydantic models for Canva integration input/output.

Provides structured data models for orchestrator integration.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CanvaDesignInput(BaseModel):
    """Input schema for Canva design creation."""

    folder_path: str = Field(
        description="Path to folder containing images (.png, .jpg, .jpeg, .webp)"
    )
    page_size: Optional[str] = Field(
        default=None,
        description='Page size in inches, format "WIDTHxHEIGHT" (e.g., "8.625x8.75"). If not provided, uses config defaults.'
    )
    page_count: Optional[int] = Field(
        default=None,
        description="Initial number of pages (default: 1, pages are added dynamically as images are placed)"
    )
    margin_percent: Optional[float] = Field(
        default=None,
        description="Margin percentage per side (default: 8.0)"
    )
    outline_height_percent: Optional[float] = Field(
        default=None,
        description="Height of top outline box as percentage of page height (default: 6.0)"
    )
    blank_between: Optional[bool] = Field(
        default=None,
        description="Add blank pages between images (default: True)"
    )
    dry_run: Optional[bool] = Field(
        default=False,
        description="If True, simulate the process without actually creating the design"
    )


class CanvaDesignOutput(BaseModel):
    """Output schema for Canva design creation results."""

    success: bool = Field(description="Whether the operation completed successfully")
    design_url: str = Field(description="URL of the created Canva design")
    design_id: str = Field(description="Canva design ID extracted from URL")
    total_images: int = Field(description="Total number of images found in folder")
    successful: int = Field(description="Number of images successfully processed")
    failed: int = Field(description="Number of images that failed to process")
    total_pages: int = Field(description="Total number of pages created in the design")
    blank_pages_added: int = Field(description="Number of blank pages added between images")
    message: str = Field(description="Human-readable summary message")
    errors: list[str] = Field(default_factory=list, description="List of error messages if any")
    output_json_path: str = Field(description="Path to the generated canva_output.json file")
