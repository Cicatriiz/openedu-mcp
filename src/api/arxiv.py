"""
arXiv API client for OpenEdu MCP Server.

This module provides a comprehensive client for interacting with the arXiv API,
including paper search, metadata retrieval, and educational content analysis
with proper error handling and rate limiting.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union
from urllib.parse import quote_plus, urljoin
import aiohttp
from datetime import datetime, date, timedelta, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)


class ArxivClient:
    """Client for arXiv API with educational focus."""
    
    def __init__(self, config: Config):
        """
        Initialize the arXiv client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.base_url = config.apis.arxiv.base_url
        self.query_url = f"{self.base_url}/query"
        self.timeout = config.apis.arxiv.timeout
        self.retry_attempts = config.apis.arxiv.retry_attempts
        self.backoff_factor = config.apis.arxiv.backoff_factor
        
        # User agent for respectful API usage
        self.headers = {
            'User-Agent': f'{config.server.name}/{config.server.version} (Educational MCP Server; https://github.com/openedu-mcp)'
        }
        
        # Session will be created when needed
        self._session: Optional[aiohttp.ClientSession] = None
        
        # arXiv category mappings for educational subjects
        self.category_mappings = {
            'physics': ['physics', 'astro-ph', 'cond-mat', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph', 'hep-th', 'math-ph', 'nlin', 'nucl-ex', 'nucl-th', 'quant-ph'],
            'mathematics': ['math'],
            'computer_science': ['cs'],
            'biology': ['q-bio'],
            'finance': ['q-fin'],
            'statistics': ['stat']
        }
        
        # Educational level keywords
        self.educational_keywords = {
            'high_school': ['introductory', 'basic', 'elementary', 'high school', 'secondary'],
            'undergraduate': ['undergraduate', 'college', 'introductory course', 'textbook'],
            'graduate': ['graduate', 'advanced', 'research', 'doctoral'],
            'research': ['research', 'novel', 'cutting-edge', 'state-of-the-art']
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(
        self,
        params: Dict[str, Any],
        retry_count: int = 0
    ) -> str:
        """
        Performs an HTTP GET request to the arXiv API with retry logic and error handling.
        
        Retries the request on network errors or rate limiting, using exponential backoff. Raises an APIError if the request fails after all retry attempts or encounters an unexpected error.
        
        Args:
            params: Query parameters for the arXiv API request.
        
        Returns:
            The XML response text from the arXiv API.
        
        Raises:
            APIError: If the request fails after all retries or encounters an unexpected error.
        """
        session = await self._get_session()
        
        try:
            # Add rate limiting delay (3 seconds between requests as per arXiv guidelines)
            if retry_count > 0:
                await asyncio.sleep(3)
            
            logger.info(f"ArxivClient _make_request to URL: {self.query_url} with params: {params}") # Added log
            async with session.get(self.query_url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:  # Rate limited
                    if retry_count < self.retry_attempts:
                        wait_time = self.backoff_factor ** retry_count * 3  # Base 3 seconds
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        return await self._make_request(params, retry_count + 1)
                    else:
                        raise APIError(f"Rate limited after {self.retry_attempts} retries", "arxiv")
                else:
                    error_text = await response.text()
                    raise APIError(f"HTTP {response.status}: {error_text}", "arxiv")
                    
        except aiohttp.ClientError as e:
            if retry_count < self.retry_attempts:
                wait_time = self.backoff_factor ** retry_count * 3
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(params, retry_count + 1)
            else:
                raise APIError(f"Request failed after {self.retry_attempts} retries: {e}", "arxiv")
        except Exception as e:
            raise APIError(f"Unexpected error: {e}", "arxiv")
    
    def _parse_atom_feed(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        Parse arXiv Atom feed XML response.
        
        Args:
            xml_text: XML response text
            
        Returns:
            List of parsed paper data
            
        Raises:
            APIError: If XML parsing fails
        """
        try:
            # Define namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            root = ET.fromstring(xml_text)
            
            papers = []
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                paper_data = {}
                
                # Extract basic information
                paper_data['id'] = self._get_text(entry.find('atom:id', namespaces))
                paper_data['title'] = self._get_text(entry.find('atom:title', namespaces))
                paper_data['summary'] = self._get_text(entry.find('atom:summary', namespaces))
                paper_data['published'] = self._get_text(entry.find('atom:published', namespaces))
                paper_data['updated'] = self._get_text(entry.find('atom:updated', namespaces))
                
                # Extract authors
                authors = []
                for author in entry.findall('atom:author', namespaces):
                    name = self._get_text(author.find('atom:name', namespaces))
                    if name:
                        authors.append({'name': name})
                paper_data['authors'] = authors
                
                # Extract categories
                categories = []
                for category in entry.findall('atom:category', namespaces):
                    term = category.get('term')
                    if term:
                        categories.append(term)
                paper_data['categories'] = categories
                
                # Extract links
                links = []
                for link in entry.findall('atom:link', namespaces):
                    link_data = {
                        'href': link.get('href'),
                        'rel': link.get('rel'),
                        'type': link.get('type'),
                        'title': link.get('title')
                    }
                    links.append(link_data)
                paper_data['links'] = links
                
                # Extract arXiv-specific metadata
                comment = entry.find('arxiv:comment', namespaces)
                if comment is not None:
                    paper_data['comment'] = comment.text
                
                primary_category = entry.find('arxiv:primary_category', namespaces)
                if primary_category is not None:
                    paper_data['primary_category'] = primary_category.get('term')
                
                doi = entry.find('arxiv:doi', namespaces)
                if doi is not None:
                    paper_data['doi'] = doi.text
                
                journal_ref = entry.find('arxiv:journal_ref', namespaces)
                if journal_ref is not None:
                    paper_data['journal'] = journal_ref.text
                
                papers.append(paper_data)
            
            return papers
            
        except ET.ParseError as e:
            raise APIError(f"Failed to parse XML response: {e}", "arxiv")
        except Exception as e:
            raise APIError(f"Error processing arXiv response: {e}", "arxiv")
    
    def _get_text(self, element) -> str:
        """Safely get text from XML element."""
        return element.text.strip() if element is not None and element.text else ""
    
    def _validate_search_params(self, query: str, max_results: int) -> None:
        """
        Validate search parameters.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Raises:
            ValidationError: If parameters are invalid
        """
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")
        
        if max_results < 1 or max_results > 100:
            raise ValidationError("max_results must be between 1 and 100")
    
    def _build_search_query(self, query: str, category: Optional[str] = None) -> str:
        """
        Build arXiv search query with category filtering.
        
        Args:
            query: Base search query
            category: Category filter
            
        Returns:
            Formatted search query
        """
        search_query = query.strip()
        
        if category:
            # Map educational subjects to arXiv categories
            arxiv_categories = self._get_arxiv_categories(category)
            if arxiv_categories:
                category_query = " OR ".join([f"cat:{cat}" for cat in arxiv_categories])
                search_query = f"({search_query}) AND ({category_query})"
        
        return search_query
    
    def _get_arxiv_categories(self, subject: str) -> List[str]:
        """Get arXiv categories for educational subject."""
        subject_lower = subject.lower()
        
        # Direct category match first (more specific)
        if subject_lower in ['math', 'cs', 'physics', 'stat', 'q-bio', 'q-fin']:
            return [subject_lower]
        
        # Then check educational subject mappings
        for edu_subject, categories in self.category_mappings.items():
            if edu_subject in subject_lower or subject_lower in edu_subject:
                return categories
        
        return []
    
    async def search_papers(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 10,
        start: int = 0,
        sort_by: str = 'relevance',
        sort_order: str = 'descending'
    ) -> List[Dict[str, Any]]:
        """
        Search academic papers on arXiv.
        
        Args:
            query: Search query
            category: Subject category filter
            max_results: Maximum number of results (1-100)
            start: Starting index for pagination
            sort_by: Sort criteria ('relevance', 'lastUpdatedDate', 'submittedDate')
            sort_order: Sort order ('ascending', 'descending')
            
        Returns:
            List of paper data
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
        """
        self._validate_search_params(query, max_results)
        
        # Build search query
        search_query = self._build_search_query(query, category)
        
        params = {
            'search_query': search_query,
            'start': start,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': sort_order
        }
        
        try:
            xml_response = await self._make_request(params)
            papers = self._parse_atom_feed(xml_response)
            
            logger.info(f"Found {len(papers)} papers for query: {query}")
            return papers
            
        except Exception as e:
            logger.error(f"Error searching papers: {e}")
            raise
    
    async def get_paper_abstract(self, paper_id: str) -> Dict[str, Any]:
        """
        Get paper abstract and metadata by arXiv ID.
        
        Args:
            paper_id: arXiv paper ID (e.g., '2301.00001' or 'math.GT/0309136')
            
        Returns:
            Paper metadata with abstract
            
        Raises:
            ValidationError: If paper_id is invalid
            APIError: If API request fails
        """
        if not paper_id or not paper_id.strip():
            raise ValidationError("Paper ID cannot be empty")
        
        # Clean paper ID (remove version if present)
        clean_id = paper_id.strip()
        if 'v' in clean_id and clean_id.split('v')[-1].isdigit():
            clean_id = clean_id.split('v')[0]
        
        params = {
            'id_list': clean_id,
            'max_results': 1
        }
        
        try:
            xml_response = await self._make_request(params)
            papers = self._parse_atom_feed(xml_response)
            
            if not papers:
                raise APIError(f"Paper not found: {paper_id}", "arxiv")
            
            return papers[0]
            
        except Exception as e:
            logger.error(f"Error getting paper abstract for {paper_id}: {e}")
            raise
    
    async def get_paper_authors(self, paper_id: str) -> List[Dict[str, str]]:
        """
        Get paper authors by arXiv ID.
        
        Args:
            paper_id: arXiv paper ID
            
        Returns:
            List of author information
            
        Raises:
            ValidationError: If paper_id is invalid
            APIError: If API request fails
        """
        paper_data = await self.get_paper_abstract(paper_id)
        return paper_data.get('authors', [])
    
    async def get_recent_papers(
        self,
        category: str,
        days: int = 7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieves recent arXiv papers in a specified category from the past given number of days.
        
        Args:
            category: The arXiv category code or educational subject to filter papers.
            days: Number of days back from today to include papers (1 to 365).
            max_results: Maximum number of papers to return.
        
        Returns:
            A list of dictionaries containing metadata for recent papers matching the criteria.
        
        Raises:
            ValidationError: If the days parameter is out of range or the category is invalid.
            APIError: If the arXiv API request fails or the response cannot be processed.
        """
        if days < 1 or days > 365:
            raise ValidationError("days must be between 1 and 365")
        
        # Calculate date range
        # FOR TESTING: Use a fixed date range from arXiv documentation example
        start_str = "202301010000"
        end_str = "202312312359"
        
        # Get arXiv categories for the subject
        arxiv_categories = self._get_arxiv_categories(category)
        if not arxiv_categories:
            # Try direct category
            arxiv_categories = [category]
        
        # Build category query
        # category_query = " OR ".join([f"cat:{cat}" for cat in arxiv_categories])
        # search_query = f"cat:{category}+AND+submittedDate:[{start_str}+TO+{end_str}]" # Match docs example order

        # Calculate date range (restored)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime('%Y%m%d0000')
        end_str = end_date.strftime('%Y%m%d2359')

        arxiv_categories = self._get_arxiv_categories(category)
        if not arxiv_categories:
            arxiv_categories = [category]

        category_query = " OR ".join([f"cat:{cat}" for cat in arxiv_categories])
        # Use submittedDate for filtering
        search_query = f"submittedDate:[{start_str} TO {end_str}] AND ({category_query})"
        
        params = {
            'search_query': search_query,
            'max_results': max_results,
            'sortBy': 'submittedDate', # Ensure sortBy matches the filter field
            'sortOrder': 'descending'
        }
        
        logger.info(f"ArXiv get_recent_papers query: '{search_query}' with params: {params}")

        try:
            xml_response = await self._make_request(params)
            logger.debug(f"ArXiv get_recent_papers XML response (first 1000 chars): {xml_response[:1000]}")
            if "<opensearch:totalResults>0</opensearch:totalResults>" in xml_response:
                logger.warning(f"ArXiv query returned 0 total results. Query: {search_query}")
            papers = self._parse_atom_feed(xml_response)
            
            logger.info(f"Found {len(papers)} recent papers in {category} using submittedDate")
            return papers
            
        except Exception as e:
            logger.error(f"Error getting recent papers: {e}")
            raise
    
    async def get_paper_categories(self) -> Dict[str, List[str]]:
        """
        Get available arXiv subject categories.
        
        Returns:
            Dictionary mapping educational subjects to arXiv categories
        """
        return {
            'Physics': self.category_mappings['physics'],
            'Mathematics': self.category_mappings['mathematics'],
            'Computer Science': self.category_mappings['computer_science'],
            'Biology': self.category_mappings['biology'],
            'Finance': self.category_mappings['finance'],
            'Statistics': self.category_mappings['statistics']
        }
    
    def analyze_educational_level(self, paper_data: Dict[str, Any]) -> str:
        """
        Analyze the educational level of a paper based on content.
        
        Args:
            paper_data: Paper metadata
            
        Returns:
            Educational level ('High School', 'Undergraduate', 'Graduate', 'Research')
        """
        title = paper_data.get('title', '').lower()
        abstract = paper_data.get('summary', '').lower()
        content = f"{title} {abstract}"
        
        # Check for educational level indicators
        for level, keywords in self.educational_keywords.items():
            if any(keyword in content for keyword in keywords):
                return level.replace('_', ' ').title()
        
        # Default classification based on complexity
        if any(term in content for term in ['theorem', 'proof', 'conjecture', 'lemma']):
            return 'Research'
        elif any(term in content for term in ['advanced', 'graduate', 'doctoral']):
            return 'Graduate'
        elif any(term in content for term in ['undergraduate', 'college', 'introductory']):
            return 'Undergraduate'
        else:
            return 'Graduate'  # Default for research papers
    
    def calculate_complexity_score(self, paper_data: Dict[str, Any]) -> float:
        """
        Calculate complexity score for educational filtering.
        
        Args:
            paper_data: Paper metadata
            
        Returns:
            Complexity score (0.0 to 1.0)
        """
        title = paper_data.get('title', '')
        abstract = paper_data.get('summary', '')
        content = f"{title} {abstract}".lower()
        
        complexity_indicators = [
            'theorem', 'proof', 'conjecture', 'lemma', 'corollary',
            'algorithm', 'optimization', 'methodology', 'framework',
            'novel', 'advanced', 'sophisticated', 'cutting-edge'
        ]
        
        # Count complexity indicators
        indicator_count = sum(1 for indicator in complexity_indicators if indicator in content)
        
        # Normalize to 0-1 scale
        max_indicators = 10
        complexity_score = min(indicator_count / max_indicators, 1.0)
        
        # Adjust based on abstract length (longer abstracts tend to be more complex)
        abstract_length = len(abstract.split())
        if abstract_length > 200:
            complexity_score += 0.2
        elif abstract_length > 150:
            complexity_score += 0.1
        
        return min(complexity_score, 1.0)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on arXiv API.
        
        Returns:
            Health check results
        """
        try:
            # Simple search to test API connectivity
            params = {
                'search_query': 'cat:cs.AI',
                'max_results': 1
            }
            
            start_time = datetime.now()
            xml_response = await self._make_request(params)
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds()
            
            # Parse to ensure valid response
            papers = self._parse_atom_feed(xml_response)
            
            return {
                'status': 'healthy',
                'response_time_seconds': response_time,
                'papers_found': len(papers),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"arXiv health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }