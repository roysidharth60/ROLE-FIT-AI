import os
from functools import lru_cache
from pathlib import Path

from botocore.config import Config
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

# backend\.env holds only non-secret settings (profile, region, model ID)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def _provider_of(model_id: str) -> str:
    """us.amazon.nova-pro-v1:0 -> amazon, openai.gpt-oss-120b-1:0 -> openai."""
    parts = model_id.split(".")
    if parts[0] in ("us", "eu", "apac", "in", "global") and len(parts) > 1:
        return parts[1]
    return parts[0]


@lru_cache
def get_llm(max_tokens: int = 2000, temperature: float = 0.0) -> ChatBedrockConverse:
    """Build and cache the Bedrock model client.

    temperature 0 = same answer every time (good for extraction and checks).
    Around 0.7 = varied answers (needed for writing projects and for Regenerate).
    """
    model_id = os.environ["BEDROCK_MODEL_ID"]

    options = {
        "model": model_id,
        "provider": _provider_of(model_id),
        "region_name": os.getenv("AWS_REGION"),
        "credentials_profile_name": os.getenv("AWS_PROFILE"),
        "max_tokens": max_tokens,
        "config": Config(
            read_timeout=120,
            retries={"max_attempts": 2},
        ),
    }

    # This model ignores temperature, so do not pass the parameter.
    if "claude-sonnet-5-5" not in model_id:
        options["temperature"] = temperature

    return ChatBedrockConverse(**options)