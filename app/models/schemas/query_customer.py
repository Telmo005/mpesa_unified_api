"""
Query Customer Name schemas
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, validator


class QueryCustomerRequest(BaseModel):
    """
    Query Customer Name request schema
    """
    customer_msisdn: str = Field(
        ...,
        description="Customer phone number in format 258XXXXXXXXX",
        example="258843330333"
    )
    third_party_reference: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique reference of the third party system",
        example="QUERY_REF_001"
    )
    service_provider_code: Optional[str] = Field(
        "171717",
        description="Service provider code",
        example="171717"
    )

    @validator('customer_msisdn')
    def validate_msisdn(cls, v):
        """Validate Mozambique MSISDN format"""
        if not re.match(r'^258[0-9]{9}$', v):
            raise ValueError('MSISDN must be in format 258XXXXXXXXX')
        return v


class QueryCustomerResponse(BaseModel):
    """
    Query Customer Name response schema
    """
    output_ConversationID: Optional[str] = Field(
        None,
        description="M-Pesa conversation ID",
        example="AG_20240101_12345"
    )
    output_ResultDesc: str = Field(
        ...,
        description="Result description from M-Pesa",
        example="Success"
    )
    output_ResultCode: str = Field(
        ...,
        description="Result code from M-Pesa",
        example="0"
    )
    output_ThirdPartyReference: str = Field(
        ...,
        description="Third party reference used in query",
        example="QUERY_REF_001"
    )
    output_CustomerName: Optional[str] = Field(
        None,
        description="Masked customer name",
        example="Jo*n Sm**h"
    )
