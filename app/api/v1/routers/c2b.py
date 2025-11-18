"""
C2B payment routes - With hybrid third_party_reference support
"""

from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import validate_api_key
from app.services.c2b_service import C2BService
from app.core.mpesa_codes import get_mpesa_code_info
from app.models.schemas.c2b import C2BPaymentRequest, C2BPaymentResponse
from app.models.schemas.base import APIResponse
from app.utils.logger import logger

router = APIRouter()

@router.post(
    "/c2b/payments",
    response_model=APIResponse[C2BPaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Process C2B Payment",
    description="""
    Process a Customer-to-Business payment with hybrid third_party_reference support.
    
    **Third Party Reference Strategy:**
    - If provided and unique: Use client's reference
    - If provided but duplicate: Auto-generate new one  
    - If not provided: Auto-generate one
    
    **Response:** Always returns the third_party_reference used in the transaction.
    """,
    responses={
        201: {"description": "Payment processed successfully"},
        400: {"description": "Validation error"},
        401: {"description": "Authentication failed"},
        409: {"description": "Duplicate transaction"},
        422: {"description": "Insufficient balance"},
        500: {"description": "Internal server error"}
    }
)
async def create_c2b_payment(
    payment_data: C2BPaymentRequest,
    api_key: str = Depends(validate_api_key)
) -> APIResponse[C2BPaymentResponse]:
    """
    Process C2B payment with hybrid third_party_reference strategy

    - **transaction_reference**: Client's unique reference (required)
    - **customer_msisdn**: Customer phone number (258XXXXXXXXX)
    - **amount**: Transaction amount (> 0)
    - **third_party_reference**: Optional client reference (auto-generated if not provided/duplicate)
    - **service_provider_code**: Service provider code (default: 900579)
    """
    try:
        logger.info(f"🔄 Processing C2B: {payment_data.transaction_reference}")

        service = C2BService()
        result = await service.process_payment(payment_data)

        # Get proper HTTP status based on M-Pesa response code
        code_info = get_mpesa_code_info(result.response_code)

        if code_info["success"]:
            logger.info(f"✅ C2B payment successful: {payment_data.transaction_reference}")
            return APIResponse(
                success=True,
                data=result,
                message="Payment processed successfully"
            )
        else:
            # For errors, raise HTTPException with proper status
            logger.warning(f"⚠️ C2B payment failed: {result.response_description}")
            raise HTTPException(
                status_code=code_info["http_status"],
                detail={
                    "success": False,
                    "error": {
                        "code": result.response_code,
                        "message": result.response_description
                    }
                }
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"💥 C2B endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error"
                }
            }
        )