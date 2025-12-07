"""
Cache module for request caching and response storage.
Supports both in-memory and Redis cache backends.
"""
import hashlib
import json
import time
from typing import Any, Optional, Dict, TYPE_CHECKING
import os
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import redis.asyncio as redis

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore


class CacheKey:
    """Generate cache keys from request parameters."""

    @staticmethod
    def generate_key(model: str, messages: list, max_tokens: Optional[int],
                     temperature: Optional[float], tools: Optional[list],
                     stream: bool, provider: str, session_id: Optional[str] = None) -> str:
        """
        Generate a unique cache key from request parameters.

        Args:
            model: Model name
            messages: List of messages
            max_tokens: Maximum tokens
            temperature: Temperature setting
            tools: Tools list
            stream: Whether streaming
            provider: Provider name
            session_id: Session ID for request isolation (optional)

        Returns:
            Cache key string
        """
        # Create a dictionary of relevant parameters
        cache_data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": tools,
            "stream": stream,
            "provider": provider,
            "session_id": session_id,
        }

        # Convert to JSON and hash
        cache_json = json.dumps(cache_data, sort_keys=True, separators=(',', ':'))
        cache_hash = hashlib.sha256(cache_json.encode('utf-8')).hexdigest()

        return f"cache:msg:{cache_hash}"


class MemoryCache:
    """In-memory cache implementation."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize memory cache.

        Args:
            max_size: Maximum number of cached items
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._access_times: Dict[str, float] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None

        item = self._cache[key]
        # Check if item has expired
        if time.time() > item["expires_at"]:
            await self.delete(key)
            return None

        # Update access time for LRU
        self._access_times[key] = time.time()
        return item["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl

        # Evict old items if cache is full (simple LRU)
        if len(self._cache) >= self._max_size:
            # Find least recently used item
            lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
            await self.delete(lru_key)

        self._cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
        self._access_times[key] = time.time()

    async def delete(self, key: str) -> None:
        """Delete item from cache."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache items."""
        self._cache.clear()
        self._access_times.clear()

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if key not in self._cache:
            return False
        if time.time() > self._cache[key]["expires_at"]:
            await self.delete(key)
            return False
        return True


class RedisCache:
    """Redis cache implementation."""

    def __init__(self, url: str, default_ttl: int = 3600, max_connections: int = 20):
        """
        Initialize Redis cache.

        Args:
            url: Redis connection URL
            default_ttl: Default time-to-live in seconds
            max_connections: Maximum connections in pool
        """
        self.url = url
        self._default_ttl = default_ttl
        self._redis: Optional[Any] = None
        self._max_connections = max_connections

    async def _get_redis(self):
        """Get Redis connection (singleton)."""
        if self._redis is None:
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis not available. Install with: pip install redis")
            self._redis = redis.from_url(
                self.url,
                max_connections=self._max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            redis_client = await self._get_redis()
            data = await redis_client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        try:
            ttl = ttl or self._default_ttl
            redis_client = await self._get_redis()
            await redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            # Log error but don't fail the request
            logger.warning(f"Cache set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete item from cache."""
        try:
            redis_client = await self._get_redis()
            await redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")

    async def clear(self) -> None:
        """Clear all cache items."""
        try:
            redis_client = await self._get_redis()
            await redis_client.flushdb()
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            redis_client = await self._get_redis()
            return await redis_client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists error: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


class MultiLevelCache:
    """Multi-level cache implementation (Memory + Redis)."""
    
    def __init__(self, memory_cache: MemoryCache, redis_cache: Optional[RedisCache] = None):
        """
        Initialize multi-level cache.
        
        Args:
            memory_cache: Memory cache instance (L1)
            redis_cache: Optional Redis cache instance (L2)
        """
        self.memory_cache = memory_cache
        self.redis_cache = redis_cache
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (check L1 first, then L2)."""
        # Try L1 (memory) first
        value = await self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try L2 (Redis) if available
        if self.redis_cache:
            value = await self.redis_cache.get(key)
            if value is not None:
                # Populate L1 cache for faster access next time
                await self.memory_cache.set(key, value)
                return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in both cache levels."""
        # Set in L1 (memory)
        await self.memory_cache.set(key, value, ttl)
        
        # Set in L2 (Redis) if available
        if self.redis_cache:
            await self.redis_cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> None:
        """Delete from both cache levels."""
        await self.memory_cache.delete(key)
        if self.redis_cache:
            await self.redis_cache.delete(key)
    
    async def clear(self) -> None:
        """Clear both cache levels."""
        await self.memory_cache.clear()
        if self.redis_cache:
            await self.redis_cache.clear()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in any cache level."""
        if await self.memory_cache.exists(key):
            return True
        if self.redis_cache:
            return await self.redis_cache.exists(key)
        return False
    
    async def close(self) -> None:
        """Close cache connections."""
        if self.redis_cache:
            await self.redis_cache.close()


class CacheManager:
    """Cache manager with configurable backend."""

    def __init__(self, cache_type: str = "memory", enable_multi_level: bool = False, **kwargs):
        """
        Initialize cache manager.

        Args:
            cache_type: Type of cache ("memory", "redis", or "multi")
            enable_multi_level: Enable multi-level cache (memory + redis)
            **kwargs: Additional cache configuration
        """
        self.cache_type = cache_type
        self.enable_multi_level = enable_multi_level or cache_type == "multi"
        self._cache = None
        self._kwargs = kwargs

    async def initialize(self) -> None:
        """Initialize the cache backend."""
        if self.enable_multi_level:
            # Multi-level cache: memory (L1) + redis (L2)
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis not available for multi-level cache. Install with: pip install redis")
            
            memory_config = {
                "max_size": int(os.getenv("CACHE_MAX_SIZE", "1000")),
                "default_ttl": int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
            }
            redis_config = {
                "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                "default_ttl": int(os.getenv("CACHE_DEFAULT_TTL", "3600")),
                "max_connections": int(os.getenv("CACHE_REDIS_MAX_CONN", "20"))
            }
            
            memory_cache = MemoryCache(**memory_config)
            redis_cache = RedisCache(**redis_config)
            self._cache = MultiLevelCache(memory_cache, redis_cache)
        elif self.cache_type == "redis":
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis not available. Install with: pip install redis")
            self._cache = RedisCache(**self._kwargs)
        else:
            # Default to memory cache
            self._cache = MemoryCache(**self._kwargs)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self._cache is None:
            await self.initialize()
        return await self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        if self._cache is None:
            await self.initialize()
        await self._cache.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        """Delete item from cache."""
        if self._cache is None:
            await self.initialize()
        await self._cache.delete(key)

    async def clear(self) -> None:
        """Clear all cache items."""
        if self._cache is None:
            await self.initialize()
        await self._cache.clear()

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if self._cache is None:
            await self.initialize()
        return await self._cache.exists(key)

    async def close(self) -> None:
        """Close cache connections."""
        if self._cache and hasattr(self._cache, "close"):
            await self._cache.close()


# Global cache instance
_cache_instance: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """
    Get or create a global cache manager instance.

    Configuration via environment variables:
    - CACHE_TYPE: "memory", "redis", or "multi" (default: "memory")
    - REDIS_URL: Redis connection URL (default: "redis://localhost:6379/0")
    - CACHE_DEFAULT_TTL: Default TTL in seconds (default: 3600)
    - CACHE_MAX_SIZE: Max memory cache size (default: 1000)
    - CACHE_REDIS_MAX_CONN: Max Redis connections (default: 20)
    """
    global _cache_instance
    if _cache_instance is not None:
        return _cache_instance
    
    cache_type = os.getenv("CACHE_TYPE", "memory")
    enable_multi_level = os.getenv("CACHE_MULTI_LEVEL", "false").lower() in ("true", "1", "yes")
    cache_config = {}

    if cache_type == "redis" or enable_multi_level:
        cache_config["url"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cache_config["default_ttl"] = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
        cache_config["max_connections"] = int(os.getenv("CACHE_REDIS_MAX_CONN", "20"))
    else:
        cache_config["max_size"] = int(os.getenv("CACHE_MAX_SIZE", "1000"))
        cache_config["default_ttl"] = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))

    _cache_instance = CacheManager(
        cache_type=cache_type,
        enable_multi_level=enable_multi_level,
        **cache_config
    )
    return _cache_instance


# Convenience functions
async def get_cached_response(cache_key: str) -> Optional[Any]:
    """Get cached response."""
    cache = get_cache_manager()
    return await cache.get(cache_key)


async def set_cached_response(cache_key: str, response: Any, ttl: Optional[int] = None) -> None:
    """Set cached response."""
    cache = get_cache_manager()
    await cache.set(cache_key, response, ttl)


async def close_cache() -> None:
    """Close cache connections."""
    cache = get_cache_manager()
    await cache.close()
