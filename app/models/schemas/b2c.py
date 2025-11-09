"""
B2C payment schemas with validation
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, validator


class B2CPaymentRequest(BaseModel):
    """
    B2C payment request schema
    Business-to-customer transaction
    """
    transaction_reference: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Client's unique transaction reference for their system",
        example="SALARY_JAN_2024"
    )
    customer_msisdn: str = Field(
        ...,
        description="Customer phone number in format 258XXXXXXXXX",
        example="258843330333"
    )
    amount: float = Field(
        ...,
        gt=0,
        le=1000000,
        description="Transaction amount (must be greater than 0)",
        example=5000.0
    )
    third_party_reference: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Client's reference for their system context",
        example="PAYROLL_001"
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

    @validator('amount')
    def validate_amount(cls, v):
        """Validate transaction amount"""
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return round(v, 2)


class B2CPaymentResponse(BaseModel):
    """
    B2C payment response schema
    Maps directly to M-Pesa B2C response
    """
    output_ConversationID: Optional[str] = Field(
        None,
        description="M-Pesa conversation ID",
        example="AG_20240101_12345"
    )
    output_TransactionID: Optional[str] = Field(
        None,
        description="M-Pesa transaction ID",
        example="4XDF12345"
    )
    output_ResponseDesc: str = Field(
        ...,
        description="M-Pesa response description",
        example="Request processed successfully"
    )
    output_ResponseCode: str = Field(
        ...,
        description="M-Pesa response code",
        example="INS-0"
    )
    output_ThirdPartyReference: str = Field(
        ...,
        description="Third party reference used in transaction",
        example="5PO4Q1"
    )
