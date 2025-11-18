# app/services/b2c_service.py
"""
Serviço de pagamentos B2C M-Pesa Mozambique
Versão atualizada seguindo padrão C2B - Shortcode sempre do .env
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_supabase
from app.core.config import settings  # ✅ IMPORT DAS CONFIGURAÇÕES
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
            logger.warning(f"🚫 B2C Third_party_reference duplicado: {third_party_ref}")
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
                logger.warning(f"🔄 B2C Referência duplicada, gerando nova: {ref_cliente}")
                ref_gerada = self._gerar_third_party_reference(dados_pagamento.transaction_reference)
                logger.info(f"🔄 B2C Duplicado substituído: {ref_cliente} → {ref_gerada}")
                return ref_gerada
        else:
            logger.info("🔄 B2C Cliente não forneceu third_party_reference, gerando automaticamente")
            return self._gerar_third_party_reference(dados_pagamento.transaction_reference)

    async def process_payment(self, dados_pagamento: B2CPaymentRequest) -> B2CPaymentResponse:
        """Processa pagamento B2C - versão atualizada"""
        logger.info(f"🔄 PROCESSANDO B2C: {dados_pagamento.transaction_reference}")

        try:
            third_party_ref = self._obter_third_party_reference(dados_pagamento)

            self._armazenar_mapeamento_referencia(
                referencia_transacao=dados_pagamento.transaction_reference,
                third_party_ref=third_party_ref
            )

            # ✅ PAYLOAD ATUALIZADO: Shortcode SEMPRE do .env
            payload_mpesa = {
                "input_TransactionReference": dados_pagamento.transaction_reference,
                "input_CustomerMSISDN": dados_pagamento.customer_msisdn,
                "input_Amount": str(dados_pagamento.amount),
                "input_ThirdPartyReference": third_party_ref,
                "input_ServiceProviderCode": settings.MPESA_SERVICE_PROVIDER_CODE  # ✅ SEMPRE do .env
            }

            logger.info(f"📤 ENVIANDO B2C PARA MPESA:")
            logger.info(f"Shortcode: {settings.MPESA_SERVICE_PROVIDER_CODE}")
            logger.info(f"Transaction Ref: {dados_pagamento.transaction_reference}")
            logger.info(f"ThirdParty Ref: {third_party_ref}")
            logger.info(f"Customer: {dados_pagamento.customer_msisdn}")
            logger.info(f"Amount: {dados_pagamento.amount}")

            asyncio.create_task(self._registrar_inicio_transacao(dados_pagamento, third_party_ref))

            resultado = self.mpesa_client.execute_request(self.endpoint, payload_mpesa, "b2c")

            logger.info(f"📥 RESPOSTA BRUTA B2C:")
            logger.info(f"Status Code: {resultado.get('status_code')}")
            logger.info(f"Success Flag: {resultado.get('success')}")

            resposta = self._processar_resposta_mpesa(resultado, third_party_ref)

            asyncio.create_task(
                self._registrar_resultado_transacao(dados_pagamento, third_party_ref, resultado, resposta))

            logger.info(f"🎯 RESPOSTA FINAL B2C:")
            logger.info(f"Response Code: {resposta.output_ResponseCode}")
            logger.info(f"Response Desc: {resposta.output_ResponseDesc}")

            return resposta

        except Exception as e:
            logger.error(f"❌ ERRO NO PROCESSAMENTO B2C: {str(e)}")

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
        """Processa resposta M-Pesa B2C com logging detalhado"""
        # ✅ LOG DETALHADO DO RESULTADO
        logger.info(f"🔍 PROCESSANDO RESPOSTA B2C DA MPESA:")
        logger.info(f"Success flag: {resultado.get('success')}")
        logger.info(f"Status code: {resultado.get('status_code')}")
        logger.info(f"Body type: {type(resultado.get('body'))}")

        # Verificar se temos um body válido
        if 'body' not in resultado or resultado['body'] is None:
            logger.error("❌ RESPOSTA B2C DA MPESA SEM BODY!")
            return B2CPaymentResponse(
                output_ConversationID=None,
                output_TransactionID=None,
                output_ResponseDesc="Resposta inválida da M-Pesa (sem body)",
                output_ResponseCode="INS-999",
                output_ThirdPartyReference=third_party_ref
            )

        body_data = resultado['body']
        logger.info(f"📋 B2C BODY CONTENT: {body_data}")

        if resultado.get("success") and resultado.get("status_code") in [200, 201]:
            # ✅ SUCESSO
            if isinstance(body_data, dict):
                dados_corpo = body_data
            else:
                # Tentar converter para dict se for string
                try:
                    if isinstance(body_data, str):
                        import json
                        dados_corpo = json.loads(body_data)
                    else:
                        dados_corpo = body_data
                except:
                    logger.error(f"❌ Não foi possível parsear o body B2C: {body_data}")
                    dados_corpo = {}

            logger.info(f"✅ RESPOSTA DE SUCESSO B2C: {dados_corpo}")
            
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-0')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            logger.info(f"✅ Código de resposta B2C: {codigo_resposta}")
            logger.info(f"✅ Descrição B2C: {info_codigo['message']}")

            return B2CPaymentResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_TransactionID=dados_corpo.get('output_TransactionID'),
                output_ResponseDesc=info_codigo["message"],
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref
            )
        else:
            # ✅ ERRO
            logger.error(f"❌ RESPOSTA DE ERRO B2C: {body_data}")
            
            if isinstance(body_data, dict):
                dados_corpo = body_data
            else:
                # Tentar converter para dict se for string
                try:
                    if isinstance(body_data, str):
                        import json
                        dados_corpo = json.loads(body_data)
                    else:
                        dados_corpo = body_data
                except:
                    logger.error(f"❌ Não foi possível parsear o body de erro B2C: {body_data}")
                    dados_corpo = {}

            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-999')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            descricao_mpesa = dados_corpo.get('output_ResponseDesc')
            descricao_final = descricao_mpesa if descricao_mpesa else info_codigo["message"]

            # ✅ LOG DO CÓDIGO DE ERRO ESPECÍFICO
            logger.error(f"❌ CÓDIGO DE ERRO B2C: {codigo_resposta}")
            logger.error(f"❌ DESCRIÇÃO DO ERRO B2C: {descricao_final}")

            return B2CPaymentResponse(
                output_ConversationID=dados_corpo.get('output_ConversationID'),
                output_TransactionID=dados_corpo.get('output_TransactionID'),
                output_ResponseDesc=descricao_final,
                output_ResponseCode=codigo_resposta,
                output_ThirdPartyReference=third_party_ref
            )

    # ✅ MÉTODOS DE LOGGING ATUALIZADOS

    async def _registrar_inicio_transacao(self, dados_pagamento: B2CPaymentRequest, third_party_ref: str):
        """Registra início da transação B2C"""
        try:
            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": settings.MPESA_SERVICE_PROVIDER_CODE,  # ✅ SEMPRE do .env
                "status": "pending",
                "response_code": "PENDING",
                "response_description": "Transação B2C iniciada",
                "api_key_used": "default",
                "transaction_type": "B2C"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📝 B2C Log de início registrado: {dados_pagamento.transaction_reference}")
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
                "service_provider_code": settings.MPESA_SERVICE_PROVIDER_CODE,  # ✅ SEMPRE do .env
                "status": status,
                "response_code": resposta.output_ResponseCode,
                "response_description": resposta.output_ResponseDesc,
                "mpesa_transaction_id": resposta.output_TransactionID,
                "mpesa_conversation_id": resposta.output_ConversationID,
                "api_key_used": "default",
                "transaction_type": "B2C"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 B2C Resultado registrado: {dados_pagamento.transaction_reference} - Status: {status}")
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
                "service_provider_code": settings.MPESA_SERVICE_PROVIDER_CODE,  # ✅ SEMPRE do .env
                "status": "failed",
                "response_code": "INS-999",
                "response_description": f"Erro B2C: {erro}",
                "api_key_used": "default",
                "transaction_type": "B2C"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 B2C Erro registrado: {dados_pagamento.transaction_reference}")
        except Exception as e:
            logger.error(f"❌ B2C Falha ao registrar erro da transação: {str(e)}")