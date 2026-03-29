"""Tests for POST /commit-files endpoint (Task 3.1).

Covers success and denial paths:
- Unauthenticated requests
- Unauthorized repo/action
- Protected branch commits
- Empty files payload
- Successful commit creation
- Audit logging
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _app_state
from app.services import CommitService, ForbiddenError


class TestCommitFilesAuth:
    """Tests for authentication on commit-files endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_missing_auth_returns_401(self, client: TestClient) -> None:
        """WHEN Authorization header is missing THEN returns 401."""
        response = client.post(
            "/commit-files",
            json={
                "repo": "owner/repo",
                "branch": "feature/test",
                "files": [{"path": "test.txt", "content": "hello"}],
                "message": "Add test file",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "unauthorized"

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """WHEN invalid token is provided THEN returns 401."""
        response = client.post(
            "/commit-files",
            json={
                "repo": "owner/repo",
                "branch": "feature/test",
                "files": [{"path": "test.txt", "content": "hello"}],
                "message": "Add test file",
            },
            headers={"Authorization": "Bearer invalid-key"},
        )

        assert response.status_code == 401

    def test_non_bearer_auth_returns_401(self, client: TestClient) -> None:
        """WHEN non-Bearer auth is used THEN returns 401."""
        response = client.post(
            "/commit-files",
            json={
                "repo": "owner/repo",
                "branch": "feature/test",
                "files": [{"path": "test.txt", "content": "hello"}],
                "message": "Add test file",
            },
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        assert response.status_code == 401


class TestCommitFilesPolicy:
    """Tests for policy enforcement on commit-files endpoint."""

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
        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.side_effect = ForbiddenError(
            "Repository 'unauthorized/repo' is not allowed"
        )

        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "unauthorized/repo",
                    "branch": "feature/test",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
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
        """WHEN commit_files is not in allowed_actions THEN returns 403."""
        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.side_effect = ForbiddenError(
            "Action 'commit_files' is not allowed"
        )

        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/repo",
                    "branch": "feature/test",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403

    def test_commit_to_main_returns_403(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN committing to 'main' branch THEN returns 403."""
        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.side_effect = ForbiddenError(
            "Branch 'main' is protected"
        )

        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "main",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "forbidden"
        assert "protected" in data["message"].lower()

    def test_commit_to_master_returns_403(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN committing to 'master' branch THEN returns 403 (implicit protection)."""
        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.side_effect = ForbiddenError(
            "Branch 'master' is protected"
        )

        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "master",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "forbidden"


class TestCommitFilesValidation:
    """Tests for request validation on commit-files endpoint."""

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
        """Create a mock commit service."""
        from app.services import CommitResult

        mock = MagicMock(spec=CommitService)
        mock.commit_files.return_value = CommitResult(
            sha="abc123",
            message="Add test file",
        )
        return mock

    def test_missing_repo_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN repo is missing THEN returns 422."""
        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "branch": "feature/test",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_branch_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN branch is missing THEN returns 422."""
        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/repo",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_files_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN files is missing THEN returns 422."""
        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/repo",
                    "branch": "feature/test",
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_missing_message_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN message is missing THEN returns 422."""
        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/repo",
                    "branch": "feature/test",
                    "files": [{"path": "test.txt", "content": "hello"}],
                },
                headers=auth_headers,
            )

        assert response.status_code == 422

    def test_empty_files_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], mock_service: MagicMock
    ) -> None:
        """WHEN files array is empty THEN returns 422."""
        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/repo",
                    "branch": "feature/test",
                    "files": [],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

        assert response.status_code == 422


class TestCommitFilesSuccess:
    """Tests for successful commit creation."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_successful_commit_creation(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN all checks pass THEN creates commit and returns success."""
        from app.services import CommitResult

        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.return_value = CommitResult(
            sha="abc123def456",
            message="Add test file",
        )

        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/test",
                    "files": [{"path": "test.txt", "content": "hello world"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "sha" in data

    def test_commit_with_multiple_files(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN committing multiple files THEN all are included."""
        from app.services import CommitResult

        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.return_value = CommitResult(
            sha="abc123",
            message="Update multiple files",
        )

        with patch.object(_app_state, "commit_service", mock_service):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/test",
                    "files": [
                        {"path": "file1.txt", "content": "content1"},
                        {"path": "file2.txt", "content": "content2"},
                        {"path": "src/main.py", "content": "print('hello')"},
                    ],
                    "message": "Update multiple files",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            # Verify service was called with all files
            call_args = mock_service.commit_files.call_args[1]
            assert len(call_args["files"]) == 3


class TestCommitFilesAuditLog:
    """Tests for audit logging on commit-files endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_successful_commit_logs_audit(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN commit succeeds THEN audit log is emitted."""
        from app.services import CommitResult

        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.return_value = CommitResult(
            sha="abc123",
            message="Add test file",
        )

        with patch.object(_app_state, "commit_service", mock_service):
            client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "feature/test",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

            # Verify service was called with correct params
            mock_service.commit_files.assert_called_once()
            call_kwargs = mock_service.commit_files.call_args[1]
            assert call_kwargs["agent"] == "hermes"
            assert call_kwargs["repo"] == "owner/allowed-repo"
            assert call_kwargs["branch"] == "feature/test"
            assert call_kwargs["message"] == "Add test file"

    def test_denied_commit_logs_audit(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """WHEN commit is denied THEN audit log is emitted with status=denied."""
        mock_service = MagicMock(spec=CommitService)
        mock_service.commit_files.side_effect = ForbiddenError(
            "Repository 'unauthorized/repo' is not allowed"
        )

        with patch.object(_app_state, "commit_service", mock_service):
            client.post(
                "/commit-files",
                json={
                    "repo": "unauthorized/repo",
                    "branch": "feature/test",
                    "files": [{"path": "test.txt", "content": "hello"}],
                    "message": "Add test file",
                },
                headers=auth_headers,
            )

            # Verify service was called
            mock_service.commit_files.assert_called_once()
