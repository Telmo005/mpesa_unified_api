"""
M-Pesa Response Codes Mapping
Official codes from Vodacom Mozambique
"""

MPESA_RESPONSE_CODES = {
    # Success codes
    "INS-0": {
        "http_status": 201,
        "message": "Request processed successfully",
        "success": True
    },

    # Error codes with proper HTTP status mapping
    "INS-1": {
        "http_status": 500,
        "message": "Internal Error",
        "success": False
    },
    "INS-2": {
        "http_status": 401,
        "message": "Invalid API Key",
        "success": False
    },
    "INS-4": {
        "http_status": 401,
        "message": "User is not active",
        "success": False
    },
    "INS-5": {
        "http_status": 401,
        "message": "Transaction cancelled by customer",
        "success": False
    },
    "INS-6": {
        "http_status": 401,
        "message": "Transaction Failed",
        "success": False
    },
    "INS-9": {
        "http_status": 408,
        "message": "Request timeout",
        "success": False
    },
    "INS-10": {
        "http_status": 409,
        "message": "Duplicate Transaction",
        "success": False
    },
    "INS-13": {
        "http_status": 400,
        "message": "Invalid Shortcode Used",
        "success": False
    },
    "INS-14": {
        "http_status": 400,
        "message": "Invalid Reference Used",
        "success": False
    },
    "INS-15": {
        "http_status": 400,
        "message": "Invalid Amount Used",
        "success": False
    },
    "INS-16": {
        "http_status": 503,
        "message": "Unable to handle the request due to a temporary overloading",
        "success": False
    },
    "INS-17": {
        "http_status": 400,
        "message": "Invalid Transaction Reference. Length Should Be Between 1 and 20.",
        "success": False
    },
    "INS-18": {
        "http_status": 400,
        "message": "Invalid TransactionID Used",
        "success": False
    },
    "INS-19": {
        "http_status": 400,
        "message": "Invalid ThirdPartyReference Used",
        "success": False
    },
    "INS-20": {
        "http_status": 400,
        "message": "Not All Parameters Provided. Please try again.",
        "success": False
    },
    "INS-21": {
        "http_status": 400,
        "message": "Parameter validations failed. Please try again.",
        "success": False
    },
    "INS-22": {
        "http_status": 400,
        "message": "Invalid Operation Type",
        "success": False
    },
    "INS-23": {
        "http_status": 400,
        "message": "Unknown Status. Contact M-Pesa Support",
        "success": False
    },
    "INS-2001": {
        "http_status": 400,
        "message": "Initiator authentication error.",
        "success": False
    },
    "INS-2002": {
        "http_status": 400,
        "message": "Receiver invalid.",
        "success": False
    },
    "INS-2006": {
        "http_status": 422,
        "message": "Insufficient balance",
        "success": False
    },
    "INS-2051": {
        "http_status": 400,
        "message": "MSISDN invalid.",
        "success": False
    },
    "INS-2057": {
        "http_status": 400,
        "message": "Language code invalid.",
        "success": False
    },

    # Default fallback codes
    "INS-999": {
        "http_status": 500,
        "message": "Unknown M-Pesa error",
        "success": False
    }
}


def get_mpesa_code_info(response_code: str):
    """
    Get M-Pesa response code information with proper HTTP mapping
    """
    return MPESA_RESPONSE_CODES.get(response_code, MPESA_RESPONSE_CODES["INS-999"])
