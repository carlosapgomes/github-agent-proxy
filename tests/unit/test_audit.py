"""Tests for structured JSON audit logging (Task 1.4)."""

import json
import logging
from io import StringIO
from unittest.mock import patch


from app.audit import AuditLog, AuditLogger


class TestAuditLog:
    """Tests for AuditLog model."""

    def test_audit_log_required_fields(self) -> None:
        """WHEN creating AuditLog THEN all required fields are set."""
        log = AuditLog(
            timestamp="2024-01-15T10:30:00Z",
            agent="hermes",
            repo="owner/repo",
            action="create_branch",
        )

        assert log.timestamp == "2024-01-15T10:30:00Z"
        assert log.agent == "hermes"
        assert log.repo == "owner/repo"
        assert log.action == "create_branch"

    def test_audit_log_optional_status_success(self) -> None:
        """WHEN status is provided THEN it is included."""
        log = AuditLog(
            timestamp="2024-01-15T10:30:00Z",
            agent="hermes",
            repo="owner/repo",
            action="create_branch",
            status="success",
        )

        assert log.status == "success"

    def test_audit_log_optional_status_denied(self) -> None:
        """WHEN status is denied THEN it is included."""
        log = AuditLog(
            timestamp="2024-01-15T10:30:00Z",
            agent="hermes",
            repo="owner/repo",
            action="create_branch",
            status="denied",
        )

        assert log.status == "denied"

    def test_audit_log_optional_error(self) -> None:
        """WHEN error message is provided THEN it is included."""
        log = AuditLog(
            timestamp="2024-01-15T10:30:00Z",
            agent="hermes",
            repo="owner/repo",
            action="create_branch",
            status="denied",
            error="Repository not allowed",
        )

        assert log.error == "Repository not allowed"

    def test_audit_log_to_json(self) -> None:
        """WHEN serializing to JSON THEN produces valid JSON with all fields."""
        log = AuditLog(
            timestamp="2024-01-15T10:30:00Z",
            agent="hermes",
            repo="owner/repo",
            action="commit_files",
            status="success",
        )

        json_str = log.to_json()
        data = json.loads(json_str)

        assert data["timestamp"] == "2024-01-15T10:30:00Z"
        assert data["agent"] == "hermes"
        assert data["repo"] == "owner/repo"
        assert data["action"] == "commit_files"
        assert data["status"] == "success"

    def test_audit_log_excludes_none_fields(self) -> None:
        """WHEN optional fields are None THEN they are excluded from JSON."""
        log = AuditLog(
            timestamp="2024-01-15T10:30:00Z",
            agent="hermes",
            repo="owner/repo",
            action="create_branch",
        )

        json_str = log.to_json()
        data = json.loads(json_str)

        assert "status" not in data
        assert "error" not in data


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_log_successful_request(self) -> None:
        """WHEN logging successful request THEN emits JSON with status=success."""
        logger = AuditLogger()

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(
                agent="hermes",
                repo="owner/repo",
                action="create_branch",
                status="success",
            )

            # Get the logged JSON
            logged_json = mock_info.call_args[0][0]
            data = json.loads(logged_json)

            assert data["agent"] == "hermes"
            assert data["repo"] == "owner/repo"
            assert data["action"] == "create_branch"
            assert data["status"] == "success"
            assert "timestamp" in data

    def test_log_denied_request(self) -> None:
        """WHEN logging denied request THEN emits JSON with status=denied."""
        logger = AuditLogger()

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(
                agent="hermes",
                repo="owner/unauthorized-repo",
                action="commit_files",
                status="denied",
                error="Repository not in allowed_repos",
            )

            logged_json = mock_info.call_args[0][0]
            data = json.loads(logged_json)

            assert data["status"] == "denied"
            assert data["error"] == "Repository not in allowed_repos"

    def test_log_includes_iso8601_timestamp(self) -> None:
        """WHEN logging THEN timestamp is ISO 8601 format in UTC."""
        logger = AuditLogger()

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(
                agent="hermes",
                repo="owner/repo",
                action="create_pr",
                status="success",
            )

            logged_json = mock_info.call_args[0][0]
            data = json.loads(logged_json)

            # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
            timestamp = data["timestamp"]
            assert "T" in timestamp
            assert timestamp.endswith("Z")

    def test_log_unauthenticated_request(self) -> None:
        """WHEN logging unauthenticated request THEN agent is unknown."""
        logger = AuditLogger()

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(
                agent="unknown",
                repo="owner/repo",
                action="create_branch",
                status="denied",
                error="Invalid API key",
            )

            logged_json = mock_info.call_args[0][0]
            data = json.loads(logged_json)

            assert data["agent"] == "unknown"
            assert data["status"] == "denied"

    def test_log_protected_branch_violation(self) -> None:
        """WHEN logging protected branch violation THEN error is clear."""
        logger = AuditLogger()

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(
                agent="hermes",
                repo="owner/repo",
                action="commit_files",
                status="denied",
                error="Branch 'main' is protected",
            )

            logged_json = mock_info.call_args[0][0]
            data = json.loads(logged_json)

            assert data["status"] == "denied"
            assert "protected" in data["error"].lower()

    def test_log_missing_repo(self) -> None:
        """WHEN repo is not provided THEN logs with empty repo."""
        logger = AuditLogger()

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(
                agent="hermes",
                repo="",
                action="create_branch",
                status="denied",
                error="Missing repository",
            )

            logged_json = mock_info.call_args[0][0]
            data = json.loads(logged_json)

            assert data["repo"] == ""

    def test_multiple_logs_are_separate(self) -> None:
        """WHEN logging multiple events THEN each is logged separately."""
        logger = AuditLogger()

        with patch.object(logger._logger, "info") as mock_info:
            logger.log(
                agent="hermes",
                repo="owner/repo",
                action="create_branch",
                status="success",
            )
            logger.log(
                agent="hermes",
                repo="owner/repo",
                action="commit_files",
                status="success",
            )
            logger.log(
                agent="hermes", repo="owner/repo", action="create_pr", status="success"
            )

            # Should have 3 separate log calls
            assert mock_info.call_count == 3

            # Each call should have valid JSON
            for call in mock_info.call_args_list:
                logged_json = call[0][0]
                data = json.loads(logged_json)
                assert "timestamp" in data
                assert "agent" in data

    def test_log_returns_json_string(self) -> None:
        """WHEN logging THEN returns the JSON string."""
        logger = AuditLogger()

        result = logger.log(
            agent="hermes",
            repo="owner/repo",
            action="create_branch",
            status="success",
        )

        # Should return valid JSON
        data = json.loads(result)
        assert data["agent"] == "hermes"
        assert data["action"] == "create_branch"


class TestAuditLoggerIntegration:
    """Integration tests for audit logging."""

    def test_uses_standard_logging_module(self) -> None:
        """WHEN using AuditLogger THEN integrates with Python logging."""
        logger = AuditLogger()

        # Verify it's using the logging module
        assert logger._logger.name == "github_agent_proxy.audit"
        assert logger._logger.level == logging.INFO

    def test_log_output_can_be_captured(self) -> None:
        """WHEN adding a custom handler THEN output can be captured."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))

        logger = AuditLogger()
        logger._logger.addHandler(handler)

        logger.log(
            agent="hermes",
            repo="owner/repo",
            action="create_branch",
            status="success",
        )

        output = stream.getvalue()
        assert output  # Should have output
        data = json.loads(output.strip())
        assert data["action"] == "create_branch"

        # Clean up
        logger._logger.removeHandler(handler)
