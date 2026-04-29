"""
Core configuration – reads all settings from environment variables.

Local development: copy .env.example to .env and fill in values.
Azure deployment: set variables via App Service / Container App settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Azure OpenAI (optional – only needed for Stage B LLM explainer)
    # ------------------------------------------------------------------
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # ------------------------------------------------------------------
    # Azure AI Search (optional – only needed for cloud retrieval)
    # ------------------------------------------------------------------
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "pfr-knowledge"

    # ------------------------------------------------------------------
    # Local paths (used in MVP / local mode)
    # ------------------------------------------------------------------
    data_dir: str = "data"
    docs_dir: str = "data/sample_docs"
    dependencies_file: str = "data/dependencies.json"
    ingest_store: str = "data/ingested_docs.jsonl"

    # ------------------------------------------------------------------
    # Feature flags
    # ------------------------------------------------------------------
    use_azure_openai: bool = False
    use_azure_search: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def azure_openai_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def azure_search_configured(self) -> bool:
        return bool(self.azure_search_endpoint and self.azure_search_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
