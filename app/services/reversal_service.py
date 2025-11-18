"""
Serviço para reversão de transações M-Pesa Mozambique
"""

import asyncio
from typing import Dict, Any

from app.core.database import get_supabase
from app.core.mpesa_codes import get_mpesa_code_info
from app.models.schemas.reversal import ReversalRequest, ReversalResponse
from app.services.database_service import DatabaseService
from app.services.mpesa_client import MpesaClient
from app.utils.logger import logger


class ReversalService:
    """Serviço para reversão de transações"""

    def __init__(self):
        self.mpesa_client = MpesaClient()
        self.endpoint = "/ipg/v1x/reversal/"

        self.servico_db = DatabaseService(get_supabase())

    async def process_reversal(self, reversal_data: ReversalRequest) -> ReversalResponse:
        """Processa reversão de transação M-Pesa"""
        logger.info(f"🔄 Processando reversão da transação: {reversal_data.transaction_id}")

        try:
            # Prepara payload para M-Pesa (PUT method)
            payload_mpesa = {
                "input_TransactionID": reversal_data.transaction_id,
                "input_SecurityCredential": reversal_data.security_credential,
                "input_InitiatorIdentifier": reversal_data.initiator_identifier,
                "input_ThirdPartyReference": reversal_data.third_party_reference,
                "input_ServiceProviderCode": reversal_data.service_provider_code or "900579"
            }

            # Adiciona reversal amount se fornecido
            if reversal_data.reversal_amount is not None:
                payload_mpesa["input_ReversalAmount"] = str(reversal_data.reversal_amount)

            logger.info(f"📤 Enviando reversão para M-Pesa - TransactionID: {reversal_data.transaction_id}")

            # Log início da reversão
            asyncio.create_task(self._registrar_inicio_reversal(reversal_data))

            # Executa request M-Pesa (método PUT para reversal)
            resultado = self.mpesa_client.execute_request(self.endpoint, payload_mpesa, "reversal")

            logger.info(f"📥 Resposta reversão M-Pesa: {resultado['status_code']}")

            # Processa resposta M-Pesa
            resposta = self._processar_resposta_mpesa(resultado, reversal_data.third_party_reference)

            # Log resultado
            asyncio.create_task(
                self._registrar_resultado_reversal(reversal_data, resultado, resposta))

            return resposta

        except Exception as e:
            logger.error(f"❌ Erro no processamento da reversão: {str(e)}")

            # Log erro
            asyncio.create_task(self._registrar_erro_reversal(reversal_data, str(e)))

            return ReversalResponse(
                output_ConversationID=None,
                output_TransactionID=None,
                output_ResponseDesc=f"Erro no serviço: {str(e)}",
                output_ResponseCode="INS-999",
                output_ThirdPartyReference=reversal_data.third_party_reference
            )

    def _processar_resposta_mpesa(self, resultado: Dict[str, Any], third_party_ref: str) -> ReversalResponse:
        """Processa resposta M-Pesa da reversão"""
        if resultado["success"] and resultado["status_code"] == 200:
            dados_corpo = resultado["body"]
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-0')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            return ReversalResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_TransactionID=dados_corpo.get('output_TransactionID'),
                output_ResponseDesc=dados_corpo.get('output_ResponseDesc', info_codigo["message"]),
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref
            )
        else:
            dados_corpo = resultado.get("body", {})
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-999')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            descricao_mpesa = dados_corpo.get('output_ResponseDesc')
            descricao_final = descricao_mpesa if descricao_mpesa else info_codigo["message"]

            return ReversalResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_TransactionID=dados_corpo.get('output_TransactionID'),
                output_ResponseDesc=descricao_final,
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref
            )

    async def _registrar_inicio_reversal(self, reversal_data: ReversalRequest):
        """Registra início da reversão"""
        try:
            dados_log = {
                "transaction_reference": f"REVERSAL_{reversal_data.third_party_reference}",
                "third_party_reference": reversal_data.third_party_reference,
                "customer_msisdn": "N/A",  # Reversão não tem MSISDN específico
                "amount": reversal_data.reversal_amount or 0.0,
                "service_provider_code": reversal_data.service_provider_code or "900579",
                "status": "pending",
                "response_code": "PENDING",
                "response_description": f"Reversão iniciada para transação {reversal_data.transaction_id}",
                "api_key_used": "default",
                "transaction_type": "REVERSAL"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
        except Exception as e:
            logger.error(f"❌ Falha ao registrar início da reversão: {str(e)}")

    async def _registrar_resultado_reversal(self, reversal_data: ReversalRequest,
                                            resultado_mpesa: Dict[str, Any],
                                            resposta: ReversalResponse):
        """Registra resultado da reversão"""
        try:
            status = "success" if resposta.output_ResponseCode == "INS-0" else "failed"

            dados_log = {
                "transaction_reference": f"REVERSAL_{reversal_data.third_party_reference}",
                "third_party_reference": reversal_data.third_party_reference,
                "customer_msisdn": "N/A",  # Reversão não tem MSISDN específico
                "amount": reversal_data.reversal_amount or 0.0,
                "service_provider_code": reversal_data.service_provider_code or "900579",
                "status": status,
                "response_code": resposta.output_ResponseCode,
                "response_description": resposta.output_ResponseDesc,
                "mpesa_transaction_id": resposta.output_TransactionID,
                "mpesa_conversation_id": resposta.output_ConversationID,
                "api_key_used": "default",
                "transaction_type": "REVERSAL"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 Resultado reversão registrado: {reversal_data.transaction_id} - Status: {status}")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar resultado da reversão: {str(e)}")

    async def _registrar_erro_reversal(self, reversal_data: ReversalRequest, erro: str):
        """Registra erro na reversão"""
        try:
            dados_log = {
                "transaction_reference": f"REVERSAL_{reversal_data.third_party_reference}",
                "third_party_reference": reversal_data.third_party_reference,
                "customer_msisdn": "N/A",  # Reversão não tem MSISDN específico
                "amount": reversal_data.reversal_amount or 0.0,
                "service_provider_code": reversal_data.service_provider_code or "900579",
                "status": "failed",
                "response_code": "INS-999",
                "response_description": f"Erro reversão: {erro}",
                "api_key_used": "default",
                "transaction_type": "REVERSAL"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 Erro reversão registrado: {reversal_data.transaction_id}")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar erro da reversão: {str(e)}")
