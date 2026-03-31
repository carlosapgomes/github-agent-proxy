"""Security validation tests for protected branch enforcement.

Verifies that there are NO bypass paths to write to protected branches.
This is a critical security validation for the proxy.
"""

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.audit import AuditLogger
from app.github_client import GitHubClient
from app.main import _app_state, app
from app.services import BranchService, CommitService, PullRequestService


@contextmanager
def patch_services_with_client(github_client: MagicMock) -> Iterator[None]:
    """Patch app services to use a specific GitHub client mock."""
    _app_state.ensure_initialized()
    assert _app_state.policy is not None

    mock_audit = MagicMock(spec=AuditLogger)
    branch_service = BranchService(
        policy=_app_state.policy,
        github_client=github_client,
        audit_logger=mock_audit,
    )
    commit_service = CommitService(
        policy=_app_state.policy,
        github_client=github_client,
        audit_logger=mock_audit,
    )
    pr_service = PullRequestService(
        policy=_app_state.policy,
        github_client=github_client,
        audit_logger=mock_audit,
    )

    with ExitStack() as stack:
        stack.enter_context(patch.object(_app_state, "branch_service", branch_service))
        stack.enter_context(patch.object(_app_state, "commit_service", commit_service))
        stack.enter_context(patch.object(_app_state, "pr_service", pr_service))
        yield


class TestProtectedBranchSecurity:
    """Security tests validating no bypass to protected branches."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    @pytest.fixture
    def mock_github_client(self) -> MagicMock:
        """Create a mock GitHub client."""
        return MagicMock(spec=GitHubClient)

    # =========================================================================
    # CREATE-BRANCH: Protected branch as target
    # =========================================================================

    @pytest.mark.parametrize("protected_branch", ["main", "master"])
    def test_cannot_create_protected_branch_by_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_github_client: MagicMock,
        protected_branch: str,
    ) -> None:
        """WHEN branch name is protected THEN creation denied regardless of other params."""
        with patch_services_with_client(mock_github_client):
            response = client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": protected_branch,
                    "base": "develop",
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert data["error"] == "forbidden"
            assert "protected" in data["message"].lower()

            # GitHub client should NEVER be called for protected branches
            mock_github_client.create_branch.assert_not_called()

    def test_create_branch_main_denied_even_with_valid_base(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_github_client: MagicMock,
    ) -> None:
        """WHEN creating 'main' branch THEN denied even with valid base."""
        with patch_services_with_client(mock_github_client):
            response = client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "main",
                    "base": "feature/some-branch",
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            mock_github_client.create_branch.assert_not_called()

    # =========================================================================
    # COMMIT-FILES: Protected branch as target
    # =========================================================================

    @pytest.mark.parametrize("protected_branch", ["main", "master"])
    def test_cannot_commit_to_protected_branch(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_github_client: MagicMock,
        protected_branch: str,
    ) -> None:
        """WHEN committing to protected branch THEN denied."""
        with patch_services_with_client(mock_github_client):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": protected_branch,
                    "message": "Direct commit to protected",
                    "files": [{"path": "file.txt", "content": "content"}],
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert data["error"] == "forbidden"

            # GitHub client should NEVER be called for protected branches
            mock_github_client.commit_files.assert_not_called()

    def test_commit_to_main_denied_even_with_single_file(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_github_client: MagicMock,
    ) -> None:
        """WHEN committing single file to main THEN denied."""
        with patch_services_with_client(mock_github_client):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "main",
                    "message": "Just one file",
                    "files": [{"path": "README.md", "content": "# Readme"}],
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            mock_github_client.commit_files.assert_not_called()

    def test_commit_to_master_denied(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_github_client: MagicMock,
    ) -> None:
        """WHEN committing to master THEN denied (implicit protection)."""
        with patch_services_with_client(mock_github_client):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "master",
                    "message": "Commit to master",
                    "files": [{"path": "file.txt", "content": "content"}],
                },
                headers=auth_headers,
            )

            assert response.status_code == 403

    # =========================================================================
    # CREATE-PR: Protected branch as HEAD (source)
    # =========================================================================

    @pytest.mark.parametrize("protected_branch", ["main", "master"])
    def test_cannot_create_pr_from_protected_head(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_github_client: MagicMock,
        protected_branch: str,
    ) -> None:
        """WHEN creating PR from protected head THEN denied."""
        with patch_services_with_client(mock_github_client):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "PR from protected",
                    "head": protected_branch,
                    "base": "develop",
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert data["error"] == "forbidden"

            # GitHub client should NEVER be called
            mock_github_client.create_pr.assert_not_called()

    # =========================================================================
    # CREATE-PR: Protected branch as BASE (target) - ALLOWED
    # =========================================================================

    @pytest.mark.parametrize("protected_branch", ["main", "master"])
    def test_can_create_pr_to_protected_base(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        protected_branch: str,
    ) -> None:
        """WHEN creating PR to protected base THEN allowed (normal workflow)."""
        from app.services import PullRequestService
        from app.audit import AuditLogger

        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_pr.return_value = {
            "number": 1,
            "html_url": "https://github.com/owner/repo/pull/1",
        }
        mock_audit = MagicMock(spec=AuditLogger)

        assert _app_state.policy is not None
        service = PullRequestService(
            policy=_app_state.policy,
            github_client=mock_client,
            audit_logger=mock_audit,
        )

        with patch.object(_app_state, "pr_service", service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Feature PR",
                    "head": "feature/test",  # not protected
                    "base": protected_branch,  # protected - OK for base
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


class TestNoPassthroughEndpoints:
    """Tests verifying no generic GitHub passthrough exists."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_no_generic_git_ref_endpoint(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN accessing generic git/ref endpoint THEN 404."""
        response = client.post(
            "/git/refs/heads/main",
            json={"sha": "abc123"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_no_generic_repos_endpoint(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN accessing generic repos endpoint THEN 404."""
        response = client.post(
            "/repos/owner/repo/contents/file.txt",
            json={"content": "content", "message": "msg"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_no_generic_pulls_endpoint(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN accessing generic pulls endpoint THEN 404."""
        response = client.post(
            "/repos/owner/repo/pulls",
            json={"title": "PR", "head": "test", "base": "main"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_only_three_write_endpoints_exist(self, client: TestClient) -> None:
        """WHEN listing routes THEN only 3 write endpoints exist."""
        from fastapi.routing import APIRoute

        write_endpoints = [
            route
            for route in app.routes
            if isinstance(route, APIRoute) and route.methods and "POST" in route.methods
        ]

        # Only create-branch, commit-files, create-pr should exist
        endpoint_paths = sorted([e.path for e in write_endpoints])
        assert endpoint_paths == ["/commit-files", "/create-branch", "/create-pr"]


class TestProtectedBranchConfiguration:
    """Tests for protected branch configuration."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_configured_protected_branch_staging(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN branch matches configured protected branch THEN denied."""
        # staging is in policy.yaml
        mock_client = MagicMock(spec=GitHubClient)

        with patch_services_with_client(mock_client):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "staging",
                    "message": "Commit",
                    "files": [{"path": "f.txt", "content": "c"}],
                },
                headers=auth_headers,
            )

            assert response.status_code == 403

    def test_branch_not_in_protected_list_allowed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN branch not in protected list THEN allowed."""
        from app.services import BranchService
        from app.audit import AuditLogger

        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_branch.return_value = {
            "ref": "refs/heads/feature/new-thing",
            "object": {"sha": "abc123"},
        }
        mock_audit = MagicMock(spec=AuditLogger)

        assert _app_state.policy is not None
        service = BranchService(
            policy=_app_state.policy,
            github_client=mock_client,
            audit_logger=mock_audit,
        )

        with patch.object(_app_state, "branch_service", service):
            response = client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/new-thing",  # not protected
                    "base": "main",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestSecurityAuditTrail:
    """Tests for security audit trail on protected branch violations."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_protected_branch_violation_logged(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN protected branch violation THEN audit logged."""
        from app.audit import AuditLogger
        from app.services import CommitService

        mock_github = MagicMock(spec=GitHubClient)
        mock_audit = MagicMock(spec=AuditLogger)

        assert _app_state.policy is not None
        service = CommitService(
            policy=_app_state.policy,
            github_client=mock_github,
            audit_logger=mock_audit,
        )

        with patch.object(_app_state, "commit_service", service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "main",
                    "message": "Attempted commit",
                    "files": [{"path": "f.txt", "content": "c"}],
                },
                headers=auth_headers,
            )

            assert response.status_code == 403

            # Verify audit was logged with denied status
            mock_audit.log.assert_called_once()
            call_kwargs = mock_audit.log.call_args[1]
            assert call_kwargs["status"] == "denied"
            assert "protected" in call_kwargs["error"].lower()
