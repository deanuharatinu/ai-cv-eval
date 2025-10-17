from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_eval_service
from app.domain.models import ResultResponse
from app.services.eval_service import EvalServiceProtocol


router = APIRouter()


@router.get("/{job_id}", response_model=ResultResponse)
async def read_result(
    job_id: str,
    service: EvalServiceProtocol = Depends(get_eval_service),
) -> ResultResponse:
    result = await service.get_status(job_id)
    if result.status == "failed" and result.error_message == "Unknown job id":
        raise HTTPException(status_code=404, detail=result.error_message)
    return result
