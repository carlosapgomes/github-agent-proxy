"""Branch service layer for create-branch operations.

Task 2.4: Separates business logic from HTTP transport layer.
"""

from dataclasses import dataclass

from app.audit import AuditLogger
from app.github_client import GitHubClient
from app.policy import Policy


class BranchCreationError(Exception):
    """Raised when branch creation fails."""

    def __init__(self, message: str, error_code: str = "error") -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ForbiddenError(BranchCreationError):
    """Raised when action is forbidden by policy."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="forbidden")


class ServerError(BranchCreationError):
    """Raised when server-side error occurs."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="server_error")


@dataclass
class CreateBranchResult:
    """Result of successful branch creation."""

    branch: str
    ref: str


class BranchService:
    """Service for branch-related operations.

    Encapsulates policy enforcement, GitHub operations, and audit logging
    for branch creation workflow.
    """

    def __init__(
        self,
        policy: Policy,
        github_client: GitHubClient,
        audit_logger: AuditLogger,
    ) -> None:
        """Initialize the branch service.

        Args:
            policy: Authorization policy
            github_client: GitHub API client
            audit_logger: Audit logger instance
        """
        self._policy = policy
        self._github_client = github_client
        self._audit_logger = audit_logger

    def create_branch(
        self,
        agent: str,
        repo: str,
        branch: str,
        base: str,
    ) -> CreateBranchResult:
        """Create a new branch with policy enforcement.

        Args:
            agent: Authenticated agent identity
            repo: Target repository
            branch: New branch name
            base: Base branch name

        Returns:
            CreateBranchResult with branch details

        Raises:
            ForbiddenError: If policy denies the operation
            ServerError: If GitHub API fails
        """
        # Check repo authorization
        if not self._policy.is_repo_allowed(repo):
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action="create_branch",
                status="denied",
                error=f"Repository '{repo}' is not in allowed_repos",
            )
            raise ForbiddenError(f"Repository '{repo}' is not allowed")

        # Check action authorization
        if not self._policy.is_action_allowed("create_branch"):
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action="create_branch",
                status="denied",
                error="Action 'create_branch' is not in allowed_actions",
            )
            raise ForbiddenError("Action 'create_branch' is not allowed")

        # Check protected branch
        if self._policy.is_branch_protected(branch):
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action="create_branch",
                status="denied",
                error=f"Branch '{branch}' is protected",
            )
            raise ForbiddenError(f"Cannot create protected branch '{branch}'")

        # Create branch via GitHub
        try:
            result = self._github_client.create_branch(
                repo=repo,
                branch=branch,
                base=base,
            )

            # Log success
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action="create_branch",
                status="success",
            )

            return CreateBranchResult(
                branch=branch,
                ref=result.get("ref", f"refs/heads/{branch}"),
            )

        except Exception as e:
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action="create_branch",
                status="denied",
                error=str(e),
            )
            raise ServerError(f"GitHub API error: {e}") from e
