"""Tool Cache - Caches computed tool results to avoid redundant computation."""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timedelta
import hashlib


@dataclass
class CacheEntry:
    """A cached tool computation result."""
    result: Any
    computed_at: datetime
    expires_at: datetime
    hit_count: int = 0


@dataclass
class ToolCache:
    """Cache for tool computation results.

    Key design:
    - Tool results are keyed by (tool_name, df_hash)
    - Cache entries expire after TTL
    - Hit count tracks usage for debugging
    """

    _cache: dict[str, CacheEntry] = field(default_factory=dict)
    _ttl_seconds: int = 300  # 5 minutes default

    def get(self, tool_name: str, df_hash: str) -> Optional[Any]:
        """Get cached result if exists and not expired.

        Args:
            tool_name: Name of the tool (e.g., "kdj")
            df_hash: Hash of the input DataFrame

        Returns:
            Cached result or None if not found/expired
        """
        key = self._make_key(tool_name, df_hash)
        entry = self._cache.get(key)

        if entry is None:
            return None

        if datetime.now() > entry.expires_at:
            # Expired, remove
            del self._cache[key]
            return None

        entry.hit_count += 1
        return entry.result

    def set(
        self, tool_name: str, df_hash: str, result: Any, ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache a tool computation result.

        Args:
            tool_name: Name of the tool
            df_hash: Hash of the input DataFrame
            result: The result to cache
            ttl_seconds: TTL in seconds (uses default if not specified)
        """
        now = datetime.now()
        key = self._make_key(tool_name, df_hash)
        self._cache[key] = CacheEntry(
            result=result,
            computed_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds or self._ttl_seconds),
        )

    def invalidate(self, tool_name: Optional[str] = None) -> None:
        """Invalidate cache entries.

        Args:
            tool_name: If specified, only invalidate entries for this tool.
                      If None, invalidate all entries.
        """
        if tool_name is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{tool_name}:")]
            for k in keys_to_remove:
                del self._cache[k]

    def stats(self) -> dict:
        """Get cache statistics."""
        total_hits = sum(e.hit_count for e in self._cache.values())
        return {
            "entries": len(self._cache),
            "total_hits": total_hits,
            "ttl_seconds": self._ttl_seconds,
        }

    @staticmethod
    def _make_key(tool_name: str, df_hash: str) -> str:
        """Create cache key from tool name and data hash."""
        return f"{tool_name}:{df_hash}"

    @staticmethod
    def hash_dataframe(df) -> str:
        """Create a hash of DataFrame content for cache keying.

        Uses only relevant columns and last N rows to create a stable hash.
        """
        import pandas as pd

        # Use only price-relevant columns
        relevant = df[["open", "high", "low", "close", "vol"]].tail(30)

        # Create hash from string representation
        content = relevant.to_csv()
        return hashlib.md5(content.encode()).hexdigest()[:16]
