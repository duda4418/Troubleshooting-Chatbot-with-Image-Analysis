from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_troubleshooting_import_service
from app.data.DTO import TroubleshootingCatalog, TroubleshootingImportResult
from app.services.troubleshooting_import_service import TroubleshootingImportService

router = APIRouter(prefix="/troubleshooting", tags=["troubleshooting-admin"])


@router.post("/import", response_model=TroubleshootingImportResult, status_code=status.HTTP_201_CREATED)
async def import_troubleshooting_catalog(
    payload: TroubleshootingCatalog,
    service: TroubleshootingImportService = Depends(get_troubleshooting_import_service),
) -> TroubleshootingImportResult:
    return await service.import_catalog(payload)
