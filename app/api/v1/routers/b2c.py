"""
B2C payment routes - Following EXACT same pattern as C2B router
"""

from fastapi import APIRouter, Depends, status, HTTPException

from app.core.mpesa_codes import get_mpesa_code_info
from app.core.security import validate_api_key
from app.models.schemas.b2c import B2CPaymentRequest, B2CPaymentResponse
from app.models.schemas.base import APIResponse
from app.services.b2c_service import B2CService
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/b2c/payments",
    response_model=APIResponse[B2CPaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Process B2C Payment",
    description="""
    Process a Business-to-Customer payment with hybrid third_party_reference support.

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
async def create_b2c_payment(
        payment_data: B2CPaymentRequest,
        api_key: str = Depends(validate_api_key)
) -> APIResponse[B2CPaymentResponse]:
    """
    Process B2C payment with hybrid third_party_reference strategy

    - **transaction_reference**: Client's unique reference (required)
    - **customer_msisdn**: Customer phone number (258XXXXXXXXX)
    - **amount**: Transaction amount (> 0)
    - **third_party_reference**: Optional client reference (auto-generated if not provided/duplicate)
    - **service_provider_code**: Service provider code (default: 900579)
    """
    try:
        logger.info(f"🔄 Processing B2C: {payment_data.transaction_reference}")

        service = B2CService()
        result = await service.process_payment(payment_data)

        # Get proper HTTP status based on M-Pesa response code - SAME LOGIC AS C2B
        code_info = get_mpesa_code_info(result.output_ResponseCode)

        if code_info["success"]:
            logger.info(f"✅ B2C payment successful: {payment_data.transaction_reference}")
            return APIResponse(
                success=True,
                data=result,
                message="B2C payment processed successfully"
            )
        else:
            # For errors, raise HTTPException with proper status - SAME LOGIC AS C2B
            logger.warning(f"⚠️ B2C payment failed: {result.output_ResponseDesc}")
            raise HTTPException(
                status_code=code_info["http_status"],
                detail={
                    "success": False,
                    "error": {
                        "code": result.output_ResponseCode,
                        "message": result.output_ResponseDesc
                    }
                }
            )

    except HTTPException:
        # Re-raise HTTP exceptions - SAME LOGIC AS C2B
        raise
    except Exception as e:
        logger.error(f"💥 B2C endpoint error: {str(e)}")
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
