from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.assistant import router as assistant_router
from app.core.config import settings
from app.core.database import get_db_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    yield
    # Shutdown
    db_provider = get_db_provider()
    await db_provider.close()


app = FastAPI(
    title="Dishwasher Troubleshooter Backend",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


app.include_router(assistant_router)
