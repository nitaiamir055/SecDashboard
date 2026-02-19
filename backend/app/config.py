from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sec_user_agent: str = "SEC-Pulse Dashboard contact@example.com"
    poll_interval_seconds: int = 5
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b-instruct-q8_0"
    db_url: str = "sqlite+aiosqlite:///./secpulse.db"
    max_concurrent_downloads: int = 8
    filing_text_max_chars: int = 20000
    slm_timeout_seconds: float = 180.0

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
