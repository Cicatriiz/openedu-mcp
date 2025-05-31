"""
Custom exception classes for OpenEdu MCP Server.

This module defines all custom exceptions used throughout the application
for proper error handling and user feedback.
"""

from typing import Optional


class OpenEduMCPError(Exception):
    """Base exception for OpenEdu MCP Server."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ToolError(OpenEduMCPError):
    """Error in tool execution."""
    
    def __init__(self, message: str, tool_name: str, details: Optional[str] = None):
        super().__init__(message, details)
        self.tool_name = tool_name


class APIError(OpenEduMCPError):
    """Error in external API communication."""
    
    def __init__(
        self, 
        message: str, 
        api_name: str, 
        status_code: Optional[int] = None,
        details: Optional[str] = None
    ):
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code

    def __str__(self) -> str:
        base_msg = f"API Error ({self.api_name}): {self.message}"
        if self.status_code:
            base_msg += f" (Status: {self.status_code})"
        if self.details:
            base_msg += f" - {self.details}"
        return base_msg


class CacheError(OpenEduMCPError):
    """Error in cache operations."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[str] = None):
        super().__init__(message, details)
        self.operation = operation

    def __str__(self) -> str:
        base_msg = f"Cache Error: {self.message}"
        if self.operation:
            base_msg += f" (Operation: {self.operation})"
        if self.details:
            base_msg += f" - {self.details}"
        return base_msg


class RateLimitError(OpenEduMCPError):
    """Rate limit exceeded."""
    
    def __init__(
        self, 
        message: str, 
        api_name: str,
        retry_after: Optional[int] = None,
        details: Optional[str] = None
    ):
        super().__init__(message, details)
        self.api_name = api_name
        self.retry_after = retry_after

    def __str__(self) -> str:
        base_msg = f"Rate Limit Error ({self.api_name}): {self.message}"
        if self.retry_after:
            base_msg += f" (Retry after: {self.retry_after}s)"
        if self.details:
            base_msg += f" - {self.details}"
        return base_msg


class ValidationError(OpenEduMCPError):
    """Input validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[str] = None):
        super().__init__(message, details)
        self.field = field

    def __str__(self) -> str:
        base_msg = f"Validation Error: {self.message}"
        if self.field:
            base_msg += f" (Field: {self.field})"
        if self.details:
            base_msg += f" - {self.details}"
        return base_msg


class ConfigurationError(OpenEduMCPError):
    """Configuration error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[str] = None):
        super().__init__(message, details)
        self.config_key = config_key

    def __str__(self) -> str:
        base_msg = f"Configuration Error: {self.message}"
        if self.config_key:
            base_msg += f" (Key: {self.config_key})"
        if self.details:
            base_msg += f" - {self.details}"
        return base_msg


class DatabaseError(OpenEduMCPError):
    """Database operation error."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[str] = None):
        super().__init__(message, details)
        self.operation = operation

    def __str__(self) -> str:
        base_msg = f"Database Error: {self.message}"
        if self.operation:
            base_msg += f" (Operation: {self.operation})"
        if self.details:
            base_msg += f" - {self.details}"
        return base_msg


class NetworkError(OpenEduMCPError):
    """Network communication error."""
    
    def __init__(self, message: str, url: Optional[str] = None, details: Optional[str] = None):
        super().__init__(message, details)
        self.url = url

    def __str__(self) -> str:
        base_msg = f"Network Error: {self.message}"
        if self.url:
            base_msg += f" (URL: {self.url})"
        if self.details:
            base_msg += f" - {self.details}"
        return base_msg