"""
arXiv tools for OpenEdu MCP Server.

This module provides MCP tool implementations for arXiv API integration,
including educational filtering, academic content analysis, and research paper search functionality.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base_tool import BaseTool
from api.arxiv import ArxivClient
from models.research_paper import ResearchPaper
from models.base import GradeLevel, EducationalMetadata
from config import Config
from services.cache_service import CacheService
from services.rate_limiting_service import RateLimitingService
from services.usage_service import UsageService
from exceptions import ToolError, ValidationError, APIError, CacheError

logger = logging.getLogger(__name__)


class ArxivTool(BaseTool):
    """Tool for arXiv API integration with educational features."""
    
    def __init__(
        self,
        config: Config,
        cache_service: CacheService,
        rate_limiting_service: RateLimitingService,
        usage_service: UsageService
    ):
        """
        Initialize arXiv tool.
        
        Args:
            config: Application configuration
            cache_service: Cache service instance
            rate_limiting_service: Rate limiting service instance
            usage_service: Usage tracking service instance
        """
        super().__init__(config, cache_service, rate_limiting_service, usage_service)
        self.client = ArxivClient(config)
        
        # Educational filtering configuration
        self.min_educational_relevance = config.education.content_filters.min_educational_relevance
        self.enable_age_appropriate = config.education.content_filters.enable_age_appropriate
        self.enable_curriculum_alignment = config.education.content_filters.enable_curriculum_alignment
        
        # Academic level thresholds
        self.academic_level_thresholds = {
            'High School': 0.3,
            'Undergraduate': 0.5,
            'Graduate': 0.7,
            'Research': 0.9
        }
        
        # Subject mappings for educational alignment
        self.subject_mappings = {
            'Mathematics': ['math', 'stat'],
            'Science': ['physics', 'q-bio', 'chem-ph', 'astro-ph'],
            'Technology': ['cs', 'eess'],
            'Engineering': ['cs', 'eess', 'physics'],
            'Statistics': ['stat', 'math.ST'],
            'Biology': ['q-bio'],
            'Physics': ['physics', 'astro-ph', 'cond-mat', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph', 'hep-th', 'math-ph', 'nlin', 'nucl-ex', 'nucl-th', 'quant-ph'],
            'Computer Science': ['cs']
        }
    
    @property
    def api_name(self) -> str:
        """Name of the API this tool uses for rate limiting."""
        return "arxiv"
    
    async def search_academic_papers(
        self,
        query: str,
        subject: Optional[str] = None,
        academic_level: Optional[str] = None,
        max_results: int = 10,
        include_educational_analysis: bool = True,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for academic papers with educational filtering.
        
        Args:
            query: Search query for papers
            subject: Educational subject filter (optional)
            academic_level: Target academic level (High School, Undergraduate, Graduate, Research)
            max_results: Maximum number of results (1-50)
            include_educational_analysis: Whether to include educational metadata
            user_session: User session identifier
            
        Returns:
            List of academic papers with educational metadata
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If search fails
        """
        async def _search():
            # Validate parameters
            validated = await self.validate_common_parameters(
                query=query,
                limit=max_results,
                subject=subject
            )
            
            if academic_level and academic_level not in self.academic_level_thresholds:
                raise ValidationError(f"Invalid academic level: {academic_level}")
            
            # Map educational subject to arXiv categories
            arxiv_category = None
            if subject:
                arxiv_category = self._map_subject_to_arxiv_category(subject)
            
            # Search papers using arXiv API
            raw_papers = await self.client.search_papers(
                query=validated['query'],
                category=arxiv_category,
                max_results=validated['limit']
            )
            
            # Convert to ResearchPaper models with educational enrichment
            papers = []
            for paper_data in raw_papers:
                try:
                    paper = ResearchPaper.from_arxiv(paper_data)
                    
                    # Enrich with educational metadata if requested
                    if include_educational_analysis:
                        paper = await self._enrich_educational_metadata(
                            paper,
                            subject=subject,
                            academic_level=academic_level
                        )
                    
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Failed to process paper data: {e}")
                    continue
            
            # Apply educational filtering
            filtered_papers = self._apply_educational_filters(
                papers,
                academic_level=academic_level,
                subject=subject
            )
            
            # Sort by educational relevance
            sorted_papers = self.sort_by_educational_relevance(filtered_papers)
            
            # Convert to dictionaries for response
            return [paper.to_dict() for paper in sorted_papers]
        
        return await self.execute_with_monitoring(
            "search_academic_papers",
            _search,
            user_session=user_session
        )
    
    async def get_paper_summary(
        self,
        paper_id: str,
        include_educational_analysis: bool = True,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get paper summary with educational analysis.
        
        Args:
            paper_id: arXiv paper ID
            include_educational_analysis: Whether to include educational metadata
            user_session: User session identifier
            
        Returns:
            Paper summary with educational metadata
            
        Raises:
            ValidationError: If paper_id is invalid
            ToolError: If retrieval fails
        """
        async def _get_summary():
            # Get paper data from arXiv
            paper_data = await self.client.get_paper_abstract(paper_id)
            
            if not paper_data:
                raise ToolError(f"Paper not found: {paper_id}", self.tool_name)
            
            # Convert to ResearchPaper model
            paper = ResearchPaper.from_arxiv(paper_data)
            
            # Enrich with educational metadata if requested
            if include_educational_analysis:
                paper = await self._enrich_educational_metadata(paper)
            
            return paper.to_dict()
        
        return await self.execute_with_monitoring(
            "get_paper_summary",
            _get_summary,
            user_session=user_session
        )
    
    async def get_recent_research(
        self,
        subject: str,
        days: int = 7,
        academic_level: Optional[str] = None,
        max_results: int = 10,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent research papers by educational subject.
        
        Args:
            subject: Educational subject
            days: Number of days back to search (1-30)
            academic_level: Target academic level (optional)
            max_results: Maximum number of results
            user_session: User session identifier
            
        Returns:
            List of recent papers in the subject area
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If search fails
        """
        async def _get_recent():
            # Validate parameters
            if days < 1 or days > 30:
                raise ValidationError("days must be between 1 and 30")
            
            validated = await self.validate_common_parameters(
                subject=subject,
                limit=max_results
            )
            
            # Map educational subject to arXiv category
            arxiv_category = self._map_subject_to_arxiv_category(validated['subject'])
            if not arxiv_category:
                raise ValidationError(f"Subject not supported for arXiv search: {subject}")
            
            # Get recent papers
            raw_papers = await self.client.get_recent_papers(
                category=arxiv_category,
                days=days,
                max_results=validated['limit']
            )
            
            # Convert and enrich papers
            papers = []
            for paper_data in raw_papers:
                try:
                    paper = ResearchPaper.from_arxiv(paper_data)
                    paper = await self._enrich_educational_metadata(
                        paper,
                        subject=subject,
                        academic_level=academic_level
                    )
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Failed to process paper data: {e}")
                    continue
            
            # Apply educational filtering
            filtered_papers = self._apply_educational_filters(
                papers,
                academic_level=academic_level,
                subject=subject
            )
            
            # Sort by publication date (most recent first)
            sorted_papers = sorted(
                filtered_papers,
                key=lambda p: p.publication_date,
                reverse=True
            )
            
            return [paper.to_dict() for paper in sorted_papers]
        
        return await self.execute_with_monitoring(
            "get_recent_research",
            _get_recent,
            user_session=user_session
        )
    
    async def get_research_by_level(
        self,
        academic_level: str,
        subject: Optional[str] = None,
        max_results: int = 10,
        user_session: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get research papers appropriate for specific academic levels.
        
        Args:
            academic_level: Target academic level (High School, Undergraduate, Graduate, Research)
            subject: Subject area filter (optional)
            max_results: Maximum number of results
            user_session: User session identifier
            
        Returns:
            List of papers appropriate for the academic level
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If search fails
        """
        async def _get_by_level():
            # Validate academic level
            if academic_level not in self.academic_level_thresholds:
                raise ValidationError(f"Invalid academic level: {academic_level}")
            
            validated = await self.validate_common_parameters(
                limit=max_results,
                subject=subject
            )
            
            # Build search query based on academic level
            level_keywords = {
                'High School': ['introductory', 'basic', 'elementary', 'tutorial'],
                'Undergraduate': ['undergraduate', 'college', 'introductory course', 'textbook'],
                'Graduate': ['graduate', 'advanced', 'research methods'],
                'Research': ['novel', 'cutting-edge', 'state-of-the-art', 'breakthrough']
            }
            
            keywords = level_keywords.get(academic_level, [])
            search_query = " OR ".join(keywords) if keywords else "education"
            
            # Add subject filter if specified
            arxiv_category = None
            if subject:
                arxiv_category = self._map_subject_to_arxiv_category(subject)
                if not arxiv_category:
                    # Use subject as additional search term
                    search_query = f"{search_query} {subject}"
            
            # Search papers
            raw_papers = await self.client.search_papers(
                query=search_query,
                category=arxiv_category,
                max_results=validated['limit']
            )
            
            # Convert and enrich papers
            papers = []
            for paper_data in raw_papers:
                try:
                    paper = ResearchPaper.from_arxiv(paper_data)
                    paper = await self._enrich_educational_metadata(
                        paper,
                        subject=subject,
                        academic_level=academic_level
                    )
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Failed to process paper data: {e}")
                    continue
            
            # Filter by academic level appropriateness
            level_filtered = [
                paper for paper in papers
                if self._is_appropriate_for_level(paper, academic_level)
            ]
            
            # Apply additional educational filtering
            filtered_papers = self._apply_educational_filters(
                level_filtered,
                academic_level=academic_level,
                subject=subject
            )
            
            # Sort by educational relevance
            sorted_papers = self.sort_by_educational_relevance(filtered_papers)
            
            return [paper.to_dict() for paper in sorted_papers]
        
        return await self.execute_with_monitoring(
            "get_research_by_level",
            _get_by_level,
            user_session=user_session
        )
    
    async def analyze_research_trends(
        self,
        subject: str,
        days: int = 30,
        user_session: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze research trends for educational insights.
        
        Args:
            subject: Educational subject to analyze
            days: Number of days to analyze (7-90)
            user_session: User session identifier
            
        Returns:
            Research trend analysis with educational insights
            
        Raises:
            ValidationError: If parameters are invalid
            ToolError: If analysis fails
        """
        async def _analyze_trends():
            # Validate parameters
            if days < 7 or days > 90:
                raise ValidationError("days must be between 7 and 90")
            
            validated = await self.validate_common_parameters(subject=subject)
            
            # Map subject to arXiv category
            arxiv_category = self._map_subject_to_arxiv_category(validated['subject'])
            if not arxiv_category:
                raise ValidationError(f"Subject not supported for trend analysis: {subject}")
            
            # Get recent papers for trend analysis
            raw_papers = await self.client.get_recent_papers(
                category=arxiv_category,
                days=days,
                max_results=50  # Get more papers for better analysis
            )
            
            # Convert to ResearchPaper models
            papers = []
            for paper_data in raw_papers:
                try:
                    paper = ResearchPaper.from_arxiv(paper_data)
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Failed to process paper data: {e}")
                    continue
            
            # Analyze trends
            trends = self._analyze_paper_trends(papers, subject)
            
            return trends
        
        return await self.execute_with_monitoring(
            "analyze_research_trends",
            _analyze_trends,
            user_session=user_session
        )
    
    async def _enrich_educational_metadata(
        self,
        paper: ResearchPaper,
        subject: Optional[str] = None,
        academic_level: Optional[str] = None
    ) -> ResearchPaper:
        """
        Enrich paper with educational metadata.
        
        Args:
            paper: ResearchPaper instance to enrich
            subject: Target subject for relevance scoring
            academic_level: Target academic level for relevance scoring
            
        Returns:
            Enriched paper instance
        """
        # Calculate educational relevance score
        relevance_score = self._calculate_educational_relevance(paper, subject, academic_level)
        paper.educational_metadata.educational_relevance_score = relevance_score
        
        # Determine academic level appropriateness
        paper_level = self.client.analyze_educational_level({
            'title': paper.title,
            'summary': paper.abstract
        })
        
        # Map to grade levels
        grade_levels = self._map_academic_level_to_grades(paper_level)
        paper.educational_metadata.grade_levels = grade_levels
        
        # Enhance subject classification
        enhanced_subjects = self._enhance_subject_classification(paper.subjects, subject)
        paper.educational_metadata.educational_subjects = enhanced_subjects
        
        # Calculate complexity and difficulty
        complexity_score = self.client.calculate_complexity_score({
            'title': paper.title,
            'summary': paper.abstract
        })
        
        if complexity_score < 0.3:
            paper.educational_metadata.difficulty_level = "Introductory"
        elif complexity_score < 0.6:
            paper.educational_metadata.difficulty_level = "Intermediate"
        else:
            paper.educational_metadata.difficulty_level = "Advanced"
        
        # Analyze curriculum alignment
        curriculum_alignment = self._analyze_curriculum_alignment(paper, subject)
        paper.educational_metadata.curriculum_alignment = curriculum_alignment
        
        # Extract educational applications
        educational_applications = self._extract_educational_applications(paper)
        paper.educational_applications = educational_applications
        
        return paper
    
    def _calculate_educational_relevance(
        self,
        paper: ResearchPaper,
        target_subject: Optional[str] = None,
        target_level: Optional[str] = None
    ) -> float:
        """Calculate educational relevance score for a paper."""
        score = 0.0
        
        # Base score for educational content indicators
        content_text = f"{paper.title} {paper.abstract}".lower()
        
        # Educational keywords scoring
        educational_keywords = [
            'education', 'learning', 'teaching', 'pedagogy', 'curriculum',
            'instruction', 'classroom', 'student', 'educational', 'academic',
            'methodology', 'framework', 'analysis', 'study', 'research'
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
        
        # Academic level appropriateness
        if target_level:
            level_keywords = {
                'High School': ['introductory', 'basic', 'elementary', 'tutorial'],
                'Undergraduate': ['undergraduate', 'college', 'introductory'],
                'Graduate': ['graduate', 'advanced', 'research'],
                'Research': ['novel', 'cutting-edge', 'state-of-the-art']
            }
            
            level_terms = level_keywords.get(target_level, [])
            level_match = any(term in content_text for term in level_terms)
            if level_match:
                score += 0.2
        
        # arXiv category relevance for STEM education
        stem_categories = ['math', 'physics', 'cs', 'stat', 'q-bio']
        if any(cat in paper.subjects for cat in stem_categories):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _map_subject_to_arxiv_category(self, subject: str) -> Optional[str]:
        """Map educational subject to arXiv category."""
        subject_lower = subject.lower()
        
        for edu_subject, categories in self.subject_mappings.items():
            if edu_subject.lower() in subject_lower or subject_lower in edu_subject.lower():
                return categories[0]  # Return primary category
        
        # Direct category mapping
        direct_mappings = {
            'math': 'math',
            'mathematics': 'math',
            'physics': 'physics',
            'computer science': 'cs',
            'cs': 'cs',
            'artificial intelligence': 'cs',
            'ai': 'cs',
            'machine learning': 'cs',
            'biology': 'q-bio',
            'statistics': 'stat',
            'finance': 'q-fin'
        }
        
        return direct_mappings.get(subject_lower)
    
    def _map_academic_level_to_grades(self, academic_level: str) -> List[GradeLevel]:
        """Map academic level to grade levels."""
        mapping = {
            'High School': [GradeLevel.GRADES_9_12],
            'Undergraduate': [GradeLevel.COLLEGE],
            'Graduate': [GradeLevel.COLLEGE],
            'Research': [GradeLevel.COLLEGE]
        }
        
        return mapping.get(academic_level, [GradeLevel.COLLEGE])
    
    def _enhance_subject_classification(
        self,
        arxiv_subjects: List[str],
        target_subject: Optional[str] = None
    ) -> List[str]:
        """Enhance subject classification for educational purposes."""
        educational_subjects = []
        
        # Map arXiv categories to educational subjects
        category_mapping = {
            'math': 'Mathematics',
            'physics': 'Science',
            'cs': 'Technology',
            'stat': 'Mathematics',
            'q-bio': 'Science',
            'q-fin': 'Social Studies'
        }
        
        for subject in arxiv_subjects:
            subject_prefix = subject.split('.')[0].lower()
            if subject_prefix in category_mapping:
                educational_subjects.append(category_mapping[subject_prefix])
        
        # Add target subject if specified
        if target_subject and target_subject not in educational_subjects:
            educational_subjects.append(target_subject)
        
        return list(set(educational_subjects))
    
    def _analyze_curriculum_alignment(
        self,
        paper: ResearchPaper,
        subject: Optional[str] = None
    ) -> Dict[str, float]:
        """Analyze curriculum alignment for educational standards."""
        alignment = {
            'Common Core': 0.0,
            'NGSS': 0.0,
            'State Standards': 0.0
        }
        
        content_text = f"{paper.title} {paper.abstract}".lower()
        
        # Common Core alignment (Math and ELA focus)
        if any(subj in ['Mathematics', 'English Language Arts'] for subj in paper.educational_metadata.educational_subjects):
            if any(term in content_text for term in ['problem solving', 'critical thinking', 'reasoning']):
                alignment['Common Core'] = 0.7
        
        # NGSS alignment (Science focus)
        if 'Science' in paper.educational_metadata.educational_subjects:
            if any(term in content_text for term in ['inquiry', 'investigation', 'evidence', 'model']):
                alignment['NGSS'] = 0.8
        
        # General state standards alignment
        if any(term in content_text for term in ['curriculum', 'standards', 'assessment', 'learning objectives']):
            alignment['State Standards'] = 0.6
        
        return alignment
    
    def _extract_educational_applications(self, paper: ResearchPaper) -> List[str]:
        """Extract potential educational applications from paper content."""
        applications = []
        content_text = f"{paper.title} {paper.abstract}".lower()
        
        # Teaching applications
        if any(term in content_text for term in ['teaching', 'instruction', 'pedagogy']):
            applications.append("Teaching methodology")
        
        # Learning applications
        if any(term in content_text for term in ['learning', 'education', 'student']):
            applications.append("Student learning")
        
        # Research applications
        if any(term in content_text for term in ['research', 'investigation', 'study']):
            applications.append("Academic research")
        
        # Technology applications
        if any(term in content_text for term in ['technology', 'digital', 'online', 'computer']):
            applications.append("Educational technology")
        
        # Assessment applications
        if any(term in content_text for term in ['assessment', 'evaluation', 'testing', 'measurement']):
            applications.append("Educational assessment")
        
        return applications
    
    def _get_subject_search_terms(self, subject: str) -> List[str]:
        """Get search terms for educational subject."""
        subject_terms = {
            'Mathematics': ['math', 'mathematics', 'algebra', 'geometry', 'calculus', 'statistics'],
            'Science': ['science', 'physics', 'chemistry', 'biology', 'earth science'],
            'Technology': ['technology', 'computer', 'programming', 'software', 'digital'],
            'Engineering': ['engineering', 'design', 'systems', 'optimization'],
            'Physics': ['physics', 'mechanics', 'thermodynamics', 'quantum', 'relativity'],
            'Computer Science': ['computer science', 'algorithm', 'programming', 'software', 'AI'],
            'Biology': ['biology', 'genetics', 'ecology', 'evolution', 'molecular'],
            'Statistics': ['statistics', 'probability', 'data analysis', 'statistical']
        }
        
        return subject_terms.get(subject, [subject.lower()])
    
    def _is_appropriate_for_level(self, paper: ResearchPaper, academic_level: str) -> bool:
        """Check if paper is appropriate for academic level."""
        complexity_score = self.client.calculate_complexity_score({
            'title': paper.title,
            'summary': paper.abstract
        })
        
        level_thresholds = {
            'High School': (0.0, 0.4),
            'Undergraduate': (0.2, 0.7),
            'Graduate': (0.5, 0.9),
            'Research': (0.7, 1.0)
        }
        
        min_threshold, max_threshold = level_thresholds.get(academic_level, (0.0, 1.0))
        return min_threshold <= complexity_score <= max_threshold
    
    def _apply_educational_filters(
        self,
        papers: List[ResearchPaper],
        academic_level: Optional[str] = None,
        subject: Optional[str] = None
    ) -> List[ResearchPaper]:
        """Apply educational filtering to papers."""
        filtered = papers
        
        # Filter by minimum educational relevance
        if self.min_educational_relevance > 0:
            filtered = [
                paper for paper in filtered
                if paper.educational_metadata.educational_relevance_score >= self.min_educational_relevance
            ]
        
        # Filter by academic level appropriateness
        if academic_level and self.enable_age_appropriate:
            filtered = [
                paper for paper in filtered
                if self._is_appropriate_for_level(paper, academic_level)
            ]
        
        # Filter by subject relevance
        if subject:
            filtered = [
                paper for paper in filtered
                if subject in paper.educational_metadata.educational_subjects or
                   any(subj.lower() in subject.lower() for subj in paper.educational_metadata.educational_subjects)
            ]
        
        return filtered
    
    def _analyze_paper_trends(self, papers: List[ResearchPaper], subject: str) -> Dict[str, Any]:
        """Analyze trends in research papers for educational insights."""
        if not papers:
            return {
                'total_papers': 0,
                'subject': subject,
                'trends': {},
                'educational_insights': []
            }
        
        # Analyze publication trends
        publication_dates = [paper.publication_date for paper in papers]
        recent_papers = len([d for d in publication_dates if (date.today() - d).days <= 7])
        
        # Analyze subject distribution
        all_subjects = []
        for paper in papers:
            all_subjects.extend(paper.subjects)
        
        subject_counts = {}
        for subj in all_subjects:
            subject_counts[subj] = subject_counts.get(subj, 0) + 1
        
        # Top trending subjects
        top_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Analyze educational relevance
        high_relevance_papers = [
            paper for paper in papers
            if paper.educational_metadata.educational_relevance_score > 0.7
        ]
        
        # Educational insights
        insights = []
        
        if recent_papers > len(papers) * 0.3:
            insights.append(f"High activity in {subject} research with {recent_papers} papers in the last week")
        
        if len(high_relevance_papers) > len(papers) * 0.5:
            insights.append(f"Strong educational relevance with {len(high_relevance_papers)} highly relevant papers")
        
        if top_subjects:
            insights.append(f"Most active area: {top_subjects[0][0]} with {top_subjects[0][1]} papers")
        
        return {
            'total_papers': len(papers),
            'subject': subject,
            'recent_papers_week': recent_papers,
            'high_relevance_papers': len(high_relevance_papers),
            'trends': {
                'top_subjects': dict(top_subjects),
                'average_relevance': sum(p.educational_metadata.educational_relevance_score for p in papers) / len(papers),
                'complexity_distribution': self._analyze_complexity_distribution(papers)
            },
            'educational_insights': insights,
            'analysis_date': date.today().isoformat()
        }
    
    def _analyze_complexity_distribution(self, papers: List[ResearchPaper]) -> Dict[str, int]:
        """Analyze complexity distribution of papers."""
        distribution = {
            'Introductory': 0,
            'Intermediate': 0,
            'Advanced': 0
        }
        
        for paper in papers:
            difficulty = paper.educational_metadata.difficulty_level
            if difficulty in distribution:
                distribution[difficulty] += 1
        
        return distribution
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on arXiv tool and API.
        
        Returns:
            Health check results
        """
        try:
            # Check API connectivity
            api_health = await self.client.health_check()
            
            # Check cache service
            try:
                cache_healthy = await self.cache_service.health_check()
            except CacheError as e:
                logger.error(f"Cache health check failed: {e}")
                cache_healthy = False
            
            # Check rate limiting
            rate_limit_status = await self.rate_limiting_service.get_rate_limit_status(self.api_name)
            
            return {
                'tool_name': self.tool_name,
                'status': 'healthy' if api_health['status'] == 'healthy' and cache_healthy else 'unhealthy',
                'api_health': api_health,
                'cache_healthy': cache_healthy,
                'rate_limit_status': rate_limit_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"arXiv tool health check failed: {e}")
            return {
                'tool_name': self.tool_name,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }