from __future__ import annotations


class TokenUsageTracker:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def record(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        return {'prompt_tokens': self.prompt_tokens, 'completion_tokens': self.completion_tokens, 'total_tokens': self.total_tokens}
