import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager


def build_async_db_url() -> str:
    """Build async database URL from environment variables."""
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "change_me")
    database = os.environ.get("POSTGRES_DB", "appdb")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


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
