from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AsyncAzureOpenAI

from app.config import settings


def _token_provider():
    credential = DefaultAzureCredential()
    return get_bearer_token_provider(credential, 'https://cognitiveservices.azure.com/.default')


def get_openai_client() -> AsyncAzureOpenAI:
    if settings.azure_openai_api_key:
        return AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
        )

    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token_provider=_token_provider(),
        api_version=settings.azure_openai_api_version,
    )


def get_search_client(index_name: str | None = None) -> SearchClient:
    index_name = index_name or settings.azure_search_index_name
    if settings.azure_search_api_key:
        credential: Any = AzureKeyCredential(settings.azure_search_api_key)
    else:
        credential = DefaultAzureCredential()

    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=index_name,
        credential=credential,
    )
