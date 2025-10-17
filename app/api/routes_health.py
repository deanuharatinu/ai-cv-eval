from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy"}
