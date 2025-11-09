"""
B2B payment routes
"""

from fastapi import APIRouter, Depends, status, HTTPException

from app.core.mpesa_codes import get_mpesa_code_info
from app.core.security import validate_api_key
from app.models.schemas.b2b import B2BPaymentRequest, B2BPaymentResponse
from app.models.schemas.base import APIResponse
from app.services.b2b_service import B2BService
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/b2b/payments",
    response_model=APIResponse[B2BPaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Process B2B Payment",
    description="""
    Process a Business-to-Business payment transaction between business wallets.
    Funds are transferred from primary party to receiver party business accounts.
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
async def create_b2b_payment(
        payment_data: B2BPaymentRequest,
        api_key: str = Depends(validate_api_key)
) -> APIResponse[B2BPaymentResponse]:
    """
    Process B2B payment with hybrid third_party_reference strategy

    - **transaction_reference**: Client's unique reference (required)
    - **amount**: Transaction amount (> 0)
    - **third_party_reference**: Optional client reference (auto-generated if not provided/duplicate)
    - **primary_party_code**: Shortcode of business where funds are debited from (required)
    - **receiver_party_code**: Shortcode of business where funds are credited to (required)
    """
    try:
        logger.info(f"🔄 Processing B2B: {payment_data.transaction_reference}")

        service = B2BService()
        result = await service.process_payment(payment_data)

        # Get proper HTTP status based on M-Pesa response code
        code_info = get_mpesa_code_info(result.output_ResponseCode)

        if code_info["success"]:
            logger.info(f"✅ B2B payment successful: {payment_data.transaction_reference}")
            return APIResponse(
                success=True,
                data=result,
                message="B2B payment processed successfully"
            )
        else:
            logger.warning(f"⚠️ B2B payment failed: {result.output_ResponseDesc}")
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
        raise
    except Exception as e:
        logger.error(f"💥 B2B endpoint error: {str(e)}")
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
