"""Tests for BranchService audit logging (Task 2.5).

Verifies that BranchService correctly logs:
- Successful branch creation
- Denied requests (repo not allowed, action not allowed, protected branch)
"""

from unittest.mock import MagicMock

import pytest

from app.audit import AuditLogger
from app.github_client import GitHubClient
from app.policy import Policy
from app.services import BranchService, ForbiddenError


class TestBranchServiceAuditLogging:
    """Tests for BranchService audit logging behavior."""

    @pytest.fixture
    def mock_policy(self) -> MagicMock:
        """Create a mock policy that allows everything."""
        mock = MagicMock(spec=Policy)
        mock.is_repo_allowed.return_value = True
        mock.is_action_allowed.return_value = True
        mock.is_branch_protected.return_value = False
        return mock

    @pytest.fixture
    def mock_github_client(self) -> MagicMock:
        """Create a mock GitHub client."""
        mock = MagicMock(spec=GitHubClient)
        mock.create_branch.return_value = {"ref": "refs/heads/feature/test"}
        return mock

    @pytest.fixture
    def mock_audit_logger(self) -> MagicMock:
        """Create a mock audit logger."""
        return MagicMock(spec=AuditLogger)

    @pytest.fixture
    def service(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> BranchService:
        """Create a BranchService with mocked dependencies."""
        return BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

    def test_successful_branch_creation_logs_audit(
        self,
        service: BranchService,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN branch creation succeeds THEN audit log with status=success."""
        result = service.create_branch(
            agent="hermes",
            repo="owner/repo",
            branch="feature/test",
            base="main",
        )

        # Verify audit log was called with success
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["agent"] == "hermes"
        assert call_kwargs["repo"] == "owner/repo"
        assert call_kwargs["action"] == "create_branch"
        assert call_kwargs["status"] == "success"
        assert result.branch == "feature/test"

    def test_repo_not_allowed_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN repo not allowed THEN audit log with status=denied."""
        mock_policy.is_repo_allowed.return_value = False

        service = BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_branch(
                agent="hermes",
                repo="unauthorized/repo",
                branch="feature/test",
                base="main",
            )

        # Verify audit log was called with denied status
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["agent"] == "hermes"
        assert call_kwargs["repo"] == "unauthorized/repo"
        assert call_kwargs["action"] == "create_branch"
        assert call_kwargs["status"] == "denied"
        assert "not in allowed_repos" in call_kwargs["error"]

    def test_action_not_allowed_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN action not allowed THEN audit log with status=denied."""
        mock_policy.is_action_allowed.return_value = False

        service = BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_branch(
                agent="hermes",
                repo="owner/repo",
                branch="feature/test",
                base="main",
            )

        # Verify audit log was called with denied status
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["status"] == "denied"
        assert "not in allowed_actions" in call_kwargs["error"]

    def test_protected_branch_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN branch is protected THEN audit log with status=denied."""
        mock_policy.is_branch_protected.return_value = True

        service = BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_branch(
                agent="hermes",
                repo="owner/repo",
                branch="main",
                base="develop",
            )

        # Verify audit log was called with denied status
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["status"] == "denied"
        assert "protected" in call_kwargs["error"].lower()

    def test_github_api_error_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN GitHub API fails THEN audit log with status=denied."""
        mock_github_client.create_branch.side_effect = Exception("API rate limit")

        service = BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        from app.services import ServerError

        with pytest.raises(ServerError):
            service.create_branch(
                agent="hermes",
                repo="owner/repo",
                branch="feature/test",
                base="main",
            )

        # Verify audit log was called with denied status
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["status"] == "denied"
        assert "API rate limit" in call_kwargs["error"]


class TestBranchServiceAuditLogFormat:
    """Tests for audit log entry format and completeness."""

    @pytest.fixture
    def service(self) -> BranchService:
        """Create a BranchService with mocked dependencies."""
        mock_policy = MagicMock(spec=Policy)
        mock_policy.is_repo_allowed.return_value = True
        mock_policy.is_action_allowed.return_value = True
        mock_policy.is_branch_protected.return_value = False

        mock_github_client = MagicMock(spec=GitHubClient)
        mock_github_client.create_branch.return_value = {
            "ref": "refs/heads/feature/test"
        }

        mock_audit_logger = MagicMock(spec=AuditLogger)

        return BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

    def test_audit_log_includes_all_required_fields(
        self, service: BranchService
    ) -> None:
        """WHEN logging THEN includes timestamp, agent, repo, action, status."""
        mock_audit = service._audit_logger

        service.create_branch(
            agent="hermes",
            repo="owner/repo",
            branch="feature/test",
            base="main",
        )

        call_kwargs = mock_audit.log.call_args[1]

        # Required fields per spec
        assert "agent" in call_kwargs
        assert "repo" in call_kwargs
        assert "action" in call_kwargs
        assert "status" in call_kwargs

        # Values should match request
        assert call_kwargs["agent"] == "hermes"
        assert call_kwargs["repo"] == "owner/repo"
        assert call_kwargs["action"] == "create_branch"
        assert call_kwargs["status"] == "success"

    def test_audit_log_agent_from_caller(self, service: BranchService) -> None:
        """WHEN agent is passed THEN audit log uses that agent."""
        mock_audit = service._audit_logger

        service.create_branch(
            agent="custom-agent",
            repo="owner/repo",
            branch="feature/test",
            base="main",
        )

        call_kwargs = mock_audit.log.call_args[1]
        assert call_kwargs["agent"] == "custom-agent"

    def test_audit_log_includes_error_on_denial(self, service: BranchService) -> None:
        """WHEN request is denied THEN audit log includes error message."""
        # Make repo not allowed
        service._policy.is_repo_allowed.return_value = False
        mock_audit = service._audit_logger

        with pytest.raises(ForbiddenError):
            service.create_branch(
                agent="hermes",
                repo="unauthorized/repo",
                branch="feature/test",
                base="main",
            )

        call_kwargs = mock_audit.log.call_args[1]
        assert "error" in call_kwargs
        assert call_kwargs["error"]  # Should have non-empty error message


class TestBranchServiceAuditLogTiming:
    """Tests for audit log timing - log should happen for every request."""

    @pytest.fixture
    def service(self) -> BranchService:
        """Create a BranchService with mocked dependencies."""
        mock_policy = MagicMock(spec=Policy)
        mock_policy.is_repo_allowed.return_value = True
        mock_policy.is_action_allowed.return_value = True
        mock_policy.is_branch_protected.return_value = False

        mock_github_client = MagicMock(spec=GitHubClient)
        mock_github_client.create_branch.return_value = {
            "ref": "refs/heads/feature/test"
        }

        mock_audit_logger = MagicMock(spec=AuditLogger)

        return BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

    def test_audit_logged_once_per_request(self, service: BranchService) -> None:
        """WHEN request completes THEN exactly one audit log entry."""
        mock_audit = service._audit_logger

        service.create_branch(
            agent="hermes",
            repo="owner/repo",
            branch="feature/test",
            base="main",
        )

        assert mock_audit.log.call_count == 1

    def test_audit_logged_once_on_denial(self, service: BranchService) -> None:
        """WHEN request is denied THEN exactly one audit log entry."""
        service._policy.is_repo_allowed.return_value = False
        mock_audit = service._audit_logger

        with pytest.raises(ForbiddenError):
            service.create_branch(
                agent="hermes",
                repo="unauthorized/repo",
                branch="feature/test",
                base="main",
            )

        assert mock_audit.log.call_count == 1

    def test_audit_logged_once_on_error(self, service: BranchService) -> None:
        """WHEN GitHub API errors THEN exactly one audit log entry."""
        service._github_client.create_branch.side_effect = Exception("Network error")
        mock_audit = service._audit_logger

        from app.services import ServerError

        with pytest.raises(ServerError):
            service.create_branch(
                agent="hermes",
                repo="owner/repo",
                branch="feature/test",
                base="main",
            )

        assert mock_audit.log.call_count == 1
