"""
Simple API Key authentication
"""

import secrets
import uuid

from fastapi import HTTPException, status, Header

from app.utils.logger import logger

# API Key - Change this to whatever you want
API_KEY = "mpesa_f2f8e4f000b4469ebd899cfbba434eec_W5qp4EMhWSIgmFoH9uO4Tg"


def validate_api_key(api_key: str = Header(..., alias="X-API-Key")):
    """Simple API Key validation"""
    if api_key != API_KEY:
        logger.warning(f"Invalid API Key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    logger.info("Valid API Key used")
    return api_key


def generate_api_key():
    """Generate API key"""
    return f"mpesa_{uuid.uuid4().hex}_{secrets.token_urlsafe(16)}"
