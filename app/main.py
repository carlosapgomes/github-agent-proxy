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
from pydantic import BaseModel, Field, field_validator, model_validator

from app.audit import AuditLogger
from app.auth import AuthGuard
from app.github_client import GitHubAppConfig, GitHubClient, TokenProvider
from app.policy import Policy, PolicyLoader
from app.services import (
    BranchService,
    CommitService,
    PullRequestService,
    ServiceError,
)


class AppState:
    """Application state container with lazy initialization."""

    def __init__(self) -> None:
        self.policy: Policy | None = None
        self.auth_guard: AuthGuard | None = None
        self.audit_logger: AuditLogger | None = None
        self.token_provider: TokenProvider | None = None
        self.github_client: GitHubClient | None = None
        self.branch_service: BranchService | None = None
        self.commit_service: CommitService | None = None
        self.pr_service: PullRequestService | None = None
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

        # Initialize services
        self._init_services()

        self._initialized = True

    def _init_services(self) -> None:
        """Initialize service layer components."""
        if (
            self.policy is not None
            and self.github_client is not None
            and self.audit_logger is not None
        ):
            self.branch_service = BranchService(
                policy=self.policy,
                github_client=self.github_client,
                audit_logger=self.audit_logger,
            )
            self.commit_service = CommitService(
                policy=self.policy,
                github_client=self.github_client,
                audit_logger=self.audit_logger,
            )
            self.pr_service = PullRequestService(
                policy=self.policy,
                github_client=self.github_client,
                audit_logger=self.audit_logger,
            )

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


class FileToCommit(BaseModel):
    """A file to be committed."""

    path: str = Field(..., description="File path in the repository")
    content: str = Field(..., description="File content")


class CommitFilesRequest(BaseModel):
    """Request model for commit-files endpoint."""

    repo: str = Field(..., description="Repository in format 'owner/repo'")
    branch: str = Field(..., description="Target branch name")
    files: list[FileToCommit] = Field(
        ..., min_length=1, description="List of files to commit"
    )
    message: str = Field(..., description="Commit message")

    @field_validator("files")
    @classmethod
    def files_not_empty(cls, v: list[FileToCommit]) -> list[FileToCommit]:
        """Validate that files list is not empty."""
        if not v:
            raise ValueError("files list cannot be empty")
        return v


class CommitFilesResponse(BaseModel):
    """Response model for successful commit."""

    status: str = "success"
    sha: str
    message: str


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


def get_branch_service() -> BranchService:
    """Get the branch service from app state."""
    _app_state.ensure_initialized()
    if _app_state.branch_service is None:
        raise RuntimeError("Branch service not initialized")
    return _app_state.branch_service


def get_commit_service() -> CommitService:
    """Get the commit service from app state."""
    _app_state.ensure_initialized()
    if _app_state.commit_service is None:
        raise RuntimeError("Commit service not initialized")
    return _app_state.commit_service


def get_pr_service() -> PullRequestService:
    """Get the PR service from app state."""
    _app_state.ensure_initialized()
    if _app_state.pr_service is None:
        raise RuntimeError("PR service not initialized")
    return _app_state.pr_service


def get_agent(request: Request) -> str:
    """Get the authenticated agent from request state."""
    return getattr(request.state, "agent", "unknown")


def handle_service_error(error: ServiceError) -> HTTPException:
    """Convert service layer error to HTTP exception."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if error.error_code == "forbidden":
        status_code = status.HTTP_403_FORBIDDEN
    elif error.error_code == "server_error":
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return HTTPException(
        status_code=status_code,
        detail={"error": error.error_code, "message": error.message},
    )


@app.post("/create-branch", response_model=CreateBranchResponse)
async def create_branch(
    request: Request,
    body: CreateBranchRequest,
    _: None = Depends(require_auth),
    service: BranchService = Depends(get_branch_service),
) -> CreateBranchResponse:
    """Create a new branch in the specified repository.

    Args:
        request: FastAPI request object
        body: Branch creation request
        _: Auth dependency (validates API key)
        service: Branch service dependency

    Returns:
        CreateBranchResponse on success

    Raises:
        HTTPException: 403 if policy violation
        HTTPException: 500 if GitHub API error
    """
    agent = get_agent(request)

    try:
        result = service.create_branch(
            agent=agent,
            repo=body.repo,
            branch=body.branch,
            base=body.base,
        )

        return CreateBranchResponse(
            status="success",
            branch=result.branch,
            ref=result.ref,
        )

    except ServiceError as e:
        raise handle_service_error(e)


@app.post("/commit-files", response_model=CommitFilesResponse)
async def commit_files(
    request: Request,
    body: CommitFilesRequest,
    _: None = Depends(require_auth),
    service: CommitService = Depends(get_commit_service),
) -> CommitFilesResponse:
    """Commit files to a branch in the specified repository.

    Args:
        request: FastAPI request object
        body: Commit files request
        _: Auth dependency (validates API key)
        service: Commit service dependency

    Returns:
        CommitFilesResponse on success

    Raises:
        HTTPException: 403 if policy violation
        HTTPException: 422 if validation error
        HTTPException: 500 if GitHub API error
    """
    from app.services import FileEntry

    agent = get_agent(request)

    # Convert request files to FileEntry objects
    files = [FileEntry(path=f.path, content=f.content) for f in body.files]

    try:
        result = service.commit_files(
            agent=agent,
            repo=body.repo,
            branch=body.branch,
            files=files,
            message=body.message,
        )

        return CommitFilesResponse(
            status="success",
            sha=result.sha,
            message=result.message,
        )

    except ServiceError as e:
        raise handle_service_error(e)


class CreatePRRequest(BaseModel):
    """Request model for create-pr endpoint."""

    repo: str = Field(..., description="Repository in format 'owner/repo'")
    title: str = Field(..., description="Pull request title")
    body: str | None = Field(None, description="Pull request body/description")
    head: str = Field(..., description="Head branch (source)")
    base: str = Field(..., description="Base branch (target)")

    @model_validator(mode="after")
    def validate_head_not_equals_base(self) -> "CreatePRRequest":
        """Validate that head != base."""
        if self.head == self.base:
            raise ValueError("head and base branches must be different")
        return self


class CreatePRResponse(BaseModel):
    """Response model for successful PR creation."""

    status: str = "success"
    number: int
    url: str


@app.post("/create-pr", response_model=CreatePRResponse)
async def create_pr(
    request: Request,
    body: CreatePRRequest,
    _: None = Depends(require_auth),
    service: PullRequestService = Depends(get_pr_service),
) -> CreatePRResponse:
    """Create a pull request in the specified repository.

    Args:
        request: FastAPI request object
        body: Create PR request
        _: Auth dependency (validates API key)
        service: PR service dependency

    Returns:
        CreatePRResponse on success

    Raises:
        HTTPException: 403 if policy violation
        HTTPException: 422 if validation error (head == base)
        HTTPException: 500 if GitHub API error
    """
    agent = get_agent(request)

    try:
        result = service.create_pr(
            agent=agent,
            repo=body.repo,
            title=body.title,
            head=body.head,
            base=body.base,
            body=body.body,
        )

        return CreatePRResponse(
            status="success",
            number=result.number,
            url=result.url,
        )

    except ServiceError as e:
        raise handle_service_error(e)
