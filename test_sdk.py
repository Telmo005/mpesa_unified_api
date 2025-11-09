# app/api/v1/routers/debug.py - ARQUIVO TEMPORÁRIO
from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter()

@router.get("/debug/config")
async def debug_config():
    settings = get_settings()
    return {
        "mpesa_host": settings.MPESA_API_HOST,
        "mpesa_port": settings.MPESA_API_PORT,
        "api_key_length": len(settings.MPESA_API_KEY),
        "public_key_info": settings.mpesa_public_key_debug,
        "base_url": settings.mpesa_base_url
    }