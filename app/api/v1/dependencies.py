"""
API dependencies - Simple and non-breaking
"""

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def get_api_key(api_key: str = Header(None, alias=settings.API_KEY_HEADER)):
    """
    Simple API key validation - Accepts any key for now
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in X-API-Key header"
        )
    return api_key
