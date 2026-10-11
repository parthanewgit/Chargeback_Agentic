import re

INJECTION_PATTERNS = [
    'ignore previous instructions',
    'ignore system prompt',
    'system override',
    'developer message',
    'reveal prompt',
    'always approve',
    'always contest',
    'execute command',
]


def detect_prompt_injection(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(pattern in lowered for pattern in INJECTION_PATTERNS)
