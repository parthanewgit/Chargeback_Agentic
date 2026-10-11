from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.llm.ollama_provider import OllamaLLMProvider
from app.observability.metrics import metrics as app_metrics

router = APIRouter()


@router.get('/health')
def health():
    return {'status': 'ok'}


@router.get('/health/ollama')
async def health_ollama():
    provider = OllamaLLMProvider()
    result = await provider.health_check()
    return result


@router.get('/metrics')
def metrics():
    return {
        'status': 'ok',
        'llm_provider': settings.LLM_PROVIDER,
        'model': settings.OLLAMA_MODEL,
        'counters': app_metrics.snapshot(),
    }
