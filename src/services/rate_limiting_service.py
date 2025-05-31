"""
Rate limiting service for OpenEdu MCP Server.

This module provides rate limiting functionality to manage API calls
to external services and prevent exceeding their limits.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import APIsConfig
from exceptions import RateLimitError


logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """State tracking for a rate-limited API."""
    current_count: int = 0
    window_start: datetime = field(default_factory=datetime.now)
    last_request: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    blocked_requests: int = 0


class RateLimitingService:
    """Service for managing API rate limits."""
    
    def __init__(self, apis_config: APIsConfig):
        self.apis_config = apis_config
        self.rate_limits: Dict[str, RateLimitState] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
        # Initialize rate limit states for each API
        self._initialize_rate_limits()
    
    def _initialize_rate_limits(self) -> None:
        """Initialize rate limit tracking for all configured APIs."""
        api_configs = {
            "open_library": self.apis_config.open_library,
            "wikipedia": self.apis_config.wikipedia,
            "dictionary": self.apis_config.dictionary,
            "arxiv": self.apis_config.arxiv
        }
        
        for api_name, config in api_configs.items():
            self.rate_limits[api_name] = RateLimitState()
            self._locks[api_name] = asyncio.Lock()
            
        logger.info(f"Initialized rate limiting for {len(api_configs)} APIs")
    
    async def check_rate_limit(self, api_name: str) -> bool:
        """
        Check if an API call is allowed under current rate limits.
        
        Args:
            api_name: Name of the API to check
            
        Returns:
            True if request is allowed, False if rate limited
            
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        if api_name not in self.rate_limits:
            logger.warning(f"Unknown API for rate limiting: {api_name}")
            return True
        
        async with self._locks[api_name]:
            state = self.rate_limits[api_name]
            config = self._get_api_config(api_name)
            
            if not config:
                return True
            
            now = datetime.now()
            
            # Determine window duration based on rate limit type
            if api_name == "arxiv":
                # arXiv: requests per second
                window_duration = timedelta(seconds=1)
            elif api_name == "dictionary":
                # Dictionary API: requests per hour
                window_duration = timedelta(hours=1)
            else:
                # Open Library, Wikipedia: requests per minute
                window_duration = timedelta(minutes=1)
            
            # Reset window if expired
            if now - state.window_start >= window_duration:
                state.current_count = 0
                state.window_start = now
            
            # Check if we're within limits
            if state.current_count >= config.rate_limit:
                state.blocked_requests += 1
                
                # Calculate retry after time
                retry_after = int((state.window_start + window_duration - now).total_seconds())
                
                raise RateLimitError(
                    f"Rate limit exceeded for {api_name}",
                    api_name,
                    retry_after=max(retry_after, 1)
                )
            
            return True
    
    async def record_request(self, api_name: str) -> None:
        """
        Record that a request was made to an API.
        
        Args:
            api_name: Name of the API
        """
        if api_name not in self.rate_limits:
            return
        
        async with self._locks[api_name]:
            state = self.rate_limits[api_name]
            state.current_count += 1
            state.last_request = datetime.now()
            state.total_requests += 1
    
    async def wait_if_needed(self, api_name: str) -> None:
        """
        Wait if necessary to respect rate limits.
        
        Args:
            api_name: Name of the API
        """
        try:
            await self.check_rate_limit(api_name)
        except RateLimitError as e:
            if e.retry_after:
                logger.info(f"Rate limited for {api_name}, waiting {e.retry_after} seconds")
                await asyncio.sleep(e.retry_after)
                # Try again after waiting
                await self.check_rate_limit(api_name)
            else:
                raise
    
    async def get_rate_limit_status(self, api_name: str) -> Dict[str, Any]:
        """
        Get current rate limit status for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Dictionary with rate limit status information
        """
        if api_name not in self.rate_limits:
            return {"error": f"Unknown API: {api_name}"}
        
        async with self._locks[api_name]:
            state = self.rate_limits[api_name]
            config = self._get_api_config(api_name)
            
            if not config:
                return {"error": f"No config found for API: {api_name}"}
            
            now = datetime.now()
            
            # Determine window info
            if api_name == "arxiv":
                window_duration = timedelta(seconds=1)
                window_type = "per_second"
            elif api_name == "dictionary":
                window_duration = timedelta(hours=1)
                window_type = "per_hour"
            else:
                window_duration = timedelta(minutes=1)
                window_type = "per_minute"
            
            # Calculate time until window reset
            window_reset = state.window_start + window_duration
            reset_in_seconds = max(0, int((window_reset - now).total_seconds()))
            
            return {
                "api_name": api_name,
                "rate_limit": config.rate_limit,
                "window_type": window_type,
                "current_count": state.current_count,
                "remaining": max(0, config.rate_limit - state.current_count),
                "reset_in_seconds": reset_in_seconds,
                "window_start": state.window_start.isoformat(),
                "last_request": state.last_request.isoformat(),
                "total_requests": state.total_requests,
                "blocked_requests": state.blocked_requests
            }
    
    async def get_all_rate_limit_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get rate limit status for all APIs.
        
        Returns:
            Dictionary mapping API names to their status
        """
        status = {}
        for api_name in self.rate_limits.keys():
            status[api_name] = await self.get_rate_limit_status(api_name)
        return status
    
    def _get_api_config(self, api_name: str):
        """Get configuration for a specific API."""
        config_map = {
            "open_library": self.apis_config.open_library,
            "wikipedia": self.apis_config.wikipedia,
            "dictionary": self.apis_config.dictionary,
            "arxiv": self.apis_config.arxiv
        }
        return config_map.get(api_name)
    
    async def reset_rate_limit(self, api_name: str) -> None:
        """
        Reset rate limit for a specific API (for testing/admin purposes).
        
        Args:
            api_name: Name of the API to reset
        """
        if api_name not in self.rate_limits:
            return
        
        async with self._locks[api_name]:
            self.rate_limits[api_name] = RateLimitState()
            logger.info(f"Reset rate limit for {api_name}")
    
    async def update_rate_limit(self, api_name: str, new_limit: int) -> None:
        """
        Update rate limit for a specific API.
        
        Args:
            api_name: Name of the API
            new_limit: New rate limit value
        """
        config = self._get_api_config(api_name)
        if config:
            config.rate_limit = new_limit
            logger.info(f"Updated rate limit for {api_name} to {new_limit}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall rate limiting statistics.
        
        Returns:
            Dictionary with statistics across all APIs
        """
        total_requests = 0
        total_blocked = 0
        api_stats = {}
        
        for api_name, state in self.rate_limits.items():
            async with self._locks[api_name]:
                total_requests += state.total_requests
                total_blocked += state.blocked_requests
                
                api_stats[api_name] = {
                    "total_requests": state.total_requests,
                    "blocked_requests": state.blocked_requests,
                    "success_rate": (
                        (state.total_requests - state.blocked_requests) / max(state.total_requests, 1)
                    ) * 100
                }
        
        return {
            "total_requests": total_requests,
            "total_blocked": total_blocked,
            "overall_success_rate": (
                (total_requests - total_blocked) / max(total_requests, 1)
            ) * 100,
            "api_statistics": api_stats
        }