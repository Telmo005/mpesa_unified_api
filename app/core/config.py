"""
Configuration - Simple and working version
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    PROJECT_NAME: str = "MPesa Mozambique API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # M-Pesa Configuration
    MPESA_API_KEY: str
    MPESA_PUBLIC_KEY: str
    MPESA_SERVICE_PROVIDER_CODE: str
    MPESA_API_HOST: str
    MPESA_API_PORT_C2B: int
    MPESA_API_PORT_B2C: int
    MPESA_API_PORT_B2B: int
    MPESA_API_PORT_QUERY: int
    MPESA_API_PORT_QUERY_TXN: int
    MPESA_API_PORT_REVERSAL: int

    # Credenciais de Reversão (obtidas do Vodacom)
    MPESA_SECURITY_CREDENTIAL: str
    MPESA_INITIATOR_IDENTIFIER: str

    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
