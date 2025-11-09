"""
Security middleware for authentication and request processing
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.logger import logger


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for authentication and logging"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Start timer
        start_time = time.time()

        # Log request
        logger.info(f"Incoming request: {request.method} {request.url}")

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url} "
                f"Status: {response.status_code} Time: {process_time:.2f}s"
            )

            return response

        except Exception as e:
            # Log errors
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url} "
                f"Error: {str(e)} Time: {process_time:.2f}s"
            )
            raise
