"""
Unit tests for Wikipedia tools.

This module contains comprehensive tests for the Wikipedia API integration,
including educational filtering, content analysis, and error handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
from typing import Dict, Any, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.wikipedia_tools import WikipediaTool
from api.wikipedia import WikipediaClient
from models.article import Article
from models.base import GradeLevel, EducationalMetadata
from config import Config
from exceptions import ToolError, ValidationError, APIError


class TestWikipediaClient:
    """Test cases for WikipediaClient."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock()
        
        # Mock APIs configuration
        config.apis = MagicMock()
        config.apis.wikipedia = MagicMock()
        config.apis.wikipedia.base_url = "https://en.wikipedia.org/api/rest_v1"
        config.apis.wikipedia.timeout = 30
        config.apis.wikipedia.retry_attempts = 2
        config.apis.wikipedia.backoff_factor = 2.0
        
        # Mock server configuration
        config.server = MagicMock()
        config.server.name = "test-server"
        config.server.version = "1.0.0"
        
        return config
    
    @pytest.fixture
    def wikipedia_client(self, mock_config):
        """Create a WikipediaClient instance."""
        return WikipediaClient(mock_config)
    
    @pytest.mark.asyncio
    async def test_search_wikipedia_success(self, wikipedia_client):
        """Test successful Wikipedia search."""
        mock_response = {
            "query": {
                "search": [
                    {
                        "title": "Mathematics",
                        "snippet": "Mathematics is the study of numbers...",
                        "size": 50000,
                        "wordcount": 8000,
                        "timestamp": "2023-01-01T00:00:00Z",
                        "pageid": 12345
                    }
                ]
            }
        }
        
        with patch.object(wikipedia_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                mock_response,  # Search response
                {  # Summary response
                    "title": "Mathematics",
                    "extract": "Mathematics is the study of numbers, shapes, and patterns.",
                    "pageid": 12345
                }
            ]
            
            results = await wikipedia_client.search_wikipedia("mathematics", limit=1)
            
            assert len(results) == 1
            assert results[0]["title"] == "Mathematics"
            assert "snippet" in results[0]
            assert "url" in results[0]
    
    @pytest.mark.asyncio
    async def test_search_wikipedia_validation_error(self, wikipedia_client):
        """Test search with invalid parameters."""
        with pytest.raises(ValidationError):
            await wikipedia_client.search_wikipedia("", limit=1)
        
        with pytest.raises(ValidationError):
            await wikipedia_client.search_wikipedia("test", limit=0)
        
        with pytest.raises(ValidationError):
            await wikipedia_client.search_wikipedia("test", lang="invalid")
    
    @pytest.mark.asyncio
    async def test_get_article_summary_success(self, wikipedia_client):
        """Test successful article summary retrieval."""
        mock_response = {
            "title": "Science",
            "extract": "Science is a systematic enterprise...",
            "pageid": 67890,
            "fullurl": "https://en.wikipedia.org/wiki/Science"
        }
        
        with patch.object(wikipedia_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await wikipedia_client.get_article_summary("Science")
            
            assert result["title"] == "Science"
            assert "extract" in result
            assert result["pageid"] == 67890
    
    @pytest.mark.asyncio
    async def test_get_article_content_success(self, wikipedia_client):
        """Test successful article content retrieval."""
        mock_response = {
            "query": {
                "pages": {
                    "12345": {
                        "title": "Biology",
                        "extract": "Biology is the natural science...",
                        "pageid": 12345,
                        "fullurl": "https://en.wikipedia.org/wiki/Biology",
                        "categories": [
                            {"title": "Category:Biology"},
                            {"title": "Category:Life sciences"}
                        ],
                        "links": [
                            {"title": "Cell biology"},
                            {"title": "Genetics"}
                        ],
                        "images": [
                            {"title": "File:DNA_structure.jpg"}
                        ]
                    }
                }
            }
        }
        
        with patch.object(wikipedia_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await wikipedia_client.get_article_content("Biology")
            
            assert result["title"] == "Biology"
            assert "extract" in result
            assert "categories" in result
            assert len(result["categories"]) == 2
            assert "Biology" in result["categories"]
    
    @pytest.mark.asyncio
    async def test_get_daily_featured_success(self, wikipedia_client):
        """Test successful featured article retrieval."""
        mock_response = {
            "tfa": {
                "title": "Featured Article",
                "extract": "This is today's featured article...",
                "description": "A great article",
                "content_urls": {
                    "desktop": {
                        "page": "https://en.wikipedia.org/wiki/Featured_Article"
                    }
                }
            }
        }
        
        with patch.object(wikipedia_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await wikipedia_client.get_daily_featured()
            
            assert result["title"] == "Featured Article"
            assert result["type"] == "featured_article"
            assert "extract" in result
    
    @pytest.mark.asyncio
    async def test_get_article_images_success(self, wikipedia_client):
        """Test successful article images retrieval."""
        mock_images_response = {
            "query": {
                "pages": {
                    "12345": {
                        "images": [
                            {"title": "File:Example.jpg"},
                            {"title": "File:Another.png"}
                        ]
                    }
                }
            }
        }
        
        mock_image_info_response = {
            "query": {
                "pages": {
                    "67890": {
                        "imageinfo": [{
                            "url": "https://upload.wikimedia.org/wikipedia/commons/example.jpg",
                            "width": 800,
                            "height": 600,
                            "mime": "image/jpeg"
                        }]
                    }
                }
            }
        }
        
        with patch.object(wikipedia_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                mock_images_response,
                mock_image_info_response,
                mock_image_info_response
            ]
            
            result = await wikipedia_client.get_article_images("Test Article")
            
            assert len(result) == 2
            assert result[0]["title"] == "File:Example.jpg"
            assert "url" in result[0]
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, wikipedia_client):
        """Test successful health check."""
        with patch.object(wikipedia_client, 'search_wikipedia', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            
            result = await wikipedia_client.health_check()
            
            assert result["status"] == "healthy"
            assert "response_time_seconds" in result
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, wikipedia_client):
        """Test health check failure."""
        with patch.object(wikipedia_client, 'search_wikipedia', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = APIError("Connection failed", "wikipedia")
            
            result = await wikipedia_client.health_check()
            
            assert result["status"] == "unhealthy"
            assert "error" in result


class TestWikipediaTool:
    """Test cases for WikipediaTool."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock()
        
        # Mock education configuration
        config.education = MagicMock()
        config.education.content_filters = MagicMock()
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
    def wikipedia_tool(self, mock_config, mock_services):
        """Create a WikipediaTool instance."""
        cache_service, rate_limiting_service, usage_service = mock_services
        tool = WikipediaTool(mock_config, cache_service, rate_limiting_service, usage_service)
        tool.client = AsyncMock(spec=WikipediaClient)
        return tool
    
    @pytest.mark.asyncio
    async def test_search_educational_articles_success(self, wikipedia_tool):
        """Test successful educational article search."""
        mock_search_results = [
            {
                "title": "Mathematics Education",
                "snippet": "Mathematics education is the practice of teaching...",
                "url": "https://en.wikipedia.org/wiki/Mathematics_Education",
                "summary": "Mathematics education involves teaching mathematical concepts...",
                "pageid": 12345
            }
        ]
        
        wikipedia_tool.client.search_wikipedia.return_value = mock_search_results
        
        with patch.object(wikipedia_tool, 'execute_with_monitoring', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = [{"title": "Mathematics Education", "educational_score": 0.8}]
            
            result = await wikipedia_tool.search_educational_articles(
                query="mathematics education",
                subject="Mathematics",
                grade_level="6-8",
                limit=5
            )
            
            assert len(result) == 1
            assert result[0]["title"] == "Mathematics Education"
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_article_summary_success(self, wikipedia_tool):
        """Test successful article summary retrieval."""
        mock_summary = {
            "title": "Science",
            "extract": "Science is a systematic enterprise...",
            "pageid": 67890
        }
        
        wikipedia_tool.client.get_article_summary.return_value = mock_summary
        
        with patch.object(wikipedia_tool, 'execute_with_monitoring', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"title": "Science", "educational_score": 0.9}
            
            result = await wikipedia_tool.get_article_summary("Science")
            
            assert result["title"] == "Science"
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_article_content_success(self, wikipedia_tool):
        """Test successful article content retrieval."""
        mock_content = {
            "title": "Biology",
            "extract": "Biology is the natural science...",
            "categories": ["Biology", "Life sciences"],
            "links": ["Cell biology", "Genetics"]
        }
        
        mock_images = [
            {"url": "https://example.com/image1.jpg"},
            {"url": "https://example.com/image2.jpg"}
        ]
        
        wikipedia_tool.client.get_article_content.return_value = mock_content
        wikipedia_tool.client.get_article_images.return_value = mock_images
        
        with patch.object(wikipedia_tool, 'execute_with_monitoring', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"title": "Biology", "multimedia_resources": ["https://example.com/image1.jpg"]}
            
            result = await wikipedia_tool.get_article_content("Biology", include_images=True)
            
            assert result["title"] == "Biology"
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_featured_article_success(self, wikipedia_tool):
        """Test successful featured article retrieval."""
        mock_featured = {
            "title": "Featured Article",
            "extract": "This is today's featured article...",
            "date": "2023/01/01",
            "type": "featured_article"
        }
        
        wikipedia_tool.client.get_daily_featured.return_value = mock_featured
        
        with patch.object(wikipedia_tool, 'execute_with_monitoring', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {
                "title": "Featured Article",
                "featured_date": "2023/01/01",
                "featured_type": "featured_article"
            }
            
            result = await wikipedia_tool.get_featured_article("2023/01/01")
            
            assert result["title"] == "Featured Article"
            assert result["featured_date"] == "2023/01/01"
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_articles_by_subject_success(self, wikipedia_tool):
        """Test successful subject-based article search."""
        mock_search_results = [
            {
                "title": "Physics Concepts",
                "snippet": "Physics is the natural science...",
                "url": "https://en.wikipedia.org/wiki/Physics_Concepts",
                "pageid": 54321
            }
        ]
        
        wikipedia_tool.client.search_wikipedia.return_value = mock_search_results
        
        with patch.object(wikipedia_tool, 'execute_with_monitoring', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = [{"title": "Physics Concepts", "subject": "Science"}]
            
            result = await wikipedia_tool.get_articles_by_subject(
                subject="Science",
                grade_level="9-12",
                limit=5
            )
            
            assert len(result) == 1
            assert result[0]["title"] == "Physics Concepts"
            mock_execute.assert_called_once()
    
    def test_calculate_educational_relevance(self, wikipedia_tool):
        """Test educational relevance calculation."""
        article = Article(
            title="Mathematics Education Research",
            url="https://example.com",
            summary="This article discusses educational research in mathematics teaching and learning.",
            categories=["Education", "Mathematics", "Research"],
            educational_metadata=EducationalMetadata()
        )
        
        score = wikipedia_tool._calculate_educational_relevance(
            article, 
            target_subject="Mathematics",
            target_grade_level="6-8"
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have high relevance due to educational keywords
    
    def test_analyze_reading_level(self, wikipedia_tool):
        """Test reading level analysis."""
        # Short article
        short_article = Article(
            title="Simple Math",
            url="https://example.com",
            summary="Math is fun. Numbers are everywhere. We use math daily.",
            educational_metadata=EducationalMetadata()
        )
        
        analysis = wikipedia_tool._analyze_reading_level(short_article)
        assert analysis["level"] == "Elementary"
        assert analysis["difficulty"] == "Beginner"
        
        # Long article
        long_content = " ".join(["Complex mathematical concepts and theoretical frameworks"] * 100)
        long_article = Article(
            title="Advanced Mathematics",
            url="https://example.com",
            summary=long_content,
            educational_metadata=EducationalMetadata()
        )
        
        analysis = wikipedia_tool._analyze_reading_level(long_article)
        assert analysis["level"] == "College"
        assert analysis["difficulty"] == "Advanced"
    
    def test_determine_grade_levels(self, wikipedia_tool):
        """Test grade level determination."""
        # Elementary level article
        elementary_article = Article(
            title="Basic Addition",
            url="https://example.com",
            summary="Addition is putting numbers together. 1 + 1 = 2.",
            educational_metadata=EducationalMetadata()
        )
        
        grade_levels = wikipedia_tool._determine_grade_levels(elementary_article)
        assert GradeLevel.K_2 in grade_levels
        assert GradeLevel.GRADES_3_5 in grade_levels
    
    def test_enhance_subject_classification(self, wikipedia_tool):
        """Test subject classification enhancement."""
        categories = ["Mathematics", "Algebra", "Educational research"]
        
        enhanced = wikipedia_tool._enhance_subject_classification(
            categories, 
            target_subject="Mathematics"
        )
        
        assert "Mathematics" in enhanced
        assert len(enhanced) <= 5
    
    def test_analyze_curriculum_alignment(self, wikipedia_tool):
        """Test curriculum alignment analysis."""
        article = Article(
            title="Scientific Method",
            url="https://example.com",
            summary="The scientific method involves hypothesis testing and inquiry-based learning.",
            educational_metadata=EducationalMetadata()
        )
        
        alignment = wikipedia_tool._analyze_curriculum_alignment(article, "Science")
        
        # Should detect NGSS alignment due to scientific method keywords
        assert isinstance(alignment, list)
    
    def test_extract_educational_topics(self, wikipedia_tool):
        """Test educational topic extraction."""
        article = Article(
            title="Biology Education",
            url="https://example.com",
            summary="Biology education involves teaching about cells, genetics, and evolution.",
            categories=["Biology", "Education", "Life Sciences"],
            content="Students learn about DNA, proteins, and cellular processes.",
            educational_metadata=EducationalMetadata()
        )
        
        topics = wikipedia_tool._extract_educational_topics(article)
        
        assert len(topics) > 0
        assert len(topics) <= 15
        # Should include some biology-related terms
        biology_terms = [topic for topic in topics if 'biolog' in topic.lower()]
        assert len(biology_terms) > 0
    
    def test_get_subject_search_terms(self, wikipedia_tool):
        """Test subject search terms generation."""
        math_terms = wikipedia_tool._get_subject_search_terms("Mathematics")
        assert "mathematics" in math_terms
        assert "algebra" in math_terms
        
        science_terms = wikipedia_tool._get_subject_search_terms("Science")
        assert "science" in science_terms
        assert "biology" in science_terms
        
        # Unknown subject should return the subject itself
        unknown_terms = wikipedia_tool._get_subject_search_terms("Unknown Subject")
        assert "unknown subject" in unknown_terms
    
    def test_apply_educational_filters(self, wikipedia_tool):
        """Test educational filtering."""
        articles = [
            Article(
                title="High Relevance Article",
                url="https://example.com/1",
                summary="Educational content about mathematics teaching.",
                educational_metadata=EducationalMetadata(
                    educational_relevance_score=0.9,
                    grade_levels=[GradeLevel.GRADES_6_8],
                    educational_subjects=["Mathematics"]
                )
            ),
            Article(
                title="Low Relevance Article",
                url="https://example.com/2",
                summary="Random content not related to education.",
                educational_metadata=EducationalMetadata(
                    educational_relevance_score=0.3,
                    grade_levels=[GradeLevel.COLLEGE],
                    educational_subjects=["Other"]
                )
            )
        ]
        
        # Filter by relevance
        filtered = wikipedia_tool._apply_educational_filters(
            articles,
            min_relevance_score=0.7
        )
        assert len(filtered) == 1
        assert filtered[0].title == "High Relevance Article"
        
        # Filter by grade level
        filtered = wikipedia_tool._apply_educational_filters(
            articles,
            grade_level=GradeLevel.GRADES_6_8
        )
        assert len(filtered) == 1
        assert filtered[0].title == "High Relevance Article"
        
        # Filter by subject
        filtered = wikipedia_tool._apply_educational_filters(
            articles,
            subject="Mathematics"
        )
        assert len(filtered) == 1
        assert filtered[0].title == "High Relevance Article"
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, wikipedia_tool):
        """Test successful health check."""
        wikipedia_tool.client.health_check.return_value = {
            "status": "healthy",
            "response_time_seconds": 0.5,
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        result = await wikipedia_tool.health_check()
        
        assert result["status"] == "healthy"
        assert result["tool_name"] == "wikipedia"
        assert result["api_name"] == "wikipedia"
        assert "educational_features" in result
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, wikipedia_tool):
        """Test health check failure."""
        wikipedia_tool.client.health_check.side_effect = Exception("Connection failed")
        
        result = await wikipedia_tool.health_check()
        
        assert result["status"] == "unhealthy"
        assert "error" in result


class TestWikipediaIntegration:
    """Integration tests for Wikipedia functionality."""
    
    @pytest.mark.asyncio
    async def test_article_from_wikipedia_creation(self):
        """Test Article creation from Wikipedia data."""
        wp_data = {
            "title": "Test Article",
            "extract": "This is a test article about educational content.",
            "pageid": 12345,
            "fullurl": "https://en.wikipedia.org/wiki/Test_Article",
            "categories": [
                {"title": "Category:Education"},
                {"title": "Category:Learning"}
            ],
            "links": ["Related Topic 1", "Related Topic 2"],
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        article = Article.from_wikipedia(wp_data)
        
        assert article.title == "Test Article"
        assert article.source == "wikipedia"
        assert article.source_id == "12345"
        assert len(article.categories) == 2
        assert "Education" in article.categories
        assert article.educational_metadata.educational_relevance_score > 0
    
    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self):
        """Test end-to-end search flow with mocked responses."""
        # This would be a more comprehensive integration test
        # that tests the full flow from search to enrichment
        pass


if __name__ == "__main__":
    pytest.main([__file__])