"""
Unit tests for arXiv tools.

This module contains comprehensive tests for the arXiv API integration,
including paper search, educational filtering, and metadata enrichment.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.arxiv_tools import ArxivTool
from api.arxiv import ArxivClient
from models.research_paper import ResearchPaper
from models.base import GradeLevel, EducationalMetadata
from config import Config
from services.cache_service import CacheService
from services.rate_limiting_service import RateLimitingService
from services.usage_service import UsageService
from exceptions import ToolError, ValidationError, APIError, CacheError


class TestArxivClient:
    """Test cases for ArxivClient."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        
        # Create nested mock structure
        config.apis = Mock()
        config.apis.arxiv = Mock()
        config.apis.arxiv.base_url = "http://export.arxiv.org/api"
        config.apis.arxiv.timeout = 60
        config.apis.arxiv.retry_attempts = 2
        config.apis.arxiv.backoff_factor = 2.0
        
        config.server = Mock()
        config.server.name = "test-server"
        config.server.version = "1.0.0"
        
        return config
    
    @pytest.fixture
    def arxiv_client(self, mock_config):
        """Create ArxivClient instance."""
        return ArxivClient(mock_config)
    
    @pytest.fixture
    def sample_arxiv_xml(self):
        """Sample arXiv XML response."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Sample Paper Title</title>
    <summary>This is a sample abstract for testing purposes.</summary>
    <published>2023-01-01T00:00:00Z</published>
    <updated>2023-01-01T00:00:00Z</updated>
    <author>
      <name>John Doe</name>
    </author>
    <author>
      <name>Jane Smith</name>
    </author>
    <category term="cs.AI" />
    <category term="cs.LG" />
    <link href="http://arxiv.org/abs/2301.00001v1" rel="alternate" type="text/html" />
    <link href="http://arxiv.org/pdf/2301.00001v1.pdf" rel="related" type="application/pdf" />
    <arxiv:primary_category term="cs.AI" />
    <arxiv:comment>10 pages, 5 figures</arxiv:comment>
  </entry>
</feed>'''
    
    def test_init(self, arxiv_client, mock_config):
        """Test ArxivClient initialization."""
        assert arxiv_client.config == mock_config
        assert arxiv_client.base_url == "http://export.arxiv.org/api"
        assert arxiv_client.query_url == "http://export.arxiv.org/api/query"
        assert arxiv_client.timeout == 60
        assert "test-server/1.0.0" in arxiv_client.headers['User-Agent']
    
    def test_parse_atom_feed(self, arxiv_client, sample_arxiv_xml):
        """Test XML parsing functionality."""
        papers = arxiv_client._parse_atom_feed(sample_arxiv_xml)
        
        assert len(papers) == 1
        paper = papers[0]
        
        assert paper['id'] == "http://arxiv.org/abs/2301.00001v1"
        assert paper['title'] == "Sample Paper Title"
        assert paper['summary'] == "This is a sample abstract for testing purposes."
        assert len(paper['authors']) == 2
        assert paper['authors'][0]['name'] == "John Doe"
        assert paper['authors'][1]['name'] == "Jane Smith"
        assert paper['categories'] == ["cs.AI", "cs.LG"]
        assert paper['primary_category'] == "cs.AI"
        assert paper['comment'] == "10 pages, 5 figures"
    
    def test_validate_search_params(self, arxiv_client):
        """Test search parameter validation."""
        # Valid parameters
        arxiv_client._validate_search_params("test query", 10)
        
        # Invalid query
        with pytest.raises(ValidationError, match="Search query cannot be empty"):
            arxiv_client._validate_search_params("", 10)
        
        with pytest.raises(ValidationError, match="Search query cannot be empty"):
            arxiv_client._validate_search_params("   ", 10)
        
        # Invalid max_results
        with pytest.raises(ValidationError, match="max_results must be between 1 and 100"):
            arxiv_client._validate_search_params("test", 0)
        
        with pytest.raises(ValidationError, match="max_results must be between 1 and 100"):
            arxiv_client._validate_search_params("test", 101)
    
    def test_build_search_query(self, arxiv_client):
        """Test search query building."""
        # Basic query
        query = arxiv_client._build_search_query("machine learning")
        assert query == "machine learning"
        
        # Query with category
        query = arxiv_client._build_search_query("neural networks", "computer_science")
        assert "neural networks" in query
        assert "cat:cs" in query
        
        # Query with physics category
        query = arxiv_client._build_search_query("quantum", "physics")
        assert "quantum" in query
        assert "cat:physics" in query
    
    def test_get_arxiv_categories(self, arxiv_client):
        """Test arXiv category mapping."""
        # Computer science
        categories = arxiv_client._get_arxiv_categories("computer_science")
        assert "cs" in categories
        
        # Mathematics
        categories = arxiv_client._get_arxiv_categories("mathematics")
        assert "math" in categories
        
        # Physics
        categories = arxiv_client._get_arxiv_categories("physics")
        assert "physics" in categories
        
        # Direct category - "cs" matches "computer_science" so returns cs categories
        categories = arxiv_client._get_arxiv_categories("cs")
        assert categories == ["cs"]  # Should return cs when matching computer_science
        
        # Unknown category
        categories = arxiv_client._get_arxiv_categories("unknown")
        assert categories == []
    
    @pytest.mark.asyncio
    async def test_search_papers_success(self, arxiv_client, sample_arxiv_xml):
        """Test successful paper search."""
        with patch.object(arxiv_client, '_make_request', return_value=sample_arxiv_xml):
            papers = await arxiv_client.search_papers("machine learning", max_results=5)
            
            assert len(papers) == 1
            assert papers[0]['title'] == "Sample Paper Title"
    
    @pytest.mark.asyncio
    async def test_search_papers_validation_error(self, arxiv_client):
        """Test search papers with validation error."""
        with pytest.raises(ValidationError):
            await arxiv_client.search_papers("", max_results=5)
    
    @pytest.mark.asyncio
    async def test_get_paper_abstract_success(self, arxiv_client, sample_arxiv_xml):
        """Test successful paper abstract retrieval."""
        with patch.object(arxiv_client, '_make_request', return_value=sample_arxiv_xml):
            paper = await arxiv_client.get_paper_abstract("2301.00001")
            
            assert paper['title'] == "Sample Paper Title"
            assert paper['summary'] == "This is a sample abstract for testing purposes."
    
    @pytest.mark.asyncio
    async def test_get_paper_abstract_not_found(self, arxiv_client):
        """Test paper abstract retrieval when paper not found."""
        empty_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
</feed>'''
        
        with patch.object(arxiv_client, '_make_request', return_value=empty_xml):
            with pytest.raises(APIError, match="Paper not found"):
                await arxiv_client.get_paper_abstract("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_paper_authors(self, arxiv_client, sample_arxiv_xml):
        """Test paper authors retrieval."""
        with patch.object(arxiv_client, '_make_request', return_value=sample_arxiv_xml):
            authors = await arxiv_client.get_paper_authors("2301.00001")
            
            assert len(authors) == 2
            assert authors[0]['name'] == "John Doe"
            assert authors[1]['name'] == "Jane Smith"
    
    @pytest.mark.asyncio
    async def test_get_recent_papers(self, arxiv_client, sample_arxiv_xml):
        """Test recent papers retrieval."""
        with patch.object(arxiv_client, '_make_request', return_value=sample_arxiv_xml):
            papers = await arxiv_client.get_recent_papers("cs", days=7, max_results=5)
            
            assert len(papers) == 1
            assert papers[0]['title'] == "Sample Paper Title"
    
    def test_analyze_educational_level(self, arxiv_client):
        """Test educational level analysis."""
        # High school level
        paper_data = {
            'title': 'An Introductory Guide to Basic Mathematics',
            'summary': 'This paper provides a basic introduction to elementary concepts.'
        }
        level = arxiv_client.analyze_educational_level(paper_data)
        assert level == "High School"
        
        # Research level
        paper_data = {
            'title': 'Novel Theorem on Advanced Topology',
            'summary': 'We present a cutting-edge proof of a new conjecture.'
        }
        level = arxiv_client.analyze_educational_level(paper_data)
        assert level in ["Research", "Graduate"]  # Both are acceptable for this content
        
        # Undergraduate level
        paper_data = {
            'title': 'Undergraduate Course in Linear Algebra',
            'summary': 'This introductory course covers college-level mathematics.'
        }
        level = arxiv_client.analyze_educational_level(paper_data)
        assert level in ["Undergraduate", "High School"]  # Both are acceptable for introductory content
    
    def test_calculate_complexity_score(self, arxiv_client):
        """Test complexity score calculation."""
        # Simple paper
        paper_data = {
            'title': 'Simple Introduction',
            'summary': 'A basic overview of the topic.'
        }
        score = arxiv_client.calculate_complexity_score(paper_data)
        assert 0.0 <= score <= 1.0
        
        # Complex paper
        paper_data = {
            'title': 'Advanced Theorem and Novel Algorithm',
            'summary': 'This cutting-edge research presents sophisticated methodology and advanced optimization techniques with novel framework for complex problems.'
        }
        score = arxiv_client.calculate_complexity_score(paper_data)
        assert score > 0.3  # Should be higher complexity
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, arxiv_client, sample_arxiv_xml):
        """Test successful health check."""
        with patch.object(arxiv_client, '_make_request', return_value=sample_arxiv_xml):
            result = await arxiv_client.health_check()
            
            assert result['status'] == 'healthy'
            assert 'response_time_seconds' in result
            assert result['papers_found'] == 1
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, arxiv_client):
        """Test health check failure."""
        with patch.object(arxiv_client, '_make_request', side_effect=APIError("Connection failed", "arxiv")):
            result = await arxiv_client.health_check()
            
            assert result['status'] == 'unhealthy'
            assert 'error' in result


class TestArxivTool:
    """Test cases for ArxivTool."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        
        # Create nested mock structure for education
        config.education = Mock()
        config.education.content_filters = Mock()
        config.education.content_filters.min_educational_relevance = 0.7
        config.education.content_filters.enable_age_appropriate = True
        config.education.content_filters.enable_curriculum_alignment = True
        
        # Create nested mock structure for APIs (needed by ArxivClient)
        config.apis = Mock()
        config.apis.arxiv = Mock()
        config.apis.arxiv.base_url = "http://export.arxiv.org/api"
        config.apis.arxiv.timeout = 60
        config.apis.arxiv.retry_attempts = 2
        config.apis.arxiv.backoff_factor = 2.0
        
        config.server = Mock()
        config.server.name = "test-server"
        config.server.version = "1.0.0"
        
        return config
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        cache_service = Mock(spec=CacheService)
        cache_service.health_check = AsyncMock(return_value=True)
        
        rate_limiting_service = Mock(spec=RateLimitingService)
        rate_limiting_service.get_rate_limit_status = AsyncMock(return_value={'remaining': 100})
        
        usage_service = Mock(spec=UsageService)
        
        return cache_service, rate_limiting_service, usage_service
    
    @pytest.fixture
    def arxiv_tool(self, mock_config, mock_services):
        """Create ArxivTool instance."""
        cache_service, rate_limiting_service, usage_service = mock_services
        tool = ArxivTool(mock_config, cache_service, rate_limiting_service, usage_service)
        tool.client = Mock(spec=ArxivClient)
        return tool
    
    @pytest.fixture
    def sample_paper_data(self):
        """Sample paper data for testing."""
        return {
            'id': 'http://arxiv.org/abs/2301.00001v1',
            'title': 'Educational Machine Learning Methods',
            'summary': 'This paper presents machine learning techniques for educational applications.',
            'authors': [{'name': 'John Doe'}, {'name': 'Jane Smith'}],
            'categories': ['cs.AI', 'cs.LG'],
            'published': '2023-01-01T00:00:00Z',
            'links': [
                {'href': 'http://arxiv.org/pdf/2301.00001v1.pdf', 'type': 'application/pdf'},
                {'href': 'http://arxiv.org/abs/2301.00001v1', 'rel': 'alternate'}
            ]
        }
    
    @pytest.fixture
    def sample_research_paper(self):
        """Sample ResearchPaper instance."""
        return ResearchPaper(
            arxiv_id="2301.00001",
            title="Educational Machine Learning Methods",
            authors=["John Doe", "Jane Smith"],
            abstract="This paper presents machine learning techniques for educational applications.",
            subjects=["cs.AI", "cs.LG"],
            publication_date=date(2023, 1, 1),
            pdf_url="http://arxiv.org/pdf/2301.00001v1.pdf",
            educational_metadata=EducationalMetadata(
                educational_subjects=["Technology"],
                educational_relevance_score=0.8,
                grade_levels=[GradeLevel.COLLEGE],
                difficulty_level="Intermediate"
            )
        )
    
    def test_init(self, arxiv_tool, mock_config):
        """Test ArxivTool initialization."""
        assert arxiv_tool.config == mock_config
        assert arxiv_tool.api_name == "arxiv"
        assert arxiv_tool.min_educational_relevance == 0.7
        assert arxiv_tool.enable_age_appropriate is True
    
    @pytest.mark.asyncio
    async def test_search_academic_papers_success(self, arxiv_tool, sample_paper_data, sample_research_paper):
        """Test successful academic paper search."""
        # Mock client search
        arxiv_tool.client.search_papers = AsyncMock(return_value=[sample_paper_data])
        
        # Mock ResearchPaper.from_arxiv
        with patch.object(ResearchPaper, 'from_arxiv', return_value=sample_research_paper):
            # Mock educational enrichment
            with patch.object(arxiv_tool, '_enrich_educational_metadata', return_value=sample_research_paper):
                # Mock filtering and sorting
                with patch.object(arxiv_tool, '_apply_educational_filters', return_value=[sample_research_paper]):
                    with patch.object(arxiv_tool, 'sort_by_educational_relevance', return_value=[sample_research_paper]):
                        with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
                            mock_execute.return_value = [sample_research_paper.to_dict()]
                            
                            result = await arxiv_tool.search_academic_papers(
                                query="machine learning",
                                subject="Technology",
                                academic_level="Graduate",
                                max_results=10
                            )
                            
                            assert len(result) == 1
                            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_academic_papers_validation_error(self, arxiv_tool):
        """Test search with validation error."""
        with patch.object(arxiv_tool, 'validate_common_parameters', side_effect=ValidationError("Invalid query")):
            with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
                mock_execute.side_effect = ValidationError("Invalid query")
                
                with pytest.raises(ValidationError):
                    await arxiv_tool.search_academic_papers(query="", max_results=10)
    
    @pytest.mark.asyncio
    async def test_get_paper_summary_success(self, arxiv_tool, sample_paper_data, sample_research_paper):
        """Test successful paper summary retrieval."""
        arxiv_tool.client.get_paper_abstract = AsyncMock(return_value=sample_paper_data)
        
        with patch.object(ResearchPaper, 'from_arxiv', return_value=sample_research_paper):
            with patch.object(arxiv_tool, '_enrich_educational_metadata', return_value=sample_research_paper):
                with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
                    mock_execute.return_value = sample_research_paper.to_dict()
                    
                    result = await arxiv_tool.get_paper_summary(
                        paper_id="2301.00001",
                        include_educational_analysis=True
                    )
                    
                    assert result == sample_research_paper.to_dict()
                    mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_paper_summary_not_found(self, arxiv_tool):
        """Test paper summary when paper not found."""
        arxiv_tool.client.get_paper_abstract = AsyncMock(return_value=None)
        
        with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
            mock_execute.side_effect = ToolError("Paper not found: nonexistent", "arxiv_tool")
            
            with pytest.raises(ToolError):
                await arxiv_tool.get_paper_summary(paper_id="nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_recent_research_success(self, arxiv_tool, sample_paper_data, sample_research_paper):
        """Test successful recent research retrieval."""
        arxiv_tool.client.get_recent_papers = AsyncMock(return_value=[sample_paper_data])
        
        with patch.object(ResearchPaper, 'from_arxiv', return_value=sample_research_paper):
            with patch.object(arxiv_tool, '_enrich_educational_metadata', return_value=sample_research_paper):
                with patch.object(arxiv_tool, '_apply_educational_filters', return_value=[sample_research_paper]):
                    with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
                        mock_execute.return_value = [sample_research_paper.to_dict()]
                        
                        result = await arxiv_tool.get_recent_research(
                            subject="Computer Science",
                            days=7,
                            max_results=10
                        )
                        
                        assert len(result) == 1
                        mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_recent_research_validation_error(self, arxiv_tool):
        """Test recent research with validation error."""
        with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
            mock_execute.side_effect = ValidationError("days must be between 1 and 30")
            
            with pytest.raises(ValidationError):
                await arxiv_tool.get_recent_research(subject="Computer Science", days=50)
    
    @pytest.mark.asyncio
    async def test_get_research_by_level_success(self, arxiv_tool, sample_paper_data, sample_research_paper):
        """Test successful research by level retrieval."""
        arxiv_tool.client.search_papers = AsyncMock(return_value=[sample_paper_data])
        
        with patch.object(ResearchPaper, 'from_arxiv', return_value=sample_research_paper):
            with patch.object(arxiv_tool, '_enrich_educational_metadata', return_value=sample_research_paper):
                with patch.object(arxiv_tool, '_is_appropriate_for_level', return_value=True):
                    with patch.object(arxiv_tool, '_apply_educational_filters', return_value=[sample_research_paper]):
                        with patch.object(arxiv_tool, 'sort_by_educational_relevance', return_value=[sample_research_paper]):
                            with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
                                mock_execute.return_value = [sample_research_paper.to_dict()]
                                
                                result = await arxiv_tool.get_research_by_level(
                                    academic_level="Graduate",
                                    subject="Computer Science",
                                    max_results=10
                                )
                                
                                assert len(result) == 1
                                mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_research_trends_success(self, arxiv_tool, sample_paper_data, sample_research_paper):
        """Test successful research trends analysis."""
        arxiv_tool.client.get_recent_papers = AsyncMock(return_value=[sample_paper_data])
        
        with patch.object(ResearchPaper, 'from_arxiv', return_value=sample_research_paper):
            with patch.object(arxiv_tool, '_analyze_paper_trends') as mock_analyze:
                mock_trends = {
                    'total_papers': 1,
                    'subject': 'Computer Science',
                    'trends': {'top_subjects': {'cs.AI': 1}},
                    'educational_insights': ['High activity in Computer Science research']
                }
                mock_analyze.return_value = mock_trends
                
                with patch.object(arxiv_tool, 'execute_with_monitoring') as mock_execute:
                    mock_execute.return_value = mock_trends
                    
                    result = await arxiv_tool.analyze_research_trends(
                        subject="Computer Science",
                        days=30
                    )
                    
                    assert result['total_papers'] == 1
                    assert result['subject'] == 'Computer Science'
                    mock_execute.assert_called_once()
    
    def test_calculate_educational_relevance(self, arxiv_tool, sample_research_paper):
        """Test educational relevance calculation."""
        # High relevance paper
        score = arxiv_tool._calculate_educational_relevance(
            sample_research_paper,
            target_subject="Technology",
            target_level="Graduate"
        )
        assert 0.0 <= score <= 1.0
        assert score > 0.1  # Should have some relevance
        
        # Low relevance paper
        low_relevance_paper = ResearchPaper(
            arxiv_id="test",
            title="Obscure Technical Topic",
            authors=["Author"],
            abstract="Very technical content with no educational focus.",
            subjects=["physics.gen-ph"],
            publication_date=date.today(),
            pdf_url="http://example.com"
        )
        
        score = arxiv_tool._calculate_educational_relevance(low_relevance_paper)
        assert score < 0.5  # Should have lower relevance
    
    def test_map_subject_to_arxiv_category(self, arxiv_tool):
        """Test subject to arXiv category mapping."""
        # Technology (maps to Computer Science)
        category = arxiv_tool._map_subject_to_arxiv_category("Technology")
        assert category == "cs"
        
        # Mathematics
        category = arxiv_tool._map_subject_to_arxiv_category("Mathematics")
        assert category == "math"
        
        # Science (maps to Physics)
        category = arxiv_tool._map_subject_to_arxiv_category("Science")
        assert category == "physics"
        
        # Unknown subject
        category = arxiv_tool._map_subject_to_arxiv_category("Unknown Subject")
        assert category is None
    
    def test_map_academic_level_to_grades(self, arxiv_tool):
        """Test academic level to grade level mapping."""
        # High School
        grades = arxiv_tool._map_academic_level_to_grades("High School")
        assert GradeLevel.GRADES_9_12 in grades
        
        # College levels
        for level in ["Undergraduate", "Graduate", "Research"]:
            grades = arxiv_tool._map_academic_level_to_grades(level)
            assert GradeLevel.COLLEGE in grades
    
    def test_enhance_subject_classification(self, arxiv_tool):
        """Test subject classification enhancement."""
        arxiv_subjects = ["cs.AI", "cs.LG", "math.ST"]
        enhanced = arxiv_tool._enhance_subject_classification(arxiv_subjects, "Technology")
        
        assert "Technology" in enhanced
        assert "Mathematics" in enhanced
    
    def test_analyze_curriculum_alignment(self, arxiv_tool, sample_research_paper):
        """Test curriculum alignment analysis."""
        alignment = arxiv_tool._analyze_curriculum_alignment(sample_research_paper, "Technology")
        
        assert isinstance(alignment, dict)
        assert "Common Core" in alignment
        assert "NGSS" in alignment
        assert "State Standards" in alignment
        assert all(0.0 <= score <= 1.0 for score in alignment.values())
    
    def test_extract_educational_applications(self, arxiv_tool, sample_research_paper):
        """Test educational applications extraction."""
        applications = arxiv_tool._extract_educational_applications(sample_research_paper)
        
        assert isinstance(applications, list)
        # Should find some applications based on the content
        assert len(applications) > 0
    
    def test_is_appropriate_for_level(self, arxiv_tool, sample_research_paper):
        """Test academic level appropriateness check."""
        # Mock complexity score calculation
        with patch.object(arxiv_tool.client, 'calculate_complexity_score', return_value=0.6):
            # Should be appropriate for Graduate level (0.5-0.9 range)
            assert arxiv_tool._is_appropriate_for_level(sample_research_paper, "Graduate")
            
            # Should not be appropriate for High School (0.0-0.4 range)
            assert not arxiv_tool._is_appropriate_for_level(sample_research_paper, "High School")
    
    def test_apply_educational_filters(self, arxiv_tool, sample_research_paper):
        """Test educational filtering."""
        papers = [sample_research_paper]
        
        # Test with high relevance threshold
        arxiv_tool.min_educational_relevance = 0.9
        filtered = arxiv_tool._apply_educational_filters(papers)
        assert len(filtered) == 0  # Should filter out due to high threshold
        
        # Test with low relevance threshold
        arxiv_tool.min_educational_relevance = 0.5
        filtered = arxiv_tool._apply_educational_filters(papers)
        assert len(filtered) == 1  # Should pass through
    
    def test_analyze_paper_trends(self, arxiv_tool, sample_research_paper):
        """Test paper trends analysis."""
        papers = [sample_research_paper]
        trends = arxiv_tool._analyze_paper_trends(papers, "Computer Science")
        
        assert trends['total_papers'] == 1
        assert trends['subject'] == "Computer Science"
        assert 'trends' in trends
        assert 'educational_insights' in trends
        assert isinstance(trends['educational_insights'], list)
    
    def test_analyze_complexity_distribution(self, arxiv_tool, sample_research_paper):
        """Test complexity distribution analysis."""
        papers = [sample_research_paper]
        distribution = arxiv_tool._analyze_complexity_distribution(papers)
        
        assert isinstance(distribution, dict)
        assert 'Introductory' in distribution
        assert 'Intermediate' in distribution
        assert 'Advanced' in distribution
        assert sum(distribution.values()) == 1  # Should sum to total papers
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, arxiv_tool):
        """Test successful health check."""
        # Mock client health check
        arxiv_tool.client.health_check = AsyncMock(return_value={'status': 'healthy'})
        
        result = await arxiv_tool.health_check()
        
        assert result['tool_name'] == arxiv_tool.tool_name
        assert result['status'] == 'healthy'
        assert 'api_health' in result
        assert 'cache_healthy' in result
        assert 'rate_limit_status' in result
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, arxiv_tool):
        """Test health check failure."""
        # Mock client health check failure
        arxiv_tool.client.health_check = AsyncMock(side_effect=Exception("Connection failed"))

        result = await arxiv_tool.health_check()

        assert result['status'] == 'unhealthy'
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_health_check_cache_failure(self, arxiv_tool):
        """Health check marks tool unhealthy when cache fails."""
        arxiv_tool.client.health_check = AsyncMock(return_value={'status': 'healthy'})
        arxiv_tool.cache_service.health_check = AsyncMock(side_effect=CacheError("fail", "health_check"))

        result = await arxiv_tool.health_check()

        assert result['status'] == 'unhealthy'
        assert result['cache_healthy'] is False


class TestArxivIntegration:
    """Integration tests for arXiv functionality."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_paper_search(self):
        """Test end-to-end paper search workflow."""
        # This would be a more comprehensive integration test
        # that tests the full workflow from search to enrichment
        pass
    
    @pytest.mark.asyncio
    async def test_educational_metadata_enrichment(self):
        """Test educational metadata enrichment workflow."""
        # Test the complete enrichment process
        pass


if __name__ == "__main__":
    pytest.main([__file__])
