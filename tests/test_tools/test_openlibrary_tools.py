"""
Unit tests for Open Library tools.

This module contains tests for the Open Library API client and MCP tools,
including mocked API responses for reliable testing.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
from typing import Dict, Any, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from api.openlibrary import OpenLibraryClient
from tools.openlibrary_tools import OpenLibraryTool
from models.book import Book
from models.base import GradeLevel, EducationalMetadata
from config import Config
from exceptions import ValidationError, APIError, ToolError


class TestOpenLibraryClient:
    """Test cases for OpenLibraryClient."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.apis.open_library.base_url = "https://openlibrary.org"
        config.apis.open_library.timeout = 30
        config.apis.open_library.retry_attempts = 3
        config.apis.open_library.backoff_factor = 2.0
        config.server.name = "test-server"
        config.server.version = "1.0.0"
        return config
    
    @pytest.fixture
    def client(self, mock_config):
        """Create OpenLibraryClient instance."""
        return OpenLibraryClient(mock_config)
    
    @pytest.fixture
    def mock_book_data(self):
        """Mock book data from Open Library API."""
        return {
            "key": "/works/OL123456W",
            "title": "Test Educational Book",
            "author_name": ["Test Author"],
            "first_publish_year": 2020,
            "isbn": ["1234567890", "9781234567890"],
            "publisher": ["Test Publisher"],
            "subject": ["Mathematics", "Education", "Elementary"],
            "cover_i": 12345,
            "number_of_pages_median": 150,
            "language": ["eng"],
            "description": "A test book for educational purposes"
        }
    
    def test_validate_isbn_valid(self, client):
        """Test ISBN validation with valid ISBNs."""
        # Valid ISBN-10
        assert client._validate_isbn("1234567890") == "1234567890"
        assert client._validate_isbn("123456789X") == "123456789X"
        
        # Valid ISBN-13
        assert client._validate_isbn("9781234567890") == "9781234567890"
        
        # With hyphens and spaces
        assert client._validate_isbn("978-1-234-56789-0") == "9781234567890"
        assert client._validate_isbn("1 234 567890") == "1234567890"
    
    def test_validate_isbn_invalid(self, client):
        """Test ISBN validation with invalid ISBNs."""
        with pytest.raises(ValidationError):
            client._validate_isbn("")
        
        with pytest.raises(ValidationError):
            client._validate_isbn("123")  # Too short
        
        with pytest.raises(ValidationError):
            client._validate_isbn("12345678901234")  # Too long
        
        with pytest.raises(ValidationError):
            client._validate_isbn("123456789a")  # Invalid character
    
    def test_validate_search_params_valid(self, client):
        """Test search parameter validation with valid inputs."""
        # Should not raise any exceptions
        client._validate_search_params("test query", 10)
        client._validate_search_params("mathematics", 1)
        client._validate_search_params("science education", 100)
    
    def test_validate_search_params_invalid(self, client):
        """Test search parameter validation with invalid inputs."""
        with pytest.raises(ValidationError):
            client._validate_search_params("", 10)  # Empty query
        
        with pytest.raises(ValidationError):
            client._validate_search_params("   ", 10)  # Whitespace only
        
        with pytest.raises(ValidationError):
            client._validate_search_params("test", 0)  # Invalid limit
        
        with pytest.raises(ValidationError):
            client._validate_search_params("test", 101)  # Limit too high
    
    @pytest.mark.asyncio
    async def test_search_books_success(self, client, mock_book_data):
        """Test successful book search."""
        mock_response = {
            "docs": [mock_book_data],
            "numFound": 1,
            "start": 0
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            results = await client.search_books("test query", limit=10)
            
            assert len(results) == 1
            assert results[0]["title"] == "Test Educational Book"
            assert results[0]["author_name"] == ["Test Author"]
    
    @pytest.mark.asyncio
    async def test_search_books_validation_error(self, client):
        """Test book search with invalid parameters."""
        with pytest.raises(ValidationError):
            await client.search_books("", limit=10)
    
    @pytest.mark.asyncio
    async def test_get_book_details_success(self, client, mock_book_data):
        """Test successful book details retrieval."""
        with patch.object(client, '_make_request', return_value=mock_book_data):
            result = await client.get_book_details("9781234567890")
            
            assert result["title"] == "Test Educational Book"
            assert result["author_name"] == ["Test Author"]
    
    @pytest.mark.asyncio
    async def test_get_book_details_not_found(self, client):
        """Test book details retrieval when book not found."""
        with patch.object(client, '_make_request', return_value={}):
            with patch.object(client, 'search_books', return_value=[]):
                result = await client.get_book_details("9781234567890")
                assert result == {}
    
    @pytest.mark.asyncio
    async def test_check_book_availability_success(self, client, mock_book_data):
        """Test book availability checking."""
        with patch.object(client, 'get_book_details', return_value=mock_book_data):
            result = await client.check_book_availability("9781234567890")
            
            assert result["available"] is True
            assert result["status"] == "available"
            assert result["isbn"] == "9781234567890"
    
    @pytest.mark.asyncio
    async def test_check_book_availability_not_found(self, client):
        """Test book availability checking when book not found."""
        with patch.object(client, 'get_book_details', return_value={}):
            result = await client.check_book_availability("9781234567890")
            
            assert result["available"] is False
            assert result["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        with patch.object(client, 'search_books', return_value=[{"title": "test"}]):
            result = await client.health_check()
            
            assert result["status"] == "healthy"
            assert "response_time_seconds" in result
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure."""
        with patch.object(client, 'search_books', side_effect=APIError("API Error", "open_library")):
            result = await client.health_check()
            
            assert result["status"] == "unhealthy"
            assert "error" in result


class TestOpenLibraryTool:
    """Test cases for OpenLibraryTool."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.education.content_filters.min_educational_relevance = 0.7
        config.education.content_filters.enable_age_appropriate = True
        config.education.content_filters.enable_curriculum_alignment = True
        return config
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        cache_service = AsyncMock()
        rate_limiting_service = AsyncMock()
        usage_service = AsyncMock()
        return cache_service, rate_limiting_service, usage_service
    
    @pytest.fixture
    def tool(self, mock_config, mock_services):
        """Create OpenLibraryTool instance."""
        cache_service, rate_limiting_service, usage_service = mock_services
        return OpenLibraryTool(mock_config, cache_service, rate_limiting_service, usage_service)
    
    @pytest.fixture
    def sample_book(self):
        """Create sample Book instance."""
        educational_metadata = EducationalMetadata(
            grade_levels=[GradeLevel.GRADES_3_5],
            educational_subjects=["Mathematics"],
            educational_relevance_score=0.8
        )
        
        return Book(
            id="OL123456W",
            title="Elementary Mathematics",
            authors=["Test Author"],
            isbn="9781234567890",
            publication_date=date(2020, 1, 1),
            subjects=["Mathematics", "Education"],
            educational_metadata=educational_metadata,
            source="open_library"
        )
    
    def test_api_name(self, tool):
        """Test API name property."""
        assert tool.api_name == "open_library"
    
    def test_calculate_educational_relevance(self, tool, sample_book):
        """Test educational relevance calculation."""
        # Test with matching subject and grade level
        score = tool._calculate_educational_relevance(
            sample_book,
            target_subject="Mathematics",
            target_grade_level="3-5"
        )
        assert score > 0.5  # Should have high relevance
        
        # Test with non-matching criteria
        score = tool._calculate_educational_relevance(
            sample_book,
            target_subject="Science",
            target_grade_level="9-12"
        )
        assert score < 0.5  # Should have lower relevance
    
    def test_infer_reading_level(self, tool, sample_book):
        """Test reading level inference."""
        reading_level = tool._infer_reading_level(sample_book)
        assert reading_level == "Elementary"
        
        # Test with college-level book
        sample_book.educational_metadata.grade_levels = [GradeLevel.COLLEGE]
        reading_level = tool._infer_reading_level(sample_book)
        assert reading_level == "College"
    
    def test_infer_difficulty_level(self, tool, sample_book):
        """Test difficulty level inference."""
        # Test with page count
        sample_book.page_count = 30
        difficulty = tool._infer_difficulty_level(sample_book)
        assert difficulty == "Beginner"
        
        sample_book.page_count = 150
        difficulty = tool._infer_difficulty_level(sample_book)
        assert difficulty == "Intermediate"
        
        sample_book.page_count = 300
        difficulty = tool._infer_difficulty_level(sample_book)
        assert difficulty == "Advanced"
    
    def test_enhance_subject_classification(self, tool):
        """Test subject classification enhancement."""
        subjects = ["Mathematics", "Algebra"]
        enhanced = tool._enhance_subject_classification(subjects)
        
        assert "Mathematics" in enhanced
        assert "Algebra" in enhanced
        assert len(enhanced) >= len(subjects)
    
    def test_get_grade_level_search_terms(self, tool):
        """Test grade level search terms generation."""
        terms = tool._get_grade_level_search_terms(GradeLevel.K_2)
        assert "kindergarten" in terms
        assert "elementary" in terms
        
        terms = tool._get_grade_level_search_terms(GradeLevel.COLLEGE)
        assert "college" in terms
        assert "university" in terms
    
    @pytest.mark.asyncio
    async def test_enrich_educational_metadata(self, tool, sample_book):
        """Test educational metadata enrichment."""
        enriched_book = await tool._enrich_educational_metadata(
            sample_book,
            subject="Mathematics",
            grade_level="3-5"
        )
        
        assert enriched_book.educational_metadata.educational_relevance_score > 0
        assert enriched_book.educational_metadata.reading_level is not None
        assert enriched_book.educational_metadata.difficulty_level is not None
    
    def test_filter_age_appropriate(self, tool, sample_book):
        """Test age-appropriate content filtering."""
        # Test with appropriate content
        books = [sample_book]
        filtered = tool._filter_age_appropriate(books, GradeLevel.GRADES_3_5)
        assert len(filtered) == 1
        
        # Test with inappropriate content
        sample_book.title = "Violence and War Stories"
        filtered = tool._filter_age_appropriate(books, GradeLevel.K_2)
        assert len(filtered) == 0
    
    @pytest.mark.asyncio
    async def test_search_educational_books_success(self, tool):
        """Test successful educational book search."""
        mock_book_data = {
            "key": "/works/OL123456W",
            "title": "Test Book",
            "author_name": ["Test Author"],
            "subject": ["Mathematics"]
        }
        
        with patch.object(tool.client, 'search_books', return_value=[mock_book_data]):
            with patch.object(tool, 'execute_with_monitoring') as mock_execute:
                mock_execute.return_value = [{"title": "Test Book"}]
                
                result = await tool.search_educational_books(
                    query="mathematics",
                    subject="Mathematics",
                    grade_level="3-5",
                    limit=10
                )
                
                mock_execute.assert_called_once()
                assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_book_details_by_isbn_success(self, tool):
        """Test successful book details retrieval by ISBN."""
        mock_book_data = {
            "key": "/works/OL123456W",
            "title": "Test Book",
            "author_name": ["Test Author"]
        }
        
        with patch.object(tool.client, 'get_book_details', return_value=mock_book_data):
            with patch.object(tool.client, 'get_book_cover', return_value="http://example.com/cover.jpg"):
                with patch.object(tool.client, 'check_book_availability', return_value={"available": True}):
                    with patch.object(tool, 'execute_with_monitoring') as mock_execute:
                        mock_execute.return_value = {"title": "Test Book"}
                        
                        result = await tool.get_book_details_by_isbn(
                            isbn="9781234567890",
                            include_cover=True
                        )
                        
                        mock_execute.assert_called_once()
                        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, tool):
        """Test successful tool health check."""
        with patch.object(tool.client, 'health_check', return_value={"status": "healthy"}):
            with patch.object(tool.client, 'search_books', return_value=[{"title": "test"}]):
                result = await tool.health_check()
                
                assert result["status"] == "healthy"
                assert "api_health" in result
                assert "test_search_results" in result
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, tool):
        """Test tool health check failure."""
        with patch.object(tool.client, 'health_check', side_effect=Exception("Test error")):
            result = await tool.health_check()
            
            assert result["status"] == "unhealthy"
            assert "error" in result


class TestBookModel:
    """Test cases for Book model Open Library integration."""
    
    @pytest.fixture
    def mock_ol_data(self):
        """Mock Open Library API response data."""
        return {
            "key": "/works/OL123456W",
            "title": "Test Educational Book",
            "author_name": ["Test Author", "Another Author"],
            "first_publish_year": 2020,
            "isbn": ["1234567890", "9781234567890"],
            "publisher": ["Test Publisher"],
            "subject": ["Mathematics", "Education", "Elementary"],
            "cover_i": 12345,
            "number_of_pages_median": 150,
            "language": ["eng"],
            "description": "A comprehensive educational book for elementary mathematics."
        }
    
    def test_from_open_library_basic(self, mock_ol_data):
        """Test basic Book creation from Open Library data."""
        book = Book.from_open_library(mock_ol_data)
        
        assert book.id == "OL123456W"
        assert book.title == "Test Educational Book"
        assert book.authors == ["Test Author", "Another Author"]
        assert book.isbn == "1234567890"
        assert book.isbn13 == "9781234567890"
        assert book.publication_date == date(2020, 1, 1)
        assert book.subjects == ["Mathematics", "Education", "Elementary"]
        assert book.source == "open_library"
    
    def test_from_open_library_educational_metadata(self, mock_ol_data):
        """Test educational metadata inference from Open Library data."""
        book = Book.from_open_library(mock_ol_data)
        
        # Should infer grade levels from subjects
        assert len(book.educational_metadata.grade_levels) > 0
        assert book.educational_metadata.educational_subjects == ["Mathematics", "Education", "Elementary"]
    
    def test_from_open_library_cover_url(self, mock_ol_data):
        """Test cover URL generation from Open Library data."""
        book = Book.from_open_library(mock_ol_data)
        
        expected_cover_url = "https://covers.openlibrary.org/b/id/12345-L.jpg"
        assert book.cover_url == expected_cover_url
    
    def test_from_open_library_missing_data(self):
        """Test Book creation with minimal Open Library data."""
        minimal_data = {
            "key": "/works/OL123456W",
            "title": "Minimal Book"
        }
        
        book = Book.from_open_library(minimal_data)
        
        assert book.id == "OL123456W"
        assert book.title == "Minimal Book"
        assert book.authors == []
        assert book.isbn is None
        assert book.subjects == []
    
    def test_is_suitable_for_grade_level(self, mock_ol_data):
        """Test grade level suitability checking."""
        book = Book.from_open_library(mock_ol_data)
        
        # Add specific grade level
        book.educational_metadata.grade_levels = [GradeLevel.GRADES_3_5]
        
        assert book.is_suitable_for_grade_level(GradeLevel.GRADES_3_5)
        assert not book.is_suitable_for_grade_level(GradeLevel.COLLEGE)
    
    def test_has_subject(self, mock_ol_data):
        """Test subject checking."""
        book = Book.from_open_library(mock_ol_data)
        
        assert book.has_subject("Mathematics")
        assert book.has_subject("math")  # Case insensitive
        assert not book.has_subject("Science")
    
    def test_get_educational_score(self, mock_ol_data):
        """Test educational score calculation."""
        book = Book.from_open_library(mock_ol_data)
        
        # Add some educational metadata
        book.educational_metadata.grade_levels = [GradeLevel.GRADES_3_5]
        book.educational_metadata.educational_relevance_score = 0.5
        book.lexile_score = 600
        
        score = book.get_educational_score()
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be boosted by metadata


if __name__ == "__main__":
    pytest.main([__file__])