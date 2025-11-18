"""
Query Customer Name routes
"""

from fastapi import APIRouter, Depends, status, HTTPException, Query
from app.core.security import validate_api_key
from app.services.query_customer_service import QueryCustomerService
from app.core.mpesa_codes import get_mpesa_code_info
from app.models.schemas.query_customer import QueryCustomerResponse
from app.models.schemas.base import APIResponse
from app.utils.logger import logger

router = APIRouter()

@router.get(
    "/query-customer",  # ✅ MUDADO PARA GET
    response_model=APIResponse[QueryCustomerResponse],
    status_code=status.HTTP_200_OK,
    summary="Query Customer Name",
    description="""
    Query customer name associated with mobile money wallet for confirmation purposes.
    Returns masked customer name (First and Second name obfuscated).
    """,
    responses={
        200: {"description": "Query processed successfully"},
        400: {"description": "Validation error"},
        401: {"description": "Authentication failed"},
        500: {"description": "Internal server error"}
    }
)
async def query_customer_name(
    customer_msisdn: str = Query(..., description="Customer phone number in format 258XXXXXXXXX", example="258843330333"),
    third_party_reference: str = Query(..., description="Unique reference of the third party system", example="QUERY_REF_001"),
    service_provider_code: str = Query("900579", description="Service provider code", example="900579"),
    api_key: str = Depends(validate_api_key)
) -> APIResponse[QueryCustomerResponse]:
    """
    Query customer name for confirmation purposes

    - **customer_msisdn**: Customer phone number (258XXXXXXXXX) - REQUIRED
    - **third_party_reference**: Unique reference for tracking - REQUIRED
    - **service_provider_code**: Service provider code (default: 900579) - OPTIONAL
    """
    try:
        logger.info(f"🔍 Processing query: {customer_msisdn}")

        # ✅ VALIDAÇÃO DO MSISDN
        import re
        if not re.match(r'^258[0-9]{9}$', customer_msisdn):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "MSISDN must be in format 258XXXXXXXXX"
                    }
                }
            )

        from app.models.schemas.query_customer import QueryCustomerRequest

        # Cria o request object
        query_data = QueryCustomerRequest(
            customer_msisdn=customer_msisdn,
            third_party_reference=third_party_reference,
            service_provider_code=service_provider_code
        )

        service = QueryCustomerService()
        result = await service.query_customer_name(query_data)

        # Get proper HTTP status based on M-Pesa response code
        code_info = get_mpesa_code_info(result.output_ResultCode)

        if code_info["success"]:
            logger.info(f"✅ Query successful: {customer_msisdn}")
            return APIResponse(
                success=True,
                data=result,
                message="Customer query processed successfully"
            )
        else:
            logger.warning(f"⚠️ Query failed: {result.output_ResultDesc}")
            raise HTTPException(
                status_code=code_info["http_status"],
                detail={
                    "success": False,
                    "error": {
                        "code": result.output_ResultCode,
                        "message": result.output_ResultDesc
                    }
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Query endpoint error: {str(e)}")
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