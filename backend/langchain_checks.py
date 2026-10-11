import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.models import Requirement

load_dotenv(Path(__file__).resolve().parent / ".env")


class RequirementList(BaseModel):
    requirements: list[Requirement]


SAMPLE_JD = """Junior Backend Engineer - Meridian Freight Tech (sample, invented)
We are hiring a backend engineer to build shipment-tracking APIs.
Required: 2+ years of Python; hands-on experience building REST APIs with FastAPI or Flask;
solid SQL knowledge (PostgreSQL preferred).
Nice to have: experience with Docker; exposure to AWS; familiarity with CI/CD pipelines.
You will work in a fast-paced environment and be a great team player."""

SYSTEM = (
    "You extract requirements from a job description. Rules: "
    "1) Never invent requirements; use only what the text says. "
    "2) Number IDs R1, R2, R3 in order. "
    "3) importance is 'mandatory' only if the text says required or must; "
    "'preferred' for nice-to-have items. "
    "4) source_quote must be copied word-for-word from the job description. "
    "5) If a requirement is vague or cannot be checked on a CV, set is_ambiguous to true "
    "and explain why in ambiguity_note."
)


def main() -> None:
    model_id = os.environ["BEDROCK_MODEL_ID"]
    provider = "anthropic" if "anthropic" in model_id else "amazon"
    print("Model:", model_id, "| Region:", os.getenv("AWS_REGION"))

    llm = ChatBedrockConverse(
        model=model_id,
        provider=provider,
        region_name=os.getenv("AWS_REGION"),
        credentials_profile_name=os.getenv("AWS_PROFILE"),
        temperature=0,
        max_tokens=1500,
    )
    structured = llm.with_structured_output(RequirementList, include_raw=True)

    try:
        result = structured.invoke(
            [SystemMessage(content=SYSTEM), HumanMessage(content=SAMPLE_JD)]
        )
    except Exception as err:  # print a clear message instead of a long traceback
        print("CALL FAILED:", type(err).__name__)
        print(err)
        return

    print("\nParsing error:", result["parsing_error"])
    parsed = result["parsed"]
    if parsed is None:
        print("No parsed result. Raw model output:")
        print(result["raw"].content)
        return

    print(f"\nGot {len(parsed.requirements)} requirements:\n")
    for r in parsed.requirements:
        flag = "AMBIGUOUS" if r.is_ambiguous else "clear"
        print(f"{r.id} [{r.importance}] ({flag}) {r.text}")
        print(f"     quote: {r.source_quote}")
        if r.ambiguity_note:
            print(f"     note : {r.ambiguity_note}")

    print("\nToken usage:", result["raw"].usage_metadata)


if __name__ == "__main__":
    main()