import pytest
from unittest.mock import patch

from config import CacheConfig
from services.cache_service import CacheService
from exceptions import CacheError


@pytest.mark.asyncio
async def test_health_check_success(tmp_path):
    db_path = tmp_path / "cache.db"
    service = CacheService(CacheConfig(database_path=str(db_path)))
    assert await service.health_check() is True


@pytest.mark.asyncio
async def test_health_check_failure(tmp_path):
    db_path = tmp_path / "cache.db"
    service = CacheService(CacheConfig(database_path=str(db_path)))
    with patch("aiosqlite.connect", side_effect=Exception("db error")):
        with pytest.raises(CacheError):
            await service.health_check()
