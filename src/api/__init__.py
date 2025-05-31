"""
API clients for OpenEdu MCP Server.

This module contains API client implementations for various educational
data sources including Open Library, Wikipedia, Dictionary API, and arXiv.
"""

from .openlibrary import OpenLibraryClient

__all__ = ['OpenLibraryClient']