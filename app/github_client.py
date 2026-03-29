"""GitHub App installation token provider and API client.

Task 1.3: Define GitHub App installation-token provider abstraction
(token per request).
"""

import time
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from pydantic import BaseModel


class GitHubTokenError(Exception):
    """Raised when GitHub token generation fails."""

    pass


class GitHubAPIError(Exception):
    """Raised when GitHub API request fails."""

    pass


class GitHubAppConfig(BaseModel):
    """Configuration for GitHub App authentication.

    Attributes:
        app_id: The GitHub App ID
        private_key: The GitHub App private key (PEM format)
        installation_id: The installation ID for the target repository
    """

    app_id: str
    private_key: str
    installation_id: str


class TokenProvider:
    """Provides GitHub App installation tokens.

    Generates short-lived installation tokens for authenticating
    with the GitHub API. Tokens are cached and reused until
    they approach expiration.
    """

    # Token is refreshed 5 minutes before actual expiration
    _TOKEN_REFRESH_BUFFER_SECONDS = 300
    # JWT expiration time (10 minutes max per GitHub docs)
    _JWT_EXPIRATION_SECONDS = 600
    # GitHub API base URL
    _GITHUB_API_URL = "https://api.github.com"

    def __init__(self, config: GitHubAppConfig) -> None:
        """Initialize the token provider.

        Args:
            config: GitHub App configuration
        """
        self._config = config
        self._cached_token: str | None = None
        self._token_expires_at: datetime | None = None

    def get_installation_token(self) -> str:
        """Get a valid installation token.

        Returns a cached token if available and not near expiration,
        otherwise fetches a new token from GitHub.

        Returns:
            A valid GitHub installation token

        Raises:
            GitHubTokenError: If token generation fails
        """
        if self._is_token_valid():
            return self._cached_token  # type: ignore[return-value]

        return self._fetch_new_token()

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid.

        Returns:
            True if token exists and is not near expiration
        """
        if self._cached_token is None or self._token_expires_at is None:
            return False

        now = datetime.now(timezone.utc)
        buffer = timedelta(seconds=self._TOKEN_REFRESH_BUFFER_SECONDS)
        return now < (self._token_expires_at - buffer)

    def _fetch_new_token(self) -> str:
        """Fetch a new installation token from GitHub.

        Returns:
            The new installation token

        Raises:
            GitHubTokenError: If the API request fails
        """
        jwt_token = self._generate_jwt()
        url = f"{self._GITHUB_API_URL}/app/installations/{self._config.installation_id}/access_tokens"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            with httpx.Client() as client:
                response = client.post(url, headers=headers)

                if response.status_code != 201:
                    raise GitHubTokenError(
                        f"Failed to get installation token: "
                        f"status={response.status_code}, body={response.text}"
                    )

                data = response.json()
                token = data["token"]
                expires_at_str = data["expires_at"]

                # Parse expiration time
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )

                # Cache the token
                self._cached_token = token
                self._token_expires_at = expires_at

                return token

        except httpx.HTTPError as e:
            raise GitHubTokenError(f"Failed to get installation token: {e}") from e

    def _generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication.

        Creates a signed JWT with the app ID as issuer and
        a short expiration time.

        Returns:
            A signed JWT token
        """
        now = int(time.time())
        payload = {
            "iss": self._config.app_id,
            "iat": now,
            "exp": now + self._JWT_EXPIRATION_SECONDS,
        }

        return jwt.encode(payload, self._config.private_key, algorithm="RS256")


class GitHubClient:
    """Client for making authenticated requests to GitHub API.

    Uses the TokenProvider to get installation tokens for each request.
    """

    _GITHUB_API_URL = "https://api.github.com"

    def __init__(self, token_provider: TokenProvider) -> None:
        """Initialize the GitHub client.

        Args:
            token_provider: Provider for GitHub App installation tokens
        """
        self._token_provider = token_provider

    def create_branch(self, repo: str, branch: str, base: str) -> dict:
        """Create a new branch in a repository.

        Args:
            repo: Repository in format 'owner/repo'
            branch: Name of the new branch
            base: Base branch to create from

        Returns:
            GitHub API response with branch reference info

        Raises:
            GitHubAPIError: If the API request fails
        """
        token = self._token_provider.get_installation_token()

        # First, get the SHA of the base branch
        owner, repo_name = repo.split("/")
        ref_url = (
            f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/git/ref/heads/{base}"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            with httpx.Client() as client:
                # Get base branch SHA
                ref_response = client.get(ref_url, headers=headers)

                if ref_response.status_code != 200:
                    raise GitHubAPIError(
                        f"Failed to get base branch '{base}': "
                        f"status={ref_response.status_code}, body={ref_response.text}"
                    )

                base_sha = ref_response.json()["object"]["sha"]

                # Create the new branch
                create_url = (
                    f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/git/refs"
                )
                create_response = client.post(
                    create_url,
                    headers=headers,
                    json={
                        "ref": f"refs/heads/{branch}",
                        "sha": base_sha,
                    },
                )

                if create_response.status_code not in (200, 201):
                    raise GitHubAPIError(
                        f"Failed to create branch '{branch}': "
                        f"status={create_response.status_code}, body={create_response.text}"
                    )

                return create_response.json()

        except httpx.HTTPError as e:
            raise GitHubAPIError(f"GitHub API request failed: {e}") from e

    def commit_files(
        self,
        repo: str,
        branch: str,
        files: list[tuple[str, str]],
        message: str,
    ) -> dict:
        """Commit files to a branch in a repository.

        Args:
            repo: Repository in format 'owner/repo'
            branch: Target branch name
            files: List of (path, content) tuples
            message: Commit message

        Returns:
            GitHub API response with commit info

        Raises:
            GitHubAPIError: If the API request fails
        """
        token = self._token_provider.get_installation_token()

        owner, repo_name = repo.split("/")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            with httpx.Client() as client:
                # Get the latest commit on the branch
                ref_url = (
                    f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/"
                    f"git/ref/heads/{branch}"
                )
                ref_response = client.get(ref_url, headers=headers)

                if ref_response.status_code != 200:
                    raise GitHubAPIError(
                        f"Failed to get branch '{branch}': "
                        f"status={ref_response.status_code}, body={ref_response.text}"
                    )

                base_sha = ref_response.json()["object"]["sha"]

                # Get the base tree
                commit_url = (
                    f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/"
                    f"git/commits/{base_sha}"
                )
                commit_response = client.get(commit_url, headers=headers)

                if commit_response.status_code != 200:
                    raise GitHubAPIError(
                        f"Failed to get commit: status={commit_response.status_code}"
                    )

                base_tree_sha = commit_response.json()["tree"]["sha"]

                # Create blobs for each file
                blobs = []
                for file_path, content in files:
                    blob_url = (
                        f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/git/blobs"
                    )
                    blob_response = client.post(
                        blob_url,
                        headers=headers,
                        json={"content": content, "encoding": "utf-8"},
                    )

                    if blob_response.status_code != 201:
                        raise GitHubAPIError(
                            f"Failed to create blob for '{file_path}': "
                            f"status={blob_response.status_code}"
                        )

                    blobs.append(
                        {
                            "path": file_path,
                            "mode": "100644",
                            "type": "blob",
                            "sha": blob_response.json()["sha"],
                        }
                    )

                # Create a new tree with the blobs
                tree_url = f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/git/trees"
                tree_response = client.post(
                    tree_url,
                    headers=headers,
                    json={"base_tree": base_tree_sha, "tree": blobs},
                )

                if tree_response.status_code != 201:
                    raise GitHubAPIError(
                        f"Failed to create tree: status={tree_response.status_code}"
                    )

                new_tree_sha = tree_response.json()["sha"]

                # Create the commit
                new_commit_url = (
                    f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/git/commits"
                )
                new_commit_response = client.post(
                    new_commit_url,
                    headers=headers,
                    json={
                        "message": message,
                        "tree": new_tree_sha,
                        "parents": [base_sha],
                    },
                )

                if new_commit_response.status_code != 201:
                    raise GitHubAPIError(
                        f"Failed to create commit: "
                        f"status={new_commit_response.status_code}"
                    )

                new_commit_sha = new_commit_response.json()["sha"]

                # Update the branch reference
                update_ref_url = (
                    f"{self._GITHUB_API_URL}/repos/{owner}/{repo_name}/"
                    f"git/refs/heads/{branch}"
                )
                update_ref_response = client.patch(
                    update_ref_url,
                    headers=headers,
                    json={"sha": new_commit_sha},
                )

                if update_ref_response.status_code != 200:
                    raise GitHubAPIError(
                        f"Failed to update branch reference: "
                        f"status={update_ref_response.status_code}"
                    )

                return {"sha": new_commit_sha, "message": message}

        except httpx.HTTPError as e:
            raise GitHubAPIError(f"GitHub API request failed: {e}") from e
