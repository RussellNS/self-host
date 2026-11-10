#!/usr/bin/env python3

import json
import os
import sys
import urllib.parse
import urllib.request


LAPI_BASE_URL = os.environ.get(
    "CROWDSEC_LAPI_URL",
    "http://lapi.example.com:8080",
)
WATCHER_PASSWORD_ENV = "CROWDSEC_WATCHER_PASSWORD"
WATCHER_MACHINE_ID = "openclaw__alerts"


def fail(message):
    print(json.dumps({
        "ok": False,
        "error": message,
    }))
    sys.exit(1)


def request_json(url, method="GET", headers=None, body=None):
    request = urllib.request.Request(
        url,
        method=method,
        headers=headers or {},
        data=body,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except Exception as exc:
        fail(f"HTTP request failed: {type(exc).__name__}")


def login(password):
    body = json.dumps({
        "machine_id": WATCHER_MACHINE_ID,
        "password": password,
    }).encode("utf-8")

    response = request_json(
        urllib.parse.urljoin(LAPI_BASE_URL.rstrip("/") + "/", "v1/watchers/login"),
        method="POST",
        headers={"Content-Type": "application/json"},
        body=body,
    )

    token = response.get("token")

    if not token:
        fail("CrowdSec authentication response did not contain a token")

    return token


def get_alerts(token):
    query = urllib.parse.urlencode({"since": "24h"})
    url = (
        LAPI_BASE_URL.rstrip("/")
        + "/v1/alerts?"
        + query
    )

    return request_json(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )


def get_active_decisions(token):
    url = (
        LAPI_BASE_URL.rstrip("/")
        + "/v1/decisions/stream?startup=true"
    )

    return request_json(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )


def main():
    password = os.environ.get(WATCHER_PASSWORD_ENV)

    if not password:
        fail(
            f"Required environment variable {WATCHER_PASSWORD_ENV} is not set"
        )

    token = login(password)

    alerts = get_alerts(token)
    decisions = get_active_decisions(token)

    result = {
        "ok": True,
        "collector": "crowdsec",
        "window": "24h",
        "evidence": {
            "alerts": alerts,
            "active_decisions": decisions,
        },
    }

    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
