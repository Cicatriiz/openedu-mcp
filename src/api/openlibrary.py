"""
Open Library API client for OpenEdu MCP Server.

This module provides a comprehensive client for interacting with the Open Library API,
including book search, detailed book information retrieval, cover images, and
availability checking with proper error handling and rate limiting.
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Union
from urllib.parse import quote_plus, urljoin
import aiohttp
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from exceptions import APIError, ValidationError

logger = logging.getLogger(__name__)


class OpenLibraryClient:
    """Client for Open Library API with educational focus."""
    
    def __init__(self, config: Config):
        """
        Initialize the Open Library client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.base_url = config.apis.open_library.base_url
        self.timeout = config.apis.open_library.timeout
        self.retry_attempts = config.apis.open_library.retry_attempts
        self.backoff_factor = config.apis.open_library.backoff_factor
        
        # User agent for respectful API usage
        self.headers = {
            'User-Agent': f'{config.server.name}/{config.server.version} (Educational MCP Server)'
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
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            retry_count: Current retry attempt
            
        Returns:
            JSON response data
            
        Raises:
            APIError: If request fails after all retries
        """
        url = urljoin(self.base_url, endpoint)
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
                        return await self._make_request(endpoint, params, retry_count + 1)
                    else:
                        raise APIError(f"Rate limited after {self.retry_attempts} retries", "open_library")
                elif response.status == 404:
                    return {}  # Return empty dict for not found
                else:
                    error_text = await response.text()
                    raise APIError(f"HTTP {response.status}: {error_text}", "open_library")
                    
        except aiohttp.ClientError as e:
            if retry_count < self.retry_attempts:
                wait_time = self.backoff_factor ** retry_count
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(endpoint, params, retry_count + 1)
            else:
                raise APIError(f"Request failed after {self.retry_attempts} retries: {e}", "open_library")
        except Exception as e:
            raise APIError(f"Unexpected error: {e}", "open_library")
    
    def _validate_isbn(self, isbn: str) -> str:
        """
        Validate and normalize ISBN.
        
        Args:
            isbn: ISBN string to validate
            
        Returns:
            Normalized ISBN
            
        Raises:
            ValidationError: If ISBN is invalid
        """
        if not isbn:
            raise ValidationError("ISBN cannot be empty")
        
        # Remove hyphens and spaces
        clean_isbn = re.sub(r'[-\s]', '', isbn.strip())
        
        # Check if it's a valid ISBN-10 or ISBN-13
        if len(clean_isbn) == 10:
            # Basic ISBN-10 validation (digits + optional X)
            if not re.match(r'^\d{9}[\dX]$', clean_isbn):
                raise ValidationError("Invalid ISBN-10 format")
        elif len(clean_isbn) == 13:
            # Basic ISBN-13 validation (all digits)
            if not re.match(r'^\d{13}$', clean_isbn):
                raise ValidationError("Invalid ISBN-13 format")
        else:
            raise ValidationError("ISBN must be 10 or 13 characters")
        
        return clean_isbn
    
    def _validate_search_params(self, query: str, limit: int) -> None:
        """
        Validate search parameters.
        
        Args:
            query: Search query
            limit: Result limit
            
        Raises:
            ValidationError: If parameters are invalid
        """
        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")
        
        if limit < 1 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")
    
    async def search_books(
        self,
        query: str,
        limit: int = 10,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for books using Open Library search API.
        
        Args:
            query: Search query (title, author, subject, etc.)
            limit: Maximum number of results (1-100)
            fields: Specific fields to return
            
        Returns:
            List of book data dictionaries
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
        """
        self._validate_search_params(query, limit)
        
        # Default fields for educational use
        if fields is None:
            fields = [
                'key', 'title', 'author_name', 'first_publish_year',
                'isbn', 'publisher', 'subject', 'cover_i',
                'number_of_pages_median', 'language', 'description'
            ]
        
        params = {
            'q': query,
            'limit': limit,
            'fields': ','.join(fields)
        }
        
        try:
            response = await self._make_request('/search.json', params)
            books = response.get('docs', [])
            
            logger.info(f"Found {len(books)} books for query: {query}")
            return books
            
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            raise
    
    async def get_book_details(self, isbn: str) -> Dict[str, Any]:
        """
        Get detailed book information by ISBN.
        
        Args:
            isbn: ISBN-10 or ISBN-13
            
        Returns:
            Detailed book information
            
        Raises:
            ValidationError: If ISBN is invalid
            APIError: If API request fails
        """
        clean_isbn = self._validate_isbn(isbn)
        
        try:
            # Try to get book details using ISBN
            response = await self._make_request(f'/books/{clean_isbn}.json')
            
            if not response:
                # If direct ISBN lookup fails, try search
                search_results = await self.search_books(f'isbn:{clean_isbn}', limit=1)
                if search_results:
                    return search_results[0]
                else:
                    return {}
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting book details for ISBN {isbn}: {e}")
            raise
    
    async def get_book_cover(
        self,
        isbn: str,
        size: str = 'M'
    ) -> Optional[str]:
        """
        Get book cover image URL by ISBN.
        
        Args:
            isbn: ISBN-10 or ISBN-13
            size: Cover size ('S', 'M', 'L')
            
        Returns:
            Cover image URL or None if not available
            
        Raises:
            ValidationError: If parameters are invalid
        """
        clean_isbn = self._validate_isbn(isbn)
        
        if size not in ['S', 'M', 'L']:
            raise ValidationError("Cover size must be 'S', 'M', or 'L'")
        
        # Open Library covers API
        cover_url = f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-{size}.jpg"
        
        try:
            # Check if cover exists by making a HEAD request
            session = await self._get_session()
            async with session.head(cover_url) as response:
                if response.status == 200:
                    return cover_url
                else:
                    return None
                    
        except Exception as e:
            logger.warning(f"Error checking cover availability for ISBN {isbn}: {e}")
            return None
    
    async def check_book_availability(self, isbn: str) -> Dict[str, Any]:
        """
        Check book borrowing availability from Open Library.
        
        Args:
            isbn: ISBN-10 or ISBN-13
            
        Returns:
            Availability information
            
        Raises:
            ValidationError: If ISBN is invalid
            APIError: If API request fails
        """
        clean_isbn = self._validate_isbn(isbn)
        
        try:
            # Get book details first
            book_details = await self.get_book_details(clean_isbn)
            
            if not book_details:
                return {
                    'available': False,
                    'status': 'not_found',
                    'message': 'Book not found in Open Library'
                }
            
            # Check if book has availability information
            # Note: Open Library's availability API is limited, so we provide basic info
            availability = {
                'available': True,
                'status': 'available',
                'message': 'Book found in Open Library catalog',
                'isbn': clean_isbn,
                'title': book_details.get('title', 'Unknown'),
                'source_url': f"https://openlibrary.org/books/{clean_isbn}"
            }
            
            # Add additional availability context if available
            if 'availability' in book_details:
                availability.update(book_details['availability'])
            
            return availability
            
        except Exception as e:
            logger.error(f"Error checking availability for ISBN {isbn}: {e}")
            raise
    
    async def get_work_details(self, work_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a work (collection of editions).
        
        Args:
            work_id: Open Library work ID
            
        Returns:
            Work details
            
        Raises:
            APIError: If API request fails
        """
        if not work_id:
            raise ValidationError("Work ID cannot be empty")
        
        # Ensure work_id has proper format
        if not work_id.startswith('/works/'):
            work_id = f'/works/{work_id}'
        
        try:
            response = await self._make_request(f'{work_id}.json')
            return response
            
        except Exception as e:
            logger.error(f"Error getting work details for {work_id}: {e}")
            raise
    
    async def search_by_subject(
        self,
        subject: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search books by educational subject.
        
        Args:
            subject: Educational subject (e.g., "mathematics", "science")
            limit: Maximum number of results
            
        Returns:
            List of books in the subject area
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
        """
        if not subject or not subject.strip():
            raise ValidationError("Subject cannot be empty")
        
        # Format subject for search
        subject_query = f'subject:"{subject.strip()}"'
        
        return await self.search_books(subject_query, limit)
    
    async def search_by_author(
        self,
        author: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search books by author name.
        
        Args:
            author: Author name
            limit: Maximum number of results
            
        Returns:
            List of books by the author
            
        Raises:
            ValidationError: If parameters are invalid
            APIError: If API request fails
        """
        if not author or not author.strip():
            raise ValidationError("Author name cannot be empty")
        
        # Format author for search
        author_query = f'author:"{author.strip()}"'
        
        return await self.search_books(author_query, limit)
    
    async def get_trending_books(
        self,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending/popular books, optionally filtered by subject.
        
        Args:
            subject: Optional subject filter
            limit: Maximum number of results
            
        Returns:
            List of trending books
            
        Raises:
            APIError: If API request fails
        """
        # Open Library doesn't have a direct trending API, so we'll search for
        # highly-rated books or use a general query
        if subject:
            query = f'subject:"{subject}" AND ratings_average:[4 TO 5]'
        else:
            query = 'ratings_average:[4 TO 5]'
        
        try:
            return await self.search_books(query, limit)
        except Exception:
            # Fallback to general popular books search
            fallback_query = subject if subject else 'popular books'
            return await self.search_books(fallback_query, limit)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Open Library API.
        
        Returns:
            Health status information
        """
        try:
            start_time = datetime.now()
            
            # Simple search to test API availability
            await self.search_books('test', limit=1)
            
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