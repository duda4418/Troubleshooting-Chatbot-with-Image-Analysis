from abc import ABC
from typing import TypeVar, Generic, Optional, List
from uuid import UUID
from sqlmodel import SQLModel, select, delete
from app.core.database import DatabaseProvider
import logging

T = TypeVar("T", bound=SQLModel)
logger = logging.getLogger(__name__)

class BaseRepository(Generic[T], ABC):
    """Base repository with common CRUD operations."""
    
    def __init__(self, db_provider: DatabaseProvider, model_class: type[T]):
        self.db_provider = db_provider
        self.model_class = model_class
    
    async def create(self, entity: T) -> T:
        """Create a new entity with debug output."""
        logger.debug(f"Creating entity: {entity}")
        async with self.db_provider.get_session() as session:
            session.add(entity)
            logger.debug(f"Added entity to session: {entity}")
            await session.commit()
            logger.debug(f"Commit successful for entity: {entity}")
            await session.refresh(entity)
            logger.debug(f"Refreshed entity: {entity}")
            return entity
    
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by ID with debug output."""
        logger.debug(f"Getting {self.model_class.__name__} by id: {entity_id}")
        async with self.db_provider.get_session() as session:
            result = await session.get(self.model_class, entity_id)
            logger.debug(f"Fetched entity: {result}")
            return result
        
    async def find_by_id(self, entity_id: UUID) -> Optional[T]:
        """Find entity by ID with debug output."""
        logger.debug(f"Finding {self.model_class.__name__} by id: {entity_id}")
        return await self.get_by_id(entity_id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination and debug output."""
        logger.debug(f"Getting all {self.model_class.__name__}s with limit={limit}, offset={offset}")
        async with self.db_provider.get_session() as session:
            stmt = select(self.model_class).limit(limit).offset(offset)
            result = await session.execute(stmt)
            entities = result.scalars().all()
            logger.debug(f"Found {len(entities)} entities")
            return entities

    async def find_all(self, limit: int = 100, offset: int = 0, **criteria) -> List[T]:
        """Find entities with optional filtering criteria, pagination and debug output."""
        if criteria:
            logger.debug(f"Finding {self.model_class.__name__} with criteria: {criteria}, limit={limit}, offset={offset}")
        else:
            logger.debug(f"Finding all {self.model_class.__name__}s with limit={limit}, offset={offset}")
        
        async with self.db_provider.get_session() as session:
            stmt = select(self.model_class)
            
            # Apply criteria filters if provided
            for field, value in criteria.items():
                if hasattr(self.model_class, field):
                    logger.debug(f"Adding filter {field}={value}")
                    stmt = stmt.where(getattr(self.model_class, field) == value)
                else:
                    logger.warning(f"Field {field} not found on model")
            
            # Apply pagination
            stmt = stmt.limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            entities = result.scalars().all()
            logger.debug(f"Found {len(entities)} entities")
            return entities

    async def update(self, entity: T) -> T:
        """Update an existing entity with debug output."""
        logger.debug(f"Updating entity: {entity}")
        async with self.db_provider.get_session() as session:
            try:
                session.add(entity)
                logger.debug(f"Added entity to session: {entity}")
                await session.commit()
                logger.debug(f"Commit successful for entity: {entity}")
                await session.refresh(entity)
                logger.debug(f"Refreshed entity: {entity}")
                return entity
            except Exception as e:
                logger.exception(f"Exception in update: {e}")
                raise
        
    async def update_by_id(self, entity_id: UUID, update_data: dict) -> T:
        """Update an entity by ID with debug output."""
        logger.debug(f"Updating {self.model_class.__name__} {entity_id} with data: {update_data}")
        async with self.db_provider.get_session() as session:
            try:
                existing = await session.get(self.model_class, entity_id)
                if not existing:
                    logger.warning(f"{self.model_class.__name__} not found for id: {entity_id}")
                    raise ValueError(f"{self.model_class.__name__} not found")
                
                logger.debug(f"Found existing: {existing}")
                
                for field, value in update_data.items():
                    if hasattr(existing, field):
                        logger.debug(f"Setting {field} = {value}")
                        setattr(existing, field, value)
                    else:
                        logger.warning(f"Field {field} not found on model")
                
                logger.debug(f"About to commit changes")
                await session.commit()
                logger.debug(f"Committed, refreshing...")
                await session.refresh(existing)
                logger.debug(f"Refreshed: {existing}")
                return existing
            except Exception as e:
                logger.exception(f"Exception in update_by_id: {e}")
                raise
        
    async def delete_by_id(self, entity_id: UUID) -> bool:
        """Delete entity by ID with debug output."""
        logger.debug(f"Deleting {self.model_class.__name__} by id: {entity_id}")
        async with self.db_provider.get_session() as session:
            stmt = delete(self.model_class).where(self.model_class.id == entity_id)
            result = await session.execute(stmt)
            await session.commit()
            logger.debug(f"Delete executed, rowcount={result.rowcount}")
            return result.rowcount > 0
    
    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists with debug output."""
        logger.debug(f"Checking existence of {self.model_class.__name__} with id: {entity_id}")
        async with self.db_provider.get_session() as session:
            result = await session.get(self.model_class, entity_id)
            exists = result is not None
            logger.debug(f"Exists: {exists}")
            return exists
    
    async def find_by_criteria(self, **criteria) -> List[T]:
        """Find entities by criteria (alias for find_all with criteria only)."""
        logger.debug(f"Finding {self.model_class.__name__} by criteria: {criteria}")
        return await self.find_all(**criteria)