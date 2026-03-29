"""Service layer for GitHub Agent Proxy operations.

Task 2.4: Separates business logic from HTTP transport layer.
Task 3.2: Adds CommitService for commit-files operations.
Task 4.4: Consolidates shared policy checks into BaseService.
"""

from dataclasses import dataclass
from typing import NamedTuple, NoReturn

from app.audit import AuditLogger
from app.github_client import GitHubClient
from app.policy import Policy


class ServiceError(Exception):
    """Base exception for service layer errors."""

    def __init__(self, message: str, error_code: str = "error") -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ForbiddenError(ServiceError):
    """Raised when action is forbidden by policy."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="forbidden")


class ServerError(ServiceError):
    """Raised when server-side error occurs."""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="server_error")


# Keep old names for backward compatibility
BranchCreationError = ServiceError


@dataclass
class CreateBranchResult:
    """Result of successful branch creation."""

    branch: str
    ref: str


@dataclass
class CommitResult:
    """Result of successful commit creation."""

    sha: str
    message: str


class FileEntry(NamedTuple):
    """A file to be committed."""

    path: str
    content: str


@dataclass
class CreatePRResult:
    """Result of successful pull request creation."""

    number: int
    url: str
    title: str


class BaseService:
    """Base class for service layer with shared policy enforcement.

    Provides common authorization checks and audit logging for all services.
    """

    def __init__(
        self,
        policy: Policy,
        github_client: GitHubClient,
        audit_logger: AuditLogger,
    ) -> None:
        """Initialize the service.

        Args:
            policy: Authorization policy
            github_client: GitHub API client
            audit_logger: Audit logger instance
        """
        self._policy = policy
        self._github_client = github_client
        self._audit_logger = audit_logger

    def _check_repo_allowed(self, repo: str, action: str, agent: str) -> None:
        """Check if repository is allowed by policy.

        Args:
            repo: Repository to check
            action: Action name for audit logging
            agent: Agent identity for audit logging

        Raises:
            ForbiddenError: If repo is not allowed
        """
        if not self._policy.is_repo_allowed(repo):
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action=action,
                status="denied",
                error=f"Repository '{repo}' is not in allowed_repos",
            )
            raise ForbiddenError(f"Repository '{repo}' is not allowed")

    def _check_action_allowed(self, action: str, repo: str, agent: str) -> None:
        """Check if action is allowed by policy.

        Args:
            action: Action to check
            repo: Repository for audit logging
            agent: Agent identity for audit logging

        Raises:
            ForbiddenError: If action is not allowed
        """
        if not self._policy.is_action_allowed(action):
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action=action,
                status="denied",
                error=f"Action '{action}' is not in allowed_actions",
            )
            raise ForbiddenError(f"Action '{action}' is not allowed")

    def _check_branch_not_protected(
        self, branch: str, action: str, repo: str, agent: str
    ) -> None:
        """Check if branch is NOT protected.

        Args:
            branch: Branch name to check
            action: Action name for audit logging
            repo: Repository for audit logging
            agent: Agent identity for audit logging

        Raises:
            ForbiddenError: If branch is protected
        """
        if self._policy.is_branch_protected(branch):
            self._audit_logger.log(
                agent=agent,
                repo=repo,
                action=action,
                status="denied",
                error=f"Branch '{branch}' is protected",
            )
            raise ForbiddenError(f"Branch '{branch}' is protected")

    def _log_success(self, agent: str, repo: str, action: str) -> None:
        """Log successful operation.

        Args:
            agent: Agent identity
            repo: Repository
            action: Action name
        """
        self._audit_logger.log(
            agent=agent,
            repo=repo,
            action=action,
            status="success",
        )

    def _log_and_raise_github_error(
        self, error: Exception, agent: str, repo: str, action: str
    ) -> NoReturn:
        """Log GitHub API error and raise ServerError.

        Args:
            error: Original exception
            agent: Agent identity
            repo: Repository
            action: Action name

        Raises:
            ServerError: Always raised with wrapped error
        """
        self._audit_logger.log(
            agent=agent,
            repo=repo,
            action=action,
            status="denied",
            error=str(error),
        )
        raise ServerError(f"GitHub API error: {error}") from error


class BranchService(BaseService):
    """Service for branch-related operations.

    Encapsulates policy enforcement, GitHub operations, and audit logging
    for branch creation workflow.
    """

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
        action = "create_branch"

        # Policy checks
        self._check_repo_allowed(repo, action, agent)
        self._check_action_allowed(action, repo, agent)
        self._check_branch_not_protected(branch, action, repo, agent)

        # Create branch via GitHub
        try:
            result = self._github_client.create_branch(
                repo=repo,
                branch=branch,
                base=base,
            )
            self._log_success(agent, repo, action)

            return CreateBranchResult(
                branch=branch,
                ref=result.get("ref", f"refs/heads/{branch}"),
            )

        except Exception as e:
            self._log_and_raise_github_error(e, agent, repo, action)


class CommitService(BaseService):
    """Service for commit-related operations.

    Encapsulates policy enforcement, GitHub operations, and audit logging
    for file commit workflow.
    """

    def commit_files(
        self,
        agent: str,
        repo: str,
        branch: str,
        files: list[FileEntry],
        message: str,
    ) -> CommitResult:
        """Commit files to a branch with policy enforcement.

        Args:
            agent: Authenticated agent identity
            repo: Target repository
            branch: Target branch name
            files: List of files to commit
            message: Commit message

        Returns:
            CommitResult with commit details

        Raises:
            ForbiddenError: If policy denies the operation
            ServerError: If GitHub API fails
        """
        action = "commit_files"

        # Policy checks
        self._check_repo_allowed(repo, action, agent)
        self._check_action_allowed(action, repo, agent)
        self._check_branch_not_protected(branch, action, repo, agent)

        # Commit files via GitHub
        try:
            result = self._github_client.commit_files(
                repo=repo,
                branch=branch,
                files=[(f.path, f.content) for f in files],
                message=message,
            )
            self._log_success(agent, repo, action)

            return CommitResult(
                sha=result.get("sha", ""),
                message=message,
            )

        except Exception as e:
            self._log_and_raise_github_error(e, agent, repo, action)


class PullRequestService(BaseService):
    """Service for pull request operations.

    Encapsulates policy enforcement, GitHub operations, and audit logging
    for PR creation workflow.
    """

    def create_pr(
        self,
        agent: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str | None = None,
    ) -> CreatePRResult:
        """Create a pull request with policy enforcement.

        Args:
            agent: Authenticated agent identity
            repo: Target repository
            title: PR title
            head: Head branch (source)
            base: Base branch (target)
            body: Optional PR body/description

        Returns:
            CreatePRResult with PR details

        Raises:
            ForbiddenError: If policy denies the operation
            ServerError: If GitHub API fails
        """
        action = "create_pr"

        # Policy checks (note: base can be protected, only head is restricted)
        self._check_repo_allowed(repo, action, agent)
        self._check_action_allowed(action, repo, agent)
        self._check_branch_not_protected(head, action, repo, agent)

        # Create PR via GitHub
        try:
            result = self._github_client.create_pr(
                repo=repo,
                title=title,
                head=head,
                base=base,
                body=body,
            )
            self._log_success(agent, repo, action)

            return CreatePRResult(
                number=result["number"],
                url=result["html_url"],
                title=title,
            )

        except Exception as e:
            self._log_and_raise_github_error(e, agent, repo, action)
