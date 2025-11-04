import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)


def _normalize_asyncpg_url(raw_url: str) -> str:
    """Ensure the URL works with asyncpg by adjusting scheme and ssl params."""
    stripped = raw_url.strip()
    parts = urlsplit(stripped)

    scheme = parts.scheme
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"
    elif scheme == "postgresql+psycopg2":
        scheme = "postgresql+asyncpg"

    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    normalized_pairs = []
    ssl_present = False
    sslmode_value = None

    for key, value in query_pairs:
        lowered = key.lower()
        if lowered == "sslmode":
            sslmode_value = value
            continue
        if lowered == "ssl":
            ssl_present = True
        normalized_pairs.append((key, value))

    if sslmode_value is not None and not ssl_present:
        mode = (sslmode_value or "").lower()
        normalized_pairs.append(("ssl", "false" if mode in {"disable", "off"} else "true"))

    normalized_query = urlencode(normalized_pairs, doseq=True)
    normalized_url = urlunsplit((scheme, parts.netloc, parts.path, normalized_query, parts.fragment))

    # Guard against leaking sslmode through inadvertently
    if "sslmode=" in normalized_url.lower():  # pragma: no cover - defensive check
        raise ValueError("Normalized asyncpg URL must not include sslmode query parameter")

    return normalized_url


def _mask_db_url(url: str) -> str:
    try:
        scheme, rest = url.split("://", 1)
        user_info, host_part = rest.split("@", 1)
        user, _pwd = user_info.split(":", 1)
        return f"{scheme}://{user}:***@{host_part}"
    except Exception:
        return url


def build_async_db_url() -> str:
    """Build async database URL from environment variables."""
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        normalized = _normalize_asyncpg_url(env_url)
        logger.info("Using DATABASE_URL for engine: %s", _mask_db_url(normalized))
        return normalized

    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "change_me")
    database = os.environ.get("POSTGRES_DB", "appdb")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    query = os.environ.get("POSTGRES_QUERY", "").lstrip("?")

    base_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    if query:
        base_url = f"{base_url}?{query}"

    normalized = _normalize_asyncpg_url(base_url)
    logger.info("Using POSTGRES_* vars for engine: %s", _mask_db_url(normalized))
    return normalized


class DatabaseProvider:
    """Async database provider for PostgreSQL."""
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    def get_engine(self) -> AsyncEngine:
        """Get or create async database engine."""
        if self._engine is None:
            db_url = build_async_db_url()
            self._engine = create_async_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
        return self._engine
    
    def get_session_factory(self) -> sessionmaker:
        """Get or create async session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._session_factory
    
    @asynccontextmanager
    async def get_session(self):
        """Get async database session with context management."""
        session_factory = self.get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close database engine."""
        if self._engine:
            await self._engine.dispose()


# Global database provider instance
_db_provider: Optional[DatabaseProvider] = None


def get_db_provider() -> DatabaseProvider:
    """Get global database provider instance."""
    global _db_provider
    if _db_provider is None:
        _db_provider = DatabaseProvider()
    return _db_provider
