"""Tests for PullRequestService audit logging (Task 4.5).

Verifies that PullRequestService correctly logs:
- Successful PR creation
- Denied requests (repo not allowed, action not allowed, protected head branch)
- GitHub API errors
"""

from unittest.mock import MagicMock

import pytest

from app.audit import AuditLogger
from app.github_client import GitHubClient
from app.policy import Policy
from app.services import PullRequestService, ForbiddenError, ServerError


class TestPullRequestServiceAuditLogging:
    """Tests for PullRequestService audit logging behavior."""

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
        mock.create_pr.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
        }
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
    ) -> PullRequestService:
        """Create a PullRequestService with mocked dependencies."""
        return PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

    def test_successful_pr_logs_audit(
        self,
        service: PullRequestService,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN PR creation succeeds THEN audit log with status=success."""
        result = service.create_pr(
            agent="hermes",
            repo="owner/repo",
            title="Add feature",
            head="feature/test",
            base="main",
            body="Description",
        )

        # Verify audit log was called with success
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["agent"] == "hermes"
        assert call_kwargs["repo"] == "owner/repo"
        assert call_kwargs["action"] == "create_pr"
        assert call_kwargs["status"] == "success"
        assert result.number == 42

    def test_repo_not_allowed_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN repo not allowed THEN audit log with status=denied."""
        mock_policy.is_repo_allowed.return_value = False

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_pr(
                agent="hermes",
                repo="unauthorized/repo",
                title="Add feature",
                head="feature/test",
                base="main",
            )

        # Verify audit log was called with denied
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["agent"] == "hermes"
        assert call_kwargs["repo"] == "unauthorized/repo"
        assert call_kwargs["action"] == "create_pr"
        assert call_kwargs["status"] == "denied"
        assert "repo" in call_kwargs["error"].lower()
        assert "not in allowed" in call_kwargs["error"].lower()

    def test_action_not_allowed_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN action not allowed THEN audit log with status=denied."""
        mock_policy.is_action_allowed.return_value = False

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_pr(
                agent="hermes",
                repo="owner/repo",
                title="Add feature",
                head="feature/test",
                base="main",
            )

        # Verify audit log was called with denied
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["status"] == "denied"
        assert call_kwargs["action"] == "create_pr"
        assert "action" in call_kwargs["error"].lower()
        assert "not in allowed" in call_kwargs["error"].lower()

    def test_protected_head_branch_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN head branch is protected THEN audit log with status=denied."""
        # main is protected
        mock_policy.is_branch_protected.side_effect = lambda b: b == "main"

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_pr(
                agent="hermes",
                repo="owner/repo",
                title="Add feature",
                head="main",  # protected head
                base="develop",
            )

        # Verify audit log was called with denied
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["status"] == "denied"
        assert call_kwargs["action"] == "create_pr"
        assert "protected" in call_kwargs["error"].lower()
        assert "main" in call_kwargs["error"].lower()

    def test_pr_to_protected_base_allowed_and_logged(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN base is protected (main) THEN PR is allowed and logged."""
        # main is protected
        mock_policy.is_branch_protected.side_effect = lambda b: b == "main"

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        # PR TO main (protected base) is allowed
        result = service.create_pr(
            agent="hermes",
            repo="owner/repo",
            title="Add feature",
            head="feature/test",  # not protected
            base="main",  # protected - but this is OK
        )

        # Verify audit log was called with success
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["status"] == "success"
        assert result.number == 42

    def test_github_api_error_logs_audit_denied(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN GitHub API fails THEN audit log with status=denied."""
        from app.github_client import GitHubAPIError

        mock_github_client.create_pr.side_effect = GitHubAPIError(
            "Failed to create pull request"
        )

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ServerError):
            service.create_pr(
                agent="hermes",
                repo="owner/repo",
                title="Add feature",
                head="feature/test",
                base="main",
            )

        # Verify audit log was called with denied
        mock_audit_logger.log.assert_called_once()
        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["status"] == "denied"
        assert call_kwargs["action"] == "create_pr"
        assert "error" in call_kwargs
        assert call_kwargs["error"] != ""


class TestPullRequestServiceAuditLogFormat:
    """Tests for audit log format and required fields."""

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
        mock.create_pr.return_value = {
            "number": 1,
            "html_url": "https://github.com/owner/repo/pull/1",
        }
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
    ) -> PullRequestService:
        """Create a PullRequestService with mocked dependencies."""
        return PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

    def test_audit_log_includes_all_required_fields(
        self,
        service: PullRequestService,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN logging THEN includes agent, repo, action, status."""
        service.create_pr(
            agent="hermes",
            repo="owner/repo",
            title="Add feature",
            head="feature/test",
            base="main",
        )

        call_kwargs = mock_audit_logger.log.call_args[1]
        assert "agent" in call_kwargs
        assert "repo" in call_kwargs
        assert "action" in call_kwargs
        assert "status" in call_kwargs

    def test_audit_log_agent_from_caller(
        self,
        service: PullRequestService,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN logging THEN uses agent from caller."""
        service.create_pr(
            agent="custom-agent",
            repo="owner/repo",
            title="Add feature",
            head="feature/test",
            base="main",
        )

        call_kwargs = mock_audit_logger.log.call_args[1]
        assert call_kwargs["agent"] == "custom-agent"

    def test_audit_log_includes_error_on_denial(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN denied THEN audit log includes error field."""
        mock_policy.is_repo_allowed.return_value = False

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_pr(
                agent="hermes",
                repo="unauthorized/repo",
                title="Add feature",
                head="feature/test",
                base="main",
            )

        call_kwargs = mock_audit_logger.log.call_args[1]
        assert "error" in call_kwargs
        assert call_kwargs["error"] != ""


class TestPullRequestServiceAuditLogTiming:
    """Tests for audit log timing - exactly one log per request."""

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
        mock.create_pr.return_value = {
            "number": 1,
            "html_url": "https://github.com/owner/repo/pull/1",
        }
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
    ) -> PullRequestService:
        """Create a PullRequestService with mocked dependencies."""
        return PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

    def test_audit_logged_once_per_request(
        self,
        service: PullRequestService,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN PR creation succeeds THEN audit logged exactly once."""
        service.create_pr(
            agent="hermes",
            repo="owner/repo",
            title="Add feature",
            head="feature/test",
            base="main",
        )

        assert mock_audit_logger.log.call_count == 1

    def test_audit_logged_once_on_denial(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN denied THEN audit logged exactly once."""
        mock_policy.is_repo_allowed.return_value = False

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ForbiddenError):
            service.create_pr(
                agent="hermes",
                repo="unauthorized/repo",
                title="Add feature",
                head="feature/test",
                base="main",
            )

        assert mock_audit_logger.log.call_count == 1

    def test_audit_logged_once_on_error(
        self,
        mock_policy: MagicMock,
        mock_github_client: MagicMock,
        mock_audit_logger: MagicMock,
    ) -> None:
        """WHEN GitHub API error THEN audit logged exactly once."""
        from app.github_client import GitHubAPIError

        mock_github_client.create_pr.side_effect = GitHubAPIError("API error")

        service = PullRequestService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit_logger,
        )

        with pytest.raises(ServerError):
            service.create_pr(
                agent="hermes",
                repo="owner/repo",
                title="Add feature",
                head="feature/test",
                base="main",
            )

        assert mock_audit_logger.log.call_count == 1
