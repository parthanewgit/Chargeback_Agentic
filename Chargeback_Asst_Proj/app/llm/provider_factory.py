from __future__ import annotations

from app.config import settings
from app.llm.ollama_provider import OllamaLLMProvider


def create_llm_provider():
    provider_name = settings.LLM_PROVIDER.strip().lower()
    if provider_name == 'ollama':
        return OllamaLLMProvider()
    raise ValueError(f'Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}')