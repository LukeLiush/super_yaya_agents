import json
import os
import subprocess
from typing import Dict

import boto3  # type: ignore
import requests


def is_mlflow_tracking_uri_alive(uri: str) -> bool:
    try:
        response = requests.get(uri)
        return response.status_code == 200
    except requests.RequestException:
        return False


def run_shell_command(command: str, env: Dict[str, str]) -> str:
    try:
        result = subprocess.run(
            command.split(), capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise e


def run_bedrock_access_role_229811874124():
    home = os.getenv("HOME")
    return run_shell_command(
        command=f"{home}/.toolbox/bin/ada credentials print --provider=conduit --role=BedrockAccessRole --account=229811874124",
        env=os.environ.copy(),
    )


def set_kb_bedrock_aws_credentials_env_variables():
    _env: Dict[str, str] = to_aws_credentials(
        ada_credentials=json.loads(run_bedrock_access_role_229811874124())
    )
    os.environ["AWS_ACCESS_KEY_ID"] = _env["aws_access_key_id"]
    os.environ["AWS_SECRET_ACCESS_KEY"] = _env["aws_secret_access_key"]
    os.environ["AWS_SESSION_TOKEN"] = _env["aws_session_token"]
    os.environ["AWS_REGION_NAME"] = "us-east-1"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


def to_aws_credentials(ada_credentials: Dict[str, str]) -> Dict[str, str]:
    required_fields = ["AccessKeyId", "SecretAccessKey", "SessionToken"]
    for field in required_fields:
        if field not in ada_credentials:
            raise KeyError(f"Missing required field: {field}")
        if not ada_credentials[field]:
            raise ValueError(f"Field {field} cannot be empty")

    return {
        "aws_access_key_id": ada_credentials["AccessKeyId"],
        "aws_secret_access_key": ada_credentials["SecretAccessKey"],
        "aws_session_token": ada_credentials["SessionToken"],
    }


def get_boto_session():
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION_NAME", "us-east-1"),
    )
    return session
