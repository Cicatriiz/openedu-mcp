"""
Base tool class for OpenEdu MCP Server.

This module provides the base class that all educational tools inherit from,
providing common functionality like caching, rate limiting, and error handling.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.cache_service import CacheService
from services.rate_limiting_service import RateLimitingService
from services.usage_service import UsageService
from exceptions import ToolError, APIError, RateLimitError, ValidationError
from utils.validation import Validator


logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all educational tools."""
    
    def __init__(
        self,
        config: Config,
        cache_service: CacheService,
        rate_limiting_service: RateLimitingService,
        usage_service: UsageService
    ):
        self.config = config
        self.cache_service = cache_service
        self.rate_limiting_service = rate_limiting_service
        self.usage_service = usage_service
        self.tool_name = self.__class__.__name__.replace("Tool", "").lower()
        
    @property
    @abstractmethod
    def api_name(self) -> str:
        """Name of the API this tool uses for rate limiting."""
        pass
    
    async def execute_with_monitoring(
        self,
        method_name: str,
        method_func,
        *args,
        user_session: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Execute a tool method with monitoring, caching, and error handling.
        
        Args:
            method_name: Name of the method being executed
            method_func: The method function to execute
            *args: Positional arguments for the method
            user_session: User session identifier
            **kwargs: Keyword arguments for the method
            
        Returns:
            Method result
            
        Raises:
            ToolError: If tool execution fails
        """
        start_time = time.time()
        cache_hit = False
        error_occurred = False
        result = None
        result_count = None
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(method_name, *args, **kwargs)
            
            # Try to get from cache first
            if cache_key:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result is not None:
                    cache_hit = True
                    result = cached_result
                    if isinstance(result, list):
                        result_count = len(result)
                    
                    # Record usage
                    execution_time = int((time.time() - start_time) * 1000)
                    await self.usage_service.record_tool_usage(
                        tool_name=self.tool_name,
                        method_name=method_name,
                        execution_time_ms=execution_time,
                        cache_hit=True,
                        error_occurred=False,
                        user_session=user_session,
                        parameters=self._sanitize_parameters(kwargs),
                        result_count=result_count
                    )
                    
                    return result
            
            # Check rate limits
            await self.rate_limiting_service.wait_if_needed(self.api_name)
            
            # Execute the method
            result = await method_func(*args, **kwargs)
            
            # Record the API request
            await self.rate_limiting_service.record_request(self.api_name)
            
            # Cache the result if we have a cache key
            if cache_key and result is not None:
                await self.cache_service.set(cache_key, result)
            
            # Count results
            if isinstance(result, list):
                result_count = len(result)
            elif result is not None:
                result_count = 1
            
        except RateLimitError:
            error_occurred = True
            raise  # Re-raise rate limit errors as-is
            
        except ValidationError:
            error_occurred = True
            raise  # Re-raise validation errors as-is
            
        except APIError:
            error_occurred = True
            raise  # Re-raise API errors as-is
            
        except Exception as e:
            error_occurred = True
            logger.error(f"Error in {self.tool_name}.{method_name}: {e}")
            raise ToolError(
                f"Tool execution failed: {str(e)}",
                self.tool_name,
                f"Method: {method_name}"
            )
            
        finally:
            # Record usage statistics
            execution_time = int((time.time() - start_time) * 1000)
            await self.usage_service.record_tool_usage(
                tool_name=self.tool_name,
                method_name=method_name,
                execution_time_ms=execution_time,
                cache_hit=cache_hit,
                error_occurred=error_occurred,
                user_session=user_session,
                parameters=self._sanitize_parameters(kwargs),
                result_count=result_count
            )
        
        return result
    
    def _generate_cache_key(self, method_name: str, *args, **kwargs) -> Optional[str]:
        """
        Generate a cache key for the method call.
        
        Args:
            method_name: Name of the method
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string or None if caching should be disabled
        """
        try:
            # Create a deterministic key from method name and parameters
            key_parts = [self.tool_name, method_name]
            
            # Add positional arguments
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
                else:
                    # For complex objects, use their string representation
                    key_parts.append(str(hash(str(arg))))
            
            # Add keyword arguments (sorted for consistency)
            for key, value in sorted(kwargs.items()):
                if isinstance(value, (str, int, float, bool, type(None))):
                    key_parts.append(f"{key}:{value}")
                else:
                    key_parts.append(f"{key}:{hash(str(value))}")
            
            # Join with separator and hash if too long
            cache_key = "|".join(key_parts)
            
            # Limit key length
            if len(cache_key) > 250:
                import hashlib
                cache_key = f"{self.tool_name}:{method_name}:{hashlib.md5(cache_key.encode()).hexdigest()}"
            
            return cache_key
            
        except Exception as e:
            logger.warning(f"Failed to generate cache key: {e}")
            return None
    
    def _sanitize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize parameters for logging (remove sensitive data).
        
        Args:
            params: Parameters dictionary
            
        Returns:
            Sanitized parameters
        """
        sanitized = {}
        sensitive_keys = {'password', 'token', 'key', 'secret', 'auth'}
        
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, (str, int, float, bool, type(None))):
                sanitized[key] = value
            else:
                sanitized[key] = str(type(value).__name__)
        
        return sanitized
    
    async def validate_common_parameters(
        self,
        query: Optional[str] = None,
        limit: Optional[int] = None,
        grade_level: Optional[str] = None,
        subject: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate common parameters used across tools.
        
        Args:
            query: Search query
            limit: Result limit
            grade_level: Educational grade level
            subject: Educational subject
            language: Language code
            
        Returns:
            Dictionary of validated parameters
            
        Raises:
            ValidationError: If any parameter is invalid
        """
        validated = {}
        
        if query is not None:
            validated['query'] = Validator.validate_query(query)
        
        if limit is not None:
            validated['limit'] = Validator.validate_limit(limit)
        
        if grade_level is not None:
            validated['grade_level'] = Validator.validate_grade_level(grade_level)
        
        if subject is not None:
            validated['subject'] = Validator.validate_subject(subject)
        
        if language is not None:
            validated['language'] = Validator.validate_language_code(language)
        
        return validated
    
    def filter_by_educational_criteria(
        self,
        items: List[Any],
        grade_level: Optional[str] = None,
        subject: Optional[str] = None,
        min_relevance_score: Optional[float] = None
    ) -> List[Any]:
        """
        Filter items by educational criteria.
        
        Args:
            items: List of items to filter
            grade_level: Target grade level
            subject: Target subject
            min_relevance_score: Minimum educational relevance score
            
        Returns:
            Filtered list of items
        """
        if not items:
            return items
        
        filtered = items
        
        # Filter by grade level
        if grade_level:
            try:
                target_grade = Validator.validate_grade_level(grade_level)
                filtered = [
                    item for item in filtered
                    if hasattr(item, 'is_suitable_for_grade_level') and 
                    item.is_suitable_for_grade_level(target_grade)
                ]
            except ValidationError:
                pass  # Skip filtering if grade level is invalid
        
        # Filter by subject
        if subject:
            filtered = [
                item for item in filtered
                if hasattr(item, 'has_subject') and item.has_subject(subject)
            ]
        
        # Filter by relevance score
        if min_relevance_score is not None:
            filtered = [
                item for item in filtered
                if hasattr(item, 'get_educational_score') and 
                item.get_educational_score() >= min_relevance_score
            ]
        
        return filtered
    
    def sort_by_educational_relevance(
        self,
        items: List[Any],
        reverse: bool = True
    ) -> List[Any]:
        """
        Sort items by educational relevance score.
        
        Args:
            items: List of items to sort
            reverse: Sort in descending order (highest relevance first)
            
        Returns:
            Sorted list of items
        """
        if not items:
            return items
        
        def get_score(item):
            if hasattr(item, 'get_educational_score'):
                return item.get_educational_score()
            elif hasattr(item, 'educational_metadata') and hasattr(item.educational_metadata, 'educational_relevance_score'):
                return item.educational_metadata.educational_relevance_score
            else:
                return 0.0
        
        return sorted(items, key=get_score, reverse=reverse)
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check for this tool.
        
        Returns:
            Dictionary with health status information
        """
        pass
    
    async def get_tool_info(self) -> Dict[str, Any]:
        """
        Get information about this tool.
        
        Returns:
            Dictionary with tool information
        """
        return {
            "name": self.tool_name,
            "api_name": self.api_name,
            "description": self.__doc__ or "No description available",
            "methods": [
                method for method in dir(self)
                if not method.startswith('_') and callable(getattr(self, method))
            ]
        }