"""
Base model classes for OpenEdu MCP Server.

This module provides base classes and common functionality for all data models
used throughout the application.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class GradeLevel(Enum):
    """Educational grade levels."""
    K_2 = "K-2"
    GRADES_3_5 = "3-5"
    GRADES_6_8 = "6-8"
    GRADES_9_12 = "9-12"
    COLLEGE = "College"

    @classmethod
    def from_string(cls, value: str) -> Optional['GradeLevel']:
        """Create GradeLevel from string value."""
        for grade_level in cls:
            if grade_level.value == value:
                return grade_level
        return None

    @classmethod
    def all_values(cls) -> list[str]:
        """Get all grade level values."""
        return [gl.value for gl in cls]


class CurriculumStandard(Enum):
    """Curriculum standards."""
    COMMON_CORE = "Common Core"
    NGSS = "NGSS"
    STATE_STANDARDS = "State Standards"

    @classmethod
    def from_string(cls, value: str) -> Optional['CurriculumStandard']:
        """Create CurriculumStandard from string value."""
        for standard in cls:
            if standard.value == value:
                return standard
        return None

    @classmethod
    def all_values(cls) -> list[str]:
        """Get all curriculum standard values."""
        return [cs.value for cs in cls]


class Subject(Enum):
    """Educational subjects."""
    MATHEMATICS = "Mathematics"
    SCIENCE = "Science"
    ENGLISH_LANGUAGE_ARTS = "English Language Arts"
    SOCIAL_STUDIES = "Social Studies"
    ARTS = "Arts"
    PHYSICAL_EDUCATION = "Physical Education"
    TECHNOLOGY = "Technology"

    @classmethod
    def from_string(cls, value: str) -> Optional['Subject']:
        """Create Subject from string value."""
        for subject in cls:
            if subject.value == value:
                return subject
        return None

    @classmethod
    def all_values(cls) -> list[str]:
        """Get all subject values."""
        return [s.value for s in cls]


@dataclass
class BaseModel(ABC):
    """Base class for all data models."""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for serialization."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model from dictionary."""
        pass

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


@dataclass
class EducationalMetadata:
    """Common educational metadata for all content types."""
    grade_levels: list[GradeLevel] = field(default_factory=list)
    curriculum_alignment: list[CurriculumStandard] = field(default_factory=list)
    educational_subjects: list[str] = field(default_factory=list)
    educational_relevance_score: float = 0.0
    reading_level: Optional[str] = None
    difficulty_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "grade_levels": [gl.value if hasattr(gl, 'value') else gl for gl in self.grade_levels],
            "curriculum_alignment": [ca.value if hasattr(ca, 'value') else ca for ca in self.curriculum_alignment],
            "educational_subjects": self.educational_subjects,
            "educational_relevance_score": self.educational_relevance_score,
            "reading_level": self.reading_level,
            "difficulty_level": self.difficulty_level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EducationalMetadata':
        """Create from dictionary."""
        return cls(
            grade_levels=[
                gl if isinstance(gl, GradeLevel) else GradeLevel.from_string(gl)
                for gl in data.get("grade_levels", [])
                if gl and (isinstance(gl, GradeLevel) or GradeLevel.from_string(gl))
            ],
            curriculum_alignment=[
                ca if isinstance(ca, CurriculumStandard) else CurriculumStandard.from_string(ca)
                for ca in data.get("curriculum_alignment", [])
                if ca and (isinstance(ca, CurriculumStandard) or CurriculumStandard.from_string(ca))
            ],
            educational_subjects=data.get("educational_subjects", []),
            educational_relevance_score=data.get("educational_relevance_score", 0.0),
            reading_level=data.get("reading_level"),
            difficulty_level=data.get("difficulty_level")
        )


@dataclass
class APIResponse:
    """Base class for API responses."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def success_response(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> 'APIResponse':
        """Create a successful response."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error_response(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> 'APIResponse':
        """Create an error response."""
        return cls(success=False, error=error, metadata=metadata)


@dataclass
class CacheEntry:
    """Cache entry model."""
    key: str
    value: Any
    content_type: str = "json"
    expires_at: datetime = field(default_factory=lambda: datetime.now())
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() > self.expires_at

    def access(self) -> None:
        """Record access to this cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "content_type": self.content_type,
            "expires_at": self.expires_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
            "size_bytes": self.size_bytes
        }