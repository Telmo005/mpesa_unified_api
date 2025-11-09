# app/api/v1/routers/monitoramento.py
"""
Endpoint para monitoramento do sistema de logging
"""

from fastapi import APIRouter, Depends

from app.services.c2b_service import C2BService

router = APIRouter()


@router.get("/monitoramento/logs")
async def obter_estatisticas_logs(servico_c2b: C2BService = Depends()):
    """
    Retorna estatísticas do sistema de logging em tempo real
    """
    estatisticas = await servico_c2b.obter_estatisticas_logging()

    return {
        "sucesso": True,
        "mensagem": "Estatísticas do sistema de logging",
        "dados": estatisticas,
        "timestamp": datetime.now().isoformat()
    }
