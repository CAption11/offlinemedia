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


class TriggerNotFound(LookupError):
    """Raised when the queue file does not exist yet on the branch.

    This is the normal state before the GitHub Actions workflow has ever run,
    not a failure. Callers that poll should treat it as "no job queued".
    """


class TriggerClaimConflict(RuntimeError):
    """Raised when another worker claimed the job first."""


def _request(
    url: str,
    token: str | None = None,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "OfflineMedia-Colab"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body: bytes | None = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, headers=headers, data=body, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")), dict(response.headers)


def get_trigger(
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    path: str = DEFAULT_PATH,
    token: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Return the queued request and its Git blob SHA.

    Raises TriggerNotFound when no request has ever been queued.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    try:
        data, _ = _request(url, token)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise TriggerNotFound(f"No queued request at {repo}@{branch}:{path}") from exc
        raise
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content), str(data["sha"])


def claim_trigger(
    trigger: dict[str, Any],
    sha: str,
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    path: str = DEFAULT_PATH,
    token: str,
    status: str = "running",
) -> dict[str, Any]:
    """Mark a queued request as claimed so a second worker will not repeat it.

    The write is conditional on ``sha``: GitHub rejects the update when the blob
    has changed since it was read, so exactly one worker can win the claim.
    Raises TriggerClaimConflict when another worker got there first.
    """
    claimed = dict(trigger, status=status)
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    payload = {
        "message": f"Claim Portable Colab job {trigger.get('job_id', 'unknown')}",
        "content": base64.b64encode(
            (json.dumps(claimed, indent=2) + "\n").encode("utf-8")
        ).decode("ascii"),
        "sha": sha,
        "branch": branch,
    }
    try:
        _request(url, token, method="PUT", payload=payload)
    except urllib.error.HTTPError as exc:
        if exc.code in (409, 422):
            raise TriggerClaimConflict(
                "Another worker claimed this job first."
            ) from exc
        raise
    return claimed


def wait_for_trigger(
    *,
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    path: str = DEFAULT_PATH,
    token: str | None = None,
    poll_seconds: int = 15,
    timeout_seconds: int | None = None,
    claim: bool = False,
    skip_job_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Poll GitHub until a queued trigger appears.

    With ``claim=True`` (which requires ``token``) the request is marked as
    running before it is returned, so a second worker polling the same queue
    will not run the same job. ``skip_job_ids`` additionally ignores jobs this
    runtime has already handled, which keeps a re-run of the notebook from
    reprocessing the last request.
    """
    if claim and not token:
        raise ValueError("Claiming a trigger requires a GitHub token.")
    started = time.monotonic()
    already_seen = skip_job_ids or set()
    while True:
        try:
            trigger, sha = get_trigger(repo, branch, path, token)
            if trigger.get("status") == "queued" and trigger.get("job_id") not in already_seen:
                if not claim:
                    return trigger
                try:
                    return claim_trigger(
                        trigger, sha, repo=repo, branch=branch, path=path, token=str(token)
                    )
                except TriggerClaimConflict:
                    print("Another worker claimed the job; continuing to poll.")
        except TriggerNotFound:
            pass  # No request has been queued yet; keep waiting.
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError) as exc:
            print(f"Trigger poll failed: {exc}")
        if timeout_seconds is not None and time.monotonic() - started >= timeout_seconds:
            raise TimeoutError("Timed out waiting for a Portable Colab trigger.")
        time.sleep(max(2, poll_seconds))


def read_trigger_or_none(
    repo: str = DEFAULT_REPO,
    branch: str = DEFAULT_BRANCH,
    path: str = DEFAULT_PATH,
    token: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    """Return the current request, or ``(None, "")`` when the queue is empty.

    Useful for an inspection step that should report an empty queue rather than
    fail before the trigger workflow has ever run.
    """
    try:
        return get_trigger(repo, branch, path, token)
    except TriggerNotFound:
        return None, ""


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
