import os
from typing import Optional

class Config:
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # File upload settings
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    UPLOAD_DIR: str = "uploads"
    ALLOWED_EXTENSIONS: set = {".bin", ".log"}

    # CORS settings
    CORS_ORIGINS: list = [
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ]

    @classmethod
    def get_llm_provider(cls) -> str:
        """Return available LLM provider"""
        if cls.OPENAI_API_KEY:
            return "openai"
        elif cls.ANTHROPIC_API_KEY:
            return "anthropic"
        else:
            return "fallback"

