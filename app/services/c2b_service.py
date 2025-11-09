# app/services/c2b_service.py
"""
Serviço de pagamentos C2B M-Pesa Mozambique
Com estratégia híbrida para third_party_reference e logging assíncrono
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_supabase
from app.core.mpesa_codes import get_mpesa_code_info
from app.models.schemas.c2b import C2BPaymentRequest, C2BPaymentResponse
# Import do database service para logging assíncrono
from app.services.database_service import DatabaseService
from app.services.mpesa_client import MpesaClient
from app.utils.logger import logger


class C2BService:
    """
    Serviço C2B com estratégia híbrida para third_party_reference
    Suporta referências fornecidas pelo cliente e auto-geradas
    """

    def __init__(self):
        self.mpesa_client = MpesaClient()
        self.endpoint = "/ipg/v1x/c2bPayment/singleStage/"

        # Armazenamento em memória para tracking de referências (em produção usar Redis)
        self._referencias_utilizadas = set()

        # Serviço de database para logging assíncrono
        self.servico_db = DatabaseService(get_supabase())

    def _gerar_third_party_reference(self, referencia_transacao: str) -> str:
        """
        Gera um third_party_reference único com timestamp e parte aleatória

        Args:
            referencia_transacao: Referência original da transação para contexto

        Returns:
            str: Third_party_reference único
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        parte_aleatoria = uuid.uuid4().hex[:8]  # 8 caracteres para unicidade

        referencia_gerada = f"mpesa_{timestamp}_{parte_aleatoria}"
        logger.info(f"🔑 Third_party_reference gerado: {referencia_gerada}")

        return referencia_gerada

    def _verificar_referencia_unica(self, third_party_ref: str) -> bool:
        """
        Verifica se um third_party_reference é único
        Em produção, deve verificar contra uma base de dados

        Args:
            third_party_ref: Referência a verificar

        Returns:
            bool: True se único, False se duplicado
        """
        unica = third_party_ref not in self._referencias_utilizadas

        if not unica:
            logger.warning(f"🚫 Third_party_reference duplicado detectado: {third_party_ref}")
        else:
            logger.debug(f"✅ Third_party_reference é único: {third_party_ref}")

        return unica

    def _armazenar_mapeamento_referencia(self, referencia_transacao: str, third_party_ref: str):
        """
        Armazena o mapeamento entre transaction_reference e third_party_reference
        Em produção, deve persistir numa base de dados

        Args:
            referencia_transacao: Referência da transação do cliente
            third_party_ref: Third_party_reference gerado
        """
        # Armazena em memória (substituir por base de dados em produção)
        self._referencias_utilizadas.add(third_party_ref)

        logger.debug(f"💾 Mapeamento armazenado: {referencia_transacao} -> {third_party_ref}")

    def _obter_third_party_reference(self, dados_pagamento: C2BPaymentRequest) -> str:
        """
        Estratégia híbrida para geração de third_party_reference

        Regras:
        1. Se cliente fornece third_party_reference E é único → Usa do cliente
        2. Se cliente fornece mas NÃO é único → Gera novo
        3. Se cliente não fornece → Gera novo

        Args:
            dados_pagamento: Dados do pedido de pagamento

        Returns:
            str: Third_party_reference a utilizar
        """
        # Caso 1: Cliente forneceu third_party_reference
        if dados_pagamento.third_party_reference:
            ref_cliente = dados_pagamento.third_party_reference

            # Valida se a referência do cliente é única
            if self._verificar_referencia_unica(ref_cliente):
                logger.info(f"🎯 Usando third_party_reference do cliente: {ref_cliente}")
                return ref_cliente
            else:
                # Caso 2: Cliente forneceu mas é duplicado
                logger.warning(f"🔄 Referência do cliente é duplicada, gerando nova: {ref_cliente}")
                ref_gerada = self._gerar_third_party_reference(dados_pagamento.transaction_reference)
                logger.info(f"🔄 Duplicado substituído: {ref_cliente} → {ref_gerada}")
                return ref_gerada
        else:
            # Caso 3: Cliente não forneceu third_party_reference
            logger.info("🔄 Cliente não forneceu third_party_reference, gerando automaticamente")
            return self._gerar_third_party_reference(dados_pagamento.transaction_reference)

    async def process_payment(self, dados_pagamento: C2BPaymentRequest) -> C2BPaymentResponse:
        """
        Processa pagamento C2B com estratégia híbrida para third_party_reference
        E logging assíncrono para melhor performance

        Args:
            dados_pagamento: Dados do pedido de pagamento

        Returns:
            C2BPaymentResponse: Resultado do processamento
        """
        logger.info(f"🔄 Processando C2B: {dados_pagamento.transaction_reference}")

        try:
            # ✅ ESTRATÉGIA HÍBRIDA: Obtém third_party_reference usando nossas regras
            third_party_ref = self._obter_third_party_reference(dados_pagamento)

            # Armazena o mapeamento para referência futura
            self._armazenar_mapeamento_referencia(
                referencia_transacao=dados_pagamento.transaction_reference,
                third_party_ref=third_party_ref
            )

            # Prepara payload M-Pesa
            payload_mpesa = {
                "input_TransactionReference": dados_pagamento.transaction_reference,
                "input_ThirdPartyReference": third_party_ref,
                "input_CustomerMSISDN": dados_pagamento.customer_msisdn,
                "input_Amount": str(dados_pagamento.amount),
                "input_ServiceProviderCode": dados_pagamento.service_provider_code or "171717"
            }

            logger.info(
                f"📤 Enviando para M-Pesa - Transação: {dados_pagamento.transaction_reference}, ThirdParty: {third_party_ref}")

            # ✅ LOG ASSÍNCRONO: Registra início da transação (não bloqueia)
            asyncio.create_task(self._registrar_inicio_transacao(dados_pagamento, third_party_ref))

            # Executa request M-Pesa (síncrono - mantém lógica principal)
            resultado = self.mpesa_client.execute_request(self.endpoint, payload_mpesa, "c2b")

            logger.info(f"📥 Resposta M-Pesa: {resultado['status_code']}")

            # Processa resposta M-Pesa
            resposta = self._processar_resposta_mpesa(resultado, third_party_ref)

            # ✅ LOG ASSÍNCRONO: Registra resultado (não bloqueia resposta)
            asyncio.create_task(
                self._registrar_resultado_transacao(dados_pagamento, third_party_ref, resultado, resposta))

            # ⚡ RETORNO IMEDIATO: Cliente recebe resposta antes do logging completar
            return resposta

        except Exception as e:
            logger.error(f"❌ Erro no processamento C2B: {str(e)}")

            # ✅ LOG ASSÍNCRONO: Registra erro
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
        Processa resposta M-Pesa com mapeamento adequado de códigos

        Args:
            resultado: Resposta da API M-Pesa
            third_party_ref: Third_party_reference usado no pedido

        Returns:
            C2BPaymentResponse: Resposta processada
        """
        if resultado["success"] and resultado["status_code"] == 200:
            dados_corpo = resultado["body"]
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-0')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            return C2BPaymentResponse(
                transaction_id=dados_corpo.get('output_TransactionID'),
                conversation_id=dados_corpo.get('output_ConversationID'),
                third_party_reference=third_party_ref,
                response_code=codigo_resposta,
                response_description=info_codigo["message"]
            )
        else:
            # Processa respostas de erro M-Pesa
            dados_corpo = resultado.get("body", {})
            codigo_resposta = dados_corpo.get('output_ResponseCode', 'INS-999')
            info_codigo = get_mpesa_code_info(codigo_resposta)

            descricao_mpesa = dados_corpo.get('output_ResponseDesc')
            descricao_final = descricao_mpesa if descricao_mpesa else info_codigo["message"]

            return C2BPaymentResponse(
                transaction_id=dados_corpo.get('output_TransactionID'),
                conversation_id=dados_corpo.get('output_ConversationID'),
                third_party_reference=third_party_ref,
                response_code=codigo_resposta,
                response_description=descricao_final
            )

    # ✅ MÉTODOS DE LOGGING ASSÍNCRONO (NOVOS)

    async def _registrar_inicio_transacao(self, dados_pagamento: C2BPaymentRequest, third_party_ref: str):
        """Registra início da transação de forma assíncrona"""
        try:
            dados_log = {
                "transaction_reference": dados_pagamento.transaction_reference,
                "third_party_reference": third_party_ref,
                "customer_msisdn": dados_pagamento.customer_msisdn,
                "amount": float(dados_pagamento.amount),
                "service_provider_code": dados_pagamento.service_provider_code or "171717",
                "status": "pending",
                "response_code": "PENDING",
                "response_description": "Transação iniciada",
                "api_key_used": "default"  # Pode adicionar info da API key depois
            }
            # ⚡ ASSÍNCRONO - não bloqueia
            await self.servico_db.registrar_transacao_async(dados_log)
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
                "service_provider_code": dados_pagamento.service_provider_code or "171717",
                "status": status,
                "response_code": resposta.response_code,
                "response_description": resposta.response_description,
                # ✅ AGORA SALVA TODOS OS CAMPOS M-PESA PARA AUDITORIA
                "mpesa_transaction_id": resposta.transaction_id,
                "mpesa_conversation_id": resposta.conversation_id,
                "api_key_used": "default"
            }
            # ⚡ ASSÍNCRONO - não bloqueia
            await self.servico_db.registrar_transacao_async(dados_log)

            logger.debug(f"📊 Resultado registrado para: {dados_pagamento.transaction_reference} - Status: {status}")

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
                "service_provider_code": dados_pagamento.service_provider_code or "171717",
                "status": "failed",
                "response_code": "INS-999",
                "response_description": f"Erro no serviço: {erro}",
                "api_key_used": "default"
            }
            # ⚡ ASSÍNCRONO - não bloqueia
            await self.servico_db.registrar_transacao_async(dados_log)

            logger.debug(f"📊 Erro registrado para: {dados_pagamento.transaction_reference}")

        except Exception as e:
            logger.error(f"❌ Falha ao registrar erro da transação: {str(e)}")

    async def obter_estatisticas_logging(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do sistema de logging

        Returns:
            Dict com estatísticas atuais
        """
        return self.servico_db.obter_estatisticas()
