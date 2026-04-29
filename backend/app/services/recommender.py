from app.models import Citation, RecommendRequest, RecommendResponse
from app.prompts import SYSTEM_PROMPT
from app.services.azure_clients import get_openai_client
from app.config import settings


def _build_user_prompt(request: RecommendRequest) -> str:
    affected = ', '.join(request.affected_machine_functions) or 'Unknown'
    return f"""
    Incident:
    {request.incident_prompt}

    Outage type: {request.outage_type}
    Affected machine functions: {affected}

    Produce a dependency-aware recovery recommendation for the DRI.
    """.strip()


async def recommend(request: RecommendRequest) -> RecommendResponse:
    client = get_openai_client()

    data_source = {
        'type': 'azure_search',
        'parameters': {
            'endpoint': settings.azure_search_endpoint,
            'index_name': settings.azure_search_index_name,
            'query_type': 'vector_semantic_hybrid',
            'semantic_configuration': f'{settings.azure_search_index_name}-semantic-configuration',
            'embedding_dependency': {
                'type': 'deployment_name',
                'deployment_name': settings.azure_openai_embedding_deployment,
            },
            'top_n_documents': request.top_k,
            'authentication': (
                {'type': 'api_key', 'key': settings.azure_search_api_key}
                if settings.azure_search_api_key
                else {'type': 'system_assigned_managed_identity'}
            ),
            'fields_mapping': {
                'content_fields': ['content'],
                'title_field': 'title',
                'url_field': 'source_url',
            },
            'filter': None,
        },
    }

    completion = await client.chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': _build_user_prompt(request)},
        ],
        temperature=0.1,
        extra_body={'data_sources': [data_source]},
        stream=False,
    )

    choice = completion.choices[0]
    message = choice.message
    content = message.content or ''
    raw_citations = (message.context or {}).get('citations', []) if hasattr(message, 'context') else []
    citations = [Citation(**{
        'title': c.get('title'),
        'content': c.get('content'),
        'filepath': c.get('filepath'),
        'url': c.get('url'),
        'chunk_id': c.get('chunk_id') or c.get('id'),
    }) for c in raw_citations]

    debug = {
        'used_search_index': settings.azure_search_index_name,
        'top_k': request.top_k,
        'outage_type': request.outage_type,
        'affected_machine_functions': request.affected_machine_functions,
    }

    return RecommendResponse(answer=content, citations=citations, debug=debug)
