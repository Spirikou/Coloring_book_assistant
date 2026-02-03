"""
Data models for Pinterest Pin Publisher.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class BookConfig:
    """Configuration loaded from coloring book JSON file."""
    title: str
    description: str
    seo_keywords: list[str]
    board_name: str
    openai_api_key: str
    
    @classmethod
    def from_json_file(cls, json_path: str, board_name: str) -> "BookConfig":
        """Load book config from JSON file in the folder."""
        import json
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Get API key from .env file (loaded via load_dotenv)
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Create a .env file with:\n"
                "OPENAI_API_KEY=sk-your-api-key-here"
            )
        
        return cls(
            title=data["title"],
            description=data["description"],
            seo_keywords=data.get("seo_keywords", []),
            board_name=board_name,
            openai_api_key=api_key,
        )


@dataclass
class PinContent:
    """Generated content for a single pin."""
    title: str
    description: str
    alt_text: str
    tags: list[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> "PinContent":
        """Create PinContent from dictionary (from LLM response)."""
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            alt_text=data.get("alt_text", data.get("description", "")[:500]),
            tags=data.get("tags", []),
        )


@dataclass
class PublishResult:
    """Result of attempting to publish a single pin."""
    image_path: str
    image_filename: str
    success: bool
    title: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": "success" if self.success else "failed",
            "timestamp": self.timestamp,
        }
        if self.title:
            result["title"] = self.title
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class ImageInfo:
    """Information about an image to be published."""
    path: str
    filename: str
    keywords: str  # Extracted from filename (minus extension)
    
    @classmethod
    def from_path(cls, path: str) -> "ImageInfo":
        """Create ImageInfo from file path, extracting keywords from filename."""
        from pathlib import Path
        p = Path(path)
        filename = p.name
        # Remove extension to get keywords
        keywords = p.stem
        return cls(
            path=str(p.resolve()),
            filename=filename,
            keywords=keywords,
        )

