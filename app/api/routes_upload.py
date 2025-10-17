from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_upload_service
from app.domain.models import UploadResponse
from app.services.upload_service import UploadServiceProtocol


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    cv: UploadFile = File(...),
    project_report: UploadFile = File(...),
    service: UploadServiceProtocol = Depends(get_upload_service),
) -> UploadResponse:
    return await service.store(cv=cv, report=project_report)
