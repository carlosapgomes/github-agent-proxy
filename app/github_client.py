"""GitHub App installation token provider.

Task 1.3: Define GitHub App installation-token provider abstraction
(token per request).
"""

import time
from datetime import datetime, timezone

import httpx
import jwt
from pydantic import BaseModel


class GitHubTokenError(Exception):
    """Raised when GitHub token generation fails."""

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


# Re-export timedelta for use in tests
from datetime import timedelta  # noqa: E402
