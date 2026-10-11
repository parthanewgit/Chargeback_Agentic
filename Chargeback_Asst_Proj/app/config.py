import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


class Settings:
    APP_ENV: str = os.getenv('APP_ENV', 'development')
    LLM_PROVIDER: str = os.getenv('LLM_PROVIDER', 'ollama')
    OLLAMA_BASE_URL: str = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL', 'qwen3:8b')
    HUMAN_REVIEW_CONFIDENCE_THRESHOLD: float = float(os.getenv('HUMAN_REVIEW_CONFIDENCE_THRESHOLD', '0.75'))
    HIGH_VALUE_CASE_THRESHOLD: float = float(os.getenv('HIGH_VALUE_CASE_THRESHOLD', '1000'))
    MAX_AGENT_ITERATIONS: int = int(os.getenv('MAX_AGENT_ITERATIONS', '10'))
    MAX_TOOL_CALLS: int = int(os.getenv('MAX_TOOL_CALLS', '8'))
    MAX_SAME_TOOL_RETRIES: int = int(os.getenv('MAX_SAME_TOOL_RETRIES', '2'))
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///./chargeback.db')
    ENABLE_OTEL: bool = os.getenv('ENABLE_OTEL', 'true').lower() == 'true'
    ENABLE_OTEL_CONSOLE_EXPORTER: bool = os.getenv('ENABLE_OTEL_CONSOLE_EXPORTER', 'false').lower() == 'true'
    ENABLE_LANGFUSE: bool = os.getenv('ENABLE_LANGFUSE', 'false').lower() == 'true'


settings = Settings()
