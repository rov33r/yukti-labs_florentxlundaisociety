from __future__ import annotations

import logging
import os

from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger("ml_lens.llm")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PRIMARY_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
FALLBACK_MODEL = os.getenv("OPENROUTER_FALLBACK_MODEL", "qwen/qwen3-coder:free")


def _api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")


def make_client() -> OpenAI:
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=_api_key())


def make_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=_api_key())


def chat_create(client: OpenAI, *, model: str = PRIMARY_MODEL, **kwargs):
    try:
        return client.chat.completions.create(model=model, **kwargs)
    except Exception as e:
        if model == FALLBACK_MODEL:
            raise
        logger.warning("Model %s failed (%s) — retrying with fallback %s", model, e, FALLBACK_MODEL)
        return client.chat.completions.create(model=FALLBACK_MODEL, **kwargs)


async def achat_create(client: AsyncOpenAI, *, model: str = PRIMARY_MODEL, **kwargs):
    try:
        return await client.chat.completions.create(model=model, **kwargs)
    except Exception as e:
        if model == FALLBACK_MODEL:
            raise
        logger.warning("Model %s failed (%s) — retrying with fallback %s", model, e, FALLBACK_MODEL)
        return await client.chat.completions.create(model=FALLBACK_MODEL, **kwargs)
