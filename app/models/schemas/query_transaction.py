"""
Query Transaction Status schemas
"""

from typing import Optional

from pydantic import BaseModel, Field


class QueryTransactionRequest(BaseModel):
    """
    Query Transaction Status request schema
    """
    third_party_reference: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique reference of the third party system",
        example="QUERY_TXN_001"
    )
    query_reference: str = Field(
        ...,
        description="Transaction ID, ThirdPartyReference, or Conversation ID to query",
        example="5C1400CVRO"
    )
    service_provider_code: Optional[str] = Field(
        "171717",
        description="Service provider code",
        example="171717"
    )


class QueryTransactionResponse(BaseModel):
    """
    Query Transaction Status response schema
    """
    output_ConversationID: Optional[str] = Field(
        None,
        description="M-Pesa conversation ID",
        example="AG_20240101_12345"
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
        description="Third party reference used in query",
        example="QUERY_TXN_001"
    )
    output_ResponseTransactionStatus: Optional[str] = Field(
        None,
        description="Transaction status from M-Pesa",
        example="Completed"
    )
