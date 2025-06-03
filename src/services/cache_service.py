"""
Cache service for OpenEdu MCP Server.

This module provides SQLite-based caching with TTL support for API responses
and other data that needs to be cached for performance.
"""

import json
import sqlite3
import asyncio
import aiosqlite
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import asdict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CacheConfig
from exceptions import CacheError, DatabaseError


logger = logging.getLogger(__name__)


class CacheService:
    """SQLite-based cache service with TTL support."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.db_path = Path(config.database_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the cache database and create tables."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value BLOB NOT NULL,
                        content_type TEXT DEFAULT 'json',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        size_bytes INTEGER DEFAULT 0
                    )
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at 
                    ON cache_entries(expires_at)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_last_accessed 
                    ON cache_entries(last_accessed)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_content_type 
                    ON cache_entries(content_type)
                """)
                
                await db.commit()
                
            self._initialized = True
            logger.info(f"Cache service initialized with database: {self.db_path}")
            
            # Start cleanup task
            asyncio.create_task(self._cleanup_loop())
            
        except Exception as e:
            raise CacheError(f"Failed to initialize cache database", "initialize", str(e))
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT value, content_type, expires_at, access_count
                    FROM cache_entries 
                    WHERE key = ? AND expires_at > ?
                """, (key, datetime.now()))
                
                row = await cursor.fetchone()
                if not row:
                    return None
                
                value_blob, content_type, expires_at, access_count = row
                
                # Update access statistics
                await db.execute("""
                    UPDATE cache_entries 
                    SET access_count = ?, last_accessed = ?
                    WHERE key = ?
                """, (access_count + 1, datetime.now(), key))
                
                await db.commit()
                
                # Deserialize value
                if content_type == "json":
                    return json.loads(value_blob.decode('utf-8'))
                else:
                    return value_blob
                    
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            raise CacheError(f"Failed to get cache key: {key}", "get", str(e))
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        content_type: str = "json"
    ) -> None:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            content_type: Content type for the cached value
        """
        if not self._initialized:
            await self.initialize()
            
        if ttl is None:
            ttl = self.config.default_ttl
            
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        try:
            # Serialize value
            if content_type == "json":
                value_blob = json.dumps(value).encode('utf-8')
            else:
                value_blob = value if isinstance(value, bytes) else str(value).encode('utf-8')
            
            size_bytes = len(value_blob)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, content_type, expires_at, size_bytes, created_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    key, value_blob, content_type, expires_at, size_bytes,
                    datetime.now(), datetime.now()
                ))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            raise CacheError(f"Failed to set cache key: {key}", "set", str(e))
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                await db.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            raise CacheError(f"Failed to delete cache key: {key}", "delete", str(e))
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM cache_entries")
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise CacheError("Failed to clear cache", "clear", str(e))
    
    async def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM cache_entries WHERE expires_at <= ?",
                    (datetime.now(),)
                )
                await db.commit()
                
                removed_count = cursor.rowcount
                if removed_count > 0:
                    logger.info(f"Cleaned up {removed_count} expired cache entries")
                
                return removed_count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired cache entries: {e}")
            raise CacheError("Failed to cleanup expired entries", "cleanup_expired", str(e))
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Total entries
                cursor = await db.execute("SELECT COUNT(*) FROM cache_entries")
                total_entries = (await cursor.fetchone())[0]
                
                # Expired entries
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM cache_entries WHERE expires_at <= ?",
                    (datetime.now(),)
                )
                expired_entries = (await cursor.fetchone())[0]
                
                # Total size
                cursor = await db.execute("SELECT SUM(size_bytes) FROM cache_entries")
                total_size = (await cursor.fetchone())[0] or 0
                
                # Most accessed entries
                cursor = await db.execute("""
                    SELECT key, access_count 
                    FROM cache_entries 
                    ORDER BY access_count DESC 
                    LIMIT 10
                """)
                most_accessed = await cursor.fetchall()
                
                return {
                    "total_entries": total_entries,
                    "active_entries": total_entries - expired_entries,
                    "expired_entries": expired_entries,
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "most_accessed": [{"key": key, "count": count} for key, count in most_accessed],
                    "hit_ratio": await self._calculate_hit_ratio()
                }
                
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            raise CacheError("Failed to get cache statistics", "get_stats", str(e))
    
    async def _calculate_hit_ratio(self) -> float:
        """Calculate cache hit ratio (simplified)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT AVG(access_count) FROM cache_entries")
                avg_access = (await cursor.fetchone())[0] or 0
                
                # Simple heuristic: if average access > 1, we have some hits
                return min(avg_access / 10.0, 1.0)  # Cap at 1.0
                
        except Exception:
            return 0.0
    
    async def _cleanup_loop(self) -> None:
        """Background task to periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self.cleanup_expired()
                
                # Check cache size and clean up if needed
                stats = await self.get_stats()
                if stats["total_size_mb"] > self.config.max_size_mb:
                    await self._cleanup_by_size()
                    
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
    
    async def _cleanup_by_size(self) -> None:
        """Clean up cache entries to reduce size."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Remove least recently accessed entries
                await db.execute("""
                    DELETE FROM cache_entries 
                    WHERE key IN (
                        SELECT key FROM cache_entries 
                        ORDER BY last_accessed ASC 
                        LIMIT (SELECT COUNT(*) / 4 FROM cache_entries)
                    )
                """)
                await db.commit()
                
                logger.info("Cleaned up cache entries to reduce size")
                
        except Exception as e:
            logger.error(f"Error cleaning up cache by size: {e}")

    async def health_check(self) -> bool:
        """Verify that the cache database is reachable."""
        if not self._initialized:
            await self.initialize()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("Cache service health check failed: %s", e)
            raise CacheError(
                "Cache health check failed",
                "health_check",
                str(e),
            ) from e

    async def close(self) -> None:
        """Close the cache service."""
        # Note: aiosqlite connections are closed automatically
        self._initialized = False
        logger.info("Cache service closed")
