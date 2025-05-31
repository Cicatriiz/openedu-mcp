"""
Usage tracking service for OpenEdu MCP Server.

This module provides usage analytics and tracking functionality
to monitor tool usage, performance, and user patterns.
"""

import asyncio
import aiosqlite
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CacheConfig
from exceptions import DatabaseError


logger = logging.getLogger(__name__)


@dataclass
class UsageEvent:
    """Represents a usage event."""
    tool_name: str
    method_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: Optional[int] = None
    cache_hit: bool = False
    error_occurred: bool = False
    user_session: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result_count: Optional[int] = None


class UsageService:
    """Service for tracking and analyzing usage patterns."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.db_path = Path(config.database_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the usage tracking database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS usage_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tool_name TEXT NOT NULL,
                        method_name TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_time_ms INTEGER,
                        cache_hit BOOLEAN DEFAULT FALSE,
                        error_occurred BOOLEAN DEFAULT FALSE,
                        user_session TEXT,
                        parameters TEXT,
                        result_count INTEGER
                    )
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tool_method 
                    ON usage_stats(tool_name, method_name)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON usage_stats(timestamp)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_session 
                    ON usage_stats(user_session)
                """)
                
                await db.commit()
            
            self._initialized = True
            
            # Start background processing task
            self._processing_task = asyncio.create_task(self._process_events())
            
            logger.info("Usage service initialized")
            
        except Exception as e:
            raise DatabaseError(f"Failed to initialize usage database", "initialize", str(e))
    
    async def record_usage(self, event: UsageEvent) -> None:
        """
        Record a usage event.
        
        Args:
            event: Usage event to record
        """
        if not self._initialized:
            await self.initialize()
        
        # Add to queue for background processing
        await self._event_queue.put(event)
    
    async def record_tool_usage(
        self,
        tool_name: str,
        method_name: str,
        execution_time_ms: Optional[int] = None,
        cache_hit: bool = False,
        error_occurred: bool = False,
        user_session: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result_count: Optional[int] = None
    ) -> None:
        """
        Record tool usage with parameters.
        
        Args:
            tool_name: Name of the tool used
            method_name: Name of the method called
            execution_time_ms: Execution time in milliseconds
            cache_hit: Whether the result came from cache
            error_occurred: Whether an error occurred
            user_session: User session identifier
            parameters: Parameters passed to the method
            result_count: Number of results returned
        """
        event = UsageEvent(
            tool_name=tool_name,
            method_name=method_name,
            execution_time_ms=execution_time_ms,
            cache_hit=cache_hit,
            error_occurred=error_occurred,
            user_session=user_session,
            parameters=parameters,
            result_count=result_count
        )
        
        await self.record_usage(event)
    
    async def get_usage_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a time period.
        
        Args:
            start_date: Start date for statistics (default: 24 hours ago)
            end_date: End date for statistics (default: now)
            tool_name: Filter by specific tool name
            
        Returns:
            Dictionary with usage statistics
        """
        if not self._initialized:
            await self.initialize()
        
        if start_date is None:
            start_date = datetime.now() - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.now()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Base query conditions
                conditions = ["timestamp BETWEEN ? AND ?"]
                params = [start_date, end_date]
                
                if tool_name:
                    conditions.append("tool_name = ?")
                    params.append(tool_name)
                
                where_clause = " AND ".join(conditions)
                
                # Total requests
                cursor = await db.execute(
                    f"SELECT COUNT(*) FROM usage_stats WHERE {where_clause}",
                    params
                )
                total_requests = (await cursor.fetchone())[0]
                
                # Successful requests
                cursor = await db.execute(
                    f"SELECT COUNT(*) FROM usage_stats WHERE {where_clause} AND error_occurred = FALSE",
                    params
                )
                successful_requests = (await cursor.fetchone())[0]
                
                # Cache hits
                cursor = await db.execute(
                    f"SELECT COUNT(*) FROM usage_stats WHERE {where_clause} AND cache_hit = TRUE",
                    params
                )
                cache_hits = (await cursor.fetchone())[0]
                
                # Average execution time
                cursor = await db.execute(
                    f"""SELECT AVG(execution_time_ms) FROM usage_stats 
                        WHERE {where_clause} AND execution_time_ms IS NOT NULL""",
                    params
                )
                avg_execution_time = (await cursor.fetchone())[0] or 0
                
                # Most used tools
                cursor = await db.execute(
                    f"""SELECT tool_name, method_name, COUNT(*) as usage_count
                        FROM usage_stats WHERE {where_clause}
                        GROUP BY tool_name, method_name
                        ORDER BY usage_count DESC
                        LIMIT 10""",
                    params
                )
                most_used = await cursor.fetchall()
                
                # Usage by hour
                cursor = await db.execute(
                    f"""SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                        FROM usage_stats WHERE {where_clause}
                        GROUP BY hour
                        ORDER BY hour""",
                    params
                )
                hourly_usage = await cursor.fetchall()
                
                return {
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "error_rate": (
                        (total_requests - successful_requests) / max(total_requests, 1)
                    ) * 100,
                    "cache_hits": cache_hits,
                    "cache_hit_rate": (cache_hits / max(total_requests, 1)) * 100,
                    "average_execution_time_ms": round(avg_execution_time, 2),
                    "most_used_tools": [
                        {
                            "tool": tool,
                            "method": method,
                            "count": count
                        }
                        for tool, method, count in most_used
                    ],
                    "hourly_usage": [
                        {"hour": int(hour), "count": count}
                        for hour, count in hourly_usage
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            raise DatabaseError("Failed to get usage statistics", "get_usage_stats", str(e))
    
    async def get_tool_performance(self, tool_name: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary with performance metrics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Method performance
                cursor = await db.execute("""
                    SELECT 
                        method_name,
                        COUNT(*) as call_count,
                        AVG(execution_time_ms) as avg_time,
                        MIN(execution_time_ms) as min_time,
                        MAX(execution_time_ms) as max_time,
                        SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) as error_count,
                        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hit_count
                    FROM usage_stats 
                    WHERE tool_name = ? AND execution_time_ms IS NOT NULL
                    GROUP BY method_name
                    ORDER BY call_count DESC
                """, (tool_name,))
                
                methods = await cursor.fetchall()
                
                method_stats = []
                for row in methods:
                    method, calls, avg_time, min_time, max_time, errors, cache_hits = row
                    method_stats.append({
                        "method": method,
                        "call_count": calls,
                        "average_time_ms": round(avg_time or 0, 2),
                        "min_time_ms": min_time or 0,
                        "max_time_ms": max_time or 0,
                        "error_rate": (errors / max(calls, 1)) * 100,
                        "cache_hit_rate": (cache_hits / max(calls, 1)) * 100
                    })
                
                return {
                    "tool_name": tool_name,
                    "method_performance": method_stats
                }
                
        except Exception as e:
            logger.error(f"Error getting tool performance for {tool_name}: {e}")
            raise DatabaseError(f"Failed to get performance for tool: {tool_name}", "get_tool_performance", str(e))
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clean up old usage data.
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            Number of records deleted
        """
        if not self._initialized:
            await self.initialize()
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM usage_stats WHERE timestamp < ?",
                    (cutoff_date,)
                )
                await db.commit()
                
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old usage records")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old usage data: {e}")
            raise DatabaseError("Failed to cleanup old usage data", "cleanup_old_data", str(e))
    
    async def _process_events(self) -> None:
        """Background task to process usage events."""
        while True:
            try:
                # Process events in batches
                events = []
                
                # Collect events for up to 1 second or until we have 100 events
                deadline = asyncio.get_event_loop().time() + 1.0
                
                while len(events) < 100 and asyncio.get_event_loop().time() < deadline:
                    try:
                        event = await asyncio.wait_for(
                            self._event_queue.get(),
                            timeout=deadline - asyncio.get_event_loop().time()
                        )
                        events.append(event)
                    except asyncio.TimeoutError:
                        break
                
                if events:
                    await self._batch_insert_events(events)
                
            except Exception as e:
                logger.error(f"Error processing usage events: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _batch_insert_events(self, events: List[UsageEvent]) -> None:
        """Insert multiple events in a single transaction."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                data = []
                for event in events:
                    parameters_json = None
                    if event.parameters:
                        import json
                        parameters_json = json.dumps(event.parameters)
                    
                    data.append((
                        event.tool_name,
                        event.method_name,
                        event.timestamp,
                        event.execution_time_ms,
                        event.cache_hit,
                        event.error_occurred,
                        event.user_session,
                        parameters_json,
                        event.result_count
                    ))
                
                await db.executemany("""
                    INSERT INTO usage_stats 
                    (tool_name, method_name, timestamp, execution_time_ms, 
                     cache_hit, error_occurred, user_session, parameters, result_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error batch inserting usage events: {e}")
    
    async def close(self) -> None:
        """Close the usage service."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining events
        remaining_events = []
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                remaining_events.append(event)
            except asyncio.QueueEmpty:
                break
        
        if remaining_events:
            await self._batch_insert_events(remaining_events)
        
        self._initialized = False
        logger.info("Usage service closed")