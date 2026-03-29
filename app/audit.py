"""Structured JSON audit logging for request tracking.

Task 1.4: Define structured JSON audit logging contract with
timestamp, agent, repo, and action fields.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class AuditLog(BaseModel):
    """Structured audit log entry.

    Attributes:
        timestamp: ISO 8601 timestamp in UTC
        agent: The authenticated agent identity (e.g., "hermes", "unknown")
        repo: The target repository (e.g., "owner/repo")
        action: The action being performed (e.g., "create_branch", "commit_files", "create_pr")
        status: Optional status ("success", "denied")
        error: Optional error message for denied/failed requests
    """

    timestamp: str
    agent: str
    repo: str
    action: str
    status: str | None = None
    error: str | None = None

    def to_json(self) -> str:
        """Serialize to JSON, excluding None fields.

        Returns:
            JSON string representation
        """
        data: dict[str, Any] = {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "repo": self.repo,
            "action": self.action,
        }

        if self.status is not None:
            data["status"] = self.status

        if self.error is not None:
            data["error"] = self.error

        return json.dumps(data)


class AuditLogger:
    """Logger for structured audit events.

    Emits JSON-formatted audit logs for each request action,
    supporting both success and denial scenarios.
    """

    def __init__(self) -> None:
        """Initialize the audit logger."""
        self._logger = logging.getLogger("github_agent_proxy.audit")
        self._logger.setLevel(logging.INFO)

        # Avoid adding duplicate handlers
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def log(
        self,
        agent: str,
        repo: str,
        action: str,
        status: str | None = None,
        error: str | None = None,
    ) -> str:
        """Log an audit event.

        Args:
            agent: The authenticated agent identity
            repo: The target repository
            action: The action being performed
            status: Optional status ("success", "denied")
            error: Optional error message

        Returns:
            The JSON log entry string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        log_entry = AuditLog(
            timestamp=timestamp,
            agent=agent,
            repo=repo,
            action=action,
            status=status,
            error=error,
        )

        json_output = log_entry.to_json()
        self._logger.info(json_output)

        return json_output
