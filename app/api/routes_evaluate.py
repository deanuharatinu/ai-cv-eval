from fastapi import APIRouter, Depends

from app.dependencies import get_eval_service
from app.domain.models import EvaluateRequest, EvaluateResponse
from app.services.eval_service import EvalServiceProtocol


router = APIRouter()


@router.post("/evaluate", response_model=EvaluateResponse)
async def enqueue_evaluation(
    payload: EvaluateRequest,
    service: EvalServiceProtocol = Depends(get_eval_service),
) -> EvaluateResponse:
    return await service.enqueue(payload)
