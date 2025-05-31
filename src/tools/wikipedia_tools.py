"""
Wikipedia tools for OpenEdu MCP Server.

This module provides MCP tool implementations for Wikipedia API integration,
including educational filtering, content analysis, and article search functionality.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base_tool import BaseTool
from api.wikipedia import WikipediaClient
from models.article import Article
from models.base import GradeLevel, EducationalMetadata
from config import Config
from services.cache_service import CacheService
from services.rate_limiting_service import RateLimitingService
from services.usage_service import UsageService
from exceptions import ToolError, ValidationError, APIError

logger = logging.getLogger(__name__)


class WikipediaTool(BaseTool):
    """Tool for Wikipedia API integration with educational features."""
    
    def __init__(
        self,
        config: Config,
        cache_service: CacheService,
        rate_limiting_service: RateLimitingService,
        usage_service: UsageService
    ):
        """
        Initialize Wikipedia tool.
        
        Args:
            config: Application configuration
            cache_service: Cache service instance
            rate_limiting_service: Rate limiting service instance
            usage_service: Usage tracking service instance
        """
        super().__init__(config, cache_service, rate_limiting_service, usage_service)
        self.client = WikipediaClient(config)
        
        # Educational filtering configuration
        self.min_educational_relevance = config.education.content_filters.min_educational_relevance
        self.enable_age_appropriate = config.education.content_filters.enable_age_appropriate
        self.enable_curriculum_alignment = config.education.content_filters.enable_curriculum_alignment
        
        # Reading level thresholds (word counts)
        self.reading_level_thresholds = {
            GradeLevel.K_2: 500,
            GradeLevel.GRADES_3_5: 1000,
            GradeLevel.GRADES_6_8: 2000,
            GradeLevel.GRADES_9_12: 4000,
            GradeLevel.COLLEGE: 8000
        }
    
    @property
    def api_name(self) -> str:
        """Name of the API this tool uses for rate limiting."""
        return "wikipedia"
    
    async def search_educational_articles(
        self,
        query: str,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        language: str = 'en',
        limit: int = 10,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for educational articles with filtering and enrichment.
        
        Args:
            query: Search query for articles
            subject: Educational subject filter (optional)
            grade_level: Target grade level (K-2, 3-5, 6-8, 9-12, College)
            language: Language code (default: 'en')
            limit: Maximum number of results (1-50)
            user_session: User session identifier
            
        Returns:
            List of educational articles with metadata
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If search fails
        """
        async def _search():
            # Validate parameters
            validated = await self.validate_common_parameters(
                query=query,
                limit=limit,
                grade_level=grade_level,
                subject=subject,
                language=language
            )
            
            # Build enhanced search query
            search_query = validated['query']
            
            # Add subject-specific terms if specified
            if subject:
                subject_terms = self._get_subject_search_terms(subject)
                if subject_terms:
                    search_query = f'{search_query} {" OR ".join(subject_terms)}'
            
            # Search articles using Wikipedia API
            raw_articles = await self.client.search_wikipedia(
                search_query, 
                validated.get('language', 'en'), 
                validated['limit']
            )
            
            # Convert to Article models with educational enrichment
            articles = []
            for article_data in raw_articles:
                try:
                    article = Article.from_wikipedia(article_data)
                    
                    # Enrich with educational metadata
                    article = await self._enrich_educational_metadata(
                        article, 
                        subject, 
                        grade_level,
                        language
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Failed to process article data: {e}")
                    continue
            
            # Apply educational filtering
            filtered_articles = self._apply_educational_filters(
                articles,
                grade_level=validated.get('grade_level'),
                subject=subject
            )
            
            # Sort by educational relevance
            sorted_articles = self.sort_by_educational_relevance(filtered_articles)
            
            # Convert to dictionaries for response
            return [article.to_dict() for article in sorted_articles]
        
        return await self.execute_with_monitoring(
            "search_educational_articles",
            _search,
            user_session=user_session
        )
    
    async def get_article_summary(
        self,
        title: str,
        language: str = 'en',
        include_educational_analysis: bool = True,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get article summary with educational analysis.
        
        Args:
            title: Article title
            language: Language code (default: 'en')
            include_educational_analysis: Whether to include educational metadata
            user_session: User session identifier
            
        Returns:
            Article summary with educational metadata
            
        Raises:
            ValidationError: If title is invalid
            ToolError: If retrieval fails
        """
        async def _get_summary():
            # Get article summary from Wikipedia
            summary_data = await self.client.get_article_summary(title, language)
            
            if not summary_data:
                raise ToolError(f"Article not found: {title}", self.tool_name)
            
            # Convert to Article model
            article = Article.from_wikipedia(summary_data)
            
            # Enrich with educational metadata if requested
            if include_educational_analysis:
                article = await self._enrich_educational_metadata(article, language=language)
            
            return article.to_dict()
        
        return await self.execute_with_monitoring(
            "get_article_summary",
            _get_summary,
            user_session=user_session
        )
    
    async def get_article_content(
        self,
        title: str,
        language: str = 'en',
        include_images: bool = False,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get full article content with educational enrichment.
        
        Args:
            title: Article title
            language: Language code (default: 'en')
            include_images: Whether to include article images
            user_session: User session identifier
            
        Returns:
            Full article content with educational metadata
            
        Raises:
            ValidationError: If title is invalid
            ToolError: If retrieval fails
        """
        async def _get_content():
            # Get full article content
            content_data = await self.client.get_article_content(title, language)
            
            if not content_data:
                raise ToolError(f"Article not found: {title}", self.tool_name)
            
            # Convert to Article model
            article = Article.from_wikipedia(content_data)
            
            # Get images if requested
            if include_images:
                try:
                    images = await self.client.get_article_images(title, language)
                    article.multimedia_resources = [img['url'] for img in images if img.get('url')]
                except Exception as e:
                    logger.warning(f"Failed to get images for {title}: {e}")
            
            # Enrich with educational metadata
            article = await self._enrich_educational_metadata(article, language=language)
            
            return article.to_dict()
        
        return await self.execute_with_monitoring(
            "get_article_content",
            _get_content,
            user_session=user_session
        )
    
    async def get_featured_article(
        self,
        date_param: Optional[str] = None,
        language: str = 'en',
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get featured article of the day with educational analysis.
        
        Args:
            date_param: Date in YYYY/MM/DD format (optional, defaults to today)
            language: Language code (default: 'en')
            user_session: User session identifier
            
        Returns:
            Featured article with educational metadata
            
        Raises:
            ValidationError: If date format is invalid
            ToolError: If retrieval fails
        """
        async def _get_featured():
            # Get featured article
            featured_data = await self.client.get_daily_featured(date_param, language)
            
            if not featured_data:
                date_str = date_param or date.today().strftime('%Y/%m/%d')
                raise ToolError(f"No featured article found for {date_str}", self.tool_name)
            
            # Convert to Article model
            article = Article.from_wikipedia(featured_data)
            
            # Enrich with educational metadata
            article = await self._enrich_educational_metadata(article, language=language)
            
            # Add featured article specific metadata
            result = article.to_dict()
            result['featured_date'] = featured_data.get('date')
            result['featured_type'] = featured_data.get('type', 'featured_article')
            
            return result
        
        return await self.execute_with_monitoring(
            "get_featured_article",
            _get_featured,
            user_session=user_session
        )
    
    async def get_articles_by_subject(
        self,
        subject: str,
        grade_level: Optional[str] = None,
        language: str = 'en',
        limit: int = 10,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get articles by educational subject with grade level filtering.
        
        Args:
            subject: Educational subject
            grade_level: Target grade level (optional)
            language: Language code (default: 'en')
            limit: Maximum number of results
            user_session: User session identifier
            
        Returns:
            List of articles in the subject area
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If search fails
        """
        async def _search_by_subject():
            # Validate parameters
            validated = await self.validate_common_parameters(
                subject=subject,
                limit=limit,
                grade_level=grade_level,
                language=language
            )
            
            # Build subject-specific search query
            subject_terms = self._get_subject_search_terms(validated['subject'])
            search_query = " OR ".join(subject_terms) if subject_terms else validated['subject']
            
            # Search articles
            raw_articles = await self.client.search_wikipedia(
                search_query,
                validated.get('language', 'en'),
                validated['limit']
            )
            
            # Convert and enrich articles
            articles = []
            for article_data in raw_articles:
                try:
                    article = Article.from_wikipedia(article_data)
                    article = await self._enrich_educational_metadata(
                        article,
                        subject=subject,
                        grade_level=grade_level,
                        language=language
                    )
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to process article data: {e}")
                    continue
            
            # Apply educational filtering
            filtered_articles = self._apply_educational_filters(
                articles,
                grade_level=validated.get('grade_level'),
                subject=subject
            )
            
            # Sort by educational relevance
            sorted_articles = self.sort_by_educational_relevance(filtered_articles)
            
            return [article.to_dict() for article in sorted_articles]
        
        return await self.execute_with_monitoring(
            "get_articles_by_subject",
            _search_by_subject,
            user_session=user_session
        )
    
    async def _enrich_educational_metadata(
        self,
        article: Article,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        language: str = 'en'
    ) -> Article:
        """
        Enrich article with educational metadata.
        
        Args:
            article: Article instance to enrich
            subject: Target subject for relevance scoring
            grade_level: Target grade level for relevance scoring
            language: Language code
            
        Returns:
            Enriched article instance
        """
        # Calculate educational relevance score
        relevance_score = self._calculate_educational_relevance(article, subject, grade_level)
        article.educational_metadata.educational_relevance_score = relevance_score
        
        # Analyze reading level and complexity
        reading_analysis = self._analyze_reading_level(article)
        article.educational_metadata.reading_level = reading_analysis.get('level')
        article.educational_metadata.difficulty_level = reading_analysis.get('difficulty')
        
        # Determine appropriate grade levels
        grade_levels = self._determine_grade_levels(article)
        article.educational_metadata.grade_levels = grade_levels
        
        # Enhance subject classification
        enhanced_subjects = self._enhance_subject_classification(article.categories, subject)
        article.educational_metadata.educational_subjects = enhanced_subjects
        
        # Analyze curriculum alignment
        curriculum_alignment = self._analyze_curriculum_alignment(article, subject)
        article.educational_metadata.curriculum_alignment = curriculum_alignment
        
        # Extract related educational topics
        related_topics = self._extract_educational_topics(article)
        article.related_topics = related_topics
        
        return article
    
    def _calculate_educational_relevance(
        self,
        article: Article,
        target_subject: Optional[str] = None,
        target_grade_level: Optional[str] = None
    ) -> float:
        """Calculate educational relevance score for an article."""
        score = 0.0
        
        # Base score for educational content indicators
        content_text = f"{article.title} {article.summary} {article.content or ''}".lower()
        
        # Educational keywords scoring
        educational_keywords = [
            'education', 'learning', 'teaching', 'study', 'research', 'academic',
            'science', 'mathematics', 'history', 'literature', 'biology', 'chemistry',
            'physics', 'geography', 'philosophy', 'psychology', 'sociology', 'economics'
        ]
        
        keyword_matches = sum(1 for keyword in educational_keywords if keyword in content_text)
        score += min(keyword_matches * 0.05, 0.3)  # Max 0.3 for keywords
        
        # Subject relevance
        if target_subject:
            subject_terms = self._get_subject_search_terms(target_subject)
            subject_match = any(
                term.lower() in content_text
                for term in subject_terms + [target_subject]
            )
            if subject_match:
                score += 0.4
        
        # Category-based scoring
        if article.categories:
            educational_categories = [
                'education', 'science', 'mathematics', 'history', 'literature',
                'academic', 'research', 'learning', 'teaching'
            ]
            category_text = " ".join(article.categories).lower()
            category_matches = sum(1 for cat in educational_categories if cat in category_text)
            score += min(category_matches * 0.1, 0.2)  # Max 0.2 for categories
        
        # Length appropriateness (not too short, not too long)
        word_count = article.get_word_count()
        if 100 <= word_count <= 5000:  # Appropriate length for educational content
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _analyze_reading_level(self, article: Article) -> Dict[str, str]:
        """Analyze reading level and difficulty of an article."""
        word_count = article.get_word_count()
        
        # Simple heuristic based on word count and complexity indicators
        content_text = f"{article.summary} {article.content or ''}"
        
        # Count complex indicators
        complex_indicators = 0
        
        # Long sentences (rough estimate)
        sentences = content_text.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        if avg_sentence_length > 20:
            complex_indicators += 1
        
        # Technical terms (words with 3+ syllables - rough estimate)
        words = content_text.split()
        long_words = [w for w in words if len(w) > 8]  # Rough syllable estimate
        if len(long_words) / max(len(words), 1) > 0.15:
            complex_indicators += 1
        
        # Determine reading level
        if word_count < 300:
            level = "Elementary"
            difficulty = "Beginner"
        elif word_count < 800:
            level = "Middle School"
            difficulty = "Beginner" if complex_indicators == 0 else "Intermediate"
        elif word_count < 2000:
            level = "High School"
            difficulty = "Intermediate" if complex_indicators <= 1 else "Advanced"
        else:
            level = "College"
            difficulty = "Advanced"
        
        return {
            'level': level,
            'difficulty': difficulty,
            'word_count': word_count,
            'complexity_score': complex_indicators
        }
    
    def _determine_grade_levels(self, article: Article) -> List[GradeLevel]:
        """Determine appropriate grade levels for an article."""
        word_count = article.get_word_count()
        grade_levels = []
        
        # Map word count to grade levels
        for grade_level, threshold in self.reading_level_thresholds.items():
            if word_count <= threshold * 1.5:  # Allow some flexibility
                grade_levels.append(grade_level)
        
        # If no grade levels match, assign based on content complexity
        if not grade_levels:
            if word_count > 4000:
                grade_levels = [GradeLevel.COLLEGE]
            else:
                grade_levels = [GradeLevel.GRADES_9_12]
        
        return grade_levels
    
    def _enhance_subject_classification(
        self, 
        categories: List[str], 
        target_subject: Optional[str] = None
    ) -> List[str]:
        """Enhance subject classification with educational mapping."""
        enhanced = []
        
        # Educational subject mapping
        subject_mapping = {
            'Mathematics': ['math', 'algebra', 'geometry', 'calculus', 'statistics', 'arithmetic'],
            'Science': ['science', 'biology', 'chemistry', 'physics', 'astronomy', 'geology'],
            'History': ['history', 'historical', 'ancient', 'medieval', 'modern', 'war', 'civilization'],
            'Literature': ['literature', 'poetry', 'novel', 'author', 'writer', 'book'],
            'Geography': ['geography', 'country', 'continent', 'city', 'region', 'climate'],
            'Arts': ['art', 'painting', 'sculpture', 'music', 'theater', 'dance'],
            'Technology': ['technology', 'computer', 'engineering', 'invention', 'innovation'],
            'Social Studies': ['society', 'culture', 'government', 'politics', 'economics', 'sociology']
        }
        
        # Analyze categories
        category_text = " ".join(categories).lower()
        
        for subject, keywords in subject_mapping.items():
            if any(keyword in category_text for keyword in keywords):
                if subject not in enhanced:
                    enhanced.append(subject)
        
        # Add target subject if specified and relevant
        if target_subject and target_subject not in enhanced:
            enhanced.append(target_subject)
        
        return enhanced[:5]  # Limit to 5 subjects
    
    def _analyze_curriculum_alignment(
        self, 
        article: Article, 
        subject: Optional[str] = None
    ) -> List[str]:
        """Analyze curriculum alignment for an article."""
        alignments = []
        
        content_text = f"{article.title} {article.summary} {article.content or ''}".lower()
        
        # Common Core alignment indicators
        common_core_indicators = {
            'Mathematics': ['problem solving', 'mathematical reasoning', 'number sense'],
            'English Language Arts': ['reading comprehension', 'writing', 'communication'],
            'Science': ['scientific method', 'inquiry', 'investigation', 'hypothesis']
        }
        
        # NGSS alignment indicators
        ngss_indicators = [
            'engineering design', 'scientific practices', 'crosscutting concepts',
            'disciplinary core ideas', 'phenomena', 'systems'
        ]
        
        # Check for Common Core alignment
        if subject in common_core_indicators:
            indicators = common_core_indicators[subject]
            if any(indicator in content_text for indicator in indicators):
                alignments.append('Common Core')
        
        # Check for NGSS alignment (science subjects)
        if subject and 'science' in subject.lower():
            if any(indicator in content_text for indicator in ngss_indicators):
                alignments.append('NGSS')
        
        return alignments
    
    def _extract_educational_topics(self, article: Article) -> List[str]:
        """Extract related educational topics from an article."""
        topics = []
        
        # Extract from categories
        if article.categories:
            # Filter for educational categories
            educational_cats = [
                cat for cat in article.categories
                if any(keyword in cat.lower() for keyword in [
                    'education', 'science', 'mathematics', 'history', 'literature',
                    'learning', 'academic', 'research', 'study'
                ])
            ]
            topics.extend(educational_cats[:5])
        
        # Extract key terms from content
        if article.content:
            # Simple keyword extraction (could be enhanced with NLP)
            content_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', article.content)
            # Filter for likely educational terms
            educational_terms = [
                term for term in content_words
                if len(term) > 3 and len(term.split()) <= 3
            ]
            topics.extend(educational_terms[:10])
        
        # Remove duplicates and limit
        unique_topics = list(dict.fromkeys(topics))
        return unique_topics[:15]
    
    def _get_subject_search_terms(self, subject: str) -> List[str]:
        """Get search terms for a specific educational subject."""
        subject_terms = {
            'Mathematics': ['mathematics', 'math', 'algebra', 'geometry', 'calculus', 'statistics'],
            'Science': ['science', 'biology', 'chemistry', 'physics', 'astronomy', 'geology'],
            'History': ['history', 'historical', 'ancient', 'medieval', 'civilization'],
            'Literature': ['literature', 'poetry', 'novel', 'author', 'writer'],
            'Geography': ['geography', 'country', 'continent', 'climate', 'region'],
            'Arts': ['art', 'painting', 'sculpture', 'music', 'theater'],
            'Technology': ['technology', 'computer', 'engineering', 'invention'],
            'Social Studies': ['society', 'culture', 'government', 'politics', 'economics']
        }
        
        return subject_terms.get(subject, [subject.lower()])
    
    def _apply_educational_filters(
        self,
        articles: List[Article],
        grade_level: Optional[GradeLevel] = None,
        subject: Optional[str] = None,
        min_relevance_score: Optional[float] = None
    ) -> List[Article]:
        """Apply educational filtering to articles."""
        if not articles:
            return articles
        
        filtered = articles
        
        # Filter by educational relevance
        min_score = min_relevance_score or self.min_educational_relevance
        filtered = [
            article for article in filtered
            if article.get_educational_score() >= min_score
        ]
        
        # Filter by grade level appropriateness
        if grade_level and self.enable_age_appropriate:
            filtered = [
                article for article in filtered
                if not article.educational_metadata.grade_levels or
                grade_level in article.educational_metadata.grade_levels
            ]
        
        # Filter by subject relevance
        if subject:
            filtered = [
                article for article in filtered
                if any(subject.lower() in subj.lower() 
                      for subj in article.educational_metadata.educational_subjects)
                or subject.lower() in article.title.lower()
                or subject.lower() in article.summary.lower()
            ]
        
        return filtered
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for Wikipedia tool.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Test Wikipedia API connectivity
            health_status = await self.client.health_check()
            
            return {
                'tool_name': self.tool_name,
                'api_name': self.api_name,
                'status': health_status['status'],
                'response_time': health_status.get('response_time_seconds'),
                'timestamp': health_status.get('timestamp'),
                'educational_features': {
                    'content_filtering': self.enable_age_appropriate,
                    'curriculum_alignment': self.enable_curriculum_alignment,
                    'min_relevance_threshold': self.min_educational_relevance
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed for {self.tool_name}: {e}")
            return {
                'tool_name': self.tool_name,
                'api_name': self.api_name,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }