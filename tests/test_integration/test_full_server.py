"""
Comprehensive Integration Tests for Education MCP Server

This module provides end-to-end testing for the complete Education MCP Server,
testing all API integrations working together and cross-API educational workflows.
"""

import asyncio
import pytest
import sys
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main import (
    initialize_services, cleanup_services, mcp,
    search_educational_books, get_book_details_by_isbn, search_books_by_subject, get_book_recommendations,
    search_educational_articles, get_article_summary, get_article_content, get_featured_article, get_articles_by_subject,
    get_word_definition, get_vocabulary_analysis, get_word_examples, get_pronunciation_guide, get_related_vocabulary,
    search_academic_papers, get_paper_summary, get_recent_research, get_research_by_level, analyze_research_trends,
    get_server_status
)
from config import load_config
from exceptions import OpenEdMCPError


class MockContext:
    """Mock context for testing MCP tools."""
    def __init__(self, session_id: str = "test_session"):
        self.session_id = session_id


@pytest.fixture
async def server_setup():
    """Set up the server for testing."""
    # Mock external dependencies
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock()
        mock_response.text = AsyncMock()
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        # Initialize services
        await initialize_services()
        
        yield
        
        # Cleanup
        await cleanup_services()


class TestFullServerIntegration:
    """Test complete server integration and cross-API workflows."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, server_setup):
        """Test that all server services initialize correctly."""
        ctx = MockContext()
        
        # Test server status
        status = await get_server_status(ctx)
        
        assert status["status"] == "healthy"
        assert "server" in status
        assert "cache" in status
        assert "rate_limits" in status
        assert "usage" in status
        assert status["server"]["name"] == "openedu-mcp-server"
    
    @pytest.mark.asyncio
    async def test_all_tools_registered(self, server_setup):
        """Test that all 20 MCP tools are properly registered."""
        # Get all registered tools
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        
        # Expected tools from all APIs
        expected_tools = [
            # Open Library tools (4)
            "search_educational_books",
            "get_book_details_by_isbn", 
            "search_books_by_subject",
            "get_book_recommendations",
            
            # Wikipedia tools (5)
            "search_educational_articles",
            "get_article_summary",
            "get_article_content", 
            "get_featured_article",
            "get_articles_by_subject",
            
            # Dictionary tools (5)
            "get_word_definition",
            "get_vocabulary_analysis",
            "get_word_examples",
            "get_pronunciation_guide",
            "get_related_vocabulary",
            
            # arXiv tools (5)
            "search_academic_papers",
            "get_paper_summary",
            "get_recent_research",
            "get_research_by_level",
            "analyze_research_trends",
            
            # Server tool (1)
            "get_server_status"
        ]
        
        # Verify all tools are registered
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered"
        
        assert len(tool_names) >= 20, f"Expected at least 20 tools, got {len(tool_names)}"
    
    @pytest.mark.asyncio
    async def test_elementary_education_workflow(self, server_setup):
        """Test complete elementary education workflow (K-2)."""
        ctx = MockContext()
        
        # Mock responses for elementary workflow
        with patch('src.api.openlibrary.OpenLibraryAPI.search_books') as mock_books, \
             patch('src.api.dictionary.DictionaryAPI.get_definition') as mock_definition, \
             patch('src.api.wikipedia.WikipediaAPI.search_articles') as mock_articles:
            
            # Mock book search for K-2
            mock_books.return_value = [{
                "title": "The Very Hungry Caterpillar",
                "author": "Eric Carle",
                "grade_level": "K-2",
                "subject": "Science",
                "educational_value": 0.9,
                "reading_level": "Beginning Reader"
            }]
            
            # Mock simple definition for young learners
            mock_definition.return_value = {
                "word": "caterpillar",
                "definition": "A small creature that turns into a butterfly",
                "grade_level": "K-2",
                "complexity_score": 0.3,
                "educational_context": "Science - Life Cycles"
            }
            
            # Mock age-appropriate articles
            mock_articles.return_value = [{
                "title": "Butterfly Life Cycle",
                "summary": "Learn how caterpillars become butterflies",
                "grade_level": "K-2",
                "educational_value": 0.8,
                "subject": "Science"
            }]
            
            # 1. Search for K-2 appropriate books
            books = await search_educational_books(
                ctx, 
                query="caterpillar", 
                grade_level="K-2",
                subject="Science"
            )
            assert len(books) > 0
            assert books[0]["grade_level"] == "K-2"
            
            # 2. Get simple definitions for vocabulary
            definition = await get_word_definition(
                ctx,
                word="caterpillar",
                grade_level="K-2"
            )
            assert definition["grade_level"] == "K-2"
            assert definition["complexity_score"] <= 0.5
            
            # 3. Find age-appropriate Wikipedia articles
            articles = await search_educational_articles(
                ctx,
                query="butterfly life cycle",
                grade_level="K-2",
                subject="Science"
            )
            assert len(articles) > 0
            assert articles[0]["grade_level"] == "K-2"
    
    @pytest.mark.asyncio
    async def test_high_school_stem_workflow(self, server_setup):
        """Test high school STEM education workflow (9-12)."""
        ctx = MockContext()
        
        with patch('src.api.openlibrary.OpenLibraryAPI.search_books') as mock_books, \
             patch('src.api.dictionary.DictionaryAPI.get_definition') as mock_definition, \
             patch('src.api.wikipedia.WikipediaAPI.search_articles') as mock_articles, \
             patch('src.api.arxiv.ArxivAPI.search_papers') as mock_papers:
            
            # Mock high school science books
            mock_books.return_value = [{
                "title": "Physics: Principles and Problems",
                "author": "McGraw-Hill",
                "grade_level": "9-12",
                "subject": "Physics",
                "educational_value": 0.95,
                "curriculum_alignment": ["NGSS"]
            }]
            
            # Mock technical definitions
            mock_definition.return_value = {
                "word": "quantum",
                "definition": "The smallest possible discrete unit of any physical property",
                "grade_level": "9-12",
                "complexity_score": 0.8,
                "examples": ["quantum mechanics", "quantum physics"]
            }
            
            # Mock educational articles
            mock_articles.return_value = [{
                "title": "Quantum Mechanics",
                "summary": "Introduction to quantum mechanics principles",
                "grade_level": "9-12",
                "subject": "Physics",
                "educational_value": 0.9
            }]
            
            # Mock accessible research papers
            mock_papers.return_value = [{
                "title": "Introduction to Quantum Computing",
                "abstract": "A beginner-friendly overview of quantum computing",
                "academic_level": "High School",
                "educational_relevance": 0.85,
                "subject": "Physics"
            }]
            
            # 1. Search for 9-12 science books
            books = await search_educational_books(
                ctx,
                query="physics",
                grade_level="9-12",
                subject="Science"
            )
            assert len(books) > 0
            assert books[0]["grade_level"] == "9-12"
            
            # 2. Get technical definitions with examples
            definition = await get_word_definition(
                ctx,
                word="quantum",
                grade_level="9-12"
            )
            assert definition["grade_level"] == "9-12"
            assert definition["complexity_score"] >= 0.7
            
            # 3. Find educational Wikipedia articles on STEM topics
            articles = await search_educational_articles(
                ctx,
                query="quantum mechanics",
                grade_level="9-12",
                subject="Physics"
            )
            assert len(articles) > 0
            
            # 4. Search for accessible research papers
            papers = await search_academic_papers(
                ctx,
                query="quantum computing",
                academic_level="High School",
                subject="Physics"
            )
            assert len(papers) > 0
            assert papers[0]["academic_level"] == "High School"
    
    @pytest.mark.asyncio
    async def test_college_research_workflow(self, server_setup):
        """Test college-level research workflow."""
        ctx = MockContext()
        
        with patch('src.api.openlibrary.OpenLibraryAPI.search_books') as mock_books, \
             patch('src.api.dictionary.DictionaryAPI.get_definition') as mock_definition, \
             patch('src.api.wikipedia.WikipediaAPI.get_article') as mock_article, \
             patch('src.api.arxiv.ArxivAPI.search_papers') as mock_papers:
            
            # Mock academic books
            mock_books.return_value = [{
                "title": "Advanced Calculus",
                "author": "Academic Press",
                "grade_level": "College",
                "subject": "Mathematics",
                "educational_value": 0.98,
                "type": "textbook"
            }]
            
            # Mock comprehensive definitions
            mock_definition.return_value = {
                "word": "derivative",
                "definition": "The rate of change of a function with respect to its variable",
                "grade_level": "College",
                "complexity_score": 0.9,
                "etymology": "From Latin derivatus",
                "related_terms": ["integral", "limit", "calculus"]
            }
            
            # Mock detailed articles
            mock_article.return_value = {
                "title": "Calculus",
                "content": "Detailed mathematical content...",
                "grade_level": "College",
                "subject": "Mathematics",
                "educational_value": 0.95
            }
            
            # Mock recent research papers
            mock_papers.return_value = [{
                "title": "Recent Advances in Differential Equations",
                "abstract": "This paper presents new methods...",
                "academic_level": "Graduate",
                "publication_date": "2024-01-15",
                "subject": "Mathematics"
            }]
            
            # 1. Search for academic books and textbooks
            books = await search_educational_books(
                ctx,
                query="calculus textbook",
                grade_level="College",
                subject="Mathematics"
            )
            assert len(books) > 0
            assert books[0]["grade_level"] == "College"
            
            # 2. Get comprehensive definitions and etymology
            definition = await get_word_definition(
                ctx,
                word="derivative",
                grade_level="College"
            )
            assert definition["grade_level"] == "College"
            assert "etymology" in definition
            
            # 3. Find detailed Wikipedia articles
            article = await get_article_content(
                ctx,
                title="Calculus",
                include_images=True
            )
            assert "content" in article
            
            # 4. Search for recent research papers by subject
            papers = await search_academic_papers(
                ctx,
                query="differential equations",
                academic_level="Graduate",
                subject="Mathematics"
            )
            assert len(papers) > 0
    
    @pytest.mark.asyncio
    async def test_educator_resource_workflow(self, server_setup):
        """Test educator resource discovery workflow."""
        ctx = MockContext()
        
        with patch('src.api.openlibrary.OpenLibraryAPI.search_books') as mock_books, \
             patch('src.api.dictionary.DictionaryAPI.get_examples') as mock_examples, \
             patch('src.api.wikipedia.WikipediaAPI.search_articles') as mock_articles, \
             patch('src.api.arxiv.ArxivAPI.get_recent_papers') as mock_recent:
            
            # Mock curriculum-aligned books
            mock_books.return_value = [{
                "title": "Teaching Mathematics Effectively",
                "grade_level": "6-8",
                "subject": "Mathematics",
                "curriculum_alignment": ["Common Core"],
                "educational_value": 0.92,
                "teacher_resource": True
            }]
            
            # Mock vocabulary for lesson planning
            mock_examples.return_value = {
                "word": "fraction",
                "examples": [
                    "1/2 of a pizza",
                    "3/4 of the students",
                    "2/3 cup of flour"
                ],
                "grade_level": "6-8",
                "subject_contexts": ["Mathematics", "Cooking", "Science"]
            }
            
            # Mock educational articles for teaching materials
            mock_articles.return_value = [{
                "title": "Fraction Concepts for Middle School",
                "summary": "Teaching strategies for fractions",
                "grade_level": "6-8",
                "subject": "Mathematics",
                "teacher_resource": True
            }]
            
            # Mock research for professional development
            mock_recent.return_value = [{
                "title": "Effective Mathematics Pedagogy",
                "abstract": "Research on teaching mathematics",
                "academic_level": "Research",
                "subject": "Education",
                "relevance_to_teaching": 0.95
            }]
            
            # 1. Search for curriculum-aligned books
            books = await search_books_by_subject(
                ctx,
                subject="Mathematics",
                grade_level="6-8"
            )
            assert len(books) > 0
            assert "Common Core" in books[0].get("curriculum_alignment", [])
            
            # 2. Get vocabulary for lesson planning
            examples = await get_word_examples(
                ctx,
                word="fraction",
                grade_level="6-8",
                subject="Mathematics"
            )
            assert len(examples["examples"]) > 0
            
            # 3. Find educational articles for teaching materials
            articles = await get_articles_by_subject(
                ctx,
                subject="Mathematics",
                grade_level="6-8"
            )
            assert len(articles) > 0
            
            # 4. Get research papers for professional development
            research = await get_recent_research(
                ctx,
                subject="Education",
                academic_level="Research"
            )
            assert len(research) > 0
    
    @pytest.mark.asyncio
    async def test_cross_api_educational_filtering(self, server_setup):
        """Test that educational filtering works consistently across all APIs."""
        ctx = MockContext()
        
        with patch('src.api.openlibrary.OpenLibraryAPI.search_books') as mock_books, \
             patch('src.api.wikipedia.WikipediaAPI.search_articles') as mock_articles, \
             patch('src.api.dictionary.DictionaryAPI.get_definition') as mock_definition, \
             patch('src.api.arxiv.ArxivAPI.search_papers') as mock_papers:
            
            # Mock responses with consistent educational metadata
            mock_books.return_value = [{
                "title": "Elementary Science",
                "grade_level": "3-5",
                "educational_value": 0.85,
                "subject": "Science"
            }]
            
            mock_articles.return_value = [{
                "title": "Plants for Kids",
                "grade_level": "3-5", 
                "educational_value": 0.82,
                "subject": "Science"
            }]
            
            mock_definition.return_value = {
                "word": "photosynthesis",
                "grade_level": "3-5",
                "complexity_score": 0.6,
                "subject": "Science"
            }
            
            mock_papers.return_value = [{
                "title": "Plant Biology Education",
                "academic_level": "Undergraduate",
                "educational_relevance": 0.88,
                "subject": "Science"
            }]
            
            # Test grade level filtering across APIs
            books = await search_educational_books(ctx, "plants", grade_level="3-5")
            articles = await search_educational_articles(ctx, "plants", grade_level="3-5")
            definition = await get_word_definition(ctx, "photosynthesis", grade_level="3-5")
            papers = await search_academic_papers(ctx, "plant biology", academic_level="Undergraduate")
            
            # Verify consistent grade level filtering
            assert books[0]["grade_level"] == "3-5"
            assert articles[0]["grade_level"] == "3-5"
            assert definition["grade_level"] == "3-5"
            assert papers[0]["academic_level"] == "Undergraduate"
            
            # Verify educational value thresholds
            assert books[0]["educational_value"] >= 0.7
            assert articles[0]["educational_value"] >= 0.7
            assert papers[0]["educational_relevance"] >= 0.7
    
    @pytest.mark.asyncio
    async def test_caching_and_rate_limiting(self, server_setup):
        """Test caching effectiveness and rate limiting across all services."""
        ctx = MockContext()
        
        with patch('src.api.openlibrary.OpenLibraryAPI.search_books') as mock_books:
            mock_books.return_value = [{"title": "Test Book"}]
            
            # First call - should hit API
            result1 = await search_educational_books(ctx, "test query")
            
            # Second call - should hit cache
            result2 = await search_educational_books(ctx, "test query")
            
            # Verify results are consistent
            assert result1 == result2
            
            # Verify API was called only once (second call used cache)
            assert mock_books.call_count == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_across_services(self, server_setup):
        """Test error handling consistency across all services."""
        ctx = MockContext()
        
        # Test with invalid parameters
        with pytest.raises(OpenEdMCPError):
            await search_educational_books(ctx, "")  # Empty query
        
        with pytest.raises(OpenEdMCPError):
            await get_book_details_by_isbn(ctx, "invalid-isbn")
        
        with pytest.raises(OpenEdMCPError):
            await get_word_definition(ctx, "")  # Empty word
        
        with pytest.raises(OpenEdMCPError):
            await search_academic_papers(ctx, "", max_results=0)  # Invalid limit
    
    @pytest.mark.asyncio
    async def test_educational_metadata_enrichment(self, server_setup):
        """Test that educational metadata is properly enriched across all APIs."""
        ctx = MockContext()
        
        with patch('src.api.openlibrary.OpenLibraryAPI.search_books') as mock_books, \
             patch('src.api.wikipedia.WikipediaAPI.get_article') as mock_article, \
             patch('src.api.dictionary.DictionaryAPI.get_definition') as mock_definition, \
             patch('src.api.arxiv.ArxivAPI.get_paper') as mock_paper:
            
            # Mock responses with educational enrichment
            mock_books.return_value = [{
                "title": "Math Concepts",
                "educational_metadata": {
                    "grade_level": "6-8",
                    "subject": "Mathematics",
                    "curriculum_alignment": ["Common Core"],
                    "reading_level": "Grade 7",
                    "educational_value": 0.9
                }
            }]
            
            mock_article.return_value = {
                "title": "Algebra",
                "educational_analysis": {
                    "complexity_score": 0.7,
                    "grade_level": "6-8",
                    "key_concepts": ["variables", "equations"],
                    "prerequisite_knowledge": ["arithmetic"]
                }
            }
            
            mock_definition.return_value = {
                "word": "variable",
                "educational_context": {
                    "grade_level": "6-8",
                    "subject_applications": ["Mathematics", "Science"],
                    "complexity_progression": ["simple", "intermediate"]
                }
            }
            
            mock_paper.return_value = {
                "title": "Algebra Education Research",
                "educational_relevance": {
                    "academic_level": "Graduate",
                    "teaching_applications": 0.85,
                    "classroom_relevance": "High"
                }
            }
            
            # Test educational metadata enrichment
            books = await search_educational_books(ctx, "math")
            article = await get_article_content(ctx, "Algebra")
            definition = await get_word_definition(ctx, "variable")
            paper = await get_paper_summary(ctx, "2301.00001")
            
            # Verify educational metadata is present
            assert "educational_metadata" in books[0]
            assert "educational_analysis" in article
            assert "educational_context" in definition
            assert "educational_relevance" in paper


if __name__ == "__main__":
    pytest.main([__file__, "-v"])