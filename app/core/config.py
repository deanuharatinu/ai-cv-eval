from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

from app.util import constants


class Settings(BaseSettings):
    app_name: str = Field(default="AI CV Evaluation Backend")
    version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db")
    storage_root: str = Field(default="./data/files")
    documents_root: str = Field(default="./data/documents")
    llm_provider: str = Field(default="mock")
    llm_model: str = Field(default=constants.GEMINI_2_5_FLASH)
    llm_model_cv_parser: str = Field(default=constants.GEMINI_2_5_FLASH)
    llm_provider_api_key: str = Field(default="")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
