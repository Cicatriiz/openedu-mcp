"""
Wikipedia API client for OpenEdu MCP Server.

This module provides a comprehensive client for interacting with the Wikipedia/Wikimedia API,
including article search, content retrieval, featured articles, and educational content analysis
with proper error handling and rate limiting.
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Union
from urllib.parse import quote_plus, urljoin
import aiohttp
from datetime import datetime, date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)


class WikipediaClient:
    """Client for Wikipedia API with educational focus."""
    
    def __init__(self, config: Config):
        """
        Initialize the Wikipedia client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.base_url = config.apis.wikipedia.base_url
        self.action_api_url = "https://en.wikipedia.org/w/api.php"
        self.timeout = config.apis.wikipedia.timeout
        self.retry_attempts = config.apis.wikipedia.retry_attempts
        self.backoff_factor = config.apis.wikipedia.backoff_factor
        
        # User agent for respectful API usage
        self.headers = {
            'User-Agent': f'{config.server.name}/{config.server.version} (Educational MCP Server; https://github.com/openedu-mcp)'
        }
        
        # Session will be created when needed
        self._session: Optional[aiohttp.ClientSession] = None
    
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
        url: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        use_action_api: bool = False
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            url: Full URL or endpoint
            params: Query parameters
            retry_count: Current retry attempt
            use_action_api: Whether to use the action API base URL
            
        Returns:
            JSON response data
            
        Raises:
            APIError: If request fails after all retries
        """
        if not url.startswith('http'):
            base = self.action_api_url if use_action_api else self.base_url
            url = urljoin(base, url)
        
        session = await self._get_session()
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 429:  # Rate limited
                    if retry_count < self.retry_attempts:
                        wait_time = self.backoff_factor ** retry_count
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        return await self._make_request(url, params, retry_count + 1, use_action_api)
                    else:
                        raise APIError(f"Rate limited after {self.retry_attempts} retries", "wikipedia")
                elif response.status == 404:
                    return {}  # Return empty dict for not found
                else:
                    error_text = await response.text()
                    raise APIError(f"HTTP {response.status}: {error_text}", "wikipedia")
                    
        except aiohttp.ClientError as e:
            if retry_count < self.retry_attempts:
                wait_time = self.backoff_factor ** retry_count
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(url, params, retry_count + 1, use_action_api)
            else:
                raise APIError(f"Request failed after {self.retry_attempts} retries: {e}", "wikipedia")
        except Exception as e:
            raise APIError(f"Unexpected error: {e}", "wikipedia")
    
    def _validate_search_params(self, query: str, limit: int, lang: str) -> None:
        """
        Validate search parameters.
        
        Args:
            query: Search query
            limit: Result limit
            lang: Language code
            
        Raises:
            ValidationError: If parameters are invalid
        """
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")
        
        if limit < 1 or limit > 50:
            raise ValidationError("Limit must be between 1 and 50")
        
        if not re.match(r'^[a-z]{2,3}$', lang):
            raise ValidationError("Language code must be 2-3 lowercase letters")
    
    def _validate_title(self, title: str) -> str:
        """
        Validate and normalize article title.
        
        Args:
            title: Article title
            
        Returns:
            Normalized title
            
        Raises:
            ValidationError: If title is invalid
        """
        if not title or not title.strip():
            raise ValidationError("Article title cannot be empty")
        
        # Basic title normalization
        normalized = title.strip()
        
        # Replace spaces with underscores for URL compatibility
        normalized = normalized.replace(' ', '_')
        
        return normalized
    
    async def search_wikipedia(
        self,
        query: str,
        lang: str = 'en',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search Wikipedia articles.
        
        Args:
            query: Search query
            lang: Language code (default: 'en')
            limit: Maximum number of results (1-50)
            
        Returns:
            List of article search results
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
        """
        self._validate_search_params(query, limit, lang)
        
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'srprop': 'snippet|titlesnippet|size|wordcount|timestamp',
            'utf8': 1
        }
        
        try:
            # Use action API for search
            response = await self._make_request('', params, use_action_api=True)
            
            if 'query' not in response or 'search' not in response['query']:
                return []
            
            results = []
            for item in response['query']['search']:
                # Get additional details for each result
                try:
                    summary = await self.get_article_summary(item['title'], lang)
                    result = {
                        'title': item['title'],
                        'snippet': item.get('snippet', ''),
                        'size': item.get('size', 0),
                        'wordcount': item.get('wordcount', 0),
                        'timestamp': item.get('timestamp', ''),
                        'url': f"https://{lang}.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                        'summary': summary.get('extract', '') if summary else '',
                        'pageid': item.get('pageid')
                    }
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to get summary for {item['title']}: {e}")
                    # Add basic result without summary
                    result = {
                        'title': item['title'],
                        'snippet': item.get('snippet', ''),
                        'size': item.get('size', 0),
                        'wordcount': item.get('wordcount', 0),
                        'timestamp': item.get('timestamp', ''),
                        'url': f"https://{lang}.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                        'pageid': item.get('pageid')
                    }
                    results.append(result)
            
            logger.info(f"Found {len(results)} articles for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Wikipedia: {e}")
            raise
    
    async def get_article_summary(
        self,
        title: str,
        lang: str = 'en'
    ) -> Dict[str, Any]:
        """
        Get article summary/extract.
        
        Args:
            title: Article title
            lang: Language code (default: 'en')
            
        Returns:
            Article summary data
            
        Raises:
            ValidationError: If title is invalid
            APIError: If API request fails
        """
        normalized_title = self._validate_title(title)
        
        try:
            # Try REST API first for summary
            rest_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(normalized_title)}"
            response = await self._make_request(rest_url)
            
            if response:
                return response
            
            # Fallback to action API
            params = {
                'action': 'query',
                'format': 'json',
                'titles': title,
                'prop': 'extracts|info|categories',
                'exintro': True,
                'explaintext': True,
                'exsectionformat': 'plain',
                'inprop': 'url',
                'utf8': 1
            }
            
            response = await self._make_request('', params, use_action_api=True)
            
            if 'query' not in response or 'pages' not in response['query']:
                return {}
            
            pages = response['query']['pages']
            page_data = next(iter(pages.values()))
            
            if 'missing' in page_data:
                return {}
            
            return {
                'title': page_data.get('title', title),
                'extract': page_data.get('extract', ''),
                'pageid': page_data.get('pageid'),
                'fullurl': page_data.get('fullurl', ''),
                'categories': page_data.get('categories', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting article summary for {title}: {e}")
            raise
    
    async def get_article_content(
        self,
        title: str,
        lang: str = 'en'
    ) -> Dict[str, Any]:
        """
        Get full article content.
        
        Args:
            title: Article title
            lang: Language code (default: 'en')
            
        Returns:
            Full article content data
            
        Raises:
            ValidationError: If title is invalid
            APIError: If API request fails
        """
        normalized_title = self._validate_title(title)
        
        try:
            # Get full extract using action API
            params = {
                'action': 'query',
                'format': 'json',
                'titles': title,
                'prop': 'extracts|info|categories|links|images',
                'explaintext': '1',
                'exsectionformat': 'plain',
                'inprop': 'url',
                'pllimit': 50,  # Limit links
                'imlimit': 10,  # Limit images
                'utf8': 1
            }
            
            response = await self._make_request('', params, use_action_api=True)
            
            if 'query' not in response or 'pages' not in response['query']:
                return {}
            
            pages = response['query']['pages']
            page_data = next(iter(pages.values()))
            
            if 'missing' in page_data:
                return {}
            
            # Extract links and images
            links = []
            if 'links' in page_data:
                links = [link['title'] for link in page_data['links']]
            
            images = []
            if 'images' in page_data:
                images = [img['title'] for img in page_data['images']]
            
            categories = []
            if 'categories' in page_data:
                categories = [cat['title'].replace('Category:', '') for cat in page_data['categories']]
            
            return {
                'title': page_data.get('title', title),
                'extract': page_data.get('extract', ''),
                'pageid': page_data.get('pageid'),
                'fullurl': page_data.get('fullurl', ''),
                'categories': categories,
                'links': links[:20],  # Limit to first 20 links
                'images': images,
                'wordcount': len(page_data.get('extract', '').split()) if page_data.get('extract') else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting article content for {title}: {e}")
            raise
    
    async def get_daily_featured(
        self,
        date_param: Optional[Union[str, date]] = None,
        lang: str = 'en'
    ) -> Dict[str, Any]:
        """
        Get featured article of the day.
        
        Args:
            date_param: Date (YYYY/MM/DD format or date object), defaults to today
            lang: Language code (default: 'en')
            
        Returns:
            Featured article data
            
        Raises:
            APIError: If API request fails
        """
        if date_param is None:
            date_param = date.today()
        
        if isinstance(date_param, date):
            date_str = date_param.strftime('%Y/%m/%d')
        else:
            # Validate date string format
            try:
                datetime.strptime(date_param, '%Y/%m/%d')
                date_str = date_param
            except ValueError:
                raise ValidationError("Date must be in YYYY/MM/DD format")
        
        try:
            # Use REST API for featured content
            url = f"https://{lang}.wikipedia.org/api/rest_v1/feed/featured/{date_str}"
            response = await self._make_request(url)
            
            if not response:
                return {}
            
            # Extract the featured article
            if 'tfa' in response:  # Today's Featured Article
                tfa = response['tfa']
                return {
                    'title': tfa.get('title', ''),
                    'extract': tfa.get('extract', ''),
                    'description': tfa.get('description', ''),
                    'content_urls': tfa.get('content_urls', {}),
                    'thumbnail': tfa.get('thumbnail', {}),
                    'date': date_str,
                    'type': 'featured_article'
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting featured article for {date_str}: {e}")
            raise
    
    async def get_article_images(
        self,
        title: str,
        lang: str = 'en'
    ) -> List[Dict[str, Any]]:
        """
        Get article images.
        
        Args:
            title: Article title
            lang: Language code (default: 'en')
            
        Returns:
            List of image data
            
        Raises:
            ValidationError: If title is invalid
            APIError: If API request fails
        """
        normalized_title = self._validate_title(title)
        
        try:
            # Get images using action API
            params = {
                'action': 'query',
                'format': 'json',
                'titles': title,
                'prop': 'images',
                'imlimit': 10,
                'utf8': 1
            }
            
            response = await self._make_request('', params, use_action_api=True)
            
            if 'query' not in response or 'pages' not in response['query']:
                return []
            
            pages = response['query']['pages']
            page_data = next(iter(pages.values()))
            
            if 'missing' in page_data or 'images' not in page_data:
                return []
            
            images = []
            for img in page_data['images']:
                img_title = img['title']
                
                # Get image info
                try:
                    img_params = {
                        'action': 'query',
                        'format': 'json',
                        'titles': img_title,
                        'prop': 'imageinfo',
                        'iiprop': 'url|size|mime',
                        'utf8': 1
                    }
                    
                    img_response = await self._make_request('', img_params, use_action_api=True)
                    
                    if 'query' in img_response and 'pages' in img_response['query']:
                        img_pages = img_response['query']['pages']
                        img_data = next(iter(img_pages.values()))
                        
                        if 'imageinfo' in img_data and img_data['imageinfo']:
                            img_info = img_data['imageinfo'][0]
                            images.append({
                                'title': img_title,
                                'url': img_info.get('url', ''),
                                'width': img_info.get('width', 0),
                                'height': img_info.get('height', 0),
                                'mime': img_info.get('mime', '')
                            })
                
                except Exception as e:
                    logger.warning(f"Failed to get info for image {img_title}: {e}")
                    continue
            
            return images
            
        except Exception as e:
            logger.error(f"Error getting images for {title}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Wikipedia API.
        
        Returns:
            Health status information
        """
        try:
            start_time = datetime.now()
            
            # Simple search to test API availability
            await self.search_wikipedia('test', limit=1)
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'response_time_seconds': response_time,
                'timestamp': end_time.isoformat(),
                'api_url': self.base_url
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'api_url': self.base_url
            }