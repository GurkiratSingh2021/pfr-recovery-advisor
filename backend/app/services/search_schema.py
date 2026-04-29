from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
)

from app.config import settings


def create_or_update_index() -> str:
    credential = AzureKeyCredential(settings.azure_search_api_key) if settings.azure_search_api_key else DefaultAzureCredential()
    client = SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=credential)

    fields = [
        SimpleField(name='id', type=SearchFieldDataType.String, key=True),
        SimpleField(name='doc_id', type=SearchFieldDataType.String, filterable=True),
        SearchableField(name='title', type=SearchFieldDataType.String),
        SearchableField(name='content', type=SearchFieldDataType.String),
        SimpleField(name='machine_function', type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(name='failure_types', type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
        SimpleField(name='source_type', type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name='source_url', type=SearchFieldDataType.String),
        SearchField(
            name='content_vector',
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name='pfr-vector-profile',
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name='pfr-hnsw')],
        profiles=[VectorSearchProfile(name='pfr-vector-profile', algorithm_configuration_name='pfr-hnsw')],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=f'{settings.azure_search_index_name}-semantic-configuration',
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name='title'),
                    content_fields=[SemanticField(field_name='content')],
                ),
            )
        ]
    )

    index = SearchIndex(
        name=settings.azure_search_index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    client.create_or_update_index(index)
    return settings.azure_search_index_name
