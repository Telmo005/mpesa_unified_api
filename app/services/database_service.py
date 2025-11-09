# app/services/database_service.py
"""
Serviço de database para registro assíncrono de logs de auditoria
Implementa fila em background para não impactar performance das transações M-Pesa
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from supabase import Client
import logging

logger = logging.getLogger("mpesa_api")


class DatabaseService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self._fila_logs = asyncio.Queue()
        self._processando = False
        self._total_logs_processados = 0
        self._total_logs_falha = 0

    async def registrar_transacao_async(self, dados_transacao: Dict[str, Any]) -> None:
        """
        Registra transação de forma assíncrona - não bloqueia a resposta principal

        Args:
            dados_transacao: Dicionário com dados da transação para auditoria
        """
        try:
            # Adiciona à fila e retorna imediatamente
            await self._fila_logs.put(dados_transacao)
            logger.debug(f"📦 Log enfileirado: {dados_transacao['transaction_reference']}")

            # Inicia o processamento em background se não estiver rodando
            if not self._processando:
                asyncio.create_task(self._processar_fila_logs())
                logger.info("🔄 Iniciando processamento da fila de logs em background")

        except Exception as e:
            logger.error(f"❌ Falha ao enfileirar log: {str(e)}")
            # Fallback imediato para log local
            self._salvar_fallback_local(dados_transacao, "erro_fila")

    async def _processar_fila_logs(self):
        """
        Processa a fila de logs em background com sistema de retry
        """
        self._processando = True
        logger.info("🎯 Processador de logs iniciado")

        try:
            while not self._fila_logs.empty():
                try:
                    # Pega item da fila com timeout
                    dados_transacao = await asyncio.wait_for(
                        self._fila_logs.get(), timeout=2.0
                    )

                    # Tenta salvar no Supabase com retry
                    sucesso = await self._salvar_com_retry(dados_transacao)

                    if sucesso:
                        self._total_logs_processados += 1
                        logger.debug(f"✅ Log processado: {dados_transacao['transaction_reference']}")
                    else:
                        self._total_logs_falha += 1
                        # Fallback: salva localmente
                        self._salvar_fallback_local(dados_transacao, "erro_supabase")

                    self._fila_logs.task_done()

                except asyncio.TimeoutError:
                    logger.debug("⏰ Timeout da fila - aguardando novos logs")
                    break
                except Exception as e:
                    logger.error(f"❌ Erro ao processar item da fila: {str(e)}")
                    self._fila_logs.task_done()

        except Exception as e:
            logger.error(f"💥 Erro crítico no processador de logs: {str(e)}")
        finally:
            self._processando = False
            logger.info(
                f"⏹️ Processador de logs finalizado. Stats: {self._total_logs_processados} sucessos, {self._total_logs_falha} falhas")

    async def _salvar_com_retry(self, dados_transacao: Dict[str, Any], tentativas_max: int = 3) -> bool:
        """
        Tenta salvar no Supabase com mecanismo de retry e backoff

        Args:
            dados_transacao: Dados da transação para salvar
            tentativas_max: Número máximo de tentativas

        Returns:
            bool: True se salvou com sucesso
        """
        for tentativa in range(tentativas_max):
            try:
                # ✅ INSERE diretamente - sem validações de duplicatas
                resposta = self.supabase.table("mpesa_transactions").insert(dados_transacao).execute()

                if resposta.data:
                    logger.debug(
                        f"💾 Log salvo no Supabase (tentativa {tentativa + 1}): {dados_transacao['transaction_reference']}")
                    return True
                else:
                    logger.warning(f"⚠️ Resposta vazia do Supabase (tentativa {tentativa + 1})")

            except Exception as e:
                logger.warning(f"⚠️ Erro de database (tentativa {tentativa + 1}): {str(e)}")

            # Backoff exponencial simples
            if tentativa < tentativas_max - 1:
                await asyncio.sleep(0.5 * (tentativa + 1))

        logger.error(f"❌ Todas as tentativas falharam para: {dados_transacao['transaction_reference']}")
        return False

    def _salvar_fallback_local(self, dados_transacao: Dict[str, Any], motivo: str):
        """
        Fallback: salva log localmente em arquivo JSON se Supabase falhar

        Args:
            dados_transacao: Dados da transação
            motivo: Motivo do fallback para auditoria
        """
        try:
            entrada_log = {
                "id_fallback": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "motivo_fallback": motivo,
                "dados": dados_transacao
            }

            # Salva em arquivo local (append mode)
            with open("logs_transacoes_fallback.json", "a", encoding="utf-8") as arquivo:
                arquivo.write(json.dumps(entrada_log, ensure_ascii=False) + "\n")

            logger.info(f"📝 Log salvo localmente (fallback): {dados_transacao['transaction_reference']}")

        except Exception as e:
            logger.error(f"💥 Fallback local também falhou: {str(e)}")

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do serviço de logging

        Returns:
            Dict com estatísticas atuais
        """
        return {
            "logs_na_fila": self._fila_logs.qsize(),
            "processando": self._processando,
            "total_processados": self._total_logs_processados,
            "total_falhas": self._total_logs_falha
        }