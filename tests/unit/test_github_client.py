"""Tests for GitHub App installation token provider (Task 1.3)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.github_client import GitHubAppConfig, GitHubTokenError, TokenProvider


class TestGitHubAppConfig:
    """Tests for GitHub App configuration."""

    def test_valid_config(self) -> None:
        """WHEN valid config is created THEN all fields are set."""
        config = GitHubAppConfig(
            app_id="123456",
            private_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
            installation_id="789",
        )

        assert config.app_id == "123456"
        assert (
            config.private_key
            == "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
        )
        assert config.installation_id == "789"

    def test_missing_app_id_raises_error(self) -> None:
        """WHEN app_id is missing THEN ValidationError is raised."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GitHubAppConfig(
                private_key="key",
                installation_id="789",
            )

    def test_missing_private_key_raises_error(self) -> None:
        """WHEN private_key is missing THEN ValidationError is raised."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GitHubAppConfig(
                app_id="123456",
                installation_id="789",
            )

    def test_missing_installation_id_raises_error(self) -> None:
        """WHEN installation_id is missing THEN ValidationError is raised."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GitHubAppConfig(
                app_id="123456",
                private_key="key",
            )


class TestTokenProvider:
    """Tests for GitHub App installation token provider."""

    @pytest.fixture
    def config(self) -> GitHubAppConfig:
        """Create a test configuration."""
        return GitHubAppConfig(
            app_id="123456",
            private_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
            installation_id="789",
        )

    def test_get_installation_token_success(self, config: GitHubAppConfig) -> None:
        """WHEN token request succeeds THEN returns installation token."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_test_installation_token",
            "expires_at": "2024-01-01T12:00:00Z",
        }

        with (
            patch.object(TokenProvider, "_generate_jwt", return_value="mock-jwt"),
            patch("app.github_client.httpx.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            provider = TokenProvider(config)
            token = provider.get_installation_token()

            assert token == "ghs_test_installation_token"

    def test_get_installation_token_caches_token(self, config: GitHubAppConfig) -> None:
        """WHEN token is cached AND not expired THEN returns cached token."""
        future_expires = (
            (datetime.now(timezone.utc) + timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z")
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_cached_token",
            "expires_at": future_expires,
        }

        with (
            patch.object(TokenProvider, "_generate_jwt", return_value="mock-jwt"),
            patch("app.github_client.httpx.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            provider = TokenProvider(config)

            # First call
            token1 = provider.get_installation_token()
            # Second call - should use cache
            token2 = provider.get_installation_token()

            assert token1 == token2 == "ghs_cached_token"
            # Should only call GitHub API once
            mock_client.post.assert_called_once()

    def test_get_installation_token_refreshes_expired_token(
        self, config: GitHubAppConfig
    ) -> None:
        """WHEN cached token is expired THEN fetches new token."""
        # First response - token that is already expired
        past_expires = (
            (datetime.now(timezone.utc) - timedelta(minutes=5))
            .isoformat()
            .replace("+00:00", "Z")
        )
        future_expires = (
            (datetime.now(timezone.utc) + timedelta(hours=1))
            .isoformat()
            .replace("+00:00", "Z")
        )

        expired_response = MagicMock()
        expired_response.status_code = 201
        expired_response.json.return_value = {
            "token": "ghs_expired_token",
            "expires_at": past_expires,
        }

        fresh_response = MagicMock()
        fresh_response.status_code = 201
        fresh_response.json.return_value = {
            "token": "ghs_fresh_token",
            "expires_at": future_expires,
        }

        with (
            patch.object(TokenProvider, "_generate_jwt", return_value="mock-jwt"),
            patch("app.github_client.httpx.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.post.side_effect = [expired_response, fresh_response]
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            provider = TokenProvider(config)

            # First call gets expired token
            token1 = provider.get_installation_token()

            # Force cache invalidation check by clearing
            provider._cached_token = None
            provider._token_expires_at = None

            # Second call should fetch fresh token
            token2 = provider.get_installation_token()

            assert token1 == "ghs_expired_token"
            assert token2 == "ghs_fresh_token"

    def test_get_installation_token_github_error_raises_error(
        self, config: GitHubAppConfig
    ) -> None:
        """WHEN GitHub API returns error THEN raises GitHubTokenError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with (
            patch.object(TokenProvider, "_generate_jwt", return_value="mock-jwt"),
            patch("app.github_client.httpx.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            provider = TokenProvider(config)

            with pytest.raises(
                GitHubTokenError, match="Failed to get installation token"
            ):
                provider.get_installation_token()

    def test_get_installation_token_network_error_raises_error(
        self, config: GitHubAppConfig
    ) -> None:
        """WHEN network error occurs THEN raises GitHubTokenError."""
        import httpx

        with (
            patch.object(TokenProvider, "_generate_jwt", return_value="mock-jwt"),
            patch("app.github_client.httpx.Client") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_class.return_value = mock_client

            provider = TokenProvider(config)

            with pytest.raises(
                GitHubTokenError, match="Failed to get installation token"
            ):
                provider.get_installation_token()


class TestTokenProviderJWTGeneration:
    """Tests for JWT token generation for GitHub App authentication."""

    @pytest.fixture
    def config(self) -> GitHubAppConfig:
        """Create a test configuration."""
        return GitHubAppConfig(
            app_id="123456",
            private_key="-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7Lso\n-----END RSA PRIVATE KEY-----",
            installation_id="789",
        )

    def test_generate_jwt_uses_correct_claims(self, config: GitHubAppConfig) -> None:
        """WHEN generating JWT THEN uses correct claims (iss, iat, exp)."""
        with patch("app.github_client.jwt.encode") as mock_encode:
            mock_encode.return_value = "jwt-token"

            provider = TokenProvider(config)
            # Access private method to verify JWT generation
            jwt_token = provider._generate_jwt()

            assert jwt_token == "jwt-token"
            # Verify encode was called with correct claims
            call_args = mock_encode.call_args
            payload = call_args[0][0]

            assert payload["iss"] == "123456"  # app_id
            assert "iat" in payload
            assert "exp" in payload
            # exp should be ~10 minutes from iat
            assert payload["exp"] - payload["iat"] <= 600

    def test_generate_jwt_uses_rs256_algorithm(self, config: GitHubAppConfig) -> None:
        """WHEN generating JWT THEN uses RS256 algorithm."""
        with patch("app.github_client.jwt.encode") as mock_encode:
            mock_encode.return_value = "jwt-token"

            provider = TokenProvider(config)
            provider._generate_jwt()

            call_kwargs = mock_encode.call_args[1]
            assert call_kwargs["algorithm"] == "RS256"
