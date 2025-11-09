"""
M-Pesa API client - WORKING VERSION
"""

from typing import Dict, Any

from app.core.config import settings
from app.utils.logger import logger
from portalsdk import APIContext, APIMethodType, APIRequest


class MpesaClient:
    """M-Pesa API client - PROVEN WORKING VERSION"""

    def execute_request(self, endpoint: str, parameters: Dict[str, Any], transaction_type: str = "c2b") -> Dict[
        str, Any]:
        """
        Execute M-Pesa request - UPDATED WITH B2B SUPPORT
        """
        try:
            # ✅ SELECT CORRECT PORT BASED ON TRANSACTION TYPE (ATUALIZADO COM B2B)
            if transaction_type.lower() == "b2c":
                port = settings.MPESA_API_PORT_B2C
            elif transaction_type.lower() == "b2b":  # ✅ NOVO: Adicionado B2B
                port = settings.MPESA_API_PORT_B2B
            elif transaction_type.lower() == "query_customer":
                port = settings.MPESA_API_PORT_QUERY
            elif transaction_type.lower() == "query_transaction":
                port = settings.MPESA_API_PORT_QUERY_TXN
            elif transaction_type.lower() == "reversal":
                port = settings.MPESA_API_PORT_REVERSAL
            else:
                port = settings.MPESA_API_PORT_C2B

            logger.info(f"🎯 Using {transaction_type} port: {port}")

            api_context = APIContext()
            api_context.api_key = settings.MPESA_API_KEY
            api_context.public_key = settings.MPESA_PUBLIC_KEY
            api_context.ssl = True
            api_context.address = settings.MPESA_API_HOST
            api_context.port = port
            api_context.add_header('Origin', '*')

            # ✅ CONFIGURE METHOD BASED ON TRANSACTION TYPE
            if transaction_type.lower() in ["query_customer", "query_transaction"]:
                # GET method for query endpoints
                api_context.method_type = APIMethodType.GET
                query_string = "&".join([f"{key}={value}" for key, value in parameters.items()])
                full_endpoint = f"{endpoint}?{query_string}" if query_string else endpoint
                api_context.path = full_endpoint
            elif transaction_type.lower() == "reversal":
                # PUT method for reversal endpoint
                api_context.method_type = APIMethodType.PUT
                api_context.path = endpoint
                for key, value in parameters.items():
                    api_context.add_parameter(key, str(value))
            else:
                # POST method for payment endpoints (C2B, B2C, B2B)
                api_context.method_type = APIMethodType.POST
                api_context.path = endpoint
                for key, value in parameters.items():
                    api_context.add_parameter(key, str(value))

            # Execute request
            api_request = APIRequest(api_context)
            result = api_request.execute()

            logger.info(f"M-Pesa {transaction_type} response: {result.status_code}")

            return {
                "status_code": result.status_code,
                "body": result.body,
                "success": result.status_code == 200
            }

        except Exception as e:
            logger.error(f"M-Pesa {transaction_type} error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 500
            }
