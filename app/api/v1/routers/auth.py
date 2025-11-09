"""
Authentication routes - Simple key generation
"""

from fastapi import APIRouter
from app.core.security import generate_api_key
from app.models.schemas.base import APIResponse

router = APIRouter()

@router.get("/auth/generate-key")
async def generate_api_key_endpoint():
    """Generate API key"""
    new_key = generate_api_key()

    return APIResponse(
        success=True,
        data={
            "generated_api_key": new_key,
            "instructions": "Copy this key to app/core/security.py API_KEY variable"
        },
        message="API key generated"
    )