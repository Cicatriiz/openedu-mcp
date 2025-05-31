"""
Open Library tools for OpenEdu MCP Server.

This module provides MCP tool implementations for Open Library API integration,
including educational filtering, metadata enrichment, and book search functionality.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base_tool import BaseTool
from api.openlibrary import OpenLibraryClient
from models.book import Book
from models.base import GradeLevel, EducationalMetadata
from config import Config
from services.cache_service import CacheService
from services.rate_limiting_service import RateLimitingService
from services.usage_service import UsageService
from exceptions import ToolError, ValidationError, APIError

logger = logging.getLogger(__name__)


class OpenLibraryTool(BaseTool):
    """Tool for Open Library API integration with educational features."""
    
    def __init__(
        self,
        config: Config,
        cache_service: CacheService,
        rate_limiting_service: RateLimitingService,
        usage_service: UsageService
    ):
        """
        Initialize Open Library tool.
        
        Args:
            config: Application configuration
            cache_service: Cache service instance
            rate_limiting_service: Rate limiting service instance
            usage_service: Usage tracking service instance
        """
        super().__init__(config, cache_service, rate_limiting_service, usage_service)
        self.client = OpenLibraryClient(config)
        
        # Educational filtering configuration
        self.min_educational_relevance = config.education.content_filters.min_educational_relevance
        self.enable_age_appropriate = config.education.content_filters.enable_age_appropriate
        self.enable_curriculum_alignment = config.education.content_filters.enable_curriculum_alignment
    
    @property
    def api_name(self) -> str:
        """Name of the API this tool uses for rate limiting."""
        return "open_library"
    
    async def search_educational_books(
        self,
        query: str,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None,
        limit: int = 10,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for educational books with filtering and enrichment.
        
        Args:
            query: Search query for books
            subject: Educational subject filter (optional)
            grade_level: Target grade level (K-2, 3-5, 6-8, 9-12, College)
            limit: Maximum number of results (1-50)
            user_session: User session identifier
            
        Returns:
            List of educational books with metadata
            
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
                subject=subject
            )
            
            # Build enhanced search query
            search_query = validated['query']
            
            # Add subject to search if specified
            if subject:
                search_query = f'{search_query} subject:"{subject}"'
            
            # Search books using Open Library API
            raw_books = await self.client.search_books(search_query, validated['limit'])
            
            # Convert to Book models with educational enrichment
            books = []
            for book_data in raw_books:
                try:
                    book = Book.from_open_library(book_data)
                    
                    # Enrich with educational metadata
                    book = await self._enrich_educational_metadata(book, subject, grade_level)
                    
                    books.append(book)
                    
                except Exception as e:
                    logger.warning(f"Failed to process book data: {e}")
                    continue
            
            # Apply educational filtering
            filtered_books = self._apply_educational_filters(
                books,
                grade_level=validated.get('grade_level'),
                subject=subject
            )
            
            # Sort by educational relevance
            sorted_books = self.sort_by_educational_relevance(filtered_books)
            
            # Convert to dictionaries for response
            return [book.to_dict() for book in sorted_books]
        
        return await self.execute_with_monitoring(
            "search_educational_books",
            _search,
            user_session=user_session
        )
    
    async def get_book_details_by_isbn(
        self,
        isbn: str,
        include_cover: bool = True,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed book information by ISBN with educational enrichment.
        
        Args:
            isbn: ISBN-10 or ISBN-13
            include_cover: Whether to include cover image URL
            user_session: User session identifier
            
        Returns:
            Detailed book information with educational metadata
            
        Raises:
            ValidationError: If ISBN is invalid
            ToolError: If retrieval fails
        """
        async def _get_details():
            # Get book details from Open Library
            book_data = await self.client.get_book_details(isbn)
            
            if not book_data:
                raise ToolError(f"Book not found for ISBN: {isbn}", self.tool_name)
            
            # Convert to Book model
            book = Book.from_open_library(book_data)
            
            # Enrich with educational metadata
            book = await self._enrich_educational_metadata(book)
            
            # Add cover image if requested
            if include_cover and not book.cover_url:
                cover_url = await self.client.get_book_cover(isbn)
                if cover_url:
                    book.cover_url = cover_url
            
            # Check availability
            availability = await self.client.check_book_availability(isbn)
            
            # Prepare response
            result = book.to_dict()
            result['availability'] = availability
            
            return result
        
        return await self.execute_with_monitoring(
            "get_book_details_by_isbn",
            _get_details,
            user_session=user_session
        )
    
    async def search_books_by_subject(
        self,
        subject: str,
        grade_level: Optional[str] = None,
        limit: int = 10,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search books by educational subject with grade level filtering.
        
        Args:
            subject: Educational subject
            grade_level: Target grade level (optional)
            limit: Maximum number of results
            user_session: User session identifier
            
        Returns:
            List of books in the subject area
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If search fails
        """
        async def _search_by_subject():
            # Validate parameters
            validated = await self.validate_common_parameters(
                subject=subject,
                limit=limit,
                grade_level=grade_level
            )
            
            # Search by subject
            raw_books = await self.client.search_by_subject(
                validated['subject'],
                validated['limit']
            )
            
            # Convert and enrich books
            books = []
            for book_data in raw_books:
                try:
                    book = Book.from_open_library(book_data)
                    book = await self._enrich_educational_metadata(
                        book,
                        subject=subject,
                        grade_level=grade_level
                    )
                    books.append(book)
                except Exception as e:
                    logger.warning(f"Failed to process book data: {e}")
                    continue
            
            # Apply educational filtering
            filtered_books = self._apply_educational_filters(
                books,
                grade_level=validated.get('grade_level'),
                subject=subject
            )
            
            # Sort by educational relevance
            sorted_books = self.sort_by_educational_relevance(filtered_books)
            
            return [book.to_dict() for book in sorted_books]
        
        return await self.execute_with_monitoring(
            "search_books_by_subject",
            _search_by_subject,
            user_session=user_session
        )
    
    async def get_book_recommendations(
        self,
        grade_level: str,
        subject: Optional[str] = None,
        limit: int = 10,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get book recommendations for a specific grade level and subject.
        
        Args:
            grade_level: Target grade level
            subject: Educational subject (optional)
            limit: Maximum number of results
            user_session: User session identifier
            
        Returns:
            List of recommended books
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If recommendation fails
        """
        async def _get_recommendations():
            # Validate parameters
            validated = await self.validate_common_parameters(
                grade_level=grade_level,
                subject=subject,
                limit=limit
            )
            
            # Build recommendation query based on grade level
            grade_terms = self._get_grade_level_search_terms(validated['grade_level'])
            
            if subject:
                query = f'subject:"{subject}" AND ({" OR ".join(grade_terms)})'
            else:
                query = f'({" OR ".join(grade_terms)})'
            
            # Search for books
            raw_books = await self.client.search_books(query, validated['limit'] * 2)  # Get more to filter
            
            # Convert and enrich books
            books = []
            for book_data in raw_books:
                try:
                    book = Book.from_open_library(book_data)
                    book = await self._enrich_educational_metadata(
                        book,
                        subject=subject,
                        grade_level=grade_level
                    )
                    books.append(book)
                except Exception as e:
                    logger.warning(f"Failed to process book data: {e}")
                    continue
            
            # Apply strict educational filtering for recommendations
            filtered_books = self._apply_educational_filters(
                books,
                grade_level=validated.get('grade_level'),
                subject=subject,
                min_relevance_score=0.8  # Higher threshold for recommendations
            )
            
            # Sort by educational relevance and limit results
            sorted_books = self.sort_by_educational_relevance(filtered_books)
            final_books = sorted_books[:validated['limit']]
            
            return [book.to_dict() for book in final_books]
        
        return await self.execute_with_monitoring(
            "get_book_recommendations",
            _get_recommendations,
            user_session=user_session
        )
    
    async def _enrich_educational_metadata(
        self,
        book: Book,
        subject: Optional[str] = None,
        grade_level: Optional[str] = None
    ) -> Book:
        """
        Enrich book with educational metadata.
        
        Args:
            book: Book instance to enrich
            subject: Target subject for relevance scoring
            grade_level: Target grade level for relevance scoring
            
        Returns:
            Enriched book instance
        """
        # Calculate educational relevance score
        relevance_score = self._calculate_educational_relevance(book, subject, grade_level)
        book.educational_metadata.educational_relevance_score = relevance_score
        
        # Infer reading level from various indicators
        reading_level = self._infer_reading_level(book)
        if reading_level:
            book.educational_metadata.reading_level = reading_level
        
        # Set difficulty level based on grade levels and content
        difficulty_level = self._infer_difficulty_level(book)
        if difficulty_level:
            book.educational_metadata.difficulty_level = difficulty_level
        
        # Enhance subject classification
        enhanced_subjects = self._enhance_subject_classification(book.subjects)
        book.educational_metadata.educational_subjects = enhanced_subjects
        
        return book
    
    def _calculate_educational_relevance(
        self,
        book: Book,
        target_subject: Optional[str] = None,
        target_grade_level: Optional[str] = None
    ) -> float:
        """Calculate educational relevance score for a book."""
        score = 0.0
        
        # Base score for having educational metadata
        if book.educational_metadata.grade_levels:
            score += 0.3
        
        # Subject relevance
        if target_subject:
            subject_match = any(
                target_subject.lower() in subject.lower()
                for subject in (book.subjects + book.educational_metadata.educational_subjects)
            )
            if subject_match:
                score += 0.4
        
        # Grade level appropriateness
        if target_grade_level:
            try:
                target_grade = GradeLevel.from_string(target_grade_level)
                if target_grade and target_grade in book.educational_metadata.grade_levels:
                    score += 0.3
            except:
                pass
        
        # Additional educational indicators
        educational_keywords = [
            'education', 'learning', 'teaching', 'student', 'curriculum',
            'textbook', 'workbook', 'study', 'academic', 'school'
        ]
        
        title_desc = f"{book.title} {book.description or ''}".lower()
        keyword_matches = sum(1 for keyword in educational_keywords if keyword in title_desc)
        score += min(keyword_matches * 0.05, 0.2)  # Max 0.2 for keywords
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _infer_reading_level(self, book: Book) -> Optional[str]:
        """Infer reading level from book metadata."""
        # Simple heuristic based on grade levels and subjects
        if not book.educational_metadata.grade_levels:
            return None
        
        grade_levels = [gl.value for gl in book.educational_metadata.grade_levels]
        
        if any('K-2' in gl or '3-5' in gl for gl in grade_levels):
            return "Elementary"
        elif any('6-8' in gl for gl in grade_levels):
            return "Middle School"
        elif any('9-12' in gl for gl in grade_levels):
            return "High School"
        elif any('College' in gl for gl in grade_levels):
            return "College"
        
        return None
    
    def _infer_difficulty_level(self, book: Book) -> Optional[str]:
        """Infer difficulty level from book metadata."""
        # Simple heuristic based on page count and grade levels
        if book.page_count:
            if book.page_count < 50:
                return "Beginner"
            elif book.page_count < 200:
                return "Intermediate"
            else:
                return "Advanced"
        
        # Fallback to grade level inference
        reading_level = self._infer_reading_level(book)
        if reading_level in ["Elementary"]:
            return "Beginner"
        elif reading_level in ["Middle School", "High School"]:
            return "Intermediate"
        elif reading_level in ["College"]:
            return "Advanced"
        
        return None
    
    def _enhance_subject_classification(self, subjects: List[str]) -> List[str]:
        """Enhance subject classification with educational mapping."""
        enhanced = []
        
        subject_mapping = {
            'mathematics': ['Mathematics', 'Math', 'Algebra', 'Geometry', 'Calculus'],
            'science': ['Science', 'Biology', 'Chemistry', 'Physics', 'Earth Science'],
            'english': ['English Language Arts', 'Literature', 'Reading', 'Writing'],
            'history': ['Social Studies', 'History', 'Geography', 'Civics'],
            'art': ['Arts', 'Visual Arts', 'Music', 'Drama'],
            'technology': ['Technology', 'Computer Science', 'Engineering']
        }
        
        for subject in subjects:
            subject_lower = subject.lower()
            enhanced.append(subject)  # Keep original
            
            # Map to educational categories
            for category, keywords in subject_mapping.items():
                if any(keyword.lower() in subject_lower for keyword in keywords):
                    if category.title() not in enhanced:
                        enhanced.append(category.title())
        
        return enhanced[:10]  # Limit to 10 subjects
    
    def _get_grade_level_search_terms(self, grade_level: GradeLevel) -> List[str]:
        """Get search terms for a specific grade level."""
        terms_map = {
            GradeLevel.K_2: ['kindergarten', 'elementary', 'primary', 'early childhood'],
            GradeLevel.GRADES_3_5: ['elementary', 'intermediate', 'upper elementary'],
            GradeLevel.GRADES_6_8: ['middle school', 'junior high', 'intermediate'],
            GradeLevel.GRADES_9_12: ['high school', 'secondary', 'teen', 'young adult'],
            GradeLevel.COLLEGE: ['college', 'university', 'higher education', 'academic']
        }
        
        return terms_map.get(grade_level, ['educational'])
    
    def _apply_educational_filters(
        self,
        books: List[Book],
        grade_level: Optional[GradeLevel] = None,
        subject: Optional[str] = None,
        min_relevance_score: Optional[float] = None
    ) -> List[Book]:
        """Apply educational filters to book list."""
        if not books:
            return books
        
        filtered = books
        
        # Use configured minimum relevance score if not specified
        if min_relevance_score is None:
            min_relevance_score = self.min_educational_relevance
        
        # Apply base educational filtering
        filtered = self.filter_by_educational_criteria(
            filtered,
            grade_level=grade_level.value if grade_level else None,
            subject=subject,
            min_relevance_score=min_relevance_score
        )
        
        # Additional age-appropriate filtering
        if self.enable_age_appropriate and grade_level:
            filtered = self._filter_age_appropriate(filtered, grade_level)
        
        return filtered
    
    def _filter_age_appropriate(self, books: List[Book], grade_level: GradeLevel) -> List[Book]:
        """Filter books for age-appropriate content."""
        # Simple content filtering based on subjects and titles
        inappropriate_keywords = {
            GradeLevel.K_2: ['violence', 'war', 'death', 'adult'],
            GradeLevel.GRADES_3_5: ['violence', 'war', 'adult'],
            GradeLevel.GRADES_6_8: ['adult', 'mature'],
            GradeLevel.GRADES_9_12: [],  # Less restrictive
            GradeLevel.COLLEGE: []  # No restrictions
        }
        
        keywords = inappropriate_keywords.get(grade_level, [])
        if not keywords:
            return books
        
        filtered = []
        for book in books:
            content = f"{book.title} {book.description or ''}".lower()
            if not any(keyword in content for keyword in keywords):
                filtered.append(book)
        
        return filtered
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for Open Library tool.
        
        Returns:
            Health status information
        """
        try:
            # Check API client health
            api_health = await self.client.health_check()
            
            # Test basic functionality
            test_books = await self.client.search_books("test", limit=1)
            
            return {
                'status': 'healthy',
                'api_health': api_health,
                'test_search_results': len(test_books),
                'timestamp': datetime.now().isoformat(),
                'tool_name': self.tool_name
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'tool_name': self.tool_name
            }
    
    async def close(self):
        """Clean up resources."""
        await self.client.close()