import os
import time

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from pydantic import BaseModel, Field

# Find .env whether this file sits in backend\scripts or scripts
HERE = os.path.dirname(os.path.abspath(__file__))
for path in (os.path.join(HERE, "..", ".env"), os.path.join(HERE, "..", "backend", ".env")):
    if os.path.exists(path):
        load_dotenv(path, override=True)
        break

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")
REGION = os.getenv("AWS_REGION", "us-east-1")
PROFILE = os.getenv("AWS_PROFILE")


class Skill(BaseModel):
    label: str = Field(min_length=3, max_length=40)
    items: list[str] = Field(min_length=2, max_length=8)


class Probe(BaseModel):
    title: str = Field(min_length=5, max_length=100)
    improvement_pct: int = Field(ge=15, le=90)
    skill_groups: list[Skill] = Field(min_length=2, max_length=3)


PROMPT = (
    "Invent a sample reporting-automation project for a data analyst at a small clinic group. "
    "Give a title, an improvement percentage between 15 and 90 (never above 90), and 2 or 3 skill "
    "groups, each with at least 2 skills. Sample data only."
)


def provider_of(model_id):
    parts = model_id.split(".")
    if parts[0] in ("us", "eu", "apac", "global") and len(parts) > 1:
        return parts[1]
    return parts[0]


print(f"Model: {MODEL_ID}   region: {REGION}   profile: {PROFILE}")
llm = ChatBedrockConverse(
    model=MODEL_ID,
    provider=provider_of(MODEL_ID),
    region_name=REGION,
    credentials_profile_name=PROFILE,
    max_tokens=800,
    temperature=0.7,
)
chain = llm.with_structured_output(Probe, include_raw=True)

ok = 0
for n in range(1, 4):
    start = time.time()
    try:
        out = chain.invoke(PROMPT)
    except Exception as err:
        print(f"Run {n}: FAILED after {time.time() - start:.1f}s: {str(err)[:300]}")
        continue
    seconds = time.time() - start
    usage = getattr(out["raw"], "usage_metadata", None) or {}
    if out["parsed"] is not None:
        ok += 1
        print(f"Run {n}: OK {seconds:.1f}s  tokens in/out = {usage.get('input_tokens')}/{usage.get('output_tokens')}")
        print(f"   title: {out['parsed'].title} | improvement_pct: {out['parsed'].improvement_pct}")
    else:
        print(f"Run {n}: NOT PARSED {seconds:.1f}s: {str(out['parsing_error'])[:250]}")

print(f"\nResult: {ok}/3 parsed correctly")