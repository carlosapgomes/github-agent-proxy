"""Tests for AppState commit author configuration."""

from unittest.mock import MagicMock, patch

import pytest

from app.main import AppState


class TestAppStateCommitAuthorConfiguration:
    """Tests for fixed commit author environment configuration."""

    @pytest.fixture(autouse=True)
    def clear_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear relevant environment variables for each test."""
        for key in [
            "PROXY_API_KEY",
            "GITHUB_APP_ID",
            "GITHUB_PRIVATE_KEY",
            "GITHUB_INSTALLATION_ID",
            "GITHUB_COMMIT_AUTHOR_NAME",
            "GITHUB_COMMIT_AUTHOR_EMAIL",
        ]:
            monkeypatch.delenv(key, raising=False)

    def test_initialize_raises_for_author_name_without_email(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WHEN only author name is configured THEN startup fails fast."""
        monkeypatch.setenv("GITHUB_COMMIT_AUTHOR_NAME", "Carlos Example")

        state = AppState()

        with pytest.raises(
            RuntimeError,
            match=(
                "GITHUB_COMMIT_AUTHOR_NAME and GITHUB_COMMIT_AUTHOR_EMAIL "
                "must be set together"
            ),
        ):
            state.initialize()

    def test_initialize_raises_for_author_email_without_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WHEN only author email is configured THEN startup fails fast."""
        monkeypatch.setenv(
            "GITHUB_COMMIT_AUTHOR_EMAIL", "123+carlos@users.noreply.github.com"
        )

        state = AppState()

        with pytest.raises(
            RuntimeError,
            match=(
                "GITHUB_COMMIT_AUTHOR_NAME and GITHUB_COMMIT_AUTHOR_EMAIL "
                "must be set together"
            ),
        ):
            state.initialize()

    def test_initialize_passes_commit_author_to_github_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WHEN full author config exists THEN GitHubClient receives commit author."""
        monkeypatch.setenv("GITHUB_APP_ID", "123")
        monkeypatch.setenv(
            "GITHUB_PRIVATE_KEY",
            "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
        )
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "456")
        monkeypatch.setenv("GITHUB_COMMIT_AUTHOR_NAME", "Carlos Example")
        monkeypatch.setenv(
            "GITHUB_COMMIT_AUTHOR_EMAIL", "123+carlos@users.noreply.github.com"
        )

        state = AppState()

        with (
            patch("app.main.TokenProvider") as mock_token_provider,
            patch("app.main.GitHubClient") as mock_github_client,
        ):
            mock_token_provider.return_value = MagicMock()
            mock_github_client.return_value = MagicMock()

            state.initialize()

            mock_github_client.assert_called_once()
            call_kwargs = mock_github_client.call_args.kwargs
            assert call_kwargs["commit_author"].name == "Carlos Example"
            assert (
                call_kwargs["commit_author"].email
                == "123+carlos@users.noreply.github.com"
            )
