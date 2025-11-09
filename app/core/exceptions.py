"""
Custom exception classes for consistent error handling
Follows RFC 7807 (Problem Details for HTTP APIs) principles
"""

from typing import Optional, Dict, Any

class MPesaAPIException(Exception):
    """
    Base exception for M-Pesa API errors
    Maps to standard HTTP status codes and error formats
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "MPESA_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(MPesaAPIException):
    """Input validation error - HTTP 400 Bad Request"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(MPesaAPIException):
    """Authentication error - HTTP 401 Unauthorized"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR"
        )


class MPesaServiceError(MPesaAPIException):
    """M-Pesa service error - HTTP 502 Bad Gateway"""

    def __init__(self, message: str, mpesa_response: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=502,
            error_code="MPESA_SERVICE_ERROR",
            details={"mpesa_response": mpesa_response} if mpesa_response else {}
        )


class RateLimitError(MPesaAPIException):
    """Rate limiting error - HTTP 429 Too Many Requests"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )