import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Phenotype Predictor API"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-local-dev-only")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Using SQLite for local dev so you don't have to install PostgreSQL right now.
    # In production (Phase 4), this will be changed to a postgresql:// URL.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./phenotype.db")

settings = Settings()
