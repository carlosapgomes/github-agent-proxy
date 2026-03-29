"""Tests for authentication guard (Task 1.2)."""

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.auth import AuthGuard


def create_test_app(api_key: str) -> FastAPI:
    """Factory to create a test app with auth guard configured."""
    app = FastAPI()
    guard = AuthGuard(api_key=api_key)

    @app.get("/protected")
    async def protected_route(request: Request, _: None = Depends(guard.require_auth)):
        return {"status": "ok", "agent": request.state.agent}

    @app.post("/create-branch")
    async def create_branch(request: Request, _: None = Depends(guard.require_auth)):
        return {"action": "create_branch", "agent": request.state.agent}

    @app.post("/commit-files")
    async def commit_files(request: Request, _: None = Depends(guard.require_auth)):
        return {"action": "commit_files", "agent": request.state.agent}

    @app.post("/create-pr")
    async def create_pr(request: Request, _: None = Depends(guard.require_auth)):
        return {"action": "create_pr", "agent": request.state.agent}

    return app


class TestAuthGuard:
    """Tests for API key authentication guard."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        app = create_test_app(api_key="test-secret-key-123")
        return TestClient(app)

    def test_valid_bearer_token_succeeds(self, client: TestClient) -> None:
        """WHEN valid Bearer token is provided THEN request succeeds."""
        response = client.get(
            "/protected", headers={"Authorization": "Bearer test-secret-key-123"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["agent"] == "hermes"

    def test_missing_authorization_header_returns_401(self, client: TestClient) -> None:
        """WHEN Authorization header is missing THEN returns 401."""
        response = client.get("/protected")

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "unauthorized"
        assert "Authorization" in data["detail"]["message"]

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """WHEN invalid token is provided THEN returns 401."""
        response = client.get(
            "/protected", headers={"Authorization": "Bearer wrong-key"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "unauthorized"

    def test_non_bearer_scheme_returns_401(self, client: TestClient) -> None:
        """WHEN non-Bearer auth scheme is used THEN returns 401."""
        response = client.get(
            "/protected", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "unauthorized"
        assert "Bearer" in data["detail"]["message"]

    def test_malformed_authorization_header_returns_401(
        self, client: TestClient
    ) -> None:
        """WHEN Authorization header is malformed THEN returns 401."""
        response = client.get(
            "/protected", headers={"Authorization": "BearerTest invalid"}
        )

        assert response.status_code == 401

    def test_empty_bearer_token_returns_401(self, client: TestClient) -> None:
        """WHEN Bearer token is empty THEN returns 401."""
        response = client.get("/protected", headers={"Authorization": "Bearer "})

        assert response.status_code == 401


class TestAuthGuardIntegration:
    """Integration tests for auth guard with different endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client with multiple protected routes."""
        app = create_test_app(api_key="secret")
        return TestClient(app)

    def test_all_endpoints_require_auth(self, client: TestClient) -> None:
        """WHEN any endpoint is called without auth THEN returns 401."""
        endpoints = ["/create-branch", "/commit-files", "/create-pr"]

        for endpoint in endpoints:
            response = client.post(endpoint)
            assert response.status_code == 401, f"{endpoint} should require auth"

    def test_all_endpoints_accept_valid_auth(self, client: TestClient) -> None:
        """WHEN valid auth is provided to any endpoint THEN succeeds."""
        endpoints = ["/create-branch", "/commit-files", "/create-pr"]
        headers = {"Authorization": "Bearer secret"}

        for endpoint in endpoints:
            response = client.post(endpoint, headers=headers)
            assert response.status_code == 200, f"{endpoint} should accept valid auth"
            assert response.json()["agent"] == "hermes"
