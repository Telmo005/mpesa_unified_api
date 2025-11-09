"""
Query Transaction Status routes
"""

from fastapi import APIRouter, Depends, status, HTTPException, Query

from app.core.mpesa_codes import get_mpesa_code_info
from app.core.security import validate_api_key
from app.models.schemas.base import APIResponse
from app.models.schemas.query_transaction import QueryTransactionResponse
from app.services.query_transaction_service import QueryTransactionService
from app.utils.logger import logger

router = APIRouter()


@router.get(
    "/query-transaction",
    response_model=APIResponse[QueryTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Query Transaction Status",
    description="""
    Query transaction status using Transaction ID, ThirdPartyReference, or Conversation ID.
    Returns current status of the transaction from M-Pesa platform.
    """,
    responses={
        200: {"description": "Query processed successfully"},
        400: {"description": "Validation error"},
        401: {"description": "Authentication failed"},
        500: {"description": "Internal server error"}
    }
)
async def query_transaction_status(
        third_party_reference: str = Query(..., description="Unique reference of the third party system",
                                           example="QUERY_TXN_001"),
        query_reference: str = Query(..., description="Transaction ID, ThirdPartyReference, or Conversation ID",
                                     example="5C1400CVRO"),
        service_provider_code: str = Query("171717", description="Service provider code", example="171717"),
        api_key: str = Depends(validate_api_key)
) -> APIResponse[QueryTransactionResponse]:
    """
    Query transaction status for tracking purposes

    - **third_party_reference**: Your unique reference for this query - REQUIRED
    - **query_reference**: Transaction ID, ThirdPartyReference, or Conversation ID - REQUIRED
    - **service_provider_code**: Service provider code (default: 171717) - OPTIONAL
    """
    try:
        logger.info(f"🔍 Processing transaction query: {query_reference}")

        from app.models.schemas.query_transaction import QueryTransactionRequest

        # Cria o request object
        query_data = QueryTransactionRequest(
            third_party_reference=third_party_reference,
            query_reference=query_reference,
            service_provider_code=service_provider_code
        )

        service = QueryTransactionService()
        result = await service.query_transaction_status(query_data)

        # Get proper HTTP status based on M-Pesa response code
        code_info = get_mpesa_code_info(result.output_ResponseCode)

        if code_info["success"]:
            logger.info(f"✅ Transaction query successful: {query_reference}")
            return APIResponse(
                success=True,
                data=result,
                message="Transaction status query processed successfully"
            )
        else:
            logger.warning(f"⚠️ Transaction query failed: {result.output_ResponseDesc}")
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
        logger.error(f"💥 Transaction query endpoint error: {str(e)}")
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
