import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

REGION = "us-east-1"  # checking us-east-1 only, regardless of .env


def main() -> None:
    session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"), region_name=REGION)
    client = session.client("bedrock")

    try:
        models = client.list_foundation_models(byProvider="Amazon")["modelSummaries"]
        print(f"=== Nova foundation models in {REGION} ===")
        for m in sorted(models, key=lambda x: x["modelId"]):
            if "nova" in m["modelId"].lower():
                print(
                    m["modelId"],
                    "| status:", m.get("modelLifecycle", {}).get("status"),
                    "| in:", m.get("inputModalities"),
                    "| out:", m.get("outputModalities"),
                )

        profiles = client.list_inference_profiles(maxResults=1000)["inferenceProfileSummaries"]
        print(f"\n=== Nova inference profiles in {REGION} ===")
        for p in sorted(profiles, key=lambda x: x["inferenceProfileId"]):
            if "nova" in p["inferenceProfileId"].lower():
                print(p["inferenceProfileId"])
    except ClientError as err:
        print("AWS error:", err.response["Error"]["Code"])
        print(err.response["Error"]["Message"])


if __name__ == "__main__":
    main()