"""
Schemas comuns para múltiplos tipos de operação
"""

from pydantic import BaseModel, Field
from typing import Optional


class TransactionQuery(BaseModel):
    """
    Schema para consulta de status de transação

    Attributes:
        query_reference: Referência da consulta
        service_provider_code: Código do provedor de serviço
        third_party_reference: Referência da transação original
    """
    query_reference: str = Field(
        ...,
        description="Referência da consulta"
    )
    service_provider_code: str = Field(
        ...,
        description="Código do provedor de serviço",
        example="171717"
    )
    third_party_reference: str = Field(
        ...,
        description="Referência da transação original"
    )


class TransactionStatusResponse(BaseModel):
    """
    Schema para resposta de status de transação
    """
    success: bool
    transaction_status: Optional[str] = None
    response_code: Optional[str] = None
    response_description: Optional[str] = None
    error_message: Optional[str] = None


class ReversalRequest(BaseModel):
    """
    Schema para requisição de reversão de transação

    Attributes:
        transaction_id: ID da transação a reverter
        amount: Valor a reverter (deve ser maior que 0)
        third_party_reference: Referência única do sistema terceiro
        service_provider_code: Código do provedor de serviço
        reversal_reason: Motivo da reversão
    """
    transaction_id: str = Field(
        ...,
        description="ID da transação a reverter"
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Valor a reverter"
    )
    third_party_reference: Optional[str] = Field(
        None,
        description="Referência única do sistema terceiro"
    )
    service_provider_code: str = Field(
        ...,
        description="Código do provedor de serviço",
        example="171717"
    )
    reversal_reason: str = Field(
        ...,
        description="Motivo da reversão",
        example="Duplicate transaction"
    )


class ReversalResponse(BaseModel):
    """
    Schema para resposta de reversão de transação
    """
    success: bool
    transaction_id: Optional[str] = None
    conversation_id: Optional[str] = None
    third_party_reference: Optional[str] = None
    response_code: Optional[str] = None
    response_description: Optional[str] = None
    error_message: Optional[str] = None