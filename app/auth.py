"""Authentication guard for API key bearer token validation.

Task 1.2: Define request auth guard for Authorization: Bearer <API_KEY>
with 401 behavior.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class AuthGuard:
    """Guards endpoints requiring API key authentication.

    Validates Bearer token against configured API key and sets
    agent identity on successful authentication.
    """

    def __init__(self, api_key: str) -> None:
        """Initialize the auth guard.

        Args:
            api_key: The expected API key for authentication
        """
        self._api_key = api_key

    async def require_auth(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(
            HTTPBearer(auto_error=False)
        ),
    ) -> None:
        """Dependency that validates Bearer token authentication.

        Args:
            request: The FastAPI request object
            credentials: Parsed bearer credentials (or None if missing/invalid)

        Raises:
            HTTPException: 401 if authentication fails

        Sets:
            request.state.agent: The authenticated agent identity ("hermes")
        """
        error_detail: str | None = None

        if credentials is None:
            error_detail = (
                "Missing Authorization header. Use: Authorization: Bearer <API_KEY>"
            )
        elif credentials.scheme.lower() != "bearer":
            error_detail = (
                f"Unsupported auth scheme '{credentials.scheme}'. Use: Bearer"
            )
        elif not credentials.credentials:
            error_detail = "Empty Bearer token. Use: Authorization: Bearer <API_KEY>"
        elif credentials.credentials != self._api_key:
            error_detail = "Invalid API key"

        if error_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "unauthorized", "message": error_detail},
            )

        # Set authenticated agent identity for audit logging
        request.state.agent = "hermes"


# Placeholder dependency for use in route signatures
# Will be overridden with actual AuthGuard instance at app setup
async def require_auth(request: Request) -> None:
    """Placeholder dependency - overridden at app setup with AuthGuard.require_auth."""
    pass
