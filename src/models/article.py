"""
Article data model for OpenEdu MCP Server.

This module defines the Article model for representing educational articles
from sources like Wikipedia.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import BaseModel, EducationalMetadata


@dataclass
class Article(BaseModel):
    """Model representing an educational article."""
    title: str = ""
    url: str = ""
    summary: str = ""
    content: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    last_modified: Optional[datetime] = None
    language: str = "en"
    
    # Educational metadata
    educational_metadata: EducationalMetadata = field(default_factory=EducationalMetadata)
    related_topics: List[str] = field(default_factory=list)
    multimedia_resources: List[str] = field(default_factory=list)
    
    # Source information
    source: str = "wikipedia"
    source_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "content": self.content,
            "categories": self.categories,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "language": self.language,
            "educational_metadata": self.educational_metadata.to_dict(),
            "related_topics": self.related_topics,
            "multimedia_resources": self.multimedia_resources,
            "source": self.source,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Article':
        """Create from dictionary."""
        educational_metadata = EducationalMetadata.from_dict(
            data.get("educational_metadata", {})
        )
        
        return cls(
            title=data["title"],
            url=data["url"],
            summary=data["summary"],
            content=data.get("content"),
            categories=data.get("categories", []),
            last_modified=datetime.fromisoformat(data["last_modified"]) if data.get("last_modified") else None,
            language=data.get("language", "en"),
            educational_metadata=educational_metadata,
            related_topics=data.get("related_topics", []),
            multimedia_resources=data.get("multimedia_resources", []),
            source=data.get("source", "wikipedia"),
            source_id=data.get("source_id"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )
    
    @classmethod
    def from_wikipedia(cls, wp_data: Dict[str, Any]) -> 'Article':
        """Create Article from Wikipedia API response."""
        title = wp_data.get("title", "")
        
        # Extract summary - handle different response formats
        summary = ""
        if "extract" in wp_data:
            summary = wp_data["extract"]
        elif "description" in wp_data:
            summary = wp_data["description"]
        elif "snippet" in wp_data:
            # Clean HTML tags from snippet
            import re
            snippet = wp_data["snippet"]
            summary = re.sub(r'<[^>]+>', '', snippet)
        
        # Extract URL - handle different response formats
        url = ""
        if "content_urls" in wp_data and "desktop" in wp_data["content_urls"]:
            url = wp_data["content_urls"]["desktop"].get("page", "")
        elif "fullurl" in wp_data:
            url = wp_data["fullurl"]
        elif "url" in wp_data:
            url = wp_data["url"]
        elif title:
            # Construct URL from title
            lang = wp_data.get("lang", "en")
            url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
        
        # Extract last modified
        last_modified = None
        if "timestamp" in wp_data:
            try:
                # Handle different timestamp formats
                timestamp = wp_data["timestamp"]
                if timestamp.endswith("Z"):
                    timestamp = timestamp.replace("Z", "+00:00")
                last_modified = datetime.fromisoformat(timestamp)
            except (ValueError, TypeError):
                pass
        
        # Create educational metadata with enhanced analysis
        educational_metadata = EducationalMetadata()
        
        # Combine all text for analysis
        content_text = f"{title} {summary}".lower()
        if "extract" in wp_data and wp_data["extract"]:
            content_text += f" {wp_data['extract']}"
        
        # Enhanced educational keyword analysis
        educational_keywords = {
            'basic': ["education", "school", "learning", "teaching", "student"],
            'academic': ["academic", "study", "research", "university", "college"],
            'subjects': ["science", "mathematics", "history", "literature", "geography"],
            'stem': ["biology", "chemistry", "physics", "engineering", "technology"],
            'humanities': ["philosophy", "psychology", "sociology", "anthropology", "linguistics"]
        }
        
        relevance_score = 0.0
        category_scores = {}
        
        for category, keywords in educational_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in content_text)
            if matches > 0:
                category_scores[category] = matches
                relevance_score += matches * 0.05
        
        # Boost score for educational categories
        if "categories" in wp_data:
            categories_text = " ".join([
                cat.replace("Category:", "").lower() if isinstance(cat, str)
                else cat.get("title", "").replace("Category:", "").lower()
                for cat in wp_data["categories"]
            ])
            
            educational_category_keywords = [
                "education", "academic", "science", "mathematics", "history",
                "learning", "research", "university", "school"
            ]
            
            for keyword in educational_category_keywords:
                if keyword in categories_text:
                    relevance_score += 0.1
        
        educational_metadata.educational_relevance_score = min(relevance_score, 1.0)
        
        # Extract and clean categories
        categories = []
        if "categories" in wp_data:
            for cat in wp_data["categories"]:
                if isinstance(cat, dict):
                    cat_title = cat.get("title", "").replace("Category:", "")
                elif isinstance(cat, str):
                    cat_title = cat.replace("Category:", "")
                else:
                    continue
                
                if cat_title and cat_title not in categories:
                    categories.append(cat_title)
        
        # Extract content - handle different formats
        content = wp_data.get("extract", "")
        if not content and "content" in wp_data:
            content = wp_data["content"]
        
        # Extract multimedia resources
        multimedia_resources = []
        if "thumbnail" in wp_data and wp_data["thumbnail"].get("source"):
            multimedia_resources.append(wp_data["thumbnail"]["source"])
        
        # Extract related topics from links
        related_topics = []
        if "links" in wp_data:
            related_topics = wp_data["links"][:10]  # Limit to first 10
        
        return cls(
            title=title,
            url=url,
            summary=summary,
            content=content,
            categories=categories,
            last_modified=last_modified,
            language=wp_data.get("lang", "en"),
            educational_metadata=educational_metadata,
            related_topics=related_topics,
            multimedia_resources=multimedia_resources,
            source="wikipedia",
            source_id=str(wp_data.get("pageid", ""))
        )
    
    def get_word_count(self) -> int:
        """Get approximate word count of the article."""
        text = self.summary
        if self.content:
            text += " " + self.content
        return len(text.split())
    
    def is_suitable_for_reading_level(self, max_words: int = 1000) -> bool:
        """Check if article is suitable for a specific reading level based on length."""
        return self.get_word_count() <= max_words
    
    def has_multimedia(self) -> bool:
        """Check if article has multimedia resources."""
        return len(self.multimedia_resources) > 0
    
    def get_educational_score(self) -> float:
        """Calculate educational relevance score."""
        score = self.educational_metadata.educational_relevance_score
        
        # Boost score based on educational indicators
        if self.educational_metadata.grade_levels:
            score += 0.2
        if self.educational_metadata.curriculum_alignment:
            score += 0.3
        if self.categories:
            score += 0.1
        if self.related_topics:
            score += 0.1
        if self.multimedia_resources:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0