"""
Serviço para consulta de status de transação M-Pesa Mozambique
"""

import asyncio
from typing import Dict, Any

from app.core.database import get_supabase
from app.core.mpesa_codes import get_mpesa_code_info
from app.models.schemas.query_transaction import QueryTransactionRequest, QueryTransactionResponse
from app.services.database_service import DatabaseService
from app.services.mpesa_client import MpesaClient
from app.utils.logger import logger


class QueryTransactionService:
    """Serviço para consulta de status de transação"""

    def __init__(self):
        self.mpesa_client = MpesaClient()
        self.endpoint = "/ipg/v1x/queryTransactionStatus/"

        self.servico_db = DatabaseService(get_supabase())

    async def query_transaction_status(self, query_data: QueryTransactionRequest) -> QueryTransactionResponse:
        """Consulta status de transação M-Pesa"""
        logger.info(f"🔍 Consultando status da transação: {query_data.query_reference}")

        try:
            # Prepara payload para M-Pesa (GET com query parameters)
            payload_mpesa = {
                "input_ThirdPartyReference": query_data.third_party_reference,
                "input_QueryReference": query_data.query_reference,
                "input_ServiceProviderCode": query_data.service_provider_code or "900579"
            }

            logger.info(f"📤 Enviando consulta GET para M-Pesa - Referência: {query_data.query_reference}")

            # Log início da consulta
            asyncio.create_task(self._registrar_inicio_consulta(query_data))

            # Executa request M-Pesa (método GET para query transaction)
            resultado = self.mpesa_client.execute_request(self.endpoint, payload_mpesa, "query_transaction")

            logger.info(f"📥 Resposta consulta M-Pesa: {resultado['status_code']}")

            # Processa resposta M-Pesa
            resposta = self._processar_resposta_mpesa(resultado, query_data.third_party_reference)

            # Log resultado
            asyncio.create_task(
                self._registrar_resultado_consulta(query_data, resultado, resposta))

            return resposta

        except Exception as e:
            logger.error(f"❌ Erro na consulta de status: {str(e)}")

            # Log erro
            asyncio.create_task(self._registrar_erro_consulta(query_data, str(e)))

            return QueryTransactionResponse(
                output_ConversationID=None,
                output_ResponseDesc=f"Erro no serviço: {str(e)}",
                output_ResponseCode="INS-999",
                output_ThirdPartyReference=query_data.third_party_reference,
                output_ResponseTransactionStatus=None
            )

    def _processar_resposta_mpesa(self, resultado: Dict[str, Any], third_party_ref: str) -> QueryTransactionResponse:
        """Processa resposta M-Pesa da consulta"""
        if resultado["success"] and resultado["status_code"] == 200:
            dados_corpo = resultado["body"]
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-0')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            return QueryTransactionResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_ResponseDesc=dados_corpo.get('output_ResponseDesc', info_codigo["message"]),
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref,
                output_ResponseTransactionStatus=dados_corpo.get('output_ResponseTransactionStatus')
            )
        else:
            dados_corpo = resultado.get("body", {})
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-999')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            descricao_mpesa = dados_corpo.get('output_ResponseDesc')
            descricao_final = descricao_mpesa if descricao_mpesa else info_codigo["message"]

            return QueryTransactionResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_ResponseDesc=descricao_final,
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref,
                output_ResponseTransactionStatus=dados_corpo.get('output_ResponseTransactionStatus')
            )

    async def _registrar_inicio_consulta(self, query_data: QueryTransactionRequest):
        """Registra início da consulta"""
        try:
            dados_log = {
                "transaction_reference": f"STATUS_{query_data.third_party_reference}",
                "third_party_reference": query_data.third_party_reference,
                "customer_msisdn": "N/A",  # Consulta não tem MSISDN
                "amount": 0.0,  # Valor default para consultas
                "service_provider_code": query_data.service_provider_code or "900579",
                "status": "pending",
                "response_code": "PENDING",
                "response_description": "Consulta de status iniciada",
                "api_key_used": "default",
                "transaction_type": "QUERY_TRANSACTION"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
        except Exception as e:
            logger.error(f"❌ Falha ao registrar início da consulta: {str(e)}")

    async def _registrar_resultado_consulta(self, query_data: QueryTransactionRequest,
                                            resultado_mpesa: Dict[str, Any],
                                            resposta: QueryTransactionResponse):
        """Registra resultado da consulta"""
        try:
            status = "success" if resposta.output_ResponseCode == "INS-0" else "failed"

            dados_log = {
                "transaction_reference": f"STATUS_{query_data.third_party_reference}",
                "third_party_reference": query_data.third_party_reference,
                "customer_msisdn": "N/A",  # Consulta não tem MSISDN
                "amount": 0.0,  # Valor default para consultas
                "service_provider_code": query_data.service_provider_code or "900579",
                "status": status,
                "response_code": resposta.output_ResponseCode,
                "response_description": resposta.output_ResponseDesc,
                "mpesa_conversation_id": resposta.output_ConversationID,
                "api_key_used": "default",
                "transaction_type": "QUERY_TRANSACTION"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 Resultado consulta registrado: {query_data.query_reference} - Status: {status}")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar resultado da consulta: {str(e)}")

    async def _registrar_erro_consulta(self, query_data: QueryTransactionRequest, erro: str):
        """Registra erro na consulta"""
        try:
            dados_log = {
                "transaction_reference": f"STATUS_{query_data.third_party_reference}",
                "third_party_reference": query_data.third_party_reference,
                "customer_msisdn": "N/A",  # Consulta não tem MSISDN
                "amount": 0.0,  # Valor default para consultas
                "service_provider_code": query_data.service_provider_code or "900579",
                "status": "failed",
                "response_code": "INS-999",
                "response_description": f"Erro consulta: {erro}",
                "api_key_used": "default",
                "transaction_type": "QUERY_TRANSACTION"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 Erro consulta registrado: {query_data.query_reference}")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar erro da consulta: {str(e)}")
