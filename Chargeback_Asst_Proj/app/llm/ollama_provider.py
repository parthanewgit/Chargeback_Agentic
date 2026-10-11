from __future__ import annotations

import asyncio
import json
from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings


class OllamaProviderError(RuntimeError):
    pass


class OllamaResponseError(OllamaProviderError):
    pass


class OllamaLLMProvider:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip('/')
        self.model = model or settings.OLLAMA_MODEL
        self.last_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        self.last_latency = 0.0

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        started = perf_counter()
        self.last_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f'{self.base_url}/api/generate',
                    json={'model': self.model, 'prompt': prompt, 'stream': False, **kwargs},
                )
                response.raise_for_status()
                payload = response.json()
                prompt_tokens = int(payload.get('prompt_eval_count', 0))
                completion_tokens = int(payload.get('eval_count', 0))
                self.last_usage = {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': prompt_tokens + completion_tokens,
                }
                self.last_latency = (perf_counter() - started) * 1000
                return payload.get('response', '')
        except Exception as exc:
            self.last_latency = (perf_counter() - started) * 1000
            raise OllamaProviderError(f'Could not generate a response with {self.model}: {exc}') from exc

    async def structured_generate(self, prompt: str, schema: Any | None = None, **kwargs: Any) -> Any:
        text = await self.generate(prompt, format='json', **kwargs)
        if schema is None:
            return text
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OllamaResponseError('Ollama returned invalid JSON.') from exc
        if not isinstance(result, dict):
            raise OllamaResponseError('Ollama returned JSON with an unexpected shape.')
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                return schema.model_validate(result)
            except ValidationError as exc:
                raise OllamaResponseError('Ollama JSON did not match the required schema.') from exc
        return result

    async def health_check(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f'{self.base_url}/api/tags')
                response.raise_for_status()
                payload = response.json()
                models = [m.get('name') for m in payload.get('models', [])]
                return {'ok': True, 'models': models}
        except Exception as exc:  # pragma: no cover - operational path
            return {'ok': False, 'error': str(exc)}
