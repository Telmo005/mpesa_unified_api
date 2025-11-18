# app/services/b2c_service.py
"""
Serviço de pagamentos B2C M-Pesa Mozambique
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_supabase
from app.core.mpesa_codes import get_mpesa_code_info
from app.models.schemas.b2c import B2CPaymentRequest, B2CPaymentResponse
from app.services.database_service import DatabaseService
from app.services.mpesa_client import MpesaClient
from app.utils.logger import logger


class B2CService:
    """Serviço para processamento de transações Business-to-Customer"""

    def __init__(self):
        self.mpesa_client = MpesaClient()
        self.endpoint = "/ipg/v1x/b2cPayment/"

        self._referencias_utilizadas = set()
        self.servico_db = DatabaseService(get_supabase())

    def _gerar_third_party_reference(self, referencia_transacao: str) -> str:
        """Gera um third_party_reference único com timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        parte_aleatoria = uuid.uuid4().hex[:8]
        referencia_gerada = f"b2c_{timestamp}_{parte_aleatoria}"
        logger.info(f"🔑 B2C Third_party_reference gerado: {referencia_gerada}")
        return referencia_gerada

    def _verificar_referencia_unica(self, third_party_ref: str) -> bool:
        """Verifica se um third_party_reference é único"""
        unica = third_party_ref not in self._referencias_utilizadas
        if not unica:
            logger.warning(f"🚫 B2C Third_party_reference duplicado detectado: {third_party_ref}")
        else:
            logger.debug(f"✅ B2C Third_party_reference é único: {third_party_ref}")
        return unica

    def _armazenar_mapeamento_referencia(self, referencia_transacao: str, third_party_ref: str):
        """Armazena o mapeamento entre referências"""
        self._referencias_utilizadas.add(third_party_ref)
        logger.debug(f"💾 B2C Mapeamento armazenado: {referencia_transacao} -> {third_party_ref}")

    def _obter_third_party_reference(self, dados_pagamento: B2CPaymentRequest) -> str:
        """Estratégia híbrida para geração de third_party_reference"""
        if dados_pagamento.third_party_reference:
            ref_cliente = dados_pagamento.third_party_reference
            if self._verificar_referencia_unica(ref_cliente):
                logger.info(f"🎯 B2C Usando third_party_reference do cliente: {ref_cliente}")
                return ref_cliente
            else:
                logger.warning(f"🔄 B2C Referência do cliente é duplicada, gerando nova: {ref_cliente}")
                ref_gerada = self._gerar_third_party_reference(dados_pagamento.transaction_reference)
                logger.info(f"🔄 B2C Duplicado substituído: {ref_cliente} → {ref_gerada}")
                return ref_gerada
        else:
            logger.info("🔄 B2C Cliente não forneceu third_party_reference, gerando automaticamente")
            return self._gerar_third_party_reference(dados_pagamento.transaction_reference)

    async def process_payment(self, dados_pagamento: B2CPaymentRequest) -> B2CPaymentResponse:
        """Processa pagamento B2C"""
        logger.info(f"🔄 Processando B2C: {dados_pagamento.transaction_reference}")

        try:
            third_party_ref = self._obter_third_party_reference(dados_pagamento)

            self._armazenar_mapeamento_referencia(
                referencia_transacao=dados_pagamento.transaction_reference,
                third_party_ref=third_party_ref
            )

            payload_mpesa = {
                "input_TransactionReference": dados_pagamento.transaction_reference,
                "input_CustomerMSISDN": dados_pagamento.customer_msisdn,
                "input_Amount": str(dados_pagamento.amount),
                "input_ThirdPartyReference": third_party_ref,
                "input_ServiceProviderCode": dados_pagamento.service_provider_code or "900579"
            }

            logger.info(f"📤 Enviando B2C para M-Pesa - Transação: {dados_pagamento.transaction_reference}, ThirdParty: {third_party_ref}")

            asyncio.create_task(self._registrar_inicio_transacao(dados_pagamento, third_party_ref))

            resultado = self.mpesa_client.execute_request(self.endpoint, payload_mpesa, "b2c")

            logger.info(f"📥 Resposta B2C M-Pesa: {resultado['status_code']}")

            resposta = self._processar_resposta_mpesa(resultado, third_party_ref)

            asyncio.create_task(
                self._registrar_resultado_transacao(dados_pagamento, third_party_ref, resultado, resposta))

            return resposta

        except Exception as e:
            logger.error(f"❌ Erro no processamento B2C: {str(e)}")

            ref_erro = third_party_ref if 'third_party_ref' in locals() else "b2c_ref_erro"
            asyncio.create_task(self._registrar_erro_transacao(dados_pagamento, ref_erro, str(e)))

            return B2CPaymentResponse(
                output_ConversationID=None,
                output_TransactionID=None,
                output_ResponseDesc=f"Erro no serviço: {str(e)}",
                output_ResponseCode="INS-999",
                output_ThirdPartyReference=ref_erro
            )

    def _processar_resposta_mpesa(self, resultado: Dict[str, Any], third_party_ref: str) -> B2CPaymentResponse:
        """Processa resposta M-Pesa B2C"""
        if resultado["success"] and resultado["status_code"] == 200:
            dados_corpo = resultado["body"]
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-0')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            return B2CPaymentResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_TransactionID=dados_corpo.get('output_TransactionID'),
                output_ResponseDesc=info_codigo["message"],
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref
            )
        else:
            dados_corpo = resultado.get("body", {})
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-999')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            descricao_mpesa = dados_corpo.get('output_ResponseDesc')
            descricao_final = descricao_mpesa if descricao_mpesa else info_codigo["message"]

            return B2CPaymentResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_TransactionID=dados_corpo.get('output_TransactionID'),
                output_ResponseDesc=descricao_final,
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref
            )

    async def _registrar_inicio_transacao(self, dados_pagamento: B2CPaymentRequest, third_party_ref: str):
        """Registra início da transação B2C"""
        try:
            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": dados_pagamento.service_provider_code or "900579",
                "status": "pending",
                "response_code": "PENDING",
                "response_description": "Transação B2C iniciada",
                "api_key_used": "default",
                "transaction_type": "B2C"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
        except Exception as e:
            logger.error(f"❌ B2C Falha ao registrar início da transação: {str(e)}")

    async def _registrar_resultado_transacao(self, dados_pagamento: B2CPaymentRequest, third_party_ref: str,
                                             resultado_mpesa: Dict[str, Any], resposta: B2CPaymentResponse):
        """Registra resultado da transação B2C"""
        try:
            status = "success" if resposta.output_ResponseCode == "INS-0" else "failed"

            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": dados_pagamento.service_provider_code or "900579",
                "status": status,
                "response_code": resposta.output_ResponseCode,
                "response_description": resposta.output_ResponseDesc,
                "mpesa_transaction_id": resposta.output_TransactionID,
                "mpesa_conversation_id": resposta.output_ConversationID,
                "api_key_used": "default",
                "transaction_type": "B2C"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 B2C Resultado registrado para: {dados_pagamento.transaction_reference} - Status: {status}")
        except Exception as e:
            logger.error(f"❌ B2C Falha ao registrar resultado da transação: {str(e)}")

    async def _registrar_erro_transacao(self, dados_pagamento: B2CPaymentRequest, third_party_ref: str, erro: str):
        """Registra erro na transação B2C"""
        try:
            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": dados_pagamento.service_provider_code or "900579",
                "status": "failed",
                "response_code": "INS-999",
                "response_description": f"Erro B2C: {erro}",
                "api_key_used": "default",
                "transaction_type": "B2C"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 B2C Erro registrado para: {dados_pagamento.transaction_reference}")
        except Exception as e:
            logger.error(f"❌ B2C Falha ao registrar erro da transação: {str(e)}")