import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)


def _ensure_asyncpg_scheme(raw_url: str) -> str:
    """Ensure the DSN uses the asyncpg dialect prefix."""
    stripped = raw_url.strip()
    if "://" not in stripped:
        return stripped

    prefix, rest = stripped.split("://", 1)
    lowered = prefix.lower()

    if lowered in {"postgresql+asyncpg"}:
        return stripped
    if lowered in {"postgres", "postgresql", "postgresql+psycopg2"}:
        return f"postgresql+asyncpg://{rest}"
    return stripped


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
        ensured = _ensure_asyncpg_scheme(env_url)
        logger.info("Using DATABASE_URL for engine: %s", _mask_db_url(ensured))
        return ensured

    user = os.environ.get("POSTGRES_USER") or os.environ.get("PGUSER") or "postgres"
    password = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("PGPASSWORD") or "change_me"
    database = os.environ.get("POSTGRES_DB") or os.environ.get("PGDATABASE") or "appdb"
    host = os.environ.get("POSTGRES_HOST") or os.environ.get("PGHOST") or "db"
    port = os.environ.get("POSTGRES_PORT") or os.environ.get("PGPORT") or "5432"

    base_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    logger.info("Using POSTGRES_* vars for engine: %s", _mask_db_url(base_url))
    return base_url


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
