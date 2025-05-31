"""
Definition data model for OpenEdu MCP Server.

This module defines the Definition model for representing word definitions
from dictionary APIs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import BaseModel, EducationalMetadata


@dataclass
class Definition(BaseModel):
    """Model representing a word definition."""
    word: str = ""
    definitions: List[str] = field(default_factory=list)
    part_of_speech: str = ""
    pronunciation: Optional[str] = None
    phonetic: Optional[str] = None
    etymology: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    antonyms: List[str] = field(default_factory=list)
    
    # Educational metadata
    educational_metadata: EducationalMetadata = field(default_factory=EducationalMetadata)
    subject_areas: List[str] = field(default_factory=list)
    
    # Source information
    source: str = "dictionary_api"
    source_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "word": self.word,
            "definitions": self.definitions,
            "part_of_speech": self.part_of_speech,
            "pronunciation": self.pronunciation,
            "phonetic": self.phonetic,
            "etymology": self.etymology,
            "examples": self.examples,
            "synonyms": self.synonyms,
            "antonyms": self.antonyms,
            "educational_metadata": self.educational_metadata.to_dict(),
            "subject_areas": self.subject_areas,
            "source": self.source,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Definition':
        """Create from dictionary."""
        educational_metadata = EducationalMetadata.from_dict(
            data.get("educational_metadata", {})
        )
        
        return cls(
            word=data["word"],
            definitions=data.get("definitions", []),
            part_of_speech=data.get("part_of_speech", ""),
            pronunciation=data.get("pronunciation"),
            phonetic=data.get("phonetic"),
            etymology=data.get("etymology"),
            examples=data.get("examples", []),
            synonyms=data.get("synonyms", []),
            antonyms=data.get("antonyms", []),
            educational_metadata=educational_metadata,
            subject_areas=data.get("subject_areas", []),
            source=data.get("source", "dictionary_api"),
            source_url=data.get("source_url"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )
    
    @classmethod
    def from_dictionary_api(cls, api_data: Dict[str, Any]) -> 'Definition':
        """Create Definition from Dictionary API response."""
        word = api_data.get("word", "")
        
        # Extract meanings (definitions)
        definitions = []
        part_of_speech = ""
        examples = []
        synonyms = []
        antonyms = []
        
        meanings = api_data.get("meanings", [])
        if meanings:
            # Use the first meaning for primary part of speech
            first_meaning = meanings[0]
            part_of_speech = first_meaning.get("partOfSpeech", "")
            
            # Collect all definitions
            for meaning in meanings:
                for definition in meaning.get("definitions", []):
                    definitions.append(definition.get("definition", ""))
                    
                    # Collect examples
                    if definition.get("example"):
                        examples.append(definition["example"])
                    
                    # Collect synonyms and antonyms
                    synonyms.extend(definition.get("synonyms", []))
                    antonyms.extend(definition.get("antonyms", []))
        
        # Extract phonetics
        pronunciation = None
        phonetic = None
        phonetics = api_data.get("phonetics", [])
        if phonetics:
            for phonetic_entry in phonetics:
                if phonetic_entry.get("audio"):
                    pronunciation = phonetic_entry["audio"]
                if phonetic_entry.get("text"):
                    phonetic = phonetic_entry["text"]
                if pronunciation and phonetic:
                    break
        
        # Create educational metadata
        educational_metadata = EducationalMetadata()
        
        # Etymology is not provided by Dictionary API
        etymology = ""
        
        # Determine difficulty level based on word characteristics
        word_length = len(word)
        definition_complexity = sum(len(d.split()) for d in definitions) / max(len(definitions), 1)
        
        if word_length <= 5 and definition_complexity <= 10:
            educational_metadata.difficulty_level = "Elementary"
        elif word_length <= 8 and definition_complexity <= 15:
            educational_metadata.difficulty_level = "Intermediate"
        else:
            educational_metadata.difficulty_level = "Advanced"
        
        # Set educational relevance based on presence of examples and complexity
        relevance_score = 0.5  # Base score
        if examples:
            relevance_score += 0.2
        if synonyms or antonyms:
            relevance_score += 0.1
        if etymology:
            relevance_score += 0.1
        if phonetic:
            relevance_score += 0.1
        
        educational_metadata.educational_relevance_score = min(relevance_score, 1.0)
        
        return cls(
            word=word,
            definitions=definitions,
            part_of_speech=part_of_speech,
            pronunciation=pronunciation,
            phonetic=phonetic,
            etymology=api_data.get("etymology"),
            examples=list(set(examples)),  # Remove duplicates
            synonyms=list(set(synonyms)),  # Remove duplicates
            antonyms=list(set(antonyms)),  # Remove duplicates
            educational_metadata=educational_metadata,
            subject_areas=[],  # Can be populated based on context
            source="dictionary_api",
            source_url=f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        )
    
    def get_primary_definition(self) -> str:
        """Get the primary (first) definition."""
        return self.definitions[0] if self.definitions else ""
    
    def has_pronunciation(self) -> bool:
        """Check if pronunciation information is available."""
        return bool(self.pronunciation or self.phonetic)
    
    def get_complexity_score(self) -> float:
        """Calculate word complexity score (0-1)."""
        score = 0.0
        
        # Word length factor
        word_length = len(self.word)
        if word_length > 10:
            score += 0.3
        elif word_length > 6:
            score += 0.2
        else:
            score += 0.1
        
        # Definition complexity
        avg_def_length = sum(len(d.split()) for d in self.definitions) / max(len(self.definitions), 1)
        if avg_def_length > 20:
            score += 0.3
        elif avg_def_length > 10:
            score += 0.2
        else:
            score += 0.1
        
        # Multiple meanings increase complexity
        if len(self.definitions) > 3:
            score += 0.2
        elif len(self.definitions) > 1:
            score += 0.1
        
        # Etymology adds complexity
        if self.etymology:
            score += 0.2
        
        return min(score, 1.0)
    
    def is_suitable_for_grade_level(self, grade_level: str) -> bool:
        """Check if word is suitable for a specific grade level."""
        complexity = self.get_complexity_score()
        
        if grade_level in ["K-2"]:
            return complexity <= 0.3
        elif grade_level in ["3-5"]:
            return complexity <= 0.5
        elif grade_level in ["6-8"]:
            return complexity <= 0.7
        else:  # 9-12, College
            return True  # All words suitable for higher grades