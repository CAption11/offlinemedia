"""Read and optionally claim a Portable Colab job queued by GitHub Actions.

Colab cannot be treated as a permanent server. This listener therefore uses
GitHub as a durable queue: Actions writes portable/trigger.json and a running
Colab notebook polls this file. A GitHub token is required for private repos or
when the listener is asked to update the request status.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_REPO = "CAption11/offlinemedia"
DEFAULT_BRANCH = "claude/scan-repo-chatgpt-review-6nljgh"
DEFAULT_PATH = "portable/trigger.json"


def _request(url: str, token: str | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "OfflineMedia-Colab"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def get_trigger(
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    path: str = DEFAULT_PATH,
    token: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Return the queued request and its Git blob SHA."""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    data, _ = _request(url, token)
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content), str(data["sha"])


def wait_for_trigger(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    path: str = DEFAULT_PATH,
    token: str | None = None,
    poll_seconds: int = 15,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Poll GitHub until a queued trigger appears."""
    started = time.monotonic()
    while True:
        try:
            trigger, _ = get_trigger(repo, branch, path, token)
            if trigger.get("status") == "queued":
                return trigger
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError) as exc:
            print(f"Trigger poll failed: {exc}")
        if timeout_seconds is not None and time.monotonic() - started >= timeout_seconds:
            raise TimeoutError("Timed out waiting for a Portable Colab trigger.")
        time.sleep(max(2, poll_seconds))


def main() -> int:
    repo = os.getenv("OFFLINEMEDIA_GITHUB_REPO", DEFAULT_REPO)
    branch = os.getenv("OFFLINEMEDIA_GITHUB_BRANCH", DEFAULT_BRANCH)
    path = os.getenv("OFFLINEMEDIA_TRIGGER_PATH", DEFAULT_PATH)
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    print(f"Polling {repo}@{branch}:{path}")
    trigger = wait_for_trigger(repo=repo, branch=branch, path=path, token=token)
    print(json.dumps(trigger, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
