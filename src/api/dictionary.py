"""
Dictionary API client for OpenEdu MCP Server.

This module provides a comprehensive client for interacting with the Dictionary API,
including word definitions, pronunciations, examples, synonyms, and etymology
with proper error handling and rate limiting.
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


class DictionaryClient:
    """Client for Dictionary API with educational focus."""
    
    def __init__(self, config: Config):
        """
        Initialize the Dictionary client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.base_url = config.apis.dictionary.base_url + "/entries/en/"
        self.timeout = config.apis.dictionary.timeout
        self.retry_attempts = config.apis.dictionary.retry_attempts
        self.backoff_factor = config.apis.dictionary.backoff_factor
        
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
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            url: Full URL or endpoint
            params: Query parameters
            retry_count: Current retry attempt
            
        Returns:
            JSON response data
            
        Raises:
            APIError: If request fails after all retries
        """
        if not url.startswith('http'):
            url = urljoin(self.base_url, url)
        
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
                        return await self._make_request(url, params, retry_count + 1)
                    else:
                        raise APIError(f"Rate limited after {self.retry_attempts} retries", "dictionary")
                elif response.status == 404:
                    return {}  # Return empty dict for not found
                else:
                    error_text = await response.text()
                    raise APIError(f"HTTP {response.status}: {error_text}", "dictionary")
                    
        except aiohttp.ClientError as e:
            if retry_count < self.retry_attempts:
                wait_time = self.backoff_factor ** retry_count
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(url, params, retry_count + 1)
            else:
                raise APIError(f"Request failed after {self.retry_attempts} retries: {e}", "dictionary")
        except Exception as e:
            raise APIError(f"Unexpected error: {e}", "dictionary")
    
    def _validate_word(self, word: str) -> str:
        """
        Validate and normalize word input.
        
        Args:
            word: Word to validate
            
        Returns:
            Normalized word
            
        Raises:
            ValidationError: If word is invalid
        """
        if not word or not word.strip():
            raise ValidationError("Word cannot be empty")
        
        # Basic word normalization
        normalized = word.strip().lower()
        
        # Check for valid word characters (letters, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\-']+$", normalized):
            raise ValidationError("Word contains invalid characters")
        
        # Limit word length
        if len(normalized) > 50:
            raise ValidationError("Word is too long (max 50 characters)")
        
        return normalized
    
    async def validate_word(self, word: str) -> bool:
        """
        Validate if a word exists in the dictionary.
        
        Args:
            word: Word to validate
            
        Returns:
            True if word exists, False otherwise
        """
        try:
            normalized_word = self._validate_word(word)
            result = await self.get_definition(normalized_word)
            return bool(result)
        except Exception:
            return False
    
    async def get_definition(self, word: str) -> Dict[str, Any]:
        """
        Get word definitions with pronunciations.
        
        Args:
            word: Word to define
            
        Returns:
            Word definition data
            
        Raises:
            ValidationError: If word is invalid
            APIError: If API request fails
        """
        normalized_word = self._validate_word(word)
        
        try:
            # Make request to Dictionary API
            url = f"{quote_plus(normalized_word)}"
            response = await self._make_request(url)
            
            if not response:
                return {}
            
            # Dictionary API returns a list of entries
            if isinstance(response, list) and len(response) > 0:
                return response[0]  # Return first entry
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting definition for {word}: {e}")
            raise
    
    async def get_word_synonyms(self, word: str) -> List[str]:
        """
        Get synonyms and related words.
        
        Args:
            word: Word to find synonyms for
            
        Returns:
            List of synonyms
            
        Raises:
            ValidationError: If word is invalid
            APIError: If API request fails
        """
        try:
            definition_data = await self.get_definition(word)
            
            if not definition_data:
                return []
            
            synonyms = []
            meanings = definition_data.get("meanings", [])
            
            for meaning in meanings:
                for definition in meaning.get("definitions", []):
                    synonyms.extend(definition.get("synonyms", []))
            
            # Remove duplicates and return
            return list(set(synonyms))
            
        except Exception as e:
            logger.error(f"Error getting synonyms for {word}: {e}")
            raise
    
    async def get_word_examples(self, word: str) -> List[str]:
        """
        Get example sentences.
        
        Args:
            word: Word to find examples for
            
        Returns:
            List of example sentences
            
        Raises:
            ValidationError: If word is invalid
            APIError: If API request fails
        """
        try:
            definition_data = await self.get_definition(word)
            
            if not definition_data:
                return []
            
            examples = []
            meanings = definition_data.get("meanings", [])
            
            for meaning in meanings:
                for definition in meaning.get("definitions", []):
                    if definition.get("example"):
                        examples.append(definition["example"])
            
            return examples
            
        except Exception as e:
            logger.error(f"Error getting examples for {word}: {e}")
            raise
    
    async def get_word_etymology(self, word: str) -> Optional[str]:
        """
        Get word origins and etymology.
        
        Args:
            word: Word to find etymology for
            
        Returns:
            Etymology information or None
            
        Raises:
            ValidationError: If word is invalid
            APIError: If API request fails
        """
        try:
            definition_data = await self.get_definition(word)
            
            if not definition_data:
                return None
            
            # Dictionary API doesn't typically include etymology
            # This would need to be enhanced with additional sources
            return definition_data.get("etymology")
            
        except Exception as e:
            logger.error(f"Error getting etymology for {word}: {e}")
            raise
    
    async def get_phonetics(self, word: str) -> Dict[str, Any]:
        """
        Get pronunciation information.
        
        Args:
            word: Word to find pronunciation for
            
        Returns:
            Phonetics data with text and audio
            
        Raises:
            ValidationError: If word is invalid
            APIError: If API request fails
        """
        try:
            definition_data = await self.get_definition(word)
            
            if not definition_data:
                return {}
            
            phonetics = definition_data.get("phonetics", [])
            
            # Find the best phonetic entry (with both text and audio if possible)
            best_phonetic = {}
            for phonetic in phonetics:
                if phonetic.get("text") and phonetic.get("audio"):
                    return {
                        "text": phonetic["text"],
                        "audio": phonetic["audio"],
                        "source": phonetic.get("sourceUrl", "")
                    }
                elif phonetic.get("text") and not best_phonetic.get("text"):
                    best_phonetic = {
                        "text": phonetic["text"],
                        "audio": phonetic.get("audio", ""),
                        "source": phonetic.get("sourceUrl", "")
                    }
                elif phonetic.get("audio") and not best_phonetic.get("audio"):
                    best_phonetic.update({
                        "audio": phonetic["audio"],
                        "source": phonetic.get("sourceUrl", "")
                    })
            
            return best_phonetic
            
        except Exception as e:
            logger.error(f"Error getting phonetics for {word}: {e}")
            raise
    
    async def get_comprehensive_data(self, word: str) -> Dict[str, Any]:
        """
        Get comprehensive word data including definitions, synonyms, examples, and phonetics.
        
        Args:
            word: Word to analyze
            
        Returns:
            Comprehensive word data
            
        Raises:
            ValidationError: If word is invalid
            APIError: If API request fails
        """
        try:
            definition_data = await self.get_definition(word)
            
            if not definition_data:
                return {}
            
            # Extract all data in one pass for efficiency
            synonyms = []
            antonyms = []
            examples = []
            definitions = []
            parts_of_speech = []
            
            meanings = definition_data.get("meanings", [])
            for meaning in meanings:
                part_of_speech = meaning.get("partOfSpeech", "")
                if part_of_speech and part_of_speech not in parts_of_speech:
                    parts_of_speech.append(part_of_speech)
                
                for definition in meaning.get("definitions", []):
                    definitions.append(definition.get("definition", ""))
                    
                    if definition.get("example"):
                        examples.append(definition["example"])
                    
                    synonyms.extend(definition.get("synonyms", []))
                    antonyms.extend(definition.get("antonyms", []))
            
            # Get phonetics from original data
            phonetics = definition_data.get("phonetics", [])
            
            return {
                "word": definition_data.get("word", word),
                "phonetics": phonetics,
                "meanings": meanings,
                "definitions": definitions,
                "parts_of_speech": parts_of_speech,
                "examples": examples,
                "synonyms": list(set(synonyms)),
                "antonyms": list(set(antonyms)),
                "source_urls": definition_data.get("sourceUrls", [])
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive data for {word}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check for the Dictionary API.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Test with a simple word
            test_word = "test"
            start_time = datetime.now()
            
            result = await self.get_definition(test_word)
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy" if result else "degraded",
                "response_time_ms": response_time,
                "api_accessible": bool(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Dictionary API health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_accessible": False,
                "timestamp": datetime.now().isoformat()
            }