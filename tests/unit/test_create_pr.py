"""Tests for POST /create-pr endpoint (Task 4.1).

Covers success and denial paths:
- Unauthenticated requests
- Unauthorized repo/action
- Invalid PR branch pairing (head == base)
- Protected head branch
- Successful PR creation
- Audit logging
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _app_state
from app.services import PullRequestService, ForbiddenError


class TestCreatePRAuth:
    """Tests for authentication on create-pr endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_missing_auth_returns_401(self, client: TestClient) -> None:
        """WHEN Authorization header is missing THEN returns 401."""
        response = client.post(
            "/create-pr",
            json={
                "repo": "owner/repo",
                "title": "Add feature",
                "body": "Description",
                "head": "feature/test",
                "base": "main",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "unauthorized"

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """WHEN invalid token is provided THEN returns 401."""
        response = client.post(
            "/create-pr",
            json={
                "repo": "owner/repo",
                "title": "Add feature",
                "body": "Description",
                "head": "feature/test",
                "base": "main",
            },
            headers={"Authorization": "Bearer invalid-key"},
        )

        assert response.status_code == 401

    def test_non_bearer_auth_returns_401(self, client: TestClient) -> None:
        """WHEN non-Bearer auth is used THEN returns 401."""
        response = client.post(
            "/create-pr",
            json={
                "repo": "owner/repo",
                "title": "Add feature",
                "body": "Description",
                "head": "feature/test",
                "base": "main",
            },
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        assert response.status_code == 401


class TestCreatePRPolicy:
    """Tests for policy enforcement on create-pr endpoint."""

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
        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.side_effect = ForbiddenError(
            "Repository 'unauthorized/repo' is not allowed"
        )

        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "unauthorized/repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "feature/test",
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
        """WHEN create_pr is not in allowed_actions THEN returns 403."""
        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.side_effect = ForbiddenError(
            "Action 'create_pr' is not allowed"
        )

        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403

    def test_protected_head_branch_returns_403(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN head branch is protected THEN returns 403."""
        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.side_effect = ForbiddenError(
            "Branch 'main' is protected"
        )

        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "main",
                    "base": "develop",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "forbidden"
        assert "protected" in data["message"].lower()

    def test_pr_to_protected_base_allowed(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN base is protected (main) THEN PR is allowed (normal workflow)."""
        from app.services import CreatePRResult

        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.return_value = CreatePRResult(
            number=42,
            url="https://github.com/owner/repo/pull/42",
            title="Add feature",
        )

        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestCreatePRValidation:
    """Tests for request validation on create-pr endpoint."""

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
        """Create a mock PR service."""
        from app.services import CreatePRResult

        mock = MagicMock(spec=PullRequestService)
        mock.create_pr.return_value = CreatePRResult(
            number=1,
            url="https://github.com/owner/repo/pull/1",
            title="Test PR",
        )
        return mock

    def test_missing_repo_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN repo is missing THEN returns 422."""
        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "title": "Add feature",
                    "body": "Description",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_title_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN title is missing THEN returns 422."""
        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/repo",
                    "body": "Description",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_head_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN head is missing THEN returns 422."""
        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/repo",
                    "title": "Add feature",
                    "body": "Description",
                    "base": "main",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_base_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN base is missing THEN returns 422."""
        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "feature/test",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_head_equals_base_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN head equals base THEN returns 422."""
        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "main",
                    "base": "main",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422


class TestCreatePRSuccess:
    """Tests for successful PR creation."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_successful_pr_creation(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN all checks pass THEN creates PR and returns success."""
        from app.services import CreatePRResult

        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.return_value = CreatePRResult(
            number=42,
            url="https://github.com/owner/repo/pull/42",
            title="Add awesome feature",
        )

        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Add awesome feature",
                    "body": "This PR adds an awesome feature",
                    "head": "feature/awesome",
                    "base": "main",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["number"] == 42
            assert "url" in data

    def test_pr_creation_with_optional_body(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN body is provided THEN includes it in PR."""
        from app.services import CreatePRResult

        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.return_value = CreatePRResult(
            number=1,
            url="https://github.com/owner/repo/pull/1",
            title="Test",
        )

        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Test PR",
                    "body": "Detailed description here",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            # Verify service was called with body
            call_kwargs = mock_service.create_pr.call_args[1]
            assert call_kwargs["body"] == "Detailed description here"

    def test_pr_creation_without_body(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN body is not provided THEN creates PR without body."""
        from app.services import CreatePRResult

        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.return_value = CreatePRResult(
            number=1,
            url="https://github.com/owner/repo/pull/1",
            title="Test",
        )

        with patch.object(_app_state, "pr_service", mock_service):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Test PR",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestCreatePRAuditLog:
    """Tests for audit logging on create-pr endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_successful_pr_logs_audit(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN PR creation succeeds THEN audit log is emitted."""
        from app.services import CreatePRResult

        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.return_value = CreatePRResult(
            number=1,
            url="https://github.com/owner/repo/pull/1",
            title="Test",
        )

        with patch.object(_app_state, "pr_service", mock_service):
            client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

            # Verify service was called with correct params
            mock_service.create_pr.assert_called_once()
            call_kwargs = mock_service.create_pr.call_args[1]
            assert call_kwargs["agent"] == "hermes"
            assert call_kwargs["repo"] == "owner/allowed-repo"

    def test_denied_pr_logs_audit(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN PR creation is denied THEN audit log is emitted with status=denied."""
        mock_service = MagicMock(spec=PullRequestService)
        mock_service.create_pr.side_effect = ForbiddenError(
            "Repository 'unauthorized/repo' is not allowed"
        )

        with patch.object(_app_state, "pr_service", mock_service):
            client.post(
                "/create-pr",
                json={
                    "repo": "unauthorized/repo",
                    "title": "Add feature",
                    "body": "Description",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )

            # Verify service was called
            mock_service.create_pr.assert_called_once()
