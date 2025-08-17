import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseSettings):
    primary_model: str = "qwen2.5:7b"
    validation_model: str = "phi3:mini"
    reasoning_model: str = "deepseek-r1:8b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Storage
    chroma_db_dir: str = Field(default=".chroma", alias="CHROMA_DB_DIR")
    sqlite_db_path: str = Field(default=".localknow/content_versions.db", alias="SQLITE_DB_PATH")

    # Processing
    similarity_threshold: float = Field(default=0.85, alias="SIMILARITY_THRESHOLD")
    max_doc_bytes: int = Field(default=50 * 1024 * 1024, alias="MAX_DOC_BYTES")
    pipeline_workers: int = Field(default=8, alias="PIPELINE_WORKERS")

    # API/UI
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    ui_port: int = Field(default=7860, alias="UI_PORT")

    # Models
    models: ModelConfig = ModelConfig()


settings = Settings() 