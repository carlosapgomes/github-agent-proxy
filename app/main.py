"""FastAPI application for GitHub Agent Proxy.

Implements the MVP endpoints:
- POST /create-branch
- POST /commit-files
- POST /create-pr
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.audit import AuditLogger
from app.auth import AuthGuard
from app.github_client import GitHubAppConfig, GitHubClient, TokenProvider
from app.policy import Policy, PolicyLoader


class AppState:
    """Application state container with lazy initialization."""

    def __init__(self) -> None:
        self.policy: Policy | None = None
        self.auth_guard: AuthGuard | None = None
        self.audit_logger: AuditLogger | None = None
        self.token_provider: TokenProvider | None = None
        self.github_client: GitHubClient | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize all state if not already done."""
        if self._initialized:
            return

        # Load policy from config/policy.yaml
        policy_path = Path("config/policy.yaml")
        if policy_path.exists():
            policy_loader = PolicyLoader(policy_path)
            self.policy = policy_loader.load()

        # Initialize auth guard with API key from environment
        api_key = os.environ.get("PROXY_API_KEY", "test-api-key")
        self.auth_guard = AuthGuard(api_key=api_key)

        # Initialize audit logger
        self.audit_logger = AuditLogger()

        # Initialize GitHub token provider (if credentials are available)
        github_app_id = os.environ.get("GITHUB_APP_ID", "")
        github_private_key = os.environ.get("GITHUB_PRIVATE_KEY", "")
        github_installation_id = os.environ.get("GITHUB_INSTALLATION_ID", "")

        if github_app_id and github_private_key and github_installation_id:
            github_config = GitHubAppConfig(
                app_id=github_app_id,
                private_key=github_private_key,
                installation_id=github_installation_id,
            )
            self.token_provider = TokenProvider(github_config)
            self.github_client = GitHubClient(token_provider=self.token_provider)

        self._initialized = True

    def ensure_initialized(self) -> None:
        """Ensure state is initialized."""
        if not self._initialized:
            self.initialize()


# Global app state
_app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application state on startup."""
    _app_state.initialize()
    yield


app = FastAPI(
    title="GitHub Agent Proxy",
    description="Security middleware for Hermes agent GitHub operations",
    version="0.1.0",
    lifespan=lifespan,
)


# Request/Response models
class CreateBranchRequest(BaseModel):
    """Request model for create-branch endpoint."""

    repo: str = Field(..., description="Repository in format 'owner/repo'")
    branch: str = Field(..., description="Name of the new branch")
    base: str = Field(..., description="Base branch to create from")


class CreateBranchResponse(BaseModel):
    """Response model for successful branch creation."""

    status: str = "success"
    branch: str
    ref: str


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    message: str


# Custom exception handler for consistent error format
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent JSON format."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        # Already in our format (auth errors)
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "error", "message": str(exc.detail)},
    )


# Dependencies
async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> None:
    """Dependency that validates Bearer token authentication."""
    _app_state.ensure_initialized()
    if _app_state.auth_guard is None:
        raise RuntimeError("Auth guard not initialized")
    await _app_state.auth_guard.require_auth(request, credentials)


def check_policy(request: Request, repo: str, action: str) -> None:
    """Check if action is allowed on repo by policy.

    Args:
        request: FastAPI request object
        repo: Repository name
        action: Action name

    Raises:
        HTTPException: 403 if action or repo not allowed
    """
    _app_state.ensure_initialized()

    # Get agent from request state (set by auth guard)
    agent = getattr(request.state, "agent", "unknown")

    # Check if repo is allowed
    if _app_state.policy is None or not _app_state.policy.is_repo_allowed(repo):
        if _app_state.audit_logger:
            _app_state.audit_logger.log(
                agent=agent,
                repo=repo,
                action=action,
                status="denied",
                error=f"Repository '{repo}' is not in allowed_repos",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": f"Repository '{repo}' is not allowed",
            },
        )

    # Check if action is allowed
    if not _app_state.policy.is_action_allowed(action):
        if _app_state.audit_logger:
            _app_state.audit_logger.log(
                agent=agent,
                repo=repo,
                action=action,
                status="denied",
                error=f"Action '{action}' is not in allowed_actions",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": f"Action '{action}' is not allowed",
            },
        )


@app.post("/create-branch", response_model=CreateBranchResponse)
async def create_branch(
    request: Request,
    body: CreateBranchRequest,
    _: None = Depends(require_auth),
) -> CreateBranchResponse:
    """Create a new branch in the specified repository.

    Args:
        request: FastAPI request object
        body: Branch creation request
        _: Auth dependency (validates API key)

    Returns:
        CreateBranchResponse on success

    Raises:
        HTTPException: 403 if policy violation
        HTTPException: 500 if GitHub API error
    """
    _app_state.ensure_initialized()

    # Get agent from request state
    agent = getattr(request.state, "agent", "unknown")

    # Check policy (repo and action)
    check_policy(request, body.repo, "create_branch")

    # Check if branch name is protected
    if _app_state.policy and _app_state.policy.is_branch_protected(body.branch):
        if _app_state.audit_logger:
            _app_state.audit_logger.log(
                agent=agent,
                repo=body.repo,
                action="create_branch",
                status="denied",
                error=f"Branch '{body.branch}' is protected",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": f"Cannot create protected branch '{body.branch}'",
            },
        )

    # Create branch via GitHub client
    if _app_state.github_client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "server_error", "message": "GitHub client not configured"},
        )

    try:
        result = _app_state.github_client.create_branch(
            repo=body.repo,
            branch=body.branch,
            base=body.base,
        )

        # Log success
        if _app_state.audit_logger:
            _app_state.audit_logger.log(
                agent=agent,
                repo=body.repo,
                action="create_branch",
                status="success",
            )

        return CreateBranchResponse(
            status="success",
            branch=body.branch,
            ref=result.get("ref", f"refs/heads/{body.branch}"),
        )

    except Exception as e:
        if _app_state.audit_logger:
            _app_state.audit_logger.log(
                agent=agent,
                repo=body.repo,
                action="create_branch",
                status="denied",
                error=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "server_error", "message": f"GitHub API error: {e}"},
        )
