"""
Dictionary tools for OpenEdu MCP Server.

This module provides MCP tool implementations for Dictionary API integration,
including educational filtering, vocabulary analysis, and word definition functionality.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base_tool import BaseTool
from api.dictionary import DictionaryClient
from models.definition import Definition
from models.base import GradeLevel, EducationalMetadata, CurriculumStandard
from config import Config
from services.cache_service import CacheService
from services.rate_limiting_service import RateLimitingService
from services.usage_service import UsageService
from exceptions import ToolError, ValidationError, APIError

logger = logging.getLogger(__name__)


class DictionaryTool(BaseTool):
    """Tool for Dictionary API integration with educational features."""
    
    def __init__(
        self,
        config: Config,
        cache_service: CacheService,
        rate_limiting_service: RateLimitingService,
        usage_service: UsageService
    ):
        """
        Initialize Dictionary tool.
        
        Args:
            config: Application configuration
            cache_service: Cache service instance
            rate_limiting_service: Rate limiting service instance
            usage_service: Usage tracking service instance
        """
        super().__init__(config, cache_service, rate_limiting_service, usage_service)
        self.client = DictionaryClient(config)
        
        # Educational filtering configuration
        self.min_educational_relevance = config.education.content_filters.min_educational_relevance
        self.enable_age_appropriate = config.education.content_filters.enable_age_appropriate
        self.enable_curriculum_alignment = config.education.content_filters.enable_curriculum_alignment
        
        # Vocabulary complexity thresholds
        self.complexity_thresholds = {
            GradeLevel.K_2: 0.3,
            GradeLevel.GRADES_3_5: 0.5,
            GradeLevel.GRADES_6_8: 0.7,
            GradeLevel.GRADES_9_12: 0.85,
            GradeLevel.COLLEGE: 1.0
        }
        
        # Subject-specific vocabulary indicators
        self.subject_indicators = {
            "science": ["biology", "chemistry", "physics", "scientific", "experiment", "hypothesis"],
            "mathematics": ["equation", "formula", "theorem", "geometric", "algebraic", "calculus"],
            "literature": ["narrative", "metaphor", "symbolism", "literary", "poetic", "prose"],
            "history": ["historical", "ancient", "medieval", "revolution", "civilization", "empire"],
            "geography": ["geographical", "climate", "terrain", "continental", "oceanic", "topographic"],
            "social_studies": ["society", "cultural", "political", "economic", "democratic", "citizenship"]
        }
    
    @property
    def api_name(self) -> str:
        """Name of the API this tool uses for rate limiting."""
        return "dictionary"
    
    async def get_word_definition(
        self,
        word: str,
        grade_level: Optional[str] = None,
        include_pronunciation: bool = True,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get educational word definition with grade-level filtering.
        
        Args:
            word: Word to define
            grade_level: Target grade level for appropriate complexity
            include_pronunciation: Whether to include pronunciation information
            user_session: User session identifier
            
        Returns:
            Word definition with educational metadata
            
        Raises:
            ValidationError: If word is invalid
            ToolError: If definition retrieval fails
        """
        async def _get_definition():
            # Get comprehensive word data from Dictionary API
            word_data = await self.client.get_comprehensive_data(word)
            
            if not word_data:
                raise ToolError(f"Word not found: {word}", self.tool_name)
            
            # Convert to Definition model with educational enrichment
            definition = Definition.from_dictionary_api(word_data)
            
            # Enrich with educational metadata
            definition = await self._enrich_educational_metadata(
                definition,
                grade_level=grade_level
            )
            
            # Apply grade-level filtering if specified
            if grade_level and not definition.is_suitable_for_grade_level(grade_level):
                # Simplify definitions for lower grade levels
                definition = self._simplify_for_grade_level(definition, grade_level)
            
            # Add pronunciation if requested
            if include_pronunciation and not definition.has_pronunciation():
                try:
                    phonetics = await self.client.get_phonetics(word)
                    if phonetics:
                        definition.phonetic = phonetics.get("text")
                        definition.pronunciation = phonetics.get("audio")
                except Exception as e:
                    logger.warning(f"Failed to get pronunciation for {word}: {e}")
            
            result = definition.to_dict()
            
            # Add educational analysis
            result["vocabulary_analysis"] = self._analyze_vocabulary_complexity(definition)
            result["educational_recommendations"] = self._generate_educational_recommendations(definition, grade_level)
            
            return result
        
        return await self.execute_with_monitoring(
            "get_word_definition",
            _get_definition,
            user_session=user_session
        )
    
    async def get_vocabulary_analysis(
        self,
        word: str,
        context: Optional[str] = None,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze word complexity and educational value.
        
        Args:
            word: Word to analyze
            context: Optional context for better analysis
            user_session: User session identifier
            
        Returns:
            Vocabulary analysis with educational insights
            
        Raises:
            ValidationError: If word is invalid
            ToolError: If analysis fails
        """
        async def _analyze_vocabulary():
            # Get word definition
            word_data = await self.client.get_comprehensive_data(word)
            
            if not word_data:
                raise ToolError(f"Word not found: {word}", self.tool_name)
            
            definition = Definition.from_dictionary_api(word_data)
            definition = await self._enrich_educational_metadata(definition)
            
            # Perform comprehensive vocabulary analysis
            analysis = {
                "word": word,
                "complexity_score": definition.get_complexity_score(),
                "difficulty_level": definition.educational_metadata.difficulty_level,
                "grade_level_recommendations": [gl.value for gl in self._determine_appropriate_grade_levels(definition)],
                "subject_classifications": self._classify_by_subject(definition),
                "vocabulary_tier": self._determine_vocabulary_tier(definition),
                "learning_objectives": self._generate_learning_objectives(definition),
                "usage_frequency": self._estimate_usage_frequency(definition),
                "morphological_analysis": self._analyze_morphology(word),
                "semantic_relationships": {
                    "synonyms": definition.synonyms[:5],  # Limit to top 5
                    "antonyms": definition.antonyms[:5],
                    "related_words": self._find_related_words(definition)
                },
                "educational_value": self._assess_educational_value(definition, context)
            }
            
            return analysis
        
        return await self.execute_with_monitoring(
            "get_vocabulary_analysis",
            _analyze_vocabulary,
            user_session=user_session
        )
    
    async def get_word_examples(
        self,
        word: str,
        grade_level: Optional[str] = None,
        subject: Optional[str] = None,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get educational examples and usage contexts.
        
        Args:
            word: Word to find examples for
            grade_level: Target grade level for appropriate examples
            subject: Subject area for context-specific examples
            user_session: User session identifier
            
        Returns:
            Educational examples with context
            
        Raises:
            ValidationError: If word is invalid
            ToolError: If example retrieval fails
        """
        async def _get_examples():
            # Get examples from Dictionary API
            examples = await self.client.get_word_examples(word)
            
            if not examples:
                # Generate educational examples if none available
                examples = self._generate_educational_examples(word, grade_level, subject)
            
            # Filter and enhance examples for educational use
            educational_examples = []
            for example in examples:
                enhanced_example = self._enhance_example_for_education(
                    example, word, grade_level, subject
                )
                if enhanced_example:
                    educational_examples.append(enhanced_example)
            
            # Add subject-specific examples if requested
            if subject:
                subject_examples = self._generate_subject_specific_examples(word, subject, grade_level)
                educational_examples.extend(subject_examples)
            
            return {
                "word": word,
                "examples": educational_examples[:10],  # Limit to 10 examples
                "usage_tips": self._generate_usage_tips(word, grade_level),
                "common_mistakes": self._identify_common_mistakes(word),
                "grade_level": grade_level,
                "subject": subject
            }
        
        return await self.execute_with_monitoring(
            "get_word_examples",
            _get_examples,
            user_session=user_session
        )
    
    async def get_pronunciation_guide(
        self,
        word: str,
        include_audio: bool = True,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get phonetic information for language learning.
        
        Args:
            word: Word to get pronunciation for
            include_audio: Whether to include audio URL
            user_session: User session identifier
            
        Returns:
            Pronunciation guide with phonetic information
            
        Raises:
            ValidationError: If word is invalid
            ToolError: If pronunciation retrieval fails
        """
        async def _get_pronunciation():
            # Get phonetics from Dictionary API
            phonetics = await self.client.get_phonetics(word)
            
            if not phonetics:
                raise ToolError(f"Pronunciation not available for: {word}", self.tool_name)
            
            # Enhance pronunciation guide for educational use
            guide = {
                "word": word,
                "phonetic_spelling": phonetics.get("text", ""),
                "audio_url": phonetics.get("audio", "") if include_audio else "",
                "pronunciation_tips": self._generate_pronunciation_tips(word, phonetics),
                "syllable_breakdown": self._break_into_syllables(word),
                "stress_pattern": self._identify_stress_pattern(word, phonetics),
                "rhyming_words": self._find_rhyming_words(word),
                "phonetic_rules": self._explain_phonetic_rules(word),
                "difficulty_level": self._assess_pronunciation_difficulty(word, phonetics)
            }
            
            return guide
        
        return await self.execute_with_monitoring(
            "get_pronunciation_guide",
            _get_pronunciation,
            user_session=user_session
        )
    
    async def get_related_vocabulary(
        self,
        word: str,
        relationship_type: str = "all",
        grade_level: Optional[str] = None,
        limit: int = 10,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get synonyms, antonyms, and related educational terms.
        
        Args:
            word: Base word
            relationship_type: Type of relationship (synonyms, antonyms, related, all)
            grade_level: Target grade level for appropriate vocabulary
            limit: Maximum number of related words
            user_session: User session identifier
            
        Returns:
            Related vocabulary with educational context
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If vocabulary retrieval fails
        """
        async def _get_related():
            # Validate relationship type
            valid_types = ["synonyms", "antonyms", "related", "all"]
            if relationship_type not in valid_types:
                raise ValidationError(f"Invalid relationship type. Must be one of: {valid_types}")
            
            # Get word data
            word_data = await self.client.get_comprehensive_data(word)
            
            if not word_data:
                raise ToolError(f"Word not found: {word}", self.tool_name)
            
            definition = Definition.from_dictionary_api(word_data)
            
            # Ensure we use the original word parameter, not the API response word
            related_vocab = {
                "word": word,  # Always use the original query word
                "base_word": word,  # Always use the original query word
                "api_word": definition.word,  # Include the API response word for reference
                "relationships": {}
            }
            
            # Get synonyms
            if relationship_type in ["synonyms", "all"]:
                synonyms = await self._get_educational_synonyms(definition, grade_level, limit)
                related_vocab["relationships"]["synonyms"] = synonyms
            
            # Get antonyms
            if relationship_type in ["antonyms", "all"]:
                antonyms = await self._get_educational_antonyms(definition, grade_level, limit)
                related_vocab["relationships"]["antonyms"] = antonyms
            
            # Get related words
            if relationship_type in ["related", "all"]:
                related_words = await self._get_educational_related_words(definition, grade_level, limit)
                related_vocab["relationships"]["related"] = related_words
            
            # Add educational context
            related_vocab["educational_notes"] = self._generate_vocabulary_notes(definition, grade_level)
            related_vocab["learning_activities"] = self._suggest_vocabulary_activities(definition, grade_level)
            
            return related_vocab
        
        return await self.execute_with_monitoring(
            "get_related_vocabulary",
            _get_related,
            user_session=user_session
        )
    
    async def _enrich_educational_metadata(
        self,
        definition: Definition,
        grade_level: Optional[str] = None
    ) -> Definition:
        """
        Enrich definition with educational metadata.
        
        Args:
            definition: Definition instance to enrich
            grade_level: Target grade level for relevance scoring
            
        Returns:
            Enriched definition instance
        """
        # Calculate educational relevance score
        relevance_score = self._calculate_educational_relevance(definition, grade_level)
        definition.educational_metadata.educational_relevance_score = relevance_score
        
        # Analyze vocabulary complexity
        complexity_analysis = self._analyze_vocabulary_complexity(definition)
        definition.educational_metadata.difficulty_level = complexity_analysis.get("difficulty_level")
        
        # Determine appropriate grade levels
        grade_levels = self._determine_appropriate_grade_levels(definition)
        definition.educational_metadata.grade_levels = grade_levels
        
        # Classify by subject areas
        subject_areas = self._classify_by_subject(definition)
        definition.subject_areas = subject_areas
        
        # Analyze curriculum alignment
        curriculum_alignment = self._analyze_curriculum_alignment(definition)
        definition.educational_metadata.curriculum_alignment = curriculum_alignment.get("standards", [])
        
        return definition
    
    def _calculate_educational_relevance(
        self,
        definition: Definition,
        target_grade_level: Optional[str] = None
    ) -> float:
        """Calculate educational relevance score for a word definition."""
        score = 0.0
        
        # Base score for having multiple definitions (indicates important word)
        if len(definition.definitions) > 1:
            score += 0.2
        
        # Score for having examples (helps with understanding)
        if definition.examples:
            score += 0.2
        
        # Score for having synonyms/antonyms (vocabulary building)
        if definition.synonyms or definition.antonyms:
            score += 0.1
        
        # Score for pronunciation information (language learning)
        if definition.has_pronunciation():
            score += 0.1
        
        # Subject area relevance
        if definition.subject_areas:
            score += 0.2
        
        # Grade level appropriateness
        if target_grade_level and definition.is_suitable_for_grade_level(target_grade_level):
            score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_vocabulary_complexity(self, definition: Definition) -> Dict[str, Any]:
        """Analyze vocabulary complexity and difficulty."""
        word = definition.word
        complexity_score = definition.get_complexity_score()
        
        # Determine difficulty level
        if complexity_score <= 0.3:
            difficulty_level = "Elementary"
        elif complexity_score <= 0.5:
            difficulty_level = "Intermediate"
        elif complexity_score <= 0.7:
            difficulty_level = "Advanced"
        else:
            difficulty_level = "Expert"
        
        return {
            "complexity_score": complexity_score,
            "difficulty_level": difficulty_level,
            "word_length": len(word),
            "syllable_count": self._count_syllables(word),
            "definition_complexity": sum(len(d.split()) for d in definition.definitions) / max(len(definition.definitions), 1),
            "has_multiple_meanings": len(definition.definitions) > 1,
            "technical_indicators": self._count_technical_indicators(definition)
        }
    
    def _determine_appropriate_grade_levels(self, definition: Definition) -> List[GradeLevel]:
        """Determine appropriate grade levels for a word."""
        complexity = definition.get_complexity_score()
        appropriate_levels = []
        
        for grade_level, threshold in self.complexity_thresholds.items():
            if complexity <= threshold:
                appropriate_levels.append(grade_level)
        
        # Ensure at least one grade level is included
        if not appropriate_levels:
            appropriate_levels = [GradeLevel.COLLEGE]
        
        return appropriate_levels
    
    def _classify_by_subject(self, definition: Definition) -> List[str]:
        """Classify word by academic subjects."""
        subjects = []
        content_text = f"{definition.word} {' '.join(definition.definitions)}".lower()
        
        for subject, indicators in self.subject_indicators.items():
            if any(indicator in content_text for indicator in indicators):
                subjects.append(subject)
        
        return subjects
    
    def _analyze_curriculum_alignment(self, definition: Definition) -> Dict[str, Any]:
        """Analyze curriculum alignment for the word."""
        # This is a simplified implementation
        # In a real system, this would align with specific curriculum standards
        
        subjects = self._classify_by_subject(definition)
        complexity = definition.get_complexity_score()
        
        # Determine relevant curriculum standards based on subjects and complexity
        standards = []
        if any(subj in ["science", "mathematics"] for subj in subjects):
            standards.append(CurriculumStandard.NGSS)
        if complexity > 0.3:  # Academic vocabulary
            standards.append(CurriculumStandard.COMMON_CORE)
        
        alignment = {
            "subjects": subjects,
            "standards": standards,
            "learning_objectives": self._generate_learning_objectives(definition),
            "assessment_potential": complexity > 0.3  # Words above basic complexity are good for assessment
        }
        
        return alignment
    
    def _simplify_for_grade_level(self, definition: Definition, grade_level: str) -> Definition:
        """Simplify definitions for lower grade levels."""
        if grade_level in ["K-2", "3-5"]:
            # Keep only the simplest definitions
            simplified_definitions = []
            for def_text in definition.definitions:
                if len(def_text.split()) <= 15:  # Simple definitions only
                    simplified_definitions.append(def_text)
            
            if simplified_definitions:
                definition.definitions = simplified_definitions[:2]  # Max 2 definitions
            
            # Keep only simple examples
            simple_examples = []
            for example in definition.examples:
                if len(example.split()) <= 10:  # Simple examples only
                    simple_examples.append(example)
            
            definition.examples = simple_examples[:3]  # Max 3 examples
        
        return definition
    
    def _generate_educational_recommendations(
        self,
        definition: Definition,
        grade_level: Optional[str]
    ) -> Dict[str, Any]:
        """Generate educational recommendations for using the word."""
        recommendations = {
            "teaching_strategies": [],
            "learning_activities": [],
            "assessment_ideas": [],
            "cross_curricular_connections": []
        }
        
        complexity = definition.get_complexity_score()
        
        # Teaching strategies based on complexity
        if complexity <= 0.3:
            recommendations["teaching_strategies"].extend([
                "Use visual aids and pictures",
                "Practice with simple sentences",
                "Connect to familiar concepts"
            ])
        elif complexity <= 0.7:
            recommendations["teaching_strategies"].extend([
                "Provide context and examples",
                "Break down into parts",
                "Use in multiple contexts"
            ])
        else:
            recommendations["teaching_strategies"].extend([
                "Explore etymology and word origins",
                "Analyze in academic contexts",
                "Compare with related terms"
            ])
        
        # Learning activities
        if definition.synonyms:
            recommendations["learning_activities"].append("Synonym matching exercises")
        if definition.examples:
            recommendations["learning_activities"].append("Context clue practice")
        if definition.has_pronunciation():
            recommendations["learning_activities"].append("Pronunciation practice")
        
        # Subject connections
        for subject in definition.subject_areas:
            recommendations["cross_curricular_connections"].append(f"Use in {subject} lessons")
        
        return recommendations
    
    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for a word."""
        # Simple syllable counting heuristic
        word = word.lower()
        vowels = "aeiouy"
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent e
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1
        
        return max(syllable_count, 1)
    
    def _count_technical_indicators(self, definition: Definition) -> int:
        """Count technical/academic indicators in definitions."""
        technical_terms = [
            "technical", "scientific", "academic", "formal", "specialized",
            "professional", "medical", "legal", "mathematical", "theoretical"
        ]
        
        content = " ".join(definition.definitions).lower()
        return sum(1 for term in technical_terms if term in content)
    
    def _determine_vocabulary_tier(self, definition: Definition) -> str:
        """Determine vocabulary tier (Tier 1: Basic, Tier 2: Academic, Tier 3: Domain-specific)."""
        complexity = definition.get_complexity_score()
        has_subject_areas = bool(definition.subject_areas)
        
        if complexity <= 0.3 and not has_subject_areas:
            return "Tier 1 (Basic)"
        elif complexity <= 0.7 and not has_subject_areas:
            return "Tier 2 (Academic)"
        else:
            return "Tier 3 (Domain-specific)"
    
    def _generate_learning_objectives(self, definition: Definition) -> List[str]:
        """Generate learning objectives for the word."""
        objectives = []
        
        objectives.append(f"Students will understand the meaning of '{definition.word}'")
        
        if definition.examples:
            objectives.append(f"Students will use '{definition.word}' correctly in context")
        
        if definition.synonyms:
            objectives.append(f"Students will identify synonyms for '{definition.word}'")
        
        if definition.has_pronunciation():
            objectives.append(f"Students will pronounce '{definition.word}' correctly")
        
        if definition.subject_areas:
            for subject in definition.subject_areas:
                objectives.append(f"Students will apply '{definition.word}' in {subject} contexts")
        
        return objectives
    
    def _estimate_usage_frequency(self, definition: Definition) -> str:
        """Estimate how frequently the word is used."""
        # This is a simplified heuristic
        # In a real system, this would use actual frequency data
        
        complexity = definition.get_complexity_score()
        
        if complexity <= 0.3:
            return "High frequency (common word)"
        elif complexity <= 0.5:
            return "Medium frequency (academic word)"
        elif complexity <= 0.7:
            return "Low frequency (specialized word)"
        else:
            return "Very low frequency (technical/rare word)"
    
    def _analyze_morphology(self, word: str) -> Dict[str, Any]:
        """Analyze word structure and morphology."""
        analysis = {
            "root": word,  # Simplified - would need morphological analyzer
            "prefixes": [],
            "suffixes": [],
            "word_family": []
        }
        
        # Simple suffix detection
        common_suffixes = ["-ing", "-ed", "-er", "-est", "-ly", "-tion", "-sion", "-ness", "-ment"]
        for suffix in common_suffixes:
            if word.endswith(suffix.replace("-", "")):
                analysis["suffixes"].append(suffix)
                analysis["root"] = word[:-len(suffix.replace("-", ""))]
                break
        
        # Simple prefix detection
        common_prefixes = ["un-", "re-", "pre-", "dis-", "mis-", "over-", "under-", "out-"]
        for prefix in common_prefixes:
            if word.startswith(prefix.replace("-", "")):
                analysis["prefixes"].append(prefix)
                analysis["root"] = word[len(prefix.replace("-", "")):]
                break
        
        return analysis
    
    def _find_related_words(self, definition: Definition) -> List[str]:
        """Find morphologically related words."""
        # This is a simplified implementation
        # In a real system, this would use a morphological database
        
        word = definition.word
        related = []
        
        # Add common variations
        if word.endswith("ing"):
            base = word[:-3]
            related.extend([base, base + "ed", base + "er"])
        elif word.endswith("ed"):
            base = word[:-2]
            related.extend([base, base + "ing", base + "er"])
        
        return related[:5]  # Limit to 5 related words
    
    def _assess_educational_value(self, definition: Definition, context: Optional[str]) -> Dict[str, Any]:
        """Assess the educational value of the word."""
        value = {
            "vocabulary_building": len(definition.synonyms) > 0,
            "concept_development": len(definition.definitions) > 1,
            "cross_curricular": len(definition.subject_areas) > 1,
            "language_development": definition.has_pronunciation(),
            "critical_thinking": definition.get_complexity_score() > 0.5,
            "overall_score": definition.educational_metadata.educational_relevance_score
        }
        
        return value
    
    def _generate_educational_examples(
        self,
        word: str,
        grade_level: Optional[str],
        subject: Optional[str]
    ) -> List[str]:
        """Generate educational examples when none are available from API."""
        # This is a simplified implementation
        # In a real system, this would use a more sophisticated example generator
        
        examples = []
        
        if grade_level in ["K-2"]:
            examples.append(f"The {word} is important.")
            examples.append(f"I can see the {word}.")
        elif grade_level in ["3-5"]:
            examples.append(f"Students should understand what {word} means.")
            examples.append(f"The teacher explained the {word} clearly.")
        else:
            examples.append(f"The concept of {word} is fundamental to understanding this topic.")
            examples.append(f"Researchers have studied {word} extensively.")
        
        return examples
    
    def _enhance_example_for_education(
        self,
        example: str,
        word: str,
        grade_level: Optional[str],
        subject: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Enhance an example sentence for educational use."""
        # Check if example is appropriate for grade level
        if grade_level in ["K-2", "3-5"] and len(example.split()) > 15:
            return None  # Too complex for young learners
        
        enhanced = {
            "sentence": example,
            "target_word": word,
            "context_clues": self._identify_context_clues(example, word),
            "educational_focus": self._identify_educational_focus(example, subject),
            "difficulty_level": "appropriate" if len(example.split()) <= 20 else "challenging"
        }
        
        return enhanced
    
    def _identify_context_clues(self, example: str, word: str) -> List[str]:
        """Identify context clues in an example sentence."""
        # Simplified implementation
        words = example.lower().split()
        word_index = -1
        
        try:
            word_index = words.index(word.lower())
        except ValueError:
            return []
        
        clues = []
        
        # Look for clues around the target word
        for i in range(max(0, word_index - 2), min(len(words), word_index + 3)):
            if i != word_index and len(words[i]) > 3:
                clues.append(words[i])
        
        return clues[:3]  # Limit to 3 clues
    
    def _identify_educational_focus(self, example: str, subject: Optional[str]) -> str:
        """Identify the educational focus of an example."""
        if subject and subject in example.lower():
            return f"{subject} context"
        
        # Look for educational indicators
        educational_words = ["learn", "study", "understand", "explain", "analyze", "compare"]
        for edu_word in educational_words:
            if edu_word in example.lower():
                return f"Learning-focused ({edu_word})"
        
        return "General usage"
    
    def _generate_subject_specific_examples(
        self,
        word: str,
        subject: str,
        grade_level: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Generate subject-specific examples."""
        examples = []
        
        # This is a simplified implementation
        # In a real system, this would have extensive subject-specific templates
        
        if subject == "science":
            examples.append({
                "sentence": f"Scientists use the term {word} to describe this phenomenon.",
                "target_word": word,
                "context_clues": ["scientists", "phenomenon"],
                "educational_focus": "Science vocabulary",
                "difficulty_level": "appropriate"
            })
        elif subject == "mathematics":
            examples.append({
                "sentence": f"In mathematics, {word} represents an important concept.",
                "target_word": word,
                "context_clues": ["mathematics", "concept"],
                "educational_focus": "Math vocabulary",
                "difficulty_level": "appropriate"
            })
        
        return examples
    
    def _generate_usage_tips(self, word: str, grade_level: Optional[str]) -> List[str]:
        """Generate usage tips for the word."""
        tips = []
        
        tips.append(f"Use '{word}' when you want to be specific and clear.")
        
        if grade_level in ["K-2", "3-5"]:
            tips.append("Practice saying the word out loud.")
            tips.append("Try using it in a simple sentence.")
        else:
            tips.append("Consider the context when using this word.")
            tips.append("Look for opportunities to use it in writing.")
        
        return tips
    
    def _identify_common_mistakes(self, word: str) -> List[str]:
        """Identify common mistakes with the word."""
        mistakes = []
        
        # This is a simplified implementation
        # In a real system, this would use error analysis data
        
        if len(word) > 8:
            mistakes.append("Watch out for spelling errors in longer words")
        
        if word.endswith("ly"):
            mistakes.append("Remember this is an adverb, not an adjective")
        
        return mistakes
    
    def _generate_pronunciation_tips(self, word: str, phonetics: Dict[str, Any]) -> List[str]:
        """Generate pronunciation tips."""
        tips = []
        
        syllable_count = self._count_syllables(word)
        
        if syllable_count > 2:
            tips.append(f"Break it down: {word} has {syllable_count} syllables")
        
        if phonetics.get("text"):
            tips.append(f"Phonetic spelling: {phonetics['text']}")
        
        return tips
    
    def _break_into_syllables(self, word: str) -> str:
        """Break word into syllables (simplified)."""
        # This is a very simplified syllable breaker
        # A real implementation would use a proper syllabification algorithm
        
        syllables = []
        current_syllable = ""
        vowels = "aeiouy"
        
        for i, char in enumerate(word.lower()):
            current_syllable += char
            
            if char in vowels and i < len(word) - 1:
                if word[i + 1].lower() not in vowels:
                    syllables.append(current_syllable)
                    current_syllable = ""
        
        if current_syllable:
            syllables.append(current_syllable)
        
        return "-".join(syllables) if syllables else word
    
    def _identify_stress_pattern(self, word: str, phonetics: Dict[str, Any]) -> str:
        """Identify stress pattern (simplified)."""
        # This is a simplified implementation
        syllable_count = self._count_syllables(word)
        
        if syllable_count == 1:
            return "Single syllable (stressed)"
        elif syllable_count == 2:
            return "First syllable stressed (typical pattern)"
        else:
            return "Varies (check pronunciation guide)"
    
    def _find_rhyming_words(self, word: str) -> List[str]:
        """Find simple rhyming words."""
        # This is a very simplified rhyme finder
        # A real implementation would use a phonetic dictionary
        
        rhymes = []
        
        if word.endswith("ing"):
            rhymes.extend(["sing", "ring", "king", "wing"])
        elif word.endswith("tion"):
            rhymes.extend(["nation", "station", "creation"])
        elif word.endswith("ly"):
            rhymes.extend(["quickly", "slowly", "carefully"])
        
        # Remove the original word if it appears
        rhymes = [r for r in rhymes if r != word]
        
        return rhymes[:5]  # Limit to 5 rhymes
    
    def _explain_phonetic_rules(self, word: str) -> List[str]:
        """Explain relevant phonetic rules."""
        rules = []
        
        if word.endswith("e") and len(word) > 3:
            rules.append("Silent 'e' at the end makes the vowel say its name")
        
        if "ph" in word:
            rules.append("'ph' makes the 'f' sound")
        
        if "ough" in word:
            rules.append("'ough' can be pronounced different ways")
        
        return rules
    
    def _assess_pronunciation_difficulty(self, word: str, phonetics: Dict[str, Any]) -> str:
        """Assess pronunciation difficulty."""
        difficulty_score = 0
        
        # Length factor
        if len(word) > 8:
            difficulty_score += 1
        
        # Syllable count
        syllables = self._count_syllables(word)
        if syllables > 3:
            difficulty_score += 1
        
        # Complex letter combinations
        complex_patterns = ["ough", "augh", "eigh", "tion", "sion"]
        for pattern in complex_patterns:
            if pattern in word.lower():
                difficulty_score += 1
                break
        
        if difficulty_score == 0:
            return "Easy"
        elif difficulty_score == 1:
            return "Moderate"
        else:
            return "Challenging"
    
    async def _get_educational_synonyms(
        self,
        definition: Definition,
        grade_level: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get educationally appropriate synonyms."""
        synonyms = []
        
        for synonym in definition.synonyms[:limit]:
            # In a real implementation, we would check each synonym's complexity
            synonym_data = {
                "word": synonym,
                "appropriateness": "suitable",  # Simplified
                "usage_note": f"Can be used instead of '{definition.word}'"
            }
            synonyms.append(synonym_data)
        
        return synonyms
    
    async def _get_educational_antonyms(
        self,
        definition: Definition,
        grade_level: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get educationally appropriate antonyms."""
        antonyms = []
        
        for antonym in definition.antonyms[:limit]:
            antonym_data = {
                "word": antonym,
                "appropriateness": "suitable",  # Simplified
                "usage_note": f"Opposite meaning of '{definition.word}'"
            }
            antonyms.append(antonym_data)
        
        return antonyms
    
    async def _get_educational_related_words(
        self,
        definition: Definition,
        grade_level: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get educationally relevant related words."""
        related_words = []
        
        # Get morphologically related words
        morphological_related = self._find_related_words(definition)
        
        for word in morphological_related[:limit]:
            word_data = {
                "word": word,
                "relationship": "morphological",
                "usage_note": f"Related to '{definition.word}' by word structure"
            }
            related_words.append(word_data)
        
        return related_words
    
    def _generate_vocabulary_notes(
        self,
        definition: Definition,
        grade_level: Optional[str]
    ) -> List[str]:
        """Generate educational notes about vocabulary relationships."""
        notes = []
        
        if definition.synonyms:
            notes.append("Learning synonyms helps expand vocabulary and improve writing variety.")
        
        if definition.antonyms:
            notes.append("Understanding antonyms helps clarify meaning through contrast.")
        
        if grade_level in ["K-2", "3-5"]:
            notes.append("Start with simple word relationships and build complexity gradually.")
        
        return notes
    
    def _suggest_vocabulary_activities(
        self,
        definition: Definition,
        grade_level: Optional[str]
    ) -> List[str]:
        """Suggest vocabulary learning activities."""
        activities = []
        
        if definition.synonyms:
            activities.append("Create a synonym web or word map")
            activities.append("Practice replacing words in sentences with synonyms")
        
        if definition.antonyms:
            activities.append("Play antonym matching games")
            activities.append("Create opposite word pairs")
        
        if grade_level in ["K-2"]:
            activities.append("Draw pictures to show word meanings")
            activities.append("Act out words with body movements")
        elif grade_level in ["3-5"]:
            activities.append("Create vocabulary journals")
            activities.append("Write sentences using new words")
        else:
            activities.append("Analyze word usage in different contexts")
            activities.append("Create semantic maps showing word relationships")
        
        return activities
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check for this tool.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Test the Dictionary API client
            api_health = await self.client.health_check()
            
            return {
                "tool_name": self.tool_name,
                "status": "healthy" if api_health.get("status") == "healthy" else "degraded",
                "api_status": api_health,
                "features": [
                    "word_definitions",
                    "vocabulary_analysis", 
                    "pronunciation_guides",
                    "educational_examples",
                    "related_vocabulary"
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Dictionary tool health check failed: {e}")
            return {
                "tool_name": self.tool_name,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }