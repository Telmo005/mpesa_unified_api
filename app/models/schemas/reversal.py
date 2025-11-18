"""
Reversal API schemas
"""

from typing import Optional

from pydantic import BaseModel, Field, validator


class ReversalRequest(BaseModel):
    """
    Reversal API request schema
    """
    transaction_id: str = Field(
        ...,
        description="Mobile Money Platform TransactionID for a successful transaction",
        example="49XCDF6"
    )
    security_credential: str = Field(
        ...,
        description="Security credential provided by Vodacom",
        example="Mpesa2019"
    )
    initiator_identifier: str = Field(
        ...,
        description="Initiator identifier provided by Vodacom",
        example="MPesa2018"
    )
    third_party_reference: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique reference of the third party system",
        example="REVERSAL_001"
    )
    service_provider_code: Optional[str] = Field(
        "900579",
        description="Service provider code",
        example="900579"
    )
    reversal_amount: Optional[float] = Field(
        None,
        gt=0,
        description="Amount to reverse (optional - full reversal if not provided)",
        example=10.0
    )

    @validator('reversal_amount')
    def validate_amount(cls, v):
        """Validate reversal amount if provided"""
        if v is not None and v <= 0:
            raise ValueError('Reversal amount must be greater than 0')
        return round(v, 2) if v is not None else v


class ReversalResponse(BaseModel):
    """
    Reversal API response schema
    """
    output_ConversationID: Optional[str] = Field(
        None,
        description="M-Pesa conversation ID",
        example="AG_20240101_12345"
    )
    output_TransactionID: Optional[str] = Field(
        None,
        description="M-Pesa transaction ID for the reversal",
        example="4XDF12345"
    )
    output_ResponseDesc: str = Field(
        ...,
        description="Response description from M-Pesa",
        example="Request processed successfully"
    )
    output_ResponseCode: str = Field(
        ...,
        description="Response code from M-Pesa",
        example="INS-0"
    )
    output_ThirdPartyReference: str = Field(
        ...,
        description="Third party reference used in reversal",
        example="L3TJ83"
    )
