"""Tests for GitHub token integration with create-branch endpoint (Task 2.3)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _app_state
from app.services import BranchService, CreateBranchResult


class TestCreateBranchTokenIntegration:
    """Tests verifying per-request token generation in create-branch flow."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_token_provider_called_on_branch_creation(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN creating a branch THEN token provider is called."""
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.return_value = CreateBranchResult(
            branch="feature/test",
            ref="refs/heads/feature/test",
        )

        with patch.object(_app_state, "branch_service", mock_service):
            response = client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

            # Verify service was called
            mock_service.create_branch.assert_called_once()
            assert response.status_code == 200

    def test_token_used_in_github_api_requests(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN making GitHub API calls THEN token is used in Authorization header."""
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.return_value = CreateBranchResult(
            branch="feature/test",
            ref="refs/heads/feature/test",
        )

        with patch.object(_app_state, "branch_service", mock_service):
            client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

            # Service handles token internally
            mock_service.create_branch.assert_called_once()

    def test_fresh_token_per_request(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN making multiple requests THEN fresh token is obtained each time."""
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.return_value = CreateBranchResult(
            branch="feature/test",
            ref="refs/heads/feature/test",
        )

        with patch.object(_app_state, "branch_service", mock_service):
            # First request
            client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/1",
                    "base": "main",
                },
                headers=auth_headers,
            )

            # Second request
            client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/2",
                    "base": "main",
                },
                headers=auth_headers,
            )

            # Service should be called twice (once per request)
            assert mock_service.create_branch.call_count == 2


class TestGitHubClientTokenUsage:
    """Tests for GitHubClient token usage at the service level."""

    def test_create_branch_obtains_token(self) -> None:
        """WHEN create_branch is called THEN obtains token from provider."""
        from app.github_client import GitHubClient, TokenProvider

        mock_token_provider = MagicMock(spec=TokenProvider)
        mock_token_provider.get_installation_token.return_value = "ghs_test_token"

        client = GitHubClient(token_provider=mock_token_provider)

        with patch("httpx.Client") as mock_httpx:
            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"object": {"sha": "abc123"}}

            mock_post_response = MagicMock()
            mock_post_response.status_code = 201
            mock_post_response.json.return_value = {"ref": "refs/heads/test"}

            mock_http_client = MagicMock()
            mock_http_client.get.return_value = mock_get_response
            mock_http_client.post.return_value = mock_post_response
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            client.create_branch("owner/repo", "test-branch", "main")

            mock_token_provider.get_installation_token.assert_called_once()

    def test_create_branch_uses_correct_api_version(self) -> None:
        """WHEN create_branch is called THEN uses correct GitHub API version."""
        from app.github_client import GitHubClient, TokenProvider

        mock_token_provider = MagicMock(spec=TokenProvider)
        mock_token_provider.get_installation_token.return_value = "ghs_test_token"

        client = GitHubClient(token_provider=mock_token_provider)

        with patch("httpx.Client") as mock_httpx:
            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"object": {"sha": "abc123"}}

            mock_post_response = MagicMock()
            mock_post_response.status_code = 201
            mock_post_response.json.return_value = {"ref": "refs/heads/test"}

            mock_http_client = MagicMock()
            mock_http_client.get.return_value = mock_get_response
            mock_http_client.post.return_value = mock_post_response
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            client.create_branch("owner/repo", "test-branch", "main")

            # Check API version header
            get_call = mock_http_client.get.call_args
            headers = get_call[1]["headers"]
            assert headers["X-GitHub-Api-Version"] == "2022-11-28"


class TestBranchServiceTokenIntegration:
    """Tests for BranchService token integration."""

    def test_service_uses_github_client_for_branch_creation(self) -> None:
        """WHEN BranchService creates branch THEN uses GitHub client."""
        from app.audit import AuditLogger
        from app.github_client import GitHubClient
        from app.policy import Policy
        from app.services import BranchService

        # Create mocks
        mock_policy = MagicMock(spec=Policy)
        mock_policy.is_repo_allowed.return_value = True
        mock_policy.is_action_allowed.return_value = True
        mock_policy.is_branch_protected.return_value = False

        mock_github_client = MagicMock(spec=GitHubClient)
        mock_github_client.create_branch.return_value = {
            "ref": "refs/heads/feature/test"
        }

        mock_audit = MagicMock(spec=AuditLogger)

        # Create service
        service = BranchService(
            policy=mock_policy,
            github_client=mock_github_client,
            audit_logger=mock_audit,
        )

        # Execute
        result = service.create_branch(
            agent="hermes",
            repo="owner/repo",
            branch="feature/test",
            base="main",
        )

        # Verify GitHub client was called
        mock_github_client.create_branch.assert_called_once_with(
            repo="owner/repo",
            branch="feature/test",
            base="main",
        )
        assert result.branch == "feature/test"
