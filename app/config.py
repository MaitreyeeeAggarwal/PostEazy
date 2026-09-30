import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Content Engine API"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]

    # Security
    SECRET_KEY: str = "supersecretjwtkey_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    PEXELS_API_KEY: str = ""

    # Pipeline Settings
    WORK_DIR: str = "./data"
    MAX_UPLOAD_MB: int = 25
    MAX_CONCURRENT_RENDERS: int = 2
    MAX_SOURCE_CHARS: int = 60000

    # Assets
    MUSIC_DIR: str = "./data/music"
    FONTS_DIR: str = "./data/fonts"
    FONT_NAME: str = "Montserrat"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
