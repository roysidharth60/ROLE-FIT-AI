import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from dotenv import load_dotenv

load_dotenv()

PROFILE = os.getenv("AWS_PROFILE", "rolefit")
REGIONS = ["us-east-1", "us-west-2", "ap-south-1"]


def list_inference_profiles(client):
    profiles = []
    token = None
    while True:
        kwargs = {"maxResults": 100}
        if token:
            kwargs["nextToken"] = token
        response = client.list_inference_profiles(**kwargs)
        profiles.extend(response["inferenceProfileSummaries"])
        token = response.get("nextToken")
        if not token:
            return profiles


def show_region(region):
    print(f"\n=== {region} ===")
    session = boto3.Session(profile_name=PROFILE, region_name=region)
    client = session.client("bedrock")

    models = client.list_foundation_models(byProvider="anthropic")["modelSummaries"]
    print("Claude foundation models:")
    if not models:
        print("  (none listed)")
    for model in sorted(models, key=lambda m: m["modelId"]):
        status = model.get("modelLifecycle", {}).get("status", "unknown")
        print(f"  {model['modelId']}  [{status}]")

    profiles = [
        p for p in list_inference_profiles(client)
        if "anthropic" in p["inferenceProfileId"]
    ]
    print("Claude inference profiles:")
    if not profiles:
        print("  (none listed)")
    for profile in sorted(profiles, key=lambda p: p["inferenceProfileId"]):
        print(f"  {profile['inferenceProfileId']}")


def main():
    for region in REGIONS:
        try:
            show_region(region)
        except ProfileNotFound:
            print(f"AWS profile '{PROFILE}' not found.")
            return
        except NoCredentialsError:
            print("No credentials found for this profile.")
            return
        except ClientError as error:
            code = error.response["Error"]["Code"]
            print(f"  AWS returned an error in {region}: {code}")


if __name__ == "__main__":
    main()