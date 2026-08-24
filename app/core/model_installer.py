"""Model manifest and download/verification helpers.

Large model weights are never committed to OfflineMedia. This module provides
small, deterministic building blocks for a future first-run installer.
"""
from __future__ import annotations

import hashlib
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    name: str
    url: str
    destination: Path
    sha256: str | None = None
    expected_bytes: int | None = None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(artifact: ModelArtifact) -> tuple[bool, str]:
    if not artifact.destination.is_file():
        return False, "missing"
    if artifact.expected_bytes is not None and artifact.destination.stat().st_size != artifact.expected_bytes:
        return False, "size mismatch"
    if artifact.sha256:
        actual = sha256_file(artifact.destination)
        if actual.lower() != artifact.sha256.lower():
            return False, "sha256 mismatch"
    return True, "verified"


def download_artifact(artifact: ModelArtifact, *, overwrite: bool = False) -> Path:
    artifact.destination.parent.mkdir(parents=True, exist_ok=True)
    if artifact.destination.exists() and not overwrite:
        ok, reason = verify_artifact(artifact)
        if ok:
            return artifact.destination
        raise RuntimeError(f"Existing artifact is invalid: {reason}. Use overwrite=True.")

    temporary = artifact.destination.with_suffix(artifact.destination.suffix + ".part")
    try:
        with urllib.request.urlopen(artifact.url, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        temporary.replace(artifact.destination)
    finally:
        temporary.unlink(missing_ok=True)

    ok, reason = verify_artifact(artifact)
    if not ok:
        artifact.destination.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded artifact failed verification: {reason}")
    return artifact.destination
