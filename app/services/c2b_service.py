"""
Serviço de pagamentos C2B M-Pesa Mozambique
Versão com logs de diagnóstico completos
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_supabase
from app.core.config import settings
from app.core.mpesa_codes import get_mpesa_code_info
from app.models.schemas.c2b import C2BPaymentRequest, C2BPaymentResponse
from app.services.database_service import DatabaseService
from app.services.mpesa_client import MpesaClient
from app.utils.logger import logger


class C2BService:
    """
    Serviço C2B com estratégia híbrida para third_party_reference
    Shortcode sempre vem do .env - versão simplificada
    """

    def __init__(self):
        self.mpesa_client = MpesaClient()
        self.endpoint = "/ipg/v1x/c2bPayment/singleStage/"

        # Armazenamento em memória para tracking de referências
        self._referencias_utilizadas = set()

        # Serviço de database para logging assíncrono
        self.servico_db = DatabaseService(get_supabase())

    def _gerar_third_party_reference(self, referencia_transacao: str) -> str:
        """
        Gera um third_party_reference único com timestamp e parte aleatória
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        parte_aleatoria = uuid.uuid4().hex[:8]
        referencia_gerada = f"mpesa_{timestamp}_{parte_aleatoria}"
        logger.info(f"🔑 Third_party_reference gerado: {referencia_gerada}")
        return referencia_gerada

    def _verificar_referencia_unica(self, third_party_ref: str) -> bool:
        """
        Verifica se um third_party_reference é único
        """
        unica = third_party_ref not in self._referencias_utilizadas
        if not unica:
            logger.warning(f"🚫 Third_party_reference duplicado: {third_party_ref}")
        else:
            logger.debug(f"✅ Third_party_reference é único: {third_party_ref}")
        return unica

    def _armazenar_mapeamento_referencia(self, referencia_transacao: str, third_party_ref: str):
        """
        Armazena o mapeamento entre transaction_reference e third_party_reference
        """
        self._referencias_utilizadas.add(third_party_ref)
        logger.debug(f"💾 Mapeamento armazenado: {referencia_transacao} -> {third_party_ref}")

    def _obter_third_party_reference(self, dados_pagamento: C2BPaymentRequest) -> str:
        """
        Estratégia híbrida para geração de third_party_reference
        """
        # Caso 1: Cliente forneceu third_party_reference E é único
        if dados_pagamento.third_party_reference:
            ref_cliente = dados_pagamento.third_party_reference
            if self._verificar_referencia_unica(ref_cliente):
                logger.info(f"🎯 Usando third_party_reference do cliente: {ref_cliente}")
                return ref_cliente
            else:
                # Caso 2: Cliente forneceu mas é duplicado
                logger.warning(f"🔄 Referência duplicada, gerando nova: {ref_cliente}")
                ref_gerada = self._gerar_third_party_reference(dados_pagamento.transaction_reference)
                logger.info(f"🔄 Duplicado substituído: {ref_cliente} → {ref_gerada}")
                return ref_gerada
        else:
            # Caso 3: Cliente não forneceu third_party_reference
            logger.info("🔄 Cliente não forneceu third_party_reference, gerando automaticamente")
            return self._gerar_third_party_reference(dados_pagamento.transaction_reference)

    async def process_payment(self, dados_pagamento: C2BPaymentRequest) -> C2BPaymentResponse:
        """
        Processa pagamento C2B - versão com diagnóstico completo
        """
        logger.info(f"🔄 PROCESSANDO C2B: {dados_pagamento.transaction_reference}")

        try:
            # ✅ ESTRATÉGIA HÍBRIDA: Obtém third_party_reference
            third_party_ref = self._obter_third_party_reference(dados_pagamento)

            # Armazena o mapeamento
            self._armazenar_mapeamento_referencia(
                referencia_transacao=dados_pagamento.transaction_reference,
                third_party_ref=third_party_ref
            )

            # ✅ PAYLOAD SIMPLIFICADO: Shortcode SEMPRE do .env
            payload_mpesa = {
                "input_TransactionReference": dados_pagamento.transaction_reference,
                "input_ThirdPartyReference": third_party_ref,
                "input_CustomerMSISDN": dados_pagamento.customer_msisdn,
                "input_Amount": str(dados_pagamento.amount),
                "input_ServiceProviderCode": settings.MPESA_SERVICE_PROVIDER_CODE
            }

            logger.info(f"📤 ENVIANDO C2B PARA MPESA:")
            logger.info(f"Shortcode: {settings.MPESA_SERVICE_PROVIDER_CODE}")
            logger.info(f"Transaction Ref: {dados_pagamento.transaction_reference}")
            logger.info(f"ThirdParty Ref: {third_party_ref}")
            logger.info(f"Customer: {dados_pagamento.customer_msisdn}")
            logger.info(f"Amount: {dados_pagamento.amount}")

            # ✅ LOG ASSÍNCRONO
            asyncio.create_task(self._registrar_inicio_transacao(dados_pagamento, third_party_ref))

            # Executa request M-Pesa
            resultado = self.mpesa_client.execute_request(self.endpoint, payload_mpesa, "c2b")

            logger.info(f"📥 RESPOSTA BRUTA DA MPESA:")
            logger.info(f"Status Code: {resultado.get('status_code')}")
            logger.info(f"Success Flag: {resultado.get('success')}")

            # Processa resposta
            resposta = self._processar_resposta_mpesa(resultado, third_party_ref)

            # ✅ LOG ASSÍNCRONO do resultado
            asyncio.create_task(
                self._registrar_resultado_transacao(dados_pagamento, third_party_ref, resultado, resposta))

            logger.info(f"🎯 RESPOSTA FINAL DO C2B:")
            logger.info(f"Response Code: {resposta.response_code}")
            logger.info(f"Response Desc: {resposta.response_description}")

            return resposta

        except Exception as e:
            logger.error(f"❌ ERRO NO PROCESSAMENTO C2B: {str(e)}")
            ref_erro = third_party_ref if 'third_party_ref' in locals() else "ref_erro"
            asyncio.create_task(self._registrar_erro_transacao(dados_pagamento, ref_erro, str(e)))
            
            return C2BPaymentResponse(
                transaction_id=None,
                conversation_id=None,
                third_party_reference=ref_erro,
                response_code="INS-999",
                response_description=f"Erro no serviço: {str(e)}"
            )

    def _processar_resposta_mpesa(self, resultado: Dict[str, Any], third_party_ref: str) -> C2BPaymentResponse:
        """
        Processa resposta M-Pesa com logging detalhado
        """
        # ✅ LOG DETALHADO DO RESULTADO
        logger.info(f"🔍 PROCESSANDO RESPOSTA DA MPESA:")
        logger.info(f"Success flag: {resultado.get('success')}")
        logger.info(f"Status code: {resultado.get('status_code')}")
        logger.info(f"Body type: {type(resultado.get('body'))}")
        logger.info(f"Full result keys: {resultado.keys()}")

        # Verificar se temos um body válido
        if 'body' not in resultado or resultado['body'] is None:
            logger.error("❌ RESPOSTA DA MPESA SEM BODY!")
            return C2BPaymentResponse(
                transaction_id=None,
                conversation_id=None,
                third_party_reference=third_party_ref,
                response_code="INS-999",
                response_description="Resposta inválida da M-Pesa (sem body)"
            )

        body_data = resultado['body']
        logger.info(f"📋 BODY CONTENT: {body_data}")

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
                    logger.error(f"❌ Não foi possível parsear o body: {body_data}")
                    dados_corpo = {}

            logger.info(f"✅ RESPOSTA DE SUCESSO DA MPESA: {dados_corpo}")
            
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-0')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            logger.info(f"✅ Código de resposta: {codigo_resposta}")
            logger.info(f"✅ Descrição: {info_codigo['message']}")

            return C2BPaymentResponse(
                transaction_id=dados_corpo.get('output_TransactionID'),
                conversation_id=dados_corpo.get('output_ConversationID'),
                third_party_reference=third_party_ref,
                response_code=codigo_resposta,
                response_description=info_codigo["message"]
            )
        else:
            # ✅ ERRO
            logger.error(f"❌ RESPOSTA DE ERRO DA MPESA: {body_data}")
            
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
                    logger.error(f"❌ Não foi possível parsear o body de erro: {body_data}")
                    dados_corpo = {}

            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-999')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            descricao_mpesa = dados_corpo.get('output_ResponseDesc')
            descricao_final = descricao_mpesa if descricao_mpesa else info_codigo["message"]

            # ✅ LOG DO CÓDIGO DE ERRO ESPECÍFICO
            logger.error(f"❌ CÓDIGO DE ERRO MPESA: {codigo_resposta}")
            logger.error(f"❌ DESCRIÇÃO DO ERRO: {descricao_final}")
            logger.error(f"❌ THIRD PARTY REF: {third_party_ref}")

            return C2BPaymentResponse(
                transaction_id=dados_corpo.get('output_TransactionID'),
                conversation_id=dados_corpo.get('output_ConversationID'),
                third_party_reference=third_party_ref,
                response_code=codigo_resposta,
                response_description=descricao_final
            )

    # ✅ MÉTODOS DE LOGGING ASSÍNCRONO

    async def _registrar_inicio_transacao(self, dados_pagamento: C2BPaymentRequest, third_party_ref: str):
        """Registra início da transação de forma assíncrona"""
        try:
            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": settings.MPESA_SERVICE_PROVIDER_CODE,
                "status": "pending",
                "response_code": "PENDING",
                "response_description": "Transação iniciada",
                "api_key_used": "default"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📝 Log de início registrado: {dados_pagamento.transaction_reference}")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar início da transação: {str(e)}")

    async def _registrar_resultado_transacao(self, dados_pagamento: C2BPaymentRequest, third_party_ref: str,
                                             resultado_mpesa: Dict[str, Any], resposta: C2BPaymentResponse):
        """Registra resultado da transação de forma assíncrona"""
        try:
            status = "success" if resposta.response_code == "INS-0" else "failed"

            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": settings.MPESA_SERVICE_PROVIDER_CODE,
                "status": status,
                "response_code": resposta.response_code,
                "response_description": resposta.response_description,
                "mpesa_transaction_id": resposta.transaction_id,
                "mpesa_conversation_id": resposta.conversation_id,
                "api_key_used": "default"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 Resultado registrado: {dados_pagamento.transaction_reference} - Status: {status}")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar resultado da transação: {str(e)}")

    async def _registrar_erro_transacao(self, dados_pagamento: C2BPaymentRequest, third_party_ref: str, erro: str):
        """Registra erro na transação de forma assíncrona"""
        try:
            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": settings.MPESA_SERVICE_PROVIDER_CODE,
                "status": "failed",
                "response_code": "INS-999",
                "response_description": f"Erro no serviço: {erro}",
                "api_key_used": "default"
            }
            await self.servico_db.registrar_transacao_async(dados_log)
            logger.debug(f"📊 Erro registrado: {dados_pagamento.transaction_reference}")
        except Exception as e:
            logger.error(f"❌ Falha ao registrar erro da transação: {str(e)}")

    async def obter_estatisticas_logging(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema de logging"""
        return self.servico_db.obter_estatisticas()