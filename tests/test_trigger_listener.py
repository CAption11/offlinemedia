"""Tests for the Portable Colab trigger listener."""
from __future__ import annotations

import base64
import json
import urllib.error
from unittest import mock

import pytest

from portable.trigger_listener import (
    TriggerClaimConflict,
    TriggerNotFound,
    claim_trigger,
    complete_trigger,
    get_trigger,
    read_trigger_or_none,
    wait_for_trigger,
)


def _contents_response(payload: dict[str, object], sha: str = "abc123") -> mock.MagicMock:
    """Build a mock urlopen context manager for a GitHub contents response."""
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    body = json.dumps({"content": encoded, "sha": sha}).encode()
    response = mock.MagicMock()
    response.read.return_value = body
    response.headers = {}
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("url", code, "error", {}, None)


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


class TestEmptyQueue:
    """An empty queue is a normal state, not a failure."""

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_get_trigger_raises_trigger_not_found_on_404(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """A queue file that was never created raises TriggerNotFound, not HTTPError."""
        mock_urlopen.side_effect = _http_error(404)

        with pytest.raises(TriggerNotFound):
            get_trigger()

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_get_trigger_propagates_other_http_errors(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """Server errors must not be disguised as an empty queue."""
        mock_urlopen.side_effect = _http_error(500)

        with pytest.raises(urllib.error.HTTPError):
            get_trigger()

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_read_trigger_or_none_returns_none_when_absent(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """read_trigger_or_none reports an empty queue instead of raising."""
        mock_urlopen.side_effect = _http_error(404)

        trigger, sha = read_trigger_or_none()
        assert trigger is None
        assert sha == ""

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    @mock.patch("portable.trigger_listener.time.sleep")
    def test_wait_for_trigger_keeps_polling_an_empty_queue(
        self, mock_sleep: mock.MagicMock, mock_urlopen: mock.MagicMock
    ) -> None:
        """Polling before the first job exists must wait, not crash."""
        mock_urlopen.side_effect = [
            _http_error(404),
            _contents_response({"status": "queued", "job_id": "123"}),
        ]

        result = wait_for_trigger(poll_seconds=1)
        assert result["job_id"] == "123"
        assert mock_urlopen.call_count == 2


class TestClaimTrigger:
    """Claiming prevents two workers from running the same job."""

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_claim_marks_request_running_conditional_on_sha(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """The claim PUT sends the blob sha so a stale write is rejected."""
        response = mock.MagicMock()
        response.read.return_value = b"{}"
        response.headers = {}
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        mock_urlopen.return_value = response

        trigger = {"job_id": "123", "status": "queued", "prompt": "a ball"}
        claimed = claim_trigger(trigger, "blob-sha", token="t")

        assert claimed["status"] == "running"
        assert claimed["prompt"] == "a ball"
        request_obj = mock_urlopen.call_args[0][0]
        assert request_obj.get_method() == "PUT"
        body = json.loads(request_obj.data.decode())
        assert body["sha"] == "blob-sha"
        # The queued request must survive the claim intact.
        written = json.loads(base64.b64decode(body["content"]).decode())
        assert written == {"job_id": "123", "status": "running", "prompt": "a ball"}

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_claim_conflict_when_another_worker_won(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """A rejected conditional write means someone else claimed the job."""
        mock_urlopen.side_effect = _http_error(409)

        with pytest.raises(TriggerClaimConflict):
            claim_trigger({"job_id": "1"}, "stale-sha", token="t")

    def test_claim_requires_token(self) -> None:
        """wait_for_trigger refuses to promise a claim it cannot perform."""
        with pytest.raises(ValueError):
            wait_for_trigger(claim=True, token=None)

    @mock.patch("portable.trigger_listener.claim_trigger")
    @mock.patch("portable.trigger_listener.get_trigger")
    def test_wait_for_trigger_returns_claimed_request(
        self, mock_get_trigger: mock.MagicMock, mock_claim: mock.MagicMock
    ) -> None:
        """With claim=True the returned request is the claimed one."""
        mock_get_trigger.return_value = ({"status": "queued", "job_id": "123"}, "sha")
        mock_claim.return_value = {"status": "running", "job_id": "123"}

        result = wait_for_trigger(token="t", claim=True, poll_seconds=0)
        assert result["status"] == "running"
        mock_claim.assert_called_once()

    @mock.patch("portable.trigger_listener.time.sleep")
    @mock.patch("portable.trigger_listener.claim_trigger")
    @mock.patch("portable.trigger_listener.get_trigger")
    def test_losing_a_claim_keeps_polling(
        self,
        mock_get_trigger: mock.MagicMock,
        mock_claim: mock.MagicMock,
        mock_sleep: mock.MagicMock,
    ) -> None:
        """Losing the race must not return the job to this worker."""
        mock_get_trigger.side_effect = [
            ({"status": "queued", "job_id": "123"}, "sha"),
            ({"status": "queued", "job_id": "456"}, "sha2"),
        ]
        mock_claim.side_effect = [
            TriggerClaimConflict("lost"),
            {"status": "running", "job_id": "456"},
        ]

        result = wait_for_trigger(token="t", claim=True, poll_seconds=1)
        assert result["job_id"] == "456"

    @mock.patch("portable.trigger_listener.time.sleep")
    @mock.patch("portable.trigger_listener.get_trigger")
    def test_skip_job_ids_prevents_reprocessing(
        self, mock_get_trigger: mock.MagicMock, mock_sleep: mock.MagicMock
    ) -> None:
        """A re-run must not pick up the job this runtime already handled."""
        mock_get_trigger.side_effect = [
            ({"status": "queued", "job_id": "done"}, "sha"),
            ({"status": "queued", "job_id": "fresh"}, "sha2"),
        ]

        result = wait_for_trigger(poll_seconds=1, skip_job_ids={"done"})
        assert result["job_id"] == "fresh"


class TestCompleteTrigger:
    """A finished job must leave an unambiguous state in the queue."""

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_completion_marks_job_and_stamps_finished_at(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        put_response = mock.MagicMock()
        put_response.read.return_value = b"{}"
        put_response.headers = {}
        put_response.__enter__.return_value = put_response
        put_response.__exit__.return_value = False
        mock_urlopen.side_effect = [
            _contents_response({"job_id": "123", "status": "running"}),
            put_response,
        ]

        finished = complete_trigger("123", token="t")

        assert finished["status"] == "completed"
        assert finished["finished_at"]
        written = json.loads(
            base64.b64decode(json.loads(mock_urlopen.call_args[0][0].data)["content"])
        )
        assert written["status"] == "completed"

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_failure_status_is_recorded_with_detail(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        put_response = mock.MagicMock()
        put_response.read.return_value = b"{}"
        put_response.headers = {}
        put_response.__enter__.return_value = put_response
        put_response.__exit__.return_value = False
        mock_urlopen.side_effect = [
            _contents_response({"job_id": "123", "status": "running"}),
            put_response,
        ]

        finished = complete_trigger("123", status="failed", token="t", detail="exit code 1")

        assert finished["status"] == "failed"
        assert finished["detail"] == "exit code 1"

    def test_arbitrary_status_is_refused(self) -> None:
        with pytest.raises(ValueError):
            complete_trigger("123", status="probably-fine", token="t")

    @mock.patch("portable.trigger_listener.urllib.request.urlopen")
    def test_will_not_overwrite_a_different_job(
        self, mock_urlopen: mock.MagicMock
    ) -> None:
        """A newer request must not be clobbered by a late finishing worker."""
        mock_urlopen.return_value = _contents_response(
            {"job_id": "456", "status": "queued"}
        )

        with pytest.raises(TriggerClaimConflict):
            complete_trigger("123", token="t")
