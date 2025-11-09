# app/api/v1/routers/utils.py - ADICIONE ESTE ENDPOINT
from fastapi import APIRouter, Depends
from app.core.database import get_supabase

router = APIRouter()

@router.get("/test-db")
async def test_db(supabase = Depends(get_supabase)):
    """
    Test Supabase connection
    """
    try:
        # Teste simples - tentar listar tabelas
        result = supabase.table("mpesa_transactions").select("*").limit(2).execute()
        return {
            "status": "success",
            "message": "Supabase connected successfully",
            "data": result.data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Supabase connection failed: {str(e)}"
        }