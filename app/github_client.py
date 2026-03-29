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
