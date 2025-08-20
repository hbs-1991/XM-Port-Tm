"""
Core configuration settings for XM-Port API
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # App settings
    APP_NAME: str = "XM-Port API"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    NODE_ENV: str = "development"
    
    # Security settings
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database settings
    DATABASE_URL: str
    DATABASE_URL_ASYNC: str
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OpenAI settings
    OPENAI_API_KEY: str
    
    # File storage settings
    UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = [".pdf", ".xlsx", ".xls", ".csv"]
    
    # AWS settings (optional for development)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-west-2"
    AWS_S3_BUCKET: str = ""
    
    # Monitoring settings
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""
    ENABLE_SWAGGER: bool = True
    ENABLE_METRICS: bool = True
    
    @field_validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator("NODE_ENV")
    def validate_node_env(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("NODE_ENV must be one of: development, staging, production")
        return v
    
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        if v not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @property
    def is_production(self) -> bool:
        return self.NODE_ENV == "production"
    
    @property
    def is_development(self) -> bool:
        return self.NODE_ENV == "development"


# Create settings instance with validation
settings = Settings()