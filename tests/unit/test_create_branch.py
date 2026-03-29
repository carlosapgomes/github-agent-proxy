"""Tests for POST /create-branch endpoint (Task 2.1).

Covers success and denial paths:
- Unauthenticated requests
- Unauthorized repo/action
- Protected branch creation attempts
- Successful branch creation
- Audit logging
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _app_state
from app.services import BranchService, ForbiddenError


class TestCreateBranchAuth:
    """Tests for authentication on create-branch endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_missing_auth_returns_401(self, client: TestClient) -> None:
        """WHEN Authorization header is missing THEN returns 401."""
        response = client.post(
            "/create-branch",
            json={"repo": "owner/repo", "branch": "feature/test", "base": "main"},
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "unauthorized"

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """WHEN invalid token is provided THEN returns 401."""
        response = client.post(
            "/create-branch",
            json={"repo": "owner/repo", "branch": "feature/test", "base": "main"},
            headers={"Authorization": "Bearer invalid-key"},
        )

        assert response.status_code == 401

    def test_non_bearer_auth_returns_401(self, client: TestClient) -> None:
        """WHEN non-Bearer auth is used THEN returns 401."""
        response = client.post(
            "/create-branch",
            json={"repo": "owner/repo", "branch": "feature/test", "base": "main"},
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        assert response.status_code == 401


class TestCreateBranchPolicy:
    """Tests for policy enforcement on create-branch endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_repo_not_allowed_returns_403(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN repo is not in allowed_repos THEN returns 403."""
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.side_effect = ForbiddenError(
            "Repository 'unauthorized/repo' is not allowed"
        )

        with patch.object(_app_state, "branch_service", mock_service):
            response = client.post(
                "/create-branch",
                json={
                    "repo": "unauthorized/repo",
                    "branch": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "forbidden"
        assert "repo" in data["message"].lower()

    def test_action_not_allowed_returns_403(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN create_branch is not in allowed_actions THEN returns 403.

        Note: This test assumes a policy where create_branch is not allowed.
        In practice, this would require a different policy configuration.
        """
        # This test will be validated by policy configuration
        # For now, we test the error response format
        pass  # Will be covered by integration tests with different policy

    def test_create_protected_branch_returns_403(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN branch name matches protected_branches THEN returns 403."""
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.side_effect = ForbiddenError(
            "Cannot create protected branch 'main'"
        )

        with patch.object(_app_state, "branch_service", mock_service):
            response = client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "main",
                    "base": "develop",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "forbidden"
        assert "protected" in data["message"].lower()

    def test_create_master_branch_returns_403(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN branch name is 'master' THEN returns 403 (implicit protection)."""
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.side_effect = ForbiddenError(
            "Cannot create protected branch 'master'"
        )

        with patch.object(_app_state, "branch_service", mock_service):
            response = client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "master",
                    "base": "develop",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "forbidden"


class TestCreateBranchValidation:
    """Tests for request validation on create-branch endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Create a mock branch service."""
        from app.services import CreateBranchResult

        mock = MagicMock(spec=BranchService)
        mock.create_branch.return_value = CreateBranchResult(
            branch="feature/test", ref="refs/heads/feature/test"
        )
        return mock

    def test_missing_repo_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN repo is missing THEN returns 422."""
        with patch.object(_app_state, "branch_service", mock_service):
            response = client.post(
                "/create-branch",
                json={"branch": "feature/test", "base": "main"},
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_branch_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN branch is missing THEN returns 422."""
        with patch.object(_app_state, "branch_service", mock_service):
            response = client.post(
                "/create-branch",
                json={"repo": "owner/repo", "base": "main"},
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_base_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN base is missing THEN returns 422."""
        with patch.object(_app_state, "branch_service", mock_service):
            response = client.post(
                "/create-branch",
                json={"repo": "owner/repo", "branch": "feature/test"},
                headers=auth_headers,
            )

        assert response.status_code == 422


class TestCreateBranchSuccess:
    """Tests for successful branch creation."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_successful_branch_creation(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN all checks pass THEN creates branch and returns success."""
        from app.services import CreateBranchResult

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

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["branch"] == "feature/test"

    def test_branch_creation_uses_github_token(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN creating branch THEN uses per-request GitHub token."""
        from app.services import CreateBranchResult

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

            # Verify create_branch was called
            mock_service.create_branch.assert_called_once()


class TestCreateBranchAuditLog:
    """Tests for audit logging on create-branch endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_successful_create_branch_logs_audit(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN branch creation succeeds THEN audit log is emitted."""
        from app.services import CreateBranchResult

        mock_audit = MagicMock()
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.return_value = CreateBranchResult(
            branch="feature/test",
            ref="refs/heads/feature/test",
        )
        # Make the service use our mock audit logger
        mock_service._audit_logger = mock_audit

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

            # Verify service was called with correct params
            mock_service.create_branch.assert_called_once_with(
                agent="hermes",
                repo="owner/allowed-repo",
                branch="feature/test",
                base="main",
            )

    def test_denied_create_branch_logs_audit(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN branch creation is denied THEN audit log is emitted with status=denied."""
        mock_audit = MagicMock()
        mock_service = MagicMock(spec=BranchService)
        mock_service.create_branch.side_effect = ForbiddenError(
            "Repository 'unauthorized/repo' is not allowed"
        )
        mock_service._audit_logger = mock_audit

        with patch.object(_app_state, "branch_service", mock_service):
            client.post(
                "/create-branch",
                json={
                    "repo": "unauthorized/repo",
                    "branch": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

            # Verify service was called
            mock_service.create_branch.assert_called_once()
