"""
Research Paper data model for OpenEdu MCP Server.

This module defines the ResearchPaper model for representing academic papers
from sources like arXiv.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, Any, Optional, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import BaseModel, EducationalMetadata


class ResearchPaper(BaseModel):
    """Model representing an academic research paper."""
    
    def __init__(
        self,
        arxiv_id: str,
        title: str,
        authors: List[str],
        abstract: str,
        subjects: List[str],
        publication_date: date,
        pdf_url: str,
        doi: Optional[str] = None,
        journal: Optional[str] = None,
        methodology: Optional[str] = None,
        source: str = "arxiv",
        source_url: Optional[str] = None,
        educational_metadata: Optional[EducationalMetadata] = None,
        key_findings: Optional[List[str]] = None,
        educational_applications: Optional[List[str]] = None,
        target_audience: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """Initialize ResearchPaper instance."""
        # Initialize BaseModel fields manually since it's a dataclass
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        
        self.arxiv_id = arxiv_id
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.subjects = subjects
        self.publication_date = publication_date
        self.pdf_url = pdf_url
        self.doi = doi
        self.journal = journal
        self.methodology = methodology
        self.source = source
        self.source_url = source_url
        self.educational_metadata = educational_metadata or EducationalMetadata()
        self.key_findings = key_findings or []
        self.educational_applications = educational_applications or []
        self.target_audience = target_audience or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "subjects": self.subjects,
            "publication_date": self.publication_date.isoformat(),
            "pdf_url": self.pdf_url,
            "doi": self.doi,
            "journal": self.journal,
            "educational_metadata": self.educational_metadata.to_dict(),
            "methodology": self.methodology,
            "key_findings": self.key_findings,
            "educational_applications": self.educational_applications,
            "target_audience": self.target_audience,
            "source": self.source,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchPaper':
        """Create from dictionary."""
        educational_metadata = EducationalMetadata.from_dict(
            data.get("educational_metadata", {})
        )
        
        return cls(
            arxiv_id=data["arxiv_id"],
            title=data["title"],
            authors=data.get("authors", []),
            abstract=data["abstract"],
            subjects=data.get("subjects", []),
            publication_date=date.fromisoformat(data["publication_date"]),
            pdf_url=data["pdf_url"],
            doi=data.get("doi"),
            journal=data.get("journal"),
            educational_metadata=educational_metadata,
            methodology=data.get("methodology"),
            key_findings=data.get("key_findings", []),
            educational_applications=data.get("educational_applications", []),
            target_audience=data.get("target_audience", []),
            source=data.get("source", "arxiv"),
            source_url=data.get("source_url"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )
    
    @classmethod
    def from_arxiv(cls, arxiv_data: Dict[str, Any]) -> 'ResearchPaper':
        """Create ResearchPaper from arXiv API response."""
        # Extract arXiv ID
        arxiv_id = arxiv_data.get("id", "").split("/")[-1]
        
        # Extract basic information
        title = arxiv_data.get("title", "").strip()
        abstract = arxiv_data.get("summary", "").strip()
        
        # Extract authors
        authors = []
        if "authors" in arxiv_data:
            if isinstance(arxiv_data["authors"], list):
                authors = [author.get("name", "") for author in arxiv_data["authors"]]
            else:
                authors = [arxiv_data["authors"].get("name", "")]
        elif "author" in arxiv_data:
            authors = [arxiv_data["author"]]
        
        # Extract publication date
        publication_date = date.today()
        if "published" in arxiv_data:
            try:
                pub_datetime = datetime.fromisoformat(arxiv_data["published"].replace("Z", "+00:00"))
                publication_date = pub_datetime.date()
            except (ValueError, TypeError):
                pass
        
        # Extract subjects/categories
        subjects = []
        if "categories" in arxiv_data:
            if isinstance(arxiv_data["categories"], list):
                subjects = arxiv_data["categories"]
            else:
                subjects = [arxiv_data["categories"]]
        elif "category" in arxiv_data:
            subjects = [arxiv_data["category"]]
        
        # Extract URLs
        pdf_url = ""
        source_url = ""
        if "links" in arxiv_data:
            for link in arxiv_data["links"]:
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href", "")
                elif link.get("rel") == "alternate":
                    source_url = link.get("href", "")
        
        if not pdf_url and arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        if not source_url and arxiv_id:
            source_url = f"https://arxiv.org/abs/{arxiv_id}"
        
        # Extract DOI if available
        doi = arxiv_data.get("doi")
        
        # Create educational metadata
        educational_metadata = EducationalMetadata()
        
        # Determine educational relevance based on subjects and abstract
        educational_subjects = []
        abstract_lower = abstract.lower()
        
        # Map arXiv categories to educational subjects
        subject_mapping = {
            "math": "Mathematics",
            "physics": "Science",
            "cs": "Technology",
            "stat": "Mathematics",
            "bio": "Science",
            "chem": "Science",
            "econ": "Social Studies",
            "q-fin": "Social Studies"
        }
        
        for subject in subjects:
            subject_prefix = subject.split(".")[0].lower()
            if subject_prefix in subject_mapping:
                educational_subjects.append(subject_mapping[subject_prefix])
        
        educational_metadata.educational_subjects = list(set(educational_subjects))
        
        # Check for educational keywords in abstract
        educational_keywords = [
            "education", "teaching", "learning", "pedagogy", "curriculum",
            "student", "classroom", "instruction", "assessment", "educational"
        ]
        
        relevance_score = 0.0
        for keyword in educational_keywords:
            if keyword in abstract_lower:
                relevance_score += 0.2
        
        # Boost score for certain subjects
        if any(subj in ["Mathematics", "Science", "Technology"] for subj in educational_subjects):
            relevance_score += 0.3
        
        educational_metadata.educational_relevance_score = min(relevance_score, 1.0)
        
        # Determine target audience based on complexity
        target_audience = ["Researchers", "Graduate Students"]
        if any(term in abstract_lower for term in ["undergraduate", "introductory", "basic"]):
            target_audience.append("Undergraduate Students")
        if any(term in abstract_lower for term in ["high school", "secondary"]):
            target_audience.append("High School Teachers")
        
        return cls(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            subjects=subjects,
            publication_date=publication_date,
            pdf_url=pdf_url,
            doi=doi,
            journal=arxiv_data.get("journal"),
            educational_metadata=educational_metadata,
            methodology=None,  # Can be extracted from full text later
            key_findings=[],  # Can be extracted from full text later
            educational_applications=[],  # Can be populated based on analysis
            target_audience=target_audience,
            source="arxiv",
            source_url=source_url
        )
    
    def get_primary_subject(self) -> str:
        """Get the primary subject category."""
        return self.subjects[0] if self.subjects else ""
    
    def is_recent(self, days: int = 365) -> bool:
        """Check if paper was published recently."""
        days_since_publication = (date.today() - self.publication_date).days
        return days_since_publication <= days
    
    def has_educational_focus(self) -> bool:
        """Check if paper has explicit educational focus."""
        educational_terms = [
            "education", "teaching", "learning", "pedagogy", "curriculum",
            "instruction", "classroom", "student", "educational"
        ]
        
        text_to_check = (self.title + " " + self.abstract).lower()
        return any(term in text_to_check for term in educational_terms)
    
    def get_complexity_level(self) -> str:
        """Determine the complexity level of the paper."""
        abstract_length = len(self.abstract.split())
        technical_terms = [
            "algorithm", "theorem", "proof", "analysis", "methodology",
            "framework", "model", "optimization", "statistical"
        ]
        
        technical_count = sum(1 for term in technical_terms if term in self.abstract.lower())
        
        if abstract_length > 200 and technical_count > 5:
            return "Advanced"
        elif abstract_length > 150 and technical_count > 3:
            return "Intermediate"
        else:
            return "Introductory"
    
    def is_suitable_for_educators(self) -> bool:
        """Check if paper is suitable for educators."""
        return (
            self.has_educational_focus() or
            self.educational_metadata.educational_relevance_score > 0.5 or
            "High School Teachers" in self.target_audience or
            "Undergraduate Students" in self.target_audience
        )