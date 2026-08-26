"""Tests for generated-output validation in the smoke test.

The notebook prints "REAL VIDEO GENERATION ... PASSED" based on this check, so
the check has to be able to tell a generated video from a still frame.
"""
from __future__ import annotations

import json
from unittest import mock

import pytest

from scripts.test_generation import validate_output


def _probe(streams: list[dict], duration: str | None = "2.0") -> mock.MagicMock:
    fmt = {"duration": duration} if duration is not None else {}
    completed = mock.MagicMock()
    completed.returncode = 0
    completed.stdout = json.dumps({"streams": streams, "format": fmt})
    completed.stderr = ""
    return completed


VIDEO_STREAM = {
    "codec_type": "video",
    "codec_name": "h264",
    "width": 320,
    "height": 240,
    "nb_frames": "17",
    "r_frame_rate": "8/1",
}
STILL_STREAM = {
    "codec_type": "video",
    "codec_name": "png",
    "width": 320,
    "height": 240,
    "nb_frames": "1",
    "r_frame_rate": "25/1",
}


@pytest.fixture
def media_file(tmp_path):
    path = tmp_path / "output_001.mp4"
    path.write_bytes(b"not really a video, ffprobe is mocked")
    return path


def test_missing_output_is_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="does not exist"):
        validate_output(tmp_path / "nope.mp4")


def test_empty_output_is_rejected(tmp_path):
    empty = tmp_path / "empty.mp4"
    empty.touch()
    with pytest.raises(RuntimeError, match="empty"):
        validate_output(empty)


def test_valid_video_reports_stream_details(media_file):
    with mock.patch("scripts.test_generation.shutil.which", return_value="/usr/bin/ffprobe"), \
         mock.patch("scripts.test_generation.subprocess.run", return_value=_probe([VIDEO_STREAM])):
        info = validate_output(media_file)
    assert info["codec"] == "h264"
    assert info["width"] == 320
    assert info["frames"] == "17"


def test_file_without_video_stream_is_rejected(media_file):
    audio_only = [{"codec_type": "audio", "codec_name": "aac"}]
    with mock.patch("scripts.test_generation.shutil.which", return_value="/usr/bin/ffprobe"), \
         mock.patch("scripts.test_generation.subprocess.run", return_value=_probe(audio_only)):
        with pytest.raises(RuntimeError, match="No video stream"):
            validate_output(media_file)


def test_single_still_frame_is_rejected(media_file):
    """ffprobe models a PNG as a one-frame video stream.

    Accepting that would let a still image satisfy a video-generation claim.
    """
    with mock.patch("scripts.test_generation.shutil.which", return_value="/usr/bin/ffprobe"), \
         mock.patch("scripts.test_generation.subprocess.run",
                    return_value=_probe([STILL_STREAM], duration=None)):
        with pytest.raises(RuntimeError, match="single still frame"):
            validate_output(media_file)


def test_animation_with_unknown_frame_count_is_accepted(media_file):
    """Animated WEBP often reports nb_frames as N/A; that must not fail."""
    webp = dict(STILL_STREAM, codec_name="webp", nb_frames="N/A")
    with mock.patch("scripts.test_generation.shutil.which", return_value="/usr/bin/ffprobe"), \
         mock.patch("scripts.test_generation.subprocess.run",
                    return_value=_probe([webp], duration="2.125")):
        info = validate_output(media_file)
    assert info["codec"] == "webp"


def test_single_frame_with_real_duration_is_accepted(media_file):
    """One reported frame but a real runtime is not provably a still image."""
    stream = dict(STILL_STREAM, nb_frames="1")
    with mock.patch("scripts.test_generation.shutil.which", return_value="/usr/bin/ffprobe"), \
         mock.patch("scripts.test_generation.subprocess.run",
                    return_value=_probe([stream], duration="2.0")):
        assert validate_output(media_file)["duration"] == "2.0"


def test_ffprobe_failure_is_reported(media_file):
    failed = mock.MagicMock()
    failed.returncode = 1
    failed.stdout = ""
    failed.stderr = "moov atom not found"
    with mock.patch("scripts.test_generation.shutil.which", return_value="/usr/bin/ffprobe"), \
         mock.patch("scripts.test_generation.subprocess.run", return_value=failed):
        with pytest.raises(RuntimeError, match="moov atom not found"):
            validate_output(media_file)


def test_without_ffprobe_size_check_still_applies(media_file):
    """No ffprobe means a weaker check, but existence and size still hold."""
    with mock.patch("scripts.test_generation.shutil.which", return_value=None):
        info = validate_output(media_file)
    assert info["ffprobe"] == "not installed"
    assert info["size_bytes"] > 0
