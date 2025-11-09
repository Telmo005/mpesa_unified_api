# app/core/database.py
"""
Supabase database client - Simple integration
"""

from supabase import create_client, Client

from app.core.config import settings


class SupabaseClient:
    _instance: Client = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            cls._instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
        return cls._instance


# Dependency para usar nos routers
def get_supabase():
    return SupabaseClient.get_client()
