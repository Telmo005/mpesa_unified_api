"""
Standardized API responses - Improved for error handling
"""

from datetime import datetime
from typing import Generic, TypeVar, Optional, Dict, Any

from pydantic import BaseModel, Field

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """Standard success response"""
    success: bool = Field(True, description="Indicates if the request was successful")
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ErrorDetail(BaseModel):
    """Standard error detail structure"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = Field(False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
