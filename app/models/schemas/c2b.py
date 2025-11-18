"""
C2B payment schemas with validation
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, validator


class C2BPaymentRequest(BaseModel):
    """
    C2B payment request schema
    Supports both client-provided and auto-generated third_party_reference
    """
    transaction_reference: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Client's unique transaction reference for their system",
        example="ORDER_789456"
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
        example=100.0
    )
    third_party_reference: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="""
        Optional: Client's reference for their system context.
        If not provided or duplicate, one will be auto-generated.
        """,
        example="INVOICE_2024_8596"
    )
    # ✅ REMOVIDO: service_provider_code não é mais necessário no request
    # O shortcode sempre virá do .env

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

    @validator('third_party_reference')
    def validate_third_party_ref(cls, v):
        """Optional validation for third_party_reference format"""
        if v is not None and len(v) > 50:
            raise ValueError('third_party_reference must be 50 characters or less')
        return v


class C2BPaymentResponse(BaseModel):
    """
    C2B payment response schema
    Always returns the third_party_reference used in the transaction
    """
    transaction_id: Optional[str] = Field(
        None,
        description="M-Pesa transaction ID",
        example="AG_20240101_12345"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="M-Pesa conversation ID",
        example="CONV_001"
    )
    third_party_reference: str = Field(
        ...,
        description="The third_party_reference used in the transaction (client-provided or auto-generated)",
        example="mpesa_20240115143025_a1b2c3d4"
    )
    response_code: str = Field(
        ...,
        description="M-Pesa response code",
        example="INS-0"
    )
    response_description: str = Field(
        ...,
        description="M-Pesa response description",
        example="Request processed successfully"
    )