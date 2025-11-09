"""
B2B payment schemas with validation
"""

from typing import Optional

from pydantic import BaseModel, Field, validator


class B2BPaymentRequest(BaseModel):
    """
    B2B payment request schema
    Business-to-business transaction
    """
    transaction_reference: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Client's unique transaction reference for their system",
        example="INVOICE_JAN_2024"
    )
    amount: float = Field(
        ...,
        gt=0,
        le=1000000,
        description="Transaction amount (must be greater than 0)",
        example=10000.0
    )
    third_party_reference: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Client's reference for their system context",
        example="B2B_INVOICE_001"
    )
    primary_party_code: str = Field(
        ...,
        description="Shortcode of the business where funds will be debited from",
        example="171717"
    )
    receiver_party_code: str = Field(
        ...,
        description="Shortcode of the business where funds will be credited to",
        example="979797"
    )

    @validator('amount')
    def validate_amount(cls, v):
        """Validate transaction amount"""
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return round(v, 2)


class B2BPaymentResponse(BaseModel):
    """
    B2B payment response schema
    Maps directly to M-Pesa B2B response
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
        example="B2B_INVOICE_001"
    )
