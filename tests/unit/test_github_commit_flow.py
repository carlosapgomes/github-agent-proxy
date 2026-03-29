"""Tests for GitHub commit flow integration (Task 3.3).

Verifies GitHubClient.commit_files() correctly orchestrates:
- Getting branch SHA
- Creating blobs
- Creating tree
- Creating commit
- Updating branch reference
"""

from unittest.mock import MagicMock, patch

import pytest

from app.github_client import GitHubAPIError, GitHubClient, TokenProvider


class TestGitHubClientCommitFiles:
    """Tests for GitHubClient.commit_files method."""

    @pytest.fixture
    def mock_token_provider(self) -> MagicMock:
        """Create a mock token provider."""
        mock = MagicMock(spec=TokenProvider)
        mock.get_installation_token.return_value = "ghs_test_token"
        return mock

    @pytest.fixture
    def client(self, mock_token_provider: MagicMock) -> GitHubClient:
        """Create a GitHubClient with mocked token provider."""
        return GitHubClient(token_provider=mock_token_provider)

    def test_commit_files_success(self, client: GitHubClient) -> None:
        """WHEN committing files THEN creates blobs, tree, commit and updates branch."""
        with patch("httpx.Client") as mock_httpx:
            # Mock responses for each step
            mock_ref_response = MagicMock()
            mock_ref_response.status_code = 200
            mock_ref_response.json.return_value = {"object": {"sha": "base-sha-123"}}

            mock_commit_response = MagicMock()
            mock_commit_response.status_code = 200
            mock_commit_response.json.return_value = {"tree": {"sha": "tree-sha-base"}}

            mock_blob_response = MagicMock()
            mock_blob_response.status_code = 201
            mock_blob_response.json.return_value = {"sha": "blob-sha-1"}

            mock_tree_response = MagicMock()
            mock_tree_response.status_code = 201
            mock_tree_response.json.return_value = {"sha": "new-tree-sha"}

            mock_new_commit_response = MagicMock()
            mock_new_commit_response.status_code = 201
            mock_new_commit_response.json.return_value = {"sha": "new-commit-sha"}

            mock_update_ref_response = MagicMock()
            mock_update_ref_response.status_code = 200

            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = [mock_ref_response, mock_commit_response]
            mock_http_client.post.side_effect = [
                mock_blob_response,
                mock_tree_response,
                mock_new_commit_response,
            ]
            mock_http_client.patch.return_value = mock_update_ref_response
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            result = client.commit_files(
                repo="owner/repo",
                branch="feature/test",
                files=[("test.txt", "hello world")],
                message="Add test file",
            )

            assert result["sha"] == "new-commit-sha"
            assert result["message"] == "Add test file"

    def test_commit_files_multiple_files(self, client: GitHubClient) -> None:
        """WHEN committing multiple files THEN creates blob for each."""
        with patch("httpx.Client") as mock_httpx:
            mock_ref_response = MagicMock()
            mock_ref_response.status_code = 200
            mock_ref_response.json.return_value = {"object": {"sha": "base-sha"}}

            mock_commit_response = MagicMock()
            mock_commit_response.status_code = 200
            mock_commit_response.json.return_value = {"tree": {"sha": "tree-sha"}}

            mock_blob_1 = MagicMock()
            mock_blob_1.status_code = 201
            mock_blob_1.json.return_value = {"sha": "blob-sha-1"}

            mock_blob_2 = MagicMock()
            mock_blob_2.status_code = 201
            mock_blob_2.json.return_value = {"sha": "blob-sha-2"}

            mock_tree_response = MagicMock()
            mock_tree_response.status_code = 201
            mock_tree_response.json.return_value = {"sha": "new-tree"}

            mock_new_commit = MagicMock()
            mock_new_commit.status_code = 201
            mock_new_commit.json.return_value = {"sha": "commit-sha"}

            mock_update_ref = MagicMock()
            mock_update_ref.status_code = 200

            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = [mock_ref_response, mock_commit_response]
            mock_http_client.post.side_effect = [
                mock_blob_1,
                mock_blob_2,
                mock_tree_response,
                mock_new_commit,
            ]
            mock_http_client.patch.return_value = mock_update_ref
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            result = client.commit_files(
                repo="owner/repo",
                branch="feature/test",
                files=[
                    ("file1.txt", "content1"),
                    ("file2.txt", "content2"),
                ],
                message="Add files",
            )

            assert result["sha"] == "commit-sha"
            # Verify 2 blobs were created + tree + commit = 4 posts
            assert mock_http_client.post.call_count == 4

    def test_commit_files_branch_not_found_raises_error(
        self, client: GitHubClient
    ) -> None:
        """WHEN branch doesn't exist THEN raises GitHubAPIError."""
        with patch("httpx.Client") as mock_httpx:
            mock_ref_response = MagicMock()
            mock_ref_response.status_code = 404
            mock_ref_response.text = "Not Found"

            mock_http_client = MagicMock()
            mock_http_client.get.return_value = mock_ref_response
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            with pytest.raises(GitHubAPIError, match="Failed to get branch"):
                client.commit_files(
                    repo="owner/repo",
                    branch="nonexistent",
                    files=[("test.txt", "content")],
                    message="Test",
                )

    def test_commit_files_blob_error_raises_error(self, client: GitHubClient) -> None:
        """WHEN blob creation fails THEN raises GitHubAPIError."""
        with patch("httpx.Client") as mock_httpx:
            mock_ref_response = MagicMock()
            mock_ref_response.status_code = 200
            mock_ref_response.json.return_value = {"object": {"sha": "base-sha"}}

            mock_commit_response = MagicMock()
            mock_commit_response.status_code = 200
            mock_commit_response.json.return_value = {"tree": {"sha": "tree-sha"}}

            mock_blob_response = MagicMock()
            mock_blob_response.status_code = 500
            mock_blob_response.text = "Internal Server Error"

            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = [mock_ref_response, mock_commit_response]
            mock_http_client.post.return_value = mock_blob_response
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            with pytest.raises(GitHubAPIError, match="Failed to create blob"):
                client.commit_files(
                    repo="owner/repo",
                    branch="feature/test",
                    files=[("test.txt", "content")],
                    message="Test",
                )

    def test_commit_files_uses_correct_api_version(self, client: GitHubClient) -> None:
        """WHEN making API calls THEN uses correct GitHub API version header."""
        with patch("httpx.Client") as mock_httpx:
            mock_ref_response = MagicMock()
            mock_ref_response.status_code = 200
            mock_ref_response.json.return_value = {"object": {"sha": "sha"}}

            mock_commit_response = MagicMock()
            mock_commit_response.status_code = 200
            mock_commit_response.json.return_value = {"tree": {"sha": "tree"}}

            mock_blob_response = MagicMock()
            mock_blob_response.status_code = 201
            mock_blob_response.json.return_value = {"sha": "blob"}

            mock_tree_response = MagicMock()
            mock_tree_response.status_code = 201
            mock_tree_response.json.return_value = {"sha": "new-tree"}

            mock_new_commit = MagicMock()
            mock_new_commit.status_code = 201
            mock_new_commit.json.return_value = {"sha": "commit"}

            mock_update_ref = MagicMock()
            mock_update_ref.status_code = 200

            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = [mock_ref_response, mock_commit_response]
            mock_http_client.post.side_effect = [
                mock_blob_response,
                mock_tree_response,
                mock_new_commit,
            ]
            mock_http_client.patch.return_value = mock_update_ref
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            client.commit_files(
                repo="owner/repo",
                branch="main",
                files=[("test.txt", "content")],
                message="Test",
            )

            # Check all calls use correct API version
            for call in mock_http_client.get.call_args_list:
                headers = call[1]["headers"]
                assert headers["X-GitHub-Api-Version"] == "2022-11-28"

            for call in mock_http_client.post.call_args_list:
                headers = call[1]["headers"]
                assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_commit_files_network_error_raises_error(
        self, client: GitHubClient
    ) -> None:
        """WHEN network error occurs THEN raises GitHubAPIError."""
        import httpx

        with patch("httpx.Client") as mock_httpx:
            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            with pytest.raises(GitHubAPIError, match="GitHub API request failed"):
                client.commit_files(
                    repo="owner/repo",
                    branch="main",
                    files=[("test.txt", "content")],
                    message="Test",
                )


class TestGitHubClientCommitFilesTokenUsage:
    """Tests for token usage in commit_files method."""

    def test_commit_files_obtains_token(self) -> None:
        """WHEN commit_files is called THEN obtains token from provider."""
        mock_token_provider = MagicMock(spec=TokenProvider)
        mock_token_provider.get_installation_token.return_value = "ghs_test_token"

        client = GitHubClient(token_provider=mock_token_provider)

        with patch("httpx.Client") as mock_httpx:
            # Setup minimal mock responses
            mock_ref = MagicMock()
            mock_ref.status_code = 200
            mock_ref.json.return_value = {"object": {"sha": "sha"}}

            mock_commit = MagicMock()
            mock_commit.status_code = 200
            mock_commit.json.return_value = {"tree": {"sha": "tree"}}

            mock_blob = MagicMock()
            mock_blob.status_code = 201
            mock_blob.json.return_value = {"sha": "blob"}

            mock_tree = MagicMock()
            mock_tree.status_code = 201
            mock_tree.json.return_value = {"sha": "new-tree"}

            mock_new_commit = MagicMock()
            mock_new_commit.status_code = 201
            mock_new_commit.json.return_value = {"sha": "commit"}

            mock_update = MagicMock()
            mock_update.status_code = 200

            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = [mock_ref, mock_commit]
            mock_http_client.post.side_effect = [mock_blob, mock_tree, mock_new_commit]
            mock_http_client.patch.return_value = mock_update
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            client.commit_files(
                repo="owner/repo",
                branch="main",
                files=[("test.txt", "content")],
                message="Test",
            )

            mock_token_provider.get_installation_token.assert_called_once()

    def test_commit_files_token_used_in_all_requests(self) -> None:
        """WHEN making commit requests THEN token is used in Authorization header."""
        test_token = "ghs_test_token_123"
        mock_token_provider = MagicMock(spec=TokenProvider)
        mock_token_provider.get_installation_token.return_value = test_token

        client = GitHubClient(token_provider=mock_token_provider)

        with patch("httpx.Client") as mock_httpx:
            mock_ref = MagicMock()
            mock_ref.status_code = 200
            mock_ref.json.return_value = {"object": {"sha": "sha"}}

            mock_commit = MagicMock()
            mock_commit.status_code = 200
            mock_commit.json.return_value = {"tree": {"sha": "tree"}}

            mock_blob = MagicMock()
            mock_blob.status_code = 201
            mock_blob.json.return_value = {"sha": "blob"}

            mock_tree = MagicMock()
            mock_tree.status_code = 201
            mock_tree.json.return_value = {"sha": "new-tree"}

            mock_new_commit = MagicMock()
            mock_new_commit.status_code = 201
            mock_new_commit.json.return_value = {"sha": "commit"}

            mock_update = MagicMock()
            mock_update.status_code = 200

            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = [mock_ref, mock_commit]
            mock_http_client.post.side_effect = [mock_blob, mock_tree, mock_new_commit]
            mock_http_client.patch.return_value = mock_update
            mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
            mock_http_client.__exit__ = MagicMock(return_value=False)
            mock_httpx.return_value = mock_http_client

            client.commit_files(
                repo="owner/repo",
                branch="main",
                files=[("test.txt", "content")],
                message="Test",
            )

            # Verify token used in all requests
            expected_auth = f"Bearer {test_token}"

            for call in mock_http_client.get.call_args_list:
                assert call[1]["headers"]["Authorization"] == expected_auth

            for call in mock_http_client.post.call_args_list:
                assert call[1]["headers"]["Authorization"] == expected_auth

            for call in mock_http_client.patch.call_args_list:
                assert call[1]["headers"]["Authorization"] == expected_auth
