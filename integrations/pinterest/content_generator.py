"""
Content generator using GPT-4o-mini to customize pin content based on image keywords.
"""

import json
import logging
from openai import OpenAI

try:
    from .config import OPENAI_MODEL
except ImportError:
    # Fallback for absolute import (shouldn't happen, but just in case)
    try:
        from integrations.pinterest.config import OPENAI_MODEL
    except ImportError:
        # Last resort: try main config or use default
        try:
            from config import PINTEREST_MODEL
            OPENAI_MODEL = PINTEREST_MODEL
        except ImportError:
            OPENAI_MODEL = "gpt-4.1-mini"

from .models import BookConfig, PinContent

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates customized Pinterest pin content using GPT-4o-mini."""
    
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        self.client = OpenAI(api_key=api_key)
        self.model = OPENAI_MODEL
    
    def generate_content(self, image_keywords: str, config: BookConfig) -> PinContent:
        """
        Generate customized pin content based on image keywords.
        
        Args:
            image_keywords: Keywords extracted from image filename
            config: Book configuration with title, description, and SEO keywords
            
        Returns:
            PinContent with customized title, description, alt_text, and tags
        """
        prompt = self._build_prompt(image_keywords, config)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Pinterest content specialist for coloring books. "
                            "Generate engaging, SEO-friendly pin content. "
                            "Always respond with valid JSON only, no additional text or markdown."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500,
            )
            
            content_str = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content_str.startswith("```"):
                content_str = content_str.split("```")[1]
                if content_str.startswith("json"):
                    content_str = content_str[4:]
                content_str = content_str.strip()
            
            content_dict = json.loads(content_str)
            
            # Ensure alt_text exists, use description if not provided
            if "alt_text" not in content_dict:
                content_dict["alt_text"] = content_dict.get("description", "")[:500]
            
            return PinContent.from_dict(content_dict)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw response: {content_str}")
            return self._fallback_content(image_keywords, config)
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return self._fallback_content(image_keywords, config)
    
    def _build_prompt(self, image_keywords: str, config: BookConfig) -> str:
        """Build the prompt for the LLM."""
        # Format SEO keywords as a string
        seo_keywords_str = ", ".join(config.seo_keywords) if config.seo_keywords else "coloring book, coloring page"
        
        return f"""Generate Pinterest pin content for a coloring book page.

Book title: "{config.title}"
Book description: "{config.description[:300]}..."
SEO keywords for the book: {seo_keywords_str}

This specific image shows: "{image_keywords}" (extracted from the image filename)

Create pin content that:
1. Title: A catchy, specific title incorporating what's shown in this image (max 100 characters)
2. Description: An engaging description that mentions the specific scene AND promotes the coloring book (2-3 sentences, SEO-friendly)
3. Alt text: A brief accessible description of the image (max 500 characters)
4. Tags: 5-8 relevant Pinterest tags combining the image subject and SEO keywords

Respond with ONLY this JSON format, no other text:
{{"title": "...", "description": "...", "alt_text": "...", "tags": ["tag1", "tag2", ...]}}"""
    
    def _fallback_content(self, image_keywords: str, config: BookConfig) -> PinContent:
        """Generate basic fallback content if LLM fails."""
        # Clean up keywords (replace underscores with spaces)
        keywords_clean = image_keywords.replace("_", " ").title()
        
        # Create title from keywords + book title
        title = f"{keywords_clean} - {config.title}"
        if len(title) > 100:
            title = f"{keywords_clean} Coloring Page"[:100]
        
        # Simple description
        description = f"Beautiful {keywords_clean.lower()} coloring page from '{config.title}'. {config.description[:200]}"
        
        # Combine image keywords with SEO keywords for tags
        tags = [kw.replace("_", " ") for kw in image_keywords.split("_") if len(kw) > 2]
        tags.extend(config.seo_keywords[:3])
        tags = list(set(tags))[:8]  # Dedupe and limit
        
        return PinContent(
            title=title,
            description=description,
            alt_text=f"Coloring page illustration of {keywords_clean.lower()}",
            tags=tags,
        )


def generate_pin_content(image_keywords: str, config: BookConfig) -> PinContent:
    """
    Convenience function to generate pin content.
    
    Args:
        image_keywords: Keywords from image filename
        config: Book configuration
        
    Returns:
        Generated PinContent
    """
    generator = ContentGenerator(config.openai_api_key)
    return generator.generate_content(image_keywords, config)
