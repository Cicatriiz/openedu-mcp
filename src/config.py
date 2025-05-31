"""
Configuration management for OpenEdu MCP Server.

This module handles loading and managing configuration from various sources
including YAML files, environment variables, and defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class ServerConfig:
    """Server configuration settings."""
    name: str = "openedu-mcp-server"
    version: str = "1.0.0"
    host: str = "localhost"
    port: int = 8000
    log_level: str = "INFO"
    debug: bool = False


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    database_path: str = "~/.openedu-mcp/cache.db"
    default_ttl: int = 3600  # 1 hour
    max_size_mb: int = 100
    cleanup_interval: int = 3600
    enable_compression: bool = True


@dataclass
class APIConfig:
    """API configuration for external services."""
    base_url: str
    rate_limit: int
    timeout: int
    retry_attempts: int = 3
    backoff_factor: float = 2.0


@dataclass
class APIsConfig:
    """Configuration for all external APIs."""
    open_library: APIConfig = field(default_factory=lambda: APIConfig(
        base_url="https://openlibrary.org",
        rate_limit=100,
        timeout=30
    ))
    wikipedia: APIConfig = field(default_factory=lambda: APIConfig(
        base_url="https://en.wikipedia.org/api/rest_v1",
        rate_limit=200,
        timeout=30,
        retry_attempts=2
    ))
    dictionary: APIConfig = field(default_factory=lambda: APIConfig(
        base_url="https://api.dictionaryapi.dev/api/v2",
        rate_limit=450,
        timeout=15
    ))
    arxiv: APIConfig = field(default_factory=lambda: APIConfig(
        base_url="http://export.arxiv.org/api",
        rate_limit=3,
        timeout=60
    ))


@dataclass
class ContentFilters:
    """Content filtering configuration."""
    enable_age_appropriate: bool = True
    enable_curriculum_alignment: bool = True
    min_educational_relevance: float = 0.7


@dataclass
class EducationConfig:
    """Educational content configuration."""
    grade_levels: list = field(default_factory=lambda: [
        "K-2", "3-5", "6-8", "9-12", "College"
    ])
    curriculum_standards: list = field(default_factory=lambda: [
        "Common Core", "NGSS", "State Standards"
    ])
    subjects: list = field(default_factory=lambda: [
        "Mathematics", "Science", "English Language Arts",
        "Social Studies", "Arts", "Physical Education", "Technology"
    ])
    content_filters: ContentFilters = field(default_factory=ContentFilters)


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    file_path: str = "~/.openedu-mcp/logs/server.log"
    max_file_size_mb: int = 10
    backup_count: int = 5


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration."""
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 60


@dataclass
class Config:
    """Main configuration class."""
    server: ServerConfig = field(default_factory=ServerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    apis: APIsConfig = field(default_factory=APIsConfig)
    education: EducationConfig = field(default_factory=EducationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        return cls(
            server=ServerConfig(**data.get('server', {})),
            cache=CacheConfig(**data.get('cache', {})),
            apis=APIsConfig(
                open_library=APIConfig(**data.get('apis', {}).get('open_library', {})),
                wikipedia=APIConfig(**data.get('apis', {}).get('wikipedia', {})),
                dictionary=APIConfig(**data.get('apis', {}).get('dictionary', {})),
                arxiv=APIConfig(**data.get('apis', {}).get('arxiv', {}))
            ),
            education=EducationConfig(
                grade_levels=data.get('education', {}).get('grade_levels', []),
                curriculum_standards=data.get('education', {}).get('curriculum_standards', []),
                subjects=data.get('education', {}).get('subjects', []),
                content_filters=ContentFilters(**data.get('education', {}).get('content_filters', {}))
            ),
            logging=LoggingConfig(**data.get('logging', {})),
            monitoring=MonitoringConfig(**data.get('monitoring', {}))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'server': self.server.__dict__,
            'cache': self.cache.__dict__,
            'apis': {
                'open_library': self.apis.open_library.__dict__,
                'wikipedia': self.apis.wikipedia.__dict__,
                'dictionary': self.apis.dictionary.__dict__,
                'arxiv': self.apis.arxiv.__dict__
            },
            'education': {
                'grade_levels': self.education.grade_levels,
                'curriculum_standards': self.education.curriculum_standards,
                'subjects': self.education.subjects,
                'content_filters': self.education.content_filters.__dict__
            },
            'logging': self.logging.__dict__,
            'monitoring': self.monitoring.__dict__
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_path: Path to configuration file. If None, uses default locations.
        
    Returns:
        Loaded configuration object.
    """
    # Default configuration
    config_data = {}
    
    # Try to load from YAML file
    if config_path:
        config_file = Path(config_path)
    else:
        # Try default locations
        possible_paths = [
            Path("config/default.yaml"),
            Path("config/development.yaml"),
            Path(os.getenv("OPENEDU_MCP_CONFIG_PATH", "config/default.yaml"))
        ]
        config_file = None
        for path in possible_paths:
            if path.exists():
                config_file = path
                break
    
    if config_file and config_file.exists():
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f) or {}
    
    # Override with environment variables
    env_overrides = _get_env_overrides()
    config_data = _merge_configs(config_data, env_overrides)
    
    return Config.from_dict(config_data)


def _get_env_overrides() -> Dict[str, Any]:
    """Get configuration overrides from environment variables."""
    overrides = {}
    
    # Server overrides
    if os.getenv("OPENEDU_MCP_HOST"):
        overrides.setdefault("server", {})["host"] = os.getenv("OPENEDU_MCP_HOST")
    if os.getenv("OPENEDU_MCP_PORT"):
        overrides.setdefault("server", {})["port"] = int(os.getenv("OPENEDU_MCP_PORT"))
    if os.getenv("OPENEDU_MCP_LOG_LEVEL"):
        overrides.setdefault("server", {})["log_level"] = os.getenv("OPENEDU_MCP_LOG_LEVEL")
    if os.getenv("OPENEDU_MCP_DEBUG"):
        overrides.setdefault("server", {})["debug"] = os.getenv("OPENEDU_MCP_DEBUG").lower() == "true"
    
    # Cache overrides
    if os.getenv("OPENEDU_MCP_CACHE_PATH"):
        overrides.setdefault("cache", {})["database_path"] = os.getenv("OPENEDU_MCP_CACHE_PATH")
    if os.getenv("OPENEDU_MCP_CACHE_TTL"):
        overrides.setdefault("cache", {})["default_ttl"] = int(os.getenv("OPENEDU_MCP_CACHE_TTL"))
    if os.getenv("OPENEDU_MCP_CACHE_MAX_SIZE_MB"):
        overrides.setdefault("cache", {})["max_size_mb"] = int(os.getenv("OPENEDU_MCP_CACHE_MAX_SIZE_MB"))
    
    # API rate limit overrides
    if os.getenv("OPENEDU_MCP_OPEN_LIBRARY_RATE_LIMIT"):
        overrides.setdefault("apis", {}).setdefault("open_library", {})["rate_limit"] = int(os.getenv("OPENEDU_MCP_OPEN_LIBRARY_RATE_LIMIT"))
    if os.getenv("OPENEDU_MCP_WIKIPEDIA_RATE_LIMIT"):
        overrides.setdefault("apis", {}).setdefault("wikipedia", {})["rate_limit"] = int(os.getenv("OPENEDU_MCP_WIKIPEDIA_RATE_LIMIT"))
    
    return overrides


def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge configuration dictionaries."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result