"""
Core configuration settings for XM-Port API
"""
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # App settings
    APP_NAME: str = "XM-Port API"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    NODE_ENV: str = "development"
    
    # Security settings
    SECRET_KEY: str
    JWT_SECRET_KEY: str  # Separate key for JWT tokens
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    ALLOWED_HOSTS: Union[str, List[str]] = ["localhost", "127.0.0.1", "localhost:8000", "127.0.0.1:8000", "*"]
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database settings
    DATABASE_URL: str
    DATABASE_URL_ASYNC: str
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OpenAI settings
    OPENAI_API_KEY: str
    OPENAI_VECTOR_STORE_ID: str = "vs_hs_codes_turkmenistan"
    OPENAI_HSCODE_DATA_FILE_ID: str = ""
    
    # File storage settings
    UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_ALLOWED_EXTENSIONS: Union[str, List[str]] = [".pdf", ".xlsx", ".xls", ".csv"]
    
    # AWS settings (optional for development)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-west-2"
    AWS_S3_BUCKET: str = ""
    
    # File upload settings
    ALLOW_S3_FALLBACK: bool = True  # Allow fallback to local storage when S3 unavailable
    
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
        extra = "ignore"  # Ignore extra fields from frontend config
        
    @property
    def is_production(self) -> bool:
        return self.NODE_ENV == "production"
    
    @property
    def is_development(self) -> bool:
        return self.NODE_ENV == "development"
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Get ALLOWED_HOSTS as a list"""
        if isinstance(self.ALLOWED_HOSTS, str):
            return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
        return self.ALLOWED_HOSTS
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS_ORIGINS as a list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS
    
    @property
    def upload_extensions_list(self) -> List[str]:
        """Get UPLOAD_ALLOWED_EXTENSIONS as a list"""
        if isinstance(self.UPLOAD_ALLOWED_EXTENSIONS, str):
            return [ext.strip() for ext in self.UPLOAD_ALLOWED_EXTENSIONS.split(",")]
        return self.UPLOAD_ALLOWED_EXTENSIONS


# Create settings instance with validation
settings = Settings()

# Getter function for dependency injection
def get_settings() -> Settings:
    """Get settings instance for dependency injection"""
    return settings