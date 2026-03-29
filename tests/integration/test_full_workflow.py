"""Integration tests for full workflow: create-branch → commit-files → create-pr.

Tests the complete agent workflow against the proxy:
1. Create a feature branch
2. Commit files to the branch
3. Create a pull request

All GitHub API calls are mocked, but the full FastAPI stack is tested.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _app_state
from app.github_client import GitHubClient


class TestFullWorkflowSuccess:
    """Tests for successful full workflow."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    @pytest.fixture
    def mock_github_responses(self) -> dict:
        """Return mock GitHub API responses for the full workflow."""
        return {
            # create-branch response
            "create_branch": {
                "ref": "refs/heads/feature/test",
                "object": {"sha": "abc123"},
            },
            # commit-files responses (blob, tree, commit, ref update)
            "get_ref": {"object": {"sha": "base-sha-123"}},
            "create_blob": {"sha": "blob-sha-1"},
            "get_tree": {"sha": "base-tree-sha"},
            "create_tree": {"sha": "new-tree-sha"},
            "create_commit": {"sha": "new-commit-sha"},
            "update_ref": {"sha": "new-commit-sha"},
            # create-pr response
            "create_pr": {
                "number": 42,
                "html_url": "https://github.com/owner/allowed-repo/pull/42",
            },
        }

    def test_full_workflow_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_github_responses: dict,
    ) -> None:
        """WHEN full workflow executed THEN all steps succeed."""
        repo = "owner/allowed-repo"
        feature_branch = "feature/test-workflow"
        base_branch = "main"

        # Mock the GitHub client to return our responses
        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_branch.return_value = mock_github_responses["create_branch"]
        mock_client.commit_files.return_value = {
            "sha": "new-commit-sha",
            "message": "Add new feature",
        }
        mock_client.create_pr.return_value = mock_github_responses["create_pr"]

        with patch.object(_app_state, "github_client", mock_client):
            # Step 1: Create branch
            branch_response = client.post(
                "/create-branch",
                json={
                    "repo": repo,
                    "branch": feature_branch,
                    "base": base_branch,
                },
                headers=auth_headers,
            )

            assert branch_response.status_code == 200
            branch_data = branch_response.json()
            assert branch_data["status"] == "success"
            assert branch_data["branch"] == feature_branch

            # Step 2: Commit files
            commit_response = client.post(
                "/commit-files",
                json={
                    "repo": repo,
                    "branch": feature_branch,
                    "message": "Add new feature",
                    "files": [
                        {"path": "src/main.py", "content": "print('hello')"},
                        {"path": "README.md", "content": "# My Project"},
                    ],
                },
                headers=auth_headers,
            )

            assert commit_response.status_code == 200
            commit_data = commit_response.json()
            assert commit_data["status"] == "success"
            assert commit_data["sha"] == "new-commit-sha"

            # Step 3: Create PR
            pr_response = client.post(
                "/create-pr",
                json={
                    "repo": repo,
                    "title": "Add new feature",
                    "body": "This PR adds a new feature",
                    "head": feature_branch,
                    "base": base_branch,
                },
                headers=auth_headers,
            )

            assert pr_response.status_code == 200
            pr_data = pr_response.json()
            assert pr_data["status"] == "success"
            assert pr_data["number"] == 42
            assert "pull/42" in pr_data["url"]

    def test_full_workflow_with_multiple_commits(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN multiple commits made THEN all succeed."""
        repo = "owner/allowed-repo"
        feature_branch = "feature/multi-commit"

        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_branch.return_value = {"ref": f"refs/heads/{feature_branch}"}
        mock_client.commit_files.return_value = {"sha": "commit-sha", "message": "msg"}
        mock_client.create_pr.return_value = {
            "number": 1,
            "html_url": "https://github.com/owner/repo/pull/1",
        }

        with patch.object(_app_state, "github_client", mock_client):
            # Create branch
            client.post(
                "/create-branch",
                json={"repo": repo, "branch": feature_branch, "base": "main"},
                headers=auth_headers,
            )

            # First commit
            r1 = client.post(
                "/commit-files",
                json={
                    "repo": repo,
                    "branch": feature_branch,
                    "message": "First commit",
                    "files": [{"path": "file1.txt", "content": "content1"}],
                },
                headers=auth_headers,
            )
            assert r1.status_code == 200

            # Second commit
            r2 = client.post(
                "/commit-files",
                json={
                    "repo": repo,
                    "branch": feature_branch,
                    "message": "Second commit",
                    "files": [{"path": "file2.txt", "content": "content2"}],
                },
                headers=auth_headers,
            )
            assert r2.status_code == 200

            # Create PR
            r3 = client.post(
                "/create-pr",
                json={
                    "repo": repo,
                    "title": "Multi-commit PR",
                    "head": feature_branch,
                    "base": "main",
                },
                headers=auth_headers,
            )
            assert r3.status_code == 200


class TestFullWorkflowProtectedBranch:
    """Tests for workflow blocked by protected branch restrictions."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_cannot_create_protected_branch(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN trying to create protected branch THEN denied."""
        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_branch.return_value = {"ref": "refs/heads/main"}

        with patch.object(_app_state, "github_client", mock_client):
            # Try to create 'main' branch (protected)
            response = client.post(
                "/create-branch",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "main",  # protected!
                    "base": "develop",
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert data["error"] == "forbidden"
            assert "protected" in data["message"].lower()

    def test_cannot_commit_to_protected_branch(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN trying to commit to protected branch THEN denied."""
        mock_client = MagicMock(spec=GitHubClient)

        with patch.object(_app_state, "github_client", mock_client):
            response = client.post(
                "/commit-files",
                json={
                    "repo": "owner/allowed-repo",
                    "branch": "main",  # protected!
                    "message": "Direct commit to main",
                    "files": [{"path": "file.txt", "content": "content"}],
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert data["error"] == "forbidden"
            assert "protected" in data["message"].lower()

    def test_cannot_create_pr_from_protected_head(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN trying to create PR from protected head THEN denied."""
        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_pr.return_value = {"number": 1, "html_url": "url"}

        with patch.object(_app_state, "github_client", mock_client):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Bad PR",
                    "head": "main",  # protected head!
                    "base": "develop",
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert data["error"] == "forbidden"
            assert "protected" in data["message"].lower()

    def test_can_create_pr_to_protected_base(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN creating PR to protected base THEN allowed."""
        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_pr.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
        }

        with patch.object(_app_state, "github_client", mock_client):
            response = client.post(
                "/create-pr",
                json={
                    "repo": "owner/allowed-repo",
                    "title": "Feature PR",
                    "head": "feature/test",  # not protected
                    "base": "main",  # protected - OK for base
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


class TestFullWorkflowUnauthorized:
    """Tests for workflow blocked by authorization."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_unauthorized_repo_blocked(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN repo not in allowed_repos THEN all operations denied."""
        mock_client = MagicMock(spec=GitHubClient)

        with patch.object(_app_state, "github_client", mock_client):
            # create-branch denied
            r1 = client.post(
                "/create-branch",
                json={
                    "repo": "unauthorized/repo",
                    "branch": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )
            assert r1.status_code == 403

            # commit-files denied
            r2 = client.post(
                "/commit-files",
                json={
                    "repo": "unauthorized/repo",
                    "branch": "feature/test",
                    "message": "msg",
                    "files": [{"path": "f.txt", "content": "c"}],
                },
                headers=auth_headers,
            )
            assert r2.status_code == 403

            # create-pr denied
            r3 = client.post(
                "/create-pr",
                json={
                    "repo": "unauthorized/repo",
                    "title": "PR",
                    "head": "feature/test",
                    "base": "main",
                },
                headers=auth_headers,
            )
            assert r3.status_code == 403


class TestFullWorkflowAuthentication:
    """Tests for authentication requirements."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_unauthenticated_requests_blocked(
        self,
        client: TestClient,
    ) -> None:
        """WHEN no auth provided THEN all endpoints return 401."""
        # create-branch
        r1 = client.post(
            "/create-branch",
            json={"repo": "owner/repo", "branch": "test", "base": "main"},
        )
        assert r1.status_code == 401

        # commit-files
        r2 = client.post(
            "/commit-files",
            json={
                "repo": "owner/repo",
                "branch": "test",
                "message": "msg",
                "files": [{"path": "f.txt", "content": "c"}],
            },
        )
        assert r2.status_code == 401

        # create-pr
        r3 = client.post(
            "/create-pr",
            json={
                "repo": "owner/repo",
                "title": "PR",
                "head": "test",
                "base": "main",
            },
        )
        assert r3.status_code == 401


class TestFullWorkflowAuditLogging:
    """Tests for audit logging across full workflow."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Return valid auth headers."""
        return {"Authorization": "Bearer test-api-key"}

    def test_full_workflow_logs_all_actions(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        """WHEN full workflow executed THEN all actions logged."""
        from app.audit import AuditLogger
        from app.services import BranchService, CommitService, PullRequestService

        mock_client = MagicMock(spec=GitHubClient)
        mock_client.create_branch.return_value = {"ref": "refs/heads/feature/test"}
        mock_client.commit_files.return_value = {"sha": "sha123", "message": "msg"}
        mock_client.create_pr.return_value = {
            "number": 1,
            "html_url": "https://github.com/owner/repo/pull/1",
        }

        mock_audit = MagicMock(spec=AuditLogger)

        # Create services with mocked audit logger
        mock_branch_service = BranchService(
            policy=_app_state.policy,
            github_client=mock_client,
            audit_logger=mock_audit,
        )
        mock_commit_service = CommitService(
            policy=_app_state.policy,
            github_client=mock_client,
            audit_logger=mock_audit,
        )
        mock_pr_service = PullRequestService(
            policy=_app_state.policy,
            github_client=mock_client,
            audit_logger=mock_audit,
        )

        with patch.object(_app_state, "branch_service", mock_branch_service):
            with patch.object(_app_state, "commit_service", mock_commit_service):
                with patch.object(_app_state, "pr_service", mock_pr_service):
                    # Execute workflow
                    client.post(
                        "/create-branch",
                        json={
                            "repo": "owner/allowed-repo",
                            "branch": "feature/test",
                            "base": "main",
                        },
                        headers=auth_headers,
                    )
                    client.post(
                        "/commit-files",
                        json={
                            "repo": "owner/allowed-repo",
                            "branch": "feature/test",
                            "message": "Add files",
                            "files": [{"path": "f.txt", "content": "c"}],
                        },
                        headers=auth_headers,
                    )
                    client.post(
                        "/create-pr",
                        json={
                            "repo": "owner/allowed-repo",
                            "title": "PR",
                            "head": "feature/test",
                            "base": "main",
                        },
                        headers=auth_headers,
                    )

                    # Verify 3 audit logs (one per action)
                    assert mock_audit.log.call_count == 3

                    # Verify each action was logged
                    actions_logged = [
                        call[1]["action"] for call in mock_audit.log.call_args_list
                    ]
                    assert "create_branch" in actions_logged
                    assert "commit_files" in actions_logged
                    assert "create_pr" in actions_logged
