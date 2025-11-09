"""
Health check routes
"""

from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings
from app.models.schemas.base import APIResponse

router = APIRouter()

@router.get("/health")
async def health_check():
    return APIResponse(
        success=True,
        data={
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.now()
        },
        message="API is healthy"
    )