from __future__ import annotations

from typing import Any, Protocol


class LLMProvider(Protocol):
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        ...

    async def structured_generate(self, prompt: str, schema: Any | None = None, **kwargs: Any) -> Any:
        ...
