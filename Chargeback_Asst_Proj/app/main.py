from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_cases import router as case_router
from app.api.routes_feedback import router as feedback_router
from app.api.routes_health import router as health_router
from app.config import settings
from app.llm.provider_factory import create_llm_provider
from app.persistence.database import create_schema

app = FastAPI(title='Chargeback Dispute Resolution Assistant')


@app.on_event('startup')
async def verify_llm_startup():
    create_schema()
    if settings.LLM_PROVIDER.strip().lower() != 'ollama':
        raise RuntimeError(f'Unsupported configured LLM_PROVIDER: {settings.LLM_PROVIDER}')
    provider = create_llm_provider()
    health = await provider.health_check()
    if not health.get('ok'):
        raise RuntimeError('Ollama is unreachable. Run: ollama serve; then ollama pull qwen3:8b')
    models = health.get('models', [])
    if settings.OLLAMA_MODEL not in models:
        raise RuntimeError(f'Ollama is reachable, but {settings.OLLAMA_MODEL} is not installed. Run: ollama pull {settings.OLLAMA_MODEL}')


app.include_router(health_router)
app.include_router(case_router)
app.include_router(feedback_router)
