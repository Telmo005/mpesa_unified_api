# Adicione este endpoint temporário para debug
# app/api/v1/routers/debug.py
from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter()

@router.get("/debug/credentials")
async def debug_credentials():
    settings = get_settings()
    return {
        "api_key_length": len(settings.MPESA_API_KEY),
        "api_key_first_10": settings.MPESA_API_KEY[:10] + "...",
        "public_key_length": len(settings.MPESA_PUBLIC_KEY),
        "public_key_first_50": settings.MPESA_PUBLIC_KEY[:50] + "...",
        "service_provider_code": settings.MPESA_SERVICE_PROVIDER_CODE
    }