"""Policy loader and validation for YAML-based authorization.

Task 1.1: Define YAML policy loader and validation for allowed_repos,
allowed_actions, and protected_branches.
"""

from pathlib import Path
import yaml
from pydantic import BaseModel, Field


class PolicyError(Exception):
    """Raised when policy loading or validation fails."""

    pass


class Policy(BaseModel):
    """Authorization policy loaded from YAML configuration.

    Attributes:
        allowed_repos: List of repositories allowed for operations (e.g., "owner/repo")
        allowed_actions: List of allowed actions (create_branch, commit_files, create_pr)
        protected_branches: Branches that cannot receive direct writes
    """

    allowed_repos: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    protected_branches: list[str] = Field(default_factory=list)

    # Implicit protected branches that are always protected
    _IMPLICIT_PROTECTED: tuple[str, ...] = ("main", "master")

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        # Add implicit protected branches if not already present
        implicit = [
            b for b in self._IMPLICIT_PROTECTED if b not in self.protected_branches
        ]
        self.protected_branches = list(implicit) + self.protected_branches

    def is_repo_allowed(self, repo: str) -> bool:
        """Check if a repository is in the allowed list."""
        return repo in self.allowed_repos

    def is_action_allowed(self, action: str) -> bool:
        """Check if an action is in the allowed list."""
        return action in self.allowed_actions

    def is_branch_protected(self, branch: str) -> bool:
        """Check if a branch is protected (exact match only)."""
        return branch in self.protected_branches


class PolicyLoader:
    """Loads and validates policy from a YAML file."""

    def __init__(self, policy_path: Path) -> None:
        """Initialize the loader with the path to the policy file.

        Args:
            policy_path: Path to the YAML policy file
        """
        self.policy_path = policy_path

    def load(self) -> Policy:
        """Load and validate the policy from the YAML file.

        Returns:
            Validated Policy instance

        Raises:
            PolicyError: If file is missing, invalid YAML, or missing required fields
        """
        if not self.policy_path.exists():
            raise PolicyError(f"Policy file not found: {self.policy_path}")

        try:
            with self.policy_path.open("r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PolicyError(f"Invalid YAML in policy file: {e}") from e

        if data is None:
            raise PolicyError("Policy file is empty")

        if not isinstance(data, dict):
            raise PolicyError("Policy file must contain a YAML mapping")

        # Validate required fields
        required_fields = ["allowed_repos", "allowed_actions"]
        for field in required_fields:
            if field not in data:
                raise PolicyError(f"Missing required field: {field}")

        # protected_branches is optional, default to empty list
        protected_branches = data.get("protected_branches", [])
        if protected_branches is None:
            protected_branches = []

        return Policy(
            allowed_repos=data["allowed_repos"],
            allowed_actions=data["allowed_actions"],
            protected_branches=protected_branches,
        )
