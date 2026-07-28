import json
import os
import urllib.error
import urllib.request
from functools import cache

import boto3


SQUARE_API_HOSTS = {
    "production": "https://connect.squareup.com",
    "sandbox": "https://connect.squareupsandbox.com",
}


def response(status_code, body, headers=None):
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json", **(headers or {})},
        "body": json.dumps(body),
    }


def square_api_url(path):
    environment = os.environ.get("SQUARE_ENVIRONMENT", "production").lower()
    host = SQUARE_API_HOSTS.get(environment, SQUARE_API_HOSTS["production"])
    return f"{host}{path}"


@cache
def square_access_token():
    if os.environ.get("SQUARE_ACCESS_TOKEN"):
        return os.environ["SQUARE_ACCESS_TOKEN"]

    secret_name = os.environ["SQUARE_ACCESS_TOKEN_SECRET_NAME"]
    data = boto3.client("secretsmanager").get_secret_value(SecretId=secret_name)
    secret = data["SecretString"]

    try:
        secret_json = json.loads(secret)
    except json.JSONDecodeError:
        return secret

    return secret_json.get("access_token") or secret_json["SQUARE_ACCESS_TOKEN"]


def square_headers():
    return {
        "Authorization": f"Bearer {square_access_token()}",
        "Content-Type": "application/json",
        "Square-Version": os.environ.get("SQUARE_API_VERSION", "2026-07-16"),
    }


def square_get(path):
    request = urllib.request.Request(
        square_api_url(path),
        headers=square_headers(),
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=20) as result:
        return json.loads(result.read())


def square_post(path, payload):
    request = urllib.request.Request(
        square_api_url(path),
        data=json.dumps(payload).encode(),
        headers=square_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as result:
            return json.loads(result.read())
    except urllib.error.HTTPError as error:
        details = error.read().decode()
        raise RuntimeError(f"Square request failed: {details}") from error


def inventory_counts(variation_ids):
    counts = {variation_id: 0 for variation_id in variation_ids}
    if not variation_ids:
        return counts

    cursor = None
    while True:
        payload = {
            "catalog_object_ids": variation_ids,
            "states": ["IN_STOCK"],
            "limit": 1000,
        }
        if cursor:
            payload["cursor"] = cursor

        data = square_post("/v2/inventory/counts/batch-retrieve", payload)
        for count in data.get("counts", []):
            variation_id = count.get("catalog_object_id")
            if variation_id in counts:
                counts[variation_id] += int(float(count.get("quantity", "0")))

        cursor = data.get("cursor")
        if not cursor:
            return counts
