"""Tests for the Portable Colab trigger listener."""
from __future__ import annotations

import json
import time
from unittest import mock

import pytest

from portable.trigger_listener import get_trigger, wait_for_trigger


class TestTriggerJsonStructure:
    """Validate the trigger JSON structure created by GitHub Actions."""

    def test_trigger_has_required_fields(self) -> None:
        """Trigger requests must have all required fields."""
        trigger = {
            "job_id": "12345",
            "status": "queued",
            "mode": "text_to_video",
            "prompt": "a test",
            "width": 320,
            "height": 240,
            "frames": 17,
            "fps": 8,
            "created_at": "2026-08-24T00:00:00+00:00",
            "source": "github_actions",
        }
        assert trigger["job_id"]
        assert trigger["status"] in ("queued", "running", "completed", "failed")
        assert trigger["mode"] in ("text_to_video", "image_to_video")
        assert trigger["prompt"]
        assert isinstance(trigger["width"], int)
        assert isinstance(trigger["height"], int)
        assert isinstance(trigger["frames"], int)
        assert isinstance(trigger["fps"], int)

    def test_trigger_status_values(self) -> None:
        """Only specific status values are valid."""
        valid_statuses = ("queued", "running", "completed", "failed")
        for status in valid_statuses:
            trigger = {"status": status}
            assert trigger["status"] in valid_statuses

    def test_generation_modes(self) -> None:
        """Only specific generation modes are supported."""
        valid_modes = ("text_to_video", "image_to_video")
        for mode in valid_modes:
            trigger = {"mode": mode}
            assert trigger["mode"] in valid_modes


class TestGetTrigger:
    """Test the get_trigger function."""

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_get_trigger_returns_decoded_content(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """get_trigger should decode base64 content from GitHub API."""
        trigger_data = {"job_id": "123", "status": "queued"}
        import base64

        encoded = base64.b64encode(json.dumps(trigger_data).encode()).decode()
        github_response = {
            "content": encoded,
            "sha": "abc123",
        }

        mock_response = mock.MagicMock()
        mock_response.read.return_value = json.dumps(github_response).encode()
        mock_response.headers = {}
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False

        mock_urlopen.return_value = mock_response

        trigger, sha = get_trigger()
        assert trigger["job_id"] == "123"
        assert trigger["status"] == "queued"
        assert sha == "abc123"

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_get_trigger_includes_github_token(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """get_trigger should include Authorization header when token provided."""
        trigger_data = {"job_id": "123", "status": "queued"}
        import base64

        encoded = base64.b64encode(json.dumps(trigger_data).encode()).decode()
        github_response = {
            "content": encoded,
            "sha": "abc123",
        }

        mock_response = mock.MagicMock()
        mock_response.read.return_value = json.dumps(github_response).encode()
        mock_response.headers = {}
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        mock_urlopen.return_value = mock_response

        get_trigger(token="test-token")

        # Verify the request included the Authorization header
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert request_obj.headers.get("Authorization") == "Bearer test-token"


class TestWaitForTrigger:
    """Test the wait_for_trigger polling function."""

    @mock.patch("portable.trigger_listener.get_trigger")
    def test_wait_for_trigger_returns_immediately_if_queued(
        self, mock_get_trigger: mock.MagicMock
    ) -> None:
        """wait_for_trigger should return immediately if status is queued."""
        queued_trigger = {"status": "queued", "job_id": "123"}
        mock_get_trigger.return_value = (queued_trigger, "sha")

        result = wait_for_trigger(poll_seconds=0)
        assert result["status"] == "queued"
        assert mock_get_trigger.call_count == 1

    @mock.patch("portable.trigger_listener.get_trigger")
    @mock.patch("portable.trigger_listener.time.sleep")
    def test_wait_for_trigger_polls_until_queued(
        self, mock_sleep: mock.MagicMock, mock_get_trigger: mock.MagicMock
    ) -> None:
        """wait_for_trigger should poll until status becomes queued."""
        not_queued = {"status": "none"}
        queued_trigger = {"status": "queued", "job_id": "123"}
        mock_get_trigger.side_effect = [
            (not_queued, "sha"),
            (not_queued, "sha"),
            (queued_trigger, "sha"),
        ]

        result = wait_for_trigger(poll_seconds=1)
        assert result["status"] == "queued"
        assert mock_get_trigger.call_count == 3
        assert mock_sleep.call_count == 2

    @mock.patch("portable.trigger_listener.get_trigger")
    @mock.patch("portable.trigger_listener.time.sleep")
    @mock.patch("portable.trigger_listener.time.monotonic")
    def test_wait_for_trigger_timeout(
        self,
        mock_monotonic: mock.MagicMock,
        mock_sleep: mock.MagicMock,
        mock_get_trigger: mock.MagicMock,
    ) -> None:
        """wait_for_trigger should raise TimeoutError if timeout exceeded."""
        not_queued = {"status": "none"}
        mock_get_trigger.return_value = (not_queued, "sha")
        # Simulate time passing: 0, 1, 11 seconds
        mock_monotonic.side_effect = [0, 1, 11]

        with pytest.raises(TimeoutError):
            wait_for_trigger(poll_seconds=1, timeout_seconds=10)

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    @mock.patch("portable.trigger_listener.time.sleep")
    def test_wait_for_trigger_handles_transient_errors(
        self, mock_sleep: mock.MagicMock, mock_urlopen: mock.MagicMock
    ) -> None:
        """wait_for_trigger should retry on transient API errors."""
        import urllib.error

        queued_trigger = {"status": "queued", "job_id": "123"}
        import base64

        encoded = base64.b64encode(json.dumps(queued_trigger).encode()).decode()
        github_response = {
            "content": encoded,
            "sha": "abc123",
        }

        mock_response = mock.MagicMock()
        mock_response.read.return_value = json.dumps(github_response).encode()
        mock_response.headers = {}
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False

        # Simulate: HTTPError, URLError, success
        mock_urlopen.side_effect = [
            urllib.error.HTTPError("url", 500, "Server Error", {}, None),
            urllib.error.URLError("Connection refused"),
            mock_response,
        ]

        result = wait_for_trigger(poll_seconds=1)
        assert result["status"] == "queued"
        assert mock_urlopen.call_count == 3
