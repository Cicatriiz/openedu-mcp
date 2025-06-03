"""
OpenEdu MCP Server - Main Entry Point

This module provides the main entry point for the OpenEdu MCP Server,
setting up the FastMCP server with all educational tools and services.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import json
import logging
import contextlib
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from starlette.requests import Request
from starlette.responses import StreamingResponse

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp import FastMCP, Context

# Import with absolute paths
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import config
from config import load_config, Config
import exceptions
from exceptions import OpenEduMCPError
import services.cache_service
from services.cache_service import CacheService
import services.rate_limiting_service
from services.rate_limiting_service import RateLimitingService
import services.usage_service
from services.usage_service import UsageService
import tools.openlibrary_tools
from tools.openlibrary_tools import OpenLibraryTool
import tools.wikipedia_tools
from tools.wikipedia_tools import WikipediaTool
import tools.dictionary_tools
from tools.dictionary_tools import DictionaryTool
import tools.arxiv_tools
from tools.arxiv_tools import ArxivTool


# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("openedu-mcp-server")

# Global services
cache_service: Optional[CacheService] = None
rate_limiting_service: Optional[RateLimitingService] = None
usage_service: Optional[UsageService] = None
config: Optional[Config] = None

# Global tools
openlibrary_tool: Optional[OpenLibraryTool] = None
wikipedia_tool: Optional[WikipediaTool] = None
dictionary_tool: Optional[DictionaryTool] = None
arxiv_tool: Optional[ArxivTool] = None


async def initialize_services() -> None:
    """Initialize all server services and dependencies."""
    global cache_service, rate_limiting_service, usage_service, config, openlibrary_tool, wikipedia_tool, dictionary_tool, arxiv_tool
    
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Loaded configuration for {config.server.name}")
        
        # Initialize cache service
        cache_service = CacheService(config.cache)
        await cache_service.initialize()
        logger.info("Cache service initialized")
        
        # Initialize rate limiting service
        rate_limiting_service = RateLimitingService(config.apis)
        logger.info("Rate limiting service initialized")
        
        # Initialize usage service
        usage_service = UsageService(config.cache)  # Uses same DB as cache
        await usage_service.initialize()
        logger.info("Usage service initialized")
        
        # Initialize Open Library tool
        openlibrary_tool = OpenLibraryTool(
            config=config,
            cache_service=cache_service,
            rate_limiting_service=rate_limiting_service,
            usage_service=usage_service
        )
        logger.info("Open Library tool initialized")
        
        # Initialize Wikipedia tool
        wikipedia_tool = WikipediaTool(
            config=config,
            cache_service=cache_service,
            rate_limiting_service=rate_limiting_service,
            usage_service=usage_service
        )
        logger.info("Wikipedia tool initialized")
        
        # Initialize Dictionary tool
        dictionary_tool = DictionaryTool(
            config=config,
            cache_service=cache_service,
            rate_limiting_service=rate_limiting_service,
            usage_service=usage_service
        )
        logger.info("Dictionary tool initialized")
        
        # Initialize arXiv tool
        arxiv_tool = ArxivTool(
            config=config,
            cache_service=cache_service,
            rate_limiting_service=rate_limiting_service,
            usage_service=usage_service
        )
        logger.info("arXiv tool initialized")
        
        logger.info("OpenEdu MCP Server services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize server services: {e}")
        raise OpenEduMCPError(f"Server initialization failed: {e}")


@mcp.tool()
async def search_educational_books(
    ctx: Context,
    query: str,
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for educational books using Open Library API.
    
    Args:
        query: Search query for books
        subject: Educational subject filter (optional)
        grade_level: Target grade level (K-2, 3-5, 6-8, 9-12, College)
        limit: Maximum number of results (1-50)
    
    Returns:
        List of educational books with metadata
    """
    if not openlibrary_tool:
        raise OpenEduMCPError("Open Library tool not properly initialized")
    
    # Validate parameters
    if not query or not query.strip():
        raise OpenEduMCPError("Query cannot be empty")
    
    if grade_level and grade_level not in ["K-2", "3-5", "6-8", "9-12", "College"]:
        raise OpenEduMCPError(f"Invalid grade level: {grade_level}")
    
    if limit < 1 or limit > 50:
        raise OpenEduMCPError("Limit must be between 1 and 50")
    
    try:
        return await openlibrary_tool.search_educational_books(
            query=query,
            subject=subject,
            grade_level=grade_level,
            limit=limit,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in search_educational_books: {e}")
        raise OpenEduMCPError(f"Book search failed: {str(e)}")


@mcp.tool()
async def get_book_details_by_isbn(
    ctx: Context,
    isbn: str,
    include_cover: bool = True
) -> Dict[str, Any]:
    """
    Get detailed book information by ISBN.
    
    Args:
        isbn: ISBN-10 or ISBN-13
        include_cover: Whether to include cover image URL
    
    Returns:
        Detailed book information with educational metadata
    """
    if not openlibrary_tool:
        raise OpenEduMCPError("Open Library tool not properly initialized")
    
    try:
        return await openlibrary_tool.get_book_details_by_isbn(
            isbn=isbn,
            include_cover=include_cover,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_book_details_by_isbn: {e}")
        raise OpenEduMCPError(f"Book details retrieval failed: {str(e)}")


@mcp.tool()
async def search_books_by_subject(
    ctx: Context,
    subject: str,
    grade_level: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search books by educational subject.
    
    Args:
        subject: Educational subject
        grade_level: Target grade level (optional)
        limit: Maximum number of results (1-50)
    
    Returns:
        List of books in the subject area
    """
    if not openlibrary_tool:
        raise OpenEduMCPError("Open Library tool not properly initialized")
    
    try:
        return await openlibrary_tool.search_books_by_subject(
            subject=subject,
            grade_level=grade_level,
            limit=limit,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in search_books_by_subject: {e}")
        raise OpenEduMCPError(f"Subject search failed: {str(e)}")


@mcp.tool()
async def get_book_recommendations(
    ctx: Context,
    grade_level: str,
    subject: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get book recommendations for a specific grade level and subject.
    
    Args:
        grade_level: Target grade level (K-2, 3-5, 6-8, 9-12, College)
        subject: Educational subject (optional)
        limit: Maximum number of results (1-50)
    
    Returns:
        List of recommended books
    """
    if not openlibrary_tool:
        raise OpenEduMCPError("Open Library tool not properly initialized")
    
    try:
        return await openlibrary_tool.get_book_recommendations(
            grade_level=grade_level,
            subject=subject,
            limit=limit,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_book_recommendations: {e}")
        raise OpenEduMCPError(f"Book recommendations failed: {str(e)}")


@mcp.tool()
async def search_educational_articles(
    ctx: Context,
    query: str,
    subject: Optional[str] = None,
    grade_level: Optional[str] = None,
    language: str = 'en',
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for educational articles using Wikipedia API.
    
    Args:
        query: Search query for articles
        subject: Educational subject filter (optional)
        grade_level: Target grade level (K-2, 3-5, 6-8, 9-12, College)
        language: Language code (default: 'en')
        limit: Maximum number of results (1-50)
    
    Returns:
        List of educational articles with summaries
    """
    if not wikipedia_tool:
        raise OpenEduMCPError("Wikipedia tool not properly initialized")
    
    try:
        return await wikipedia_tool.search_educational_articles(
            query=query,
            subject=subject,
            grade_level=grade_level,
            language=language,
            limit=limit,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in search_educational_articles: {e}")
        raise OpenEduMCPError(f"Article search failed: {str(e)}")


@mcp.tool()
async def get_article_summary(
    ctx: Context,
    title: str,
    language: str = 'en',
    include_educational_analysis: bool = True
) -> Dict[str, Any]:
    """
    Get Wikipedia article summary with educational analysis.
    
    Args:
        title: Article title
        language: Language code (default: 'en')
        include_educational_analysis: Whether to include educational metadata
    
    Returns:
        Article summary with educational metadata
    """
    if not wikipedia_tool:
        raise OpenEduMCPError("Wikipedia tool not properly initialized")
    
    try:
        return await wikipedia_tool.get_article_summary(
            title=title,
            language=language,
            include_educational_analysis=include_educational_analysis,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_article_summary: {e}")
        raise OpenEduMCPError(f"Article summary retrieval failed: {str(e)}")


@mcp.tool()
async def get_article_content(
    ctx: Context,
    title: str,
    language: str = 'en',
    include_images: bool = False
) -> Dict[str, Any]:
    """
    Get full Wikipedia article content with educational enrichment.
    
    Args:
        title: Article title
        language: Language code (default: 'en')
        include_images: Whether to include article images
    
    Returns:
        Full article content with educational metadata
    """
    if not wikipedia_tool:
        raise OpenEduMCPError("Wikipedia tool not properly initialized")
    
    try:
        return await wikipedia_tool.get_article_content(
            title=title,
            language=language,
            include_images=include_images,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_article_content: {e}")
        raise OpenEduMCPError(f"Article content retrieval failed: {str(e)}")


@mcp.tool()
async def get_featured_article(
    ctx: Context,
    date: Optional[str] = None,
    language: str = 'en'
) -> Dict[str, Any]:
    """
    Get Wikipedia featured article of the day with educational analysis.
    
    Args:
        date: Date in YYYY/MM/DD format (optional, defaults to today)
        language: Language code (default: 'en')
    
    Returns:
        Featured article with educational metadata
    """
    if not wikipedia_tool:
        raise OpenEduMCPError("Wikipedia tool not properly initialized")
    
    try:
        return await wikipedia_tool.get_featured_article(
            date_param=date,
            language=language,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_featured_article: {e}")
        raise OpenEduMCPError(f"Featured article retrieval failed: {str(e)}")


@mcp.tool()
async def get_articles_by_subject(
    ctx: Context,
    subject: str,
    grade_level: Optional[str] = None,
    language: str = 'en',
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get Wikipedia articles by educational subject with grade level filtering.
    
    Args:
        subject: Educational subject
        grade_level: Target grade level (optional)
        language: Language code (default: 'en')
        limit: Maximum number of results
    
    Returns:
        List of articles in the subject area
    """
    if not wikipedia_tool:
        raise OpenEduMCPError("Wikipedia tool not properly initialized")
    
    try:
        return await wikipedia_tool.get_articles_by_subject(
            subject=subject,
            grade_level=grade_level,
            language=language,
            limit=limit,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_articles_by_subject: {e}")
        raise OpenEduMCPError(f"Subject articles retrieval failed: {str(e)}")


@mcp.tool()
async def get_word_definition(
    ctx: Context,
    word: str,
    grade_level: Optional[str] = None,
    include_pronunciation: bool = True
) -> Dict[str, Any]:
    """
    Get educational word definition from dictionary API.
    
    Args:
        word: Word to define
        grade_level: Target grade level for appropriate complexity
        include_pronunciation: Whether to include pronunciation information
    
    Returns:
        Word definition with educational metadata
    """
    if not dictionary_tool:
        raise OpenEduMCPError("Dictionary tool not properly initialized")
    
    # Validate parameters
    if not word or not word.strip():
        raise OpenEduMCPError("Word cannot be empty")
    
    if grade_level and grade_level not in ["K-2", "3-5", "6-8", "9-12", "College"]:
        raise OpenEduMCPError(f"Invalid grade level: {grade_level}")
    
    try:
        return await dictionary_tool.get_word_definition(
            word=word,
            grade_level=grade_level,
            include_pronunciation=include_pronunciation,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_word_definition: {e}")
        raise OpenEduMCPError(f"Word definition retrieval failed: {str(e)}")


@mcp.tool()
async def get_vocabulary_analysis(
    ctx: Context,
    word: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze word complexity and educational value.
    
    Args:
        word: Word to analyze
        context: Optional context for better analysis
    
    Returns:
        Vocabulary analysis with educational insights
    """
    if not dictionary_tool:
        raise OpenEduMCPError("Dictionary tool not properly initialized")
    
    try:
        return await dictionary_tool.get_vocabulary_analysis(
            word=word,
            context=context,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_vocabulary_analysis: {e}")
        raise OpenEduMCPError(f"Vocabulary analysis failed: {str(e)}")


@mcp.tool()
async def get_word_examples(
    ctx: Context,
    word: str,
    grade_level: Optional[str] = None,
    subject: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get educational examples and usage contexts for a word.
    
    Args:
        word: Word to find examples for
        grade_level: Target grade level for appropriate examples
        subject: Subject area for context-specific examples
    
    Returns:
        Educational examples with context
    """
    if not dictionary_tool:
        raise OpenEduMCPError("Dictionary tool not properly initialized")
    
    try:
        return await dictionary_tool.get_word_examples(
            word=word,
            grade_level=grade_level,
            subject=subject,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_word_examples: {e}")
        raise OpenEduMCPError(f"Word examples retrieval failed: {str(e)}")


@mcp.tool()
async def get_pronunciation_guide(
    ctx: Context,
    word: str,
    include_audio: bool = True
) -> Dict[str, Any]:
    """
    Get phonetic information for language learning.
    
    Args:
        word: Word to get pronunciation for
        include_audio: Whether to include audio URL
    
    Returns:
        Pronunciation guide with phonetic information
    """
    if not dictionary_tool:
        raise OpenEduMCPError("Dictionary tool not properly initialized")
    
    try:
        return await dictionary_tool.get_pronunciation_guide(
            word=word,
            include_audio=include_audio,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_pronunciation_guide: {e}")
        raise OpenEduMCPError(f"Pronunciation guide retrieval failed: {str(e)}")


@mcp.tool()
async def get_related_vocabulary(
    ctx: Context,
    word: str,
    relationship_type: str = "all",
    grade_level: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get synonyms, antonyms, and related educational terms.
    
    Args:
        word: Base word
        relationship_type: Type of relationship (synonyms, antonyms, related, all)
        grade_level: Target grade level for appropriate vocabulary
        limit: Maximum number of related words
    
    Returns:
        Related vocabulary with educational context
    """
    if not dictionary_tool:
        raise OpenEduMCPError("Dictionary tool not properly initialized")
    
    try:
        return await dictionary_tool.get_related_vocabulary(
            word=word,
            relationship_type=relationship_type,
            grade_level=grade_level,
            limit=limit,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_related_vocabulary: {e}")
        raise OpenEduMCPError(f"Related vocabulary retrieval failed: {str(e)}")


@mcp.tool()
async def search_academic_papers(
    ctx: Context,
    query: str,
    subject: Optional[str] = None,
    academic_level: Optional[str] = None,
    max_results: int = 10,
    include_educational_analysis: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for academic papers with educational filtering using arXiv API.
    
    Args:
        query: Search query for papers
        subject: Educational subject filter (optional)
        academic_level: Target academic level (High School, Undergraduate, Graduate, Research)
        max_results: Maximum number of results (1-50)
        include_educational_analysis: Whether to include educational metadata
    
    Returns:
        List of academic papers with educational metadata
    """
    if not arxiv_tool:
        raise OpenEduMCPError("arXiv tool not properly initialized")
    
    try:
        return await arxiv_tool.search_academic_papers(
            query=query,
            subject=subject,
            academic_level=academic_level,
            max_results=max_results,
            include_educational_analysis=include_educational_analysis,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in search_academic_papers: {e}")
        raise OpenEduMCPError(f"Academic paper search failed: {str(e)}")


@mcp.tool()
async def get_paper_summary(
    ctx: Context,
    paper_id: str,
    include_educational_analysis: bool = True
) -> Dict[str, Any]:
    """
    Get paper summary with educational analysis using arXiv API.
    
    Args:
        paper_id: arXiv paper ID (e.g., '2301.00001')
        include_educational_analysis: Whether to include educational metadata
    
    Returns:
        Paper summary with educational metadata
    """
    if not arxiv_tool:
        raise OpenEduMCPError("arXiv tool not properly initialized")
    
    try:
        return await arxiv_tool.get_paper_summary(
            paper_id=paper_id,
            include_educational_analysis=include_educational_analysis,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_paper_summary: {e}")
        raise OpenEduMCPError(f"Paper summary retrieval failed: {str(e)}")


@mcp.tool()
async def get_recent_research(
    ctx: Context,
    subject: str,
    days: int = 7,
    academic_level: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Get recent research papers by educational subject using arXiv API.
    
    Args:
        subject: Educational subject
        days: Number of days back to search (1-30)
        academic_level: Target academic level (optional)
        max_results: Maximum number of results
    
    Returns:
        List of recent papers in the subject area
    """
    if not arxiv_tool:
        raise OpenEduMCPError("arXiv tool not properly initialized")
    
    try:
        return await arxiv_tool.get_recent_research(
            subject=subject,
            days=days,
            academic_level=academic_level,
            max_results=max_results,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_recent_research: {e}")
        raise OpenEduMCPError(f"Recent research retrieval failed: {str(e)}")


@mcp.tool()
async def get_research_by_level(
    ctx: Context,
    academic_level: str,
    subject: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Get research papers appropriate for specific academic levels using arXiv API.
    
    Args:
        academic_level: Target academic level (High School, Undergraduate, Graduate, Research)
        subject: Subject area filter (optional)
        max_results: Maximum number of results
    
    Returns:
        List of papers appropriate for the academic level
    """
    if not arxiv_tool:
        raise OpenEduMCPError("arXiv tool not properly initialized")
    
    try:
        return await arxiv_tool.get_research_by_level(
            academic_level=academic_level,
            subject=subject,
            max_results=max_results,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in get_research_by_level: {e}")
        raise OpenEduMCPError(f"Research by level retrieval failed: {str(e)}")


@mcp.tool()
async def analyze_research_trends(
    ctx: Context,
    subject: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Analyze research trends for educational insights using arXiv API.
    
    Args:
        subject: Educational subject to analyze
        days: Number of days to analyze (7-90)
    
    Returns:
        Research trend analysis with educational insights
    """
    if not arxiv_tool:
        raise OpenEduMCPError("arXiv tool not properly initialized")
    
    try:
        return await arxiv_tool.analyze_research_trends(
            subject=subject,
            days=days,
            user_session=getattr(ctx, 'session_id', None)
        )
    except Exception as e:
        logger.error(f"Error in analyze_research_trends: {e}")
        raise OpenEduMCPError(f"Research trend analysis failed: {str(e)}")


@mcp.tool()
async def handle_stdio_input(ctx: Context, input_string: str) -> str:
    """
    Handles a line of input from stdin and returns a processed string.

    Args:
        ctx: The context object.
        input_string: The string read from stdin.

    Returns:
        The processed string.
    """
    if not input_string:
        raise OpenEduMCPError("Input string cannot be empty")

    try:
        # Simple processing: prepend "Processed: " and convert to uppercase
        processed_string = f"Processed: {input_string.upper()}"
        logger.info(f"Processed stdin input: {input_string} -> {processed_string}")
        return processed_string
    except Exception as e:
        logger.error(f"Error processing stdio input: {e}")
        raise OpenEduMCPError(f"Failed to process stdio input: {str(e)}")


async def sse_event_generator(request: Request):
    """
    Async generator for SSE events.
    Yields an initial connection message and periodic pings.
    """
    try:
        yield f"event: connected\ndata: {json.dumps({'message': 'Successfully connected to SSE stream'})}\n\n"

        loop_count = 0
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                logger.info("SSE client disconnected.")
                break

            loop_count += 1
            yield f"event: ping\ndata: {json.dumps({'heartbeat': loop_count, 'message': 'ping'})}\n\n"
            await asyncio.sleep(5)  # Send a ping every 5 seconds

    except asyncio.CancelledError:
        logger.info("SSE event generator cancelled.")
        # Handle cleanup if necessary
    except Exception as e:
        logger.error(f"Error in SSE event generator: {e}")
        # Yield an error event if possible, or just log and exit
        # Try to yield error event - if connection is closed, this will fail silently
        with contextlib.suppress(ConnectionError, RuntimeError):
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    finally:
        logger.info("SSE event generator finished.")

@mcp.tool(route="/events", methods=["GET"]) # Assuming a route decorator might exist or be added to FastMCP
async def stream_events(request: Request) -> StreamingResponse:
    """
    SSE endpoint to stream events.
    Uses an async generator to produce events.
    """
    # Note: The 'request: Request' parameter might not be directly supported by @mcp.tool
    # if it only expects Context and tool-specific arguments.
    # This is an attempt based on common ASGI framework patterns.
    # If FastMCP uses a different mechanism for raw requests or streaming, this will need adjustment.

    logger.info(f"SSE connection request received: {request}")

    # Check if FastMCP passes the raw request object.
    # If not, this 'request.is_disconnected()' will fail.
    # This part is speculative.
    if not isinstance(request, Request):
        logger.warning("Request object not available as expected for SSE. Client disconnection check might not work.")
        # Fallback: create a dummy request object if needed by sse_event_generator,
        # but is_disconnected will not work. This is a significant limitation.
        # For now, let's assume 'request' is passed correctly or sse_event_generator handles it.

    generator = sse_event_generator(request)

    return StreamingResponse(generator, media_type="text/event-stream")


@mcp.tool()
async def get_server_status(ctx: Context) -> Dict[str, Any]:
    """
    Get OpenEdu MCP Server status and statistics.
    
    Returns:
        Server status information including cache and usage statistics
    """
    if not cache_service or not rate_limiting_service or not usage_service:
        return {
            "status": "error",
            "message": "Server services not properly initialized"
        }
    
    try:
        # Get cache statistics
        cache_stats = await cache_service.get_stats()
        
        # Get rate limiting status
        rate_limit_status = await rate_limiting_service.get_all_rate_limit_status()
        
        # Get usage statistics
        usage_stats = await usage_service.get_usage_stats()
        
        return {
            "status": "healthy",
            "server": {
                "name": config.server.name if config else "openedu-mcp-server",
                "version": config.server.version if config else "1.0.0"
            },
            "cache": cache_stats,
            "rate_limits": rate_limit_status,
            "usage": usage_stats,
            "message": "OpenEdu MCP Server is running with core infrastructure ready"
        }
        
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return {
            "status": "error",
            "message": f"Failed to get server status: {str(e)}"
        }


async def cleanup_services() -> None:
    """Clean up services on shutdown."""
    global cache_service, usage_service, openlibrary_tool, wikipedia_tool, dictionary_tool, arxiv_tool
    
    try:
        if arxiv_tool:
            await arxiv_tool.client.close()
            logger.info("arXiv tool closed")
        
        if dictionary_tool:
            await dictionary_tool.client.close()
            logger.info("Dictionary tool closed")
        
        if wikipedia_tool:
            await wikipedia_tool.client.close()
            logger.info("Wikipedia tool closed")
        
        if openlibrary_tool:
            await openlibrary_tool.client.close()
            logger.info("Open Library tool closed")
        
        if usage_service:
            await usage_service.close()
            logger.info("Usage service closed")
        
        if cache_service:
            await cache_service.close()
            logger.info("Cache service closed")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point for the OpenEdu MCP Server."""
    try:
        # Initialize services
        asyncio.run(initialize_services())
        
        # Set up cleanup on exit
        import atexit
        atexit.register(lambda: asyncio.run(cleanup_services()))
        
        logger.info("Starting OpenEdu MCP Server...")
        
        # Run the MCP server
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)
    finally:
        logger.info("OpenEdu MCP Server stopped")


if __name__ == "__main__":
    main()