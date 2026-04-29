from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = Field(default='PFR Recovery Advisor API', alias='APP_NAME')
    app_env: str = Field(default='dev', alias='APP_ENV')
    app_cors_origins: str = Field(default='http://localhost:5173', alias='APP_CORS_ORIGINS')

    azure_openai_endpoint: str = Field(alias='AZURE_OPENAI_ENDPOINT')
    azure_openai_chat_deployment: str = Field(alias='AZURE_OPENAI_CHAT_DEPLOYMENT')
    azure_openai_embedding_deployment: str = Field(alias='AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
    azure_openai_api_version: str = Field(default='2024-10-21', alias='AZURE_OPENAI_API_VERSION')
    azure_openai_api_key: str | None = Field(default=None, alias='AZURE_OPENAI_API_KEY')

    azure_search_endpoint: str = Field(alias='AZURE_SEARCH_ENDPOINT')
    azure_search_index_name: str = Field(alias='AZURE_SEARCH_INDEX_NAME')
    azure_search_api_key: str | None = Field(default=None, alias='AZURE_SEARCH_API_KEY')

    @property
    def cors_origins(self) -> list[str]:
        return [x.strip() for x in self.app_cors_origins.split(',') if x.strip()]


settings = Settings()
