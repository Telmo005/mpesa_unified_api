"""
Reversal API routes
"""

from fastapi import APIRouter, Depends, status, HTTPException

from app.core.mpesa_codes import get_mpesa_code_info
from app.core.security import validate_api_key
from app.models.schemas.base import APIResponse
from app.models.schemas.reversal import ReversalRequest, ReversalResponse
from app.services.reversal_service import ReversalService
from app.utils.logger import logger

router = APIRouter()


@router.put(
    "/reversal",
    response_model=APIResponse[ReversalResponse],
    status_code=status.HTTP_200_OK,
    summary="Reverse Transaction",
    description="""
    Reverse a successful transaction using the Transaction ID.
    Withdraws funds from recipient and reverts to initiating party.
    """,
    responses={
        200: {"description": "Reversal processed successfully"},
        400: {"description": "Validation error"},
        401: {"description": "Authentication failed"},
        500: {"description": "Internal server error"}
    }
)
async def reverse_transaction(
        reversal_data: ReversalRequest,
        api_key: str = Depends(validate_api_key)
) -> APIResponse[ReversalResponse]:
    """
    Reverse a successful transaction

    - **transaction_id**: Mobile Money Platform TransactionID - REQUIRED
    - **security_credential**: Security credential from Vodacom - REQUIRED
    - **initiator_identifier**: Initiator identifier from Vodacom - REQUIRED
    - **third_party_reference**: Your unique reference - REQUIRED
    - **service_provider_code**: Service provider code (default: 171717) - OPTIONAL
    - **reversal_amount**: Amount to reverse (optional - full reversal if not provided) - OPTIONAL
    """
    try:
        logger.info(f"🔄 Processing reversal for transaction: {reversal_data.transaction_id}")

        service = ReversalService()
        result = await service.process_reversal(reversal_data)

        # Get proper HTTP status based on M-Pesa response code
        code_info = get_mpesa_code_info(result.output_ResponseCode)

        if code_info["success"]:
            logger.info(f"✅ Reversal successful: {reversal_data.transaction_id}")
            return APIResponse(
                success=True,
                data=result,
                message="Transaction reversal processed successfully"
            )
        else:
            logger.warning(f"⚠️ Reversal failed: {result.output_ResponseDesc}")
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
        logger.error(f"💥 Reversal endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error"
                }
            }
        )
    
