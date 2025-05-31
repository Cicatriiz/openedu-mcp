"""
Book data model for OpenEdu MCP Server.

This module defines the Book model for representing educational books
from various sources like Open Library.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, Any, Optional, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import BaseModel, EducationalMetadata, GradeLevel, CurriculumStandard


@dataclass
class Book(BaseModel):
    """Model representing an educational book."""
    # Required fields first
    id: str = ""
    title: str = ""
    
    # Optional fields with defaults
    authors: List[str] = field(default_factory=list)
    isbn: Optional[str] = None
    isbn13: Optional[str] = None
    publication_date: Optional[date] = None
    publisher: Optional[str] = None
    subjects: List[str] = field(default_factory=list)
    description: Optional[str] = None
    cover_url: Optional[str] = None
    page_count: Optional[int] = None
    language: str = "en"
    
    # Educational metadata
    educational_metadata: EducationalMetadata = field(default_factory=EducationalMetadata)
    lexile_score: Optional[int] = None
    
    # Source information
    source: str = "open_library"
    source_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "isbn": self.isbn,
            "isbn13": self.isbn13,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "publisher": self.publisher,
            "subjects": self.subjects,
            "description": self.description,
            "cover_url": self.cover_url,
            "page_count": self.page_count,
            "language": self.language,
            "educational_metadata": self.educational_metadata.to_dict(),
            "lexile_score": self.lexile_score,
            "source": self.source,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Book':
        """Create from dictionary."""
        educational_metadata = EducationalMetadata.from_dict(
            data.get("educational_metadata", {})
        )
        
        return cls(
            id=data["id"],
            title=data["title"],
            authors=data.get("authors", []),
            isbn=data.get("isbn"),
            isbn13=data.get("isbn13"),
            publication_date=date.fromisoformat(data["publication_date"]) if data.get("publication_date") else None,
            publisher=data.get("publisher"),
            subjects=data.get("subjects", []),
            description=data.get("description"),
            cover_url=data.get("cover_url"),
            page_count=data.get("page_count"),
            language=data.get("language", "en"),
            educational_metadata=educational_metadata,
            lexile_score=data.get("lexile_score"),
            source=data.get("source", "open_library"),
            source_url=data.get("source_url"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )
    
    @classmethod
    def from_open_library(cls, ol_data: Dict[str, Any]) -> 'Book':
        """Create Book from Open Library API response."""
        # Extract basic information
        work_id = ol_data.get("key", "").replace("/works/", "")
        title = ol_data.get("title", "")
        authors = []
        
        # Extract authors
        if "author_name" in ol_data:
            authors = ol_data["author_name"]
        elif "authors" in ol_data:
            authors = [author.get("name", "") for author in ol_data["authors"]]
        
        # Extract publication info
        publication_date = None
        if "first_publish_year" in ol_data:
            try:
                publication_date = date(ol_data["first_publish_year"], 1, 1)
            except (ValueError, TypeError):
                pass
        
        # Extract ISBNs
        isbn = None
        isbn13 = None
        if "isbn" in ol_data and ol_data["isbn"]:
            for isbn_val in ol_data["isbn"]:
                if len(isbn_val) == 10:
                    isbn = isbn_val
                elif len(isbn_val) == 13:
                    isbn13 = isbn_val
        
        # Extract subjects
        subjects = ol_data.get("subject", [])
        if isinstance(subjects, str):
            subjects = [subjects]
        
        # Create educational metadata
        educational_metadata = EducationalMetadata()
        
        # Try to infer grade levels from subjects
        for subject in subjects:
            subject_lower = subject.lower()
            if any(term in subject_lower for term in ["elementary", "primary", "kindergarten"]):
                educational_metadata.grade_levels.append(GradeLevel.K_2)
            elif any(term in subject_lower for term in ["middle", "junior"]):
                educational_metadata.grade_levels.append(GradeLevel.GRADES_6_8)
            elif any(term in subject_lower for term in ["high school", "secondary"]):
                educational_metadata.grade_levels.append(GradeLevel.GRADES_9_12)
            elif any(term in subject_lower for term in ["college", "university"]):
                educational_metadata.grade_levels.append(GradeLevel.COLLEGE)
        
        # Set educational subjects
        educational_metadata.educational_subjects = subjects[:5]  # Limit to first 5
        
        return cls(
            id=work_id,
            title=title,
            authors=authors,
            isbn=isbn,
            isbn13=isbn13,
            publication_date=publication_date,
            publisher=ol_data.get("publisher", [None])[0] if ol_data.get("publisher") else None,
            subjects=subjects,
            description=ol_data.get("description", ""),
            cover_url=f"https://covers.openlibrary.org/b/id/{ol_data.get('cover_i', '')}-L.jpg" if ol_data.get('cover_i') else None,
            page_count=ol_data.get("number_of_pages_median"),
            language=ol_data.get("language", ["en"])[0] if ol_data.get("language") else "en",
            educational_metadata=educational_metadata,
            source="open_library",
            source_url=f"https://openlibrary.org/works/{work_id}"
        )
    
    def is_suitable_for_grade_level(self, grade_level: GradeLevel) -> bool:
        """Check if book is suitable for a specific grade level."""
        return grade_level in self.educational_metadata.grade_levels
    
    def has_subject(self, subject: str) -> bool:
        """Check if book covers a specific subject."""
        subject_lower = subject.lower()
        return any(
            subject_lower in s.lower() 
            for s in (self.subjects + self.educational_metadata.educational_subjects)
        )
    
    def get_educational_score(self) -> float:
        """Calculate educational relevance score."""
        score = self.educational_metadata.educational_relevance_score
        
        # Boost score based on educational indicators
        if self.educational_metadata.grade_levels:
            score += 0.2
        if self.educational_metadata.curriculum_alignment:
            score += 0.3
        if self.educational_metadata.educational_subjects:
            score += 0.1
        if self.lexile_score:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0