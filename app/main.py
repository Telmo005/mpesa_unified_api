"""
APLICAÇÃO FASTAPI PRINCIPAL
Ponto de entrada da API M-Pesa Mozambique
"""

from fastapi import FastAPI

from app.api.v1.routers import health, auth, c2b, b2c, b2b, reversal, query_customer, query_transaction
from app.core.config import settings

# 🚀 INICIALIZAÇÃO DA APLICAÇÃO FASTAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API Unificada para transações M-Pesa Mozambique",
    version="1.0.0",
    debug=settings.DEBUG
)

# 🌐 REGISTRO DE ROUTERS
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Auth"])
app.include_router(c2b.router, prefix=settings.API_V1_STR, tags=["C2B"])
app.include_router(b2c.router, prefix=settings.API_V1_STR, tags=["B2C"])
app.include_router(b2b.router, prefix=settings.API_V1_STR, tags=["B2B"])
app.include_router(query_customer.router, prefix=settings.API_V1_STR, tags=["Query Customer"])
app.include_router(query_transaction.router, prefix=settings.API_V1_STR, tags=["Query Transaction"])
app.include_router(reversal.router, prefix=settings.API_V1_STR, tags=["Reversal"])


@app.get("/")
async def root():
    """Endpoint raiz para verificação de status"""
    return {
        "message": "MPesa Mozambique API",
        "status": "online",
        "version": "1.0.0"
    }


@app.get("/db-status")
async def db_status():
    """Endpoint para verificação de conexão com banco de dados"""
    try:
        from app.core.database import SupabaseClient
        client = SupabaseClient.get_client()
        result = client.table("mpesa_transactions").select("id", count="exact").execute()

        return {
            "message": "MPesa Mozambique API",
            "status": "online",
            "database": "connected",
            "transactions_count": result.count
        }
    except Exception as e:
        return {
            "message": "MPesa Mozambique API",
            "status": "online",
            "database": "disconnected",
            "error": str(e)
        }
