from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_database_provider
from app.core.database import DatabaseProvider
from app.data.repositories import (
    ProblemCategoryRepository,
    ProblemCauseRepository,
    ProblemSolutionRepository,
)
from app.data.schemas.models import ProblemCategory, ProblemCause, ProblemSolution

router = APIRouter(prefix="/catalogue", tags=["catalogue"])


# ==================== DTOs ====================


class ProblemCategoryCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None


class ProblemCategoryUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=1, max_length=64)
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None


class ProblemCategoryRead(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ProblemCauseCreate(BaseModel):
    category_id: UUID
    slug: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    detection_hints: List[str] = Field(default_factory=list)
    default_priority: int = Field(default=0)


class ProblemCauseUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=1, max_length=64)
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    detection_hints: Optional[List[str]] = None
    default_priority: Optional[int] = None


class ProblemCauseRead(BaseModel):
    id: UUID
    category_id: UUID
    slug: str
    name: str
    description: Optional[str] = None
    detection_hints: List[str]
    default_priority: int

    class Config:
        from_attributes = True


class ProblemSolutionCreate(BaseModel):
    cause_id: UUID
    slug: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=160)
    summary: Optional[str] = None
    instructions: str = Field(..., min_length=1)
    step_order: int = Field(default=0)
    requires_escalation: bool = Field(default=False)


class ProblemSolutionUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=1, max_length=64)
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    summary: Optional[str] = None
    instructions: Optional[str] = Field(None, min_length=1)
    step_order: Optional[int] = None
    requires_escalation: Optional[bool] = None


class ProblemSolutionRead(BaseModel):
    id: UUID
    cause_id: UUID
    slug: str
    title: str
    summary: Optional[str] = None
    instructions: str
    step_order: int
    requires_escalation: bool

    class Config:
        from_attributes = True


# ==================== Problem Categories ====================


@router.get("/categories", response_model=List[ProblemCategoryRead])
async def list_categories(
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> List[ProblemCategoryRead]:
    """List all problem categories."""
    repo = ProblemCategoryRepository(db_provider)
    categories = await repo.find_all(limit=500)
    return [ProblemCategoryRead.model_validate(cat) for cat in categories]


@router.get("/categories/{category_id}", response_model=ProblemCategoryRead)
async def get_category(
    category_id: UUID,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemCategoryRead:
    """Get a specific problem category by ID."""
    repo = ProblemCategoryRepository(db_provider)
    category = await repo.find_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return ProblemCategoryRead.model_validate(category)


@router.post("/categories", response_model=ProblemCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: ProblemCategoryCreate,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemCategoryRead:
    """Create a new problem category."""
    repo = ProblemCategoryRepository(db_provider)
    
    # Check if slug already exists
    existing = await repo.get_by_slug(payload.slug)
    if existing:
        raise HTTPException(status_code=409, detail=f"Category with slug '{payload.slug}' already exists")
    
    category = ProblemCategory(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
    )
    created = await repo.create(category)
    return ProblemCategoryRead.model_validate(created)


@router.put("/categories/{category_id}", response_model=ProblemCategoryRead)
async def update_category(
    category_id: UUID,
    payload: ProblemCategoryUpdate,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemCategoryRead:
    """Update an existing problem category."""
    repo = ProblemCategoryRepository(db_provider)
    
    category = await repo.find_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check slug uniqueness if being updated
    if payload.slug and payload.slug != category.slug:
        existing = await repo.get_by_slug(payload.slug)
        if existing:
            raise HTTPException(status_code=409, detail=f"Category with slug '{payload.slug}' already exists")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    updated = await repo.update(category)
    return ProblemCategoryRead.model_validate(updated)


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: UUID,
    db_provider: DatabaseProvider = Depends(get_database_provider),
):
    """Delete a problem category."""
    repo = ProblemCategoryRepository(db_provider)
    
    category = await repo.find_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category has causes
    cause_repo = ProblemCauseRepository(db_provider)
    causes = await cause_repo.list_by_category(category_id)
    if causes:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete category '{category.name}' because it has {len(causes)} associated cause(s). Delete all causes first."
        )
    
    try:
        await repo.delete_by_id(category_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete category: {str(e)}"
        )


# ==================== Problem Causes ====================


@router.get("/causes", response_model=List[ProblemCauseRead])
async def list_causes(
    category_id: Optional[UUID] = None,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> List[ProblemCauseRead]:
    """List all problem causes, optionally filtered by category."""
    repo = ProblemCauseRepository(db_provider)
    
    if category_id:
        causes = await repo.list_by_category(category_id)
    else:
        causes = await repo.find_all(limit=500)
    
    return [ProblemCauseRead.model_validate(cause) for cause in causes]


@router.get("/causes/{cause_id}", response_model=ProblemCauseRead)
async def get_cause(
    cause_id: UUID,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemCauseRead:
    """Get a specific problem cause by ID."""
    repo = ProblemCauseRepository(db_provider)
    cause = await repo.find_by_id(cause_id)
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")
    return ProblemCauseRead.model_validate(cause)


@router.post("/causes", response_model=ProblemCauseRead, status_code=status.HTTP_201_CREATED)
async def create_cause(
    payload: ProblemCauseCreate,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemCauseRead:
    """Create a new problem cause."""
    repo = ProblemCauseRepository(db_provider)
    cat_repo = ProblemCategoryRepository(db_provider)
    
    # Verify category exists
    category = await cat_repo.find_by_id(payload.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if slug already exists for this category
    existing = await repo.get_by_category_and_slug(payload.category_id, payload.slug)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Cause with slug '{payload.slug}' already exists in this category"
        )
    
    cause = ProblemCause(
        category_id=payload.category_id,
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        detection_hints=payload.detection_hints,
        default_priority=payload.default_priority,
    )
    created = await repo.create(cause)
    return ProblemCauseRead.model_validate(created)


@router.put("/causes/{cause_id}", response_model=ProblemCauseRead)
async def update_cause(
    cause_id: UUID,
    payload: ProblemCauseUpdate,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemCauseRead:
    """Update an existing problem cause."""
    repo = ProblemCauseRepository(db_provider)
    
    cause = await repo.find_by_id(cause_id)
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")
    
    # Check slug uniqueness if being updated
    if payload.slug and payload.slug != cause.slug:
        existing = await repo.get_by_category_and_slug(cause.category_id, payload.slug)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Cause with slug '{payload.slug}' already exists in this category"
            )
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cause, field, value)
    
    updated = await repo.update(cause)
    return ProblemCauseRead.model_validate(updated)


@router.delete("/causes/{cause_id}")
async def delete_cause(
    cause_id: UUID,
    db_provider: DatabaseProvider = Depends(get_database_provider),
):
    """Delete a problem cause."""
    repo = ProblemCauseRepository(db_provider)
    
    cause = await repo.find_by_id(cause_id)
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")
    
    # Check if cause has solutions
    solution_repo = ProblemSolutionRepository(db_provider)
    solutions = await solution_repo.list_by_cause(cause_id, limit=1000)
    if solutions:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete cause '{cause.name}' because it has {len(solutions)} associated solution(s). Delete all solutions first."
        )
    
    try:
        await repo.delete_by_id(cause_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete cause: {str(e)}"
        )


# ==================== Problem Solutions ====================


@router.get("/solutions", response_model=List[ProblemSolutionRead])
async def list_solutions(
    cause_id: Optional[UUID] = None,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> List[ProblemSolutionRead]:
    """List all problem solutions, optionally filtered by cause."""
    repo = ProblemSolutionRepository(db_provider)
    
    if cause_id:
        solutions = await repo.list_by_cause(cause_id, limit=500)
    else:
        solutions = await repo.find_all(limit=500)
    
    return [ProblemSolutionRead.model_validate(sol) for sol in solutions]


@router.get("/solutions/{solution_id}", response_model=ProblemSolutionRead)
async def get_solution(
    solution_id: UUID,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemSolutionRead:
    """Get a specific problem solution by ID."""
    repo = ProblemSolutionRepository(db_provider)
    solution = await repo.find_by_id(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    return ProblemSolutionRead.model_validate(solution)


@router.post("/solutions", response_model=ProblemSolutionRead, status_code=status.HTTP_201_CREATED)
async def create_solution(
    payload: ProblemSolutionCreate,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemSolutionRead:
    """Create a new problem solution."""
    repo = ProblemSolutionRepository(db_provider)
    cause_repo = ProblemCauseRepository(db_provider)
    
    # Verify cause exists
    cause = await cause_repo.find_by_id(payload.cause_id)
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")
    
    # Check if slug already exists for this cause
    existing = await repo.get_by_slug(payload.slug)
    if existing and existing.cause_id == payload.cause_id:
        raise HTTPException(
            status_code=409,
            detail=f"Solution with slug '{payload.slug}' already exists for this cause"
        )
    
    solution = ProblemSolution(
        cause_id=payload.cause_id,
        slug=payload.slug,
        title=payload.title,
        summary=payload.summary,
        instructions=payload.instructions,
        step_order=payload.step_order,
        requires_escalation=payload.requires_escalation,
    )
    created = await repo.create(solution)
    return ProblemSolutionRead.model_validate(created)


@router.put("/solutions/{solution_id}", response_model=ProblemSolutionRead)
async def update_solution(
    solution_id: UUID,
    payload: ProblemSolutionUpdate,
    db_provider: DatabaseProvider = Depends(get_database_provider),
) -> ProblemSolutionRead:
    """Update an existing problem solution."""
    repo = ProblemSolutionRepository(db_provider)
    
    solution = await repo.find_by_id(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    
    # Check slug uniqueness if being updated
    if payload.slug and payload.slug != solution.slug:
        existing = await repo.get_by_slug(payload.slug)
        if existing and existing.cause_id == solution.cause_id:
            raise HTTPException(
                status_code=409,
                detail=f"Solution with slug '{payload.slug}' already exists for this cause"
            )
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(solution, field, value)
    
    updated = await repo.update(solution)
    return ProblemSolutionRead.model_validate(updated)


@router.delete("/solutions/{solution_id}")
async def delete_solution(
    solution_id: UUID,
    db_provider: DatabaseProvider = Depends(get_database_provider),
):
    """Delete a problem solution."""
    repo = ProblemSolutionRepository(db_provider)
    
    solution = await repo.find_by_id(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    
    try:
        await repo.delete_by_id(solution_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete solution: {str(e)}"
        )
