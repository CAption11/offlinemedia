from pathlib import Path

import pytest

from app.core.model_installer import ModelArtifact, sha256_file, verify_artifact


def test_sha256_and_verify(tmp_path: Path):
    target = tmp_path / "model.bin"
    target.write_bytes(b"offline-media-test")
    digest = sha256_file(target)
    artifact = ModelArtifact("test", "https://example.invalid/model", target, sha256=digest, expected_bytes=target.stat().st_size)
    assert verify_artifact(artifact) == (True, "verified")


def test_bad_hash(tmp_path: Path):
    target = tmp_path / "model.bin"
    target.write_bytes(b"offline-media-test")
    artifact = ModelArtifact("test", "https://example.invalid/model", target, sha256="0" * 64)
    assert verify_artifact(artifact) == (False, "sha256 mismatch")


def test_missing_artifact(tmp_path: Path):
    artifact = ModelArtifact("test", "https://example.invalid/model", tmp_path / "missing.bin")
    assert verify_artifact(artifact) == (False, "missing")
