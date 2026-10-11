import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

# backend\.env holds only non-secret settings (profile, region, model ID)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@lru_cache
def get_llm() -> ChatBedrockConverse:
    """Build the model client once. Changing the model = changing BEDROCK_MODEL_ID in .env."""
    model_id = os.environ["BEDROCK_MODEL_ID"]
    provider = "anthropic" if "anthropic" in model_id else "amazon"
    return ChatBedrockConverse(
        model=model_id,
        provider=provider,
        region_name=os.getenv("AWS_REGION"),
        credentials_profile_name=os.getenv("AWS_PROFILE"),
        temperature=0,
        max_tokens=2000,
    )