"""Send one message to Claude on Amazon Bedrock and print the reply.

Settings come from backend/.env. AWS keys come from your AWS profile.
"""
import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from dotenv import load_dotenv

load_dotenv()

PROFILE = os.getenv("AWS_PROFILE", "rolefit")
REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")


def main():
    if not MODEL_ID:
        print("BEDROCK_MODEL_ID is empty. Open backend/.env, set it, and press Ctrl+S.")
        return

    print(f"Profile: {PROFILE} | Region: {REGION} | Model: {MODEL_ID}")

    try:
        session = boto3.Session(profile_name=PROFILE, region_name=REGION)
        client = session.client("bedrock-runtime")
        response = client.converse(
            modelId=MODEL_ID,
            system=[{"text": "You are a friendly assistant. Answer in one or two short sentences."}],
            messages=[
                {"role": "user", "content": [{"text": "In one sentence, what is a resume?"}]}
            ],
            inferenceConfig={"maxTokens": 200},
        )
    except ProfileNotFound:
        print(f"AWS profile '{PROFILE}' not found.")
        return
    except NoCredentialsError:
        print("No AWS credentials found for this profile.")
        return
    except ClientError as error:
        code = error.response["Error"]["Code"]
        message = error.response["Error"]["Message"]
        print(f"AWS error: {code}\n{message}")
        return

    reply = response["output"]["message"]["content"][0]["text"]
    usage = response["usage"]

    print("\nClaude says:")
    print(reply)
    print(
        f"\nTokens used: input={usage['inputTokens']}, output={usage['outputTokens']}"
    )


if __name__ == "__main__":
    main()