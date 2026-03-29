"""Tests for policy loader and validation (Task 1.1)."""

from pathlib import Path

import pytest
import yaml

from app.policy import Policy, PolicyLoader, PolicyError


class TestPolicyLoader:
    """Tests for YAML policy loading and validation."""

    def test_load_valid_policy(self, tmp_path: Path) -> None:
        """WHEN a valid policy YAML exists THEN it loads successfully."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(
            yaml.dump(
                {
                    "allowed_repos": ["owner/repo1", "owner/repo2"],
                    "allowed_actions": ["create_branch", "commit_files", "create_pr"],
                    "protected_branches": ["release/*"],
                }
            )
        )

        loader = PolicyLoader(policy_file)
        policy = loader.load()

        assert policy.allowed_repos == ["owner/repo1", "owner/repo2"]
        assert policy.allowed_actions == ["create_branch", "commit_files", "create_pr"]
        # protected_branches should include configured + implicit main/master
        assert "release/*" in policy.protected_branches
        assert "main" in policy.protected_branches
        assert "master" in policy.protected_branches

    def test_missing_policy_file_raises_error(self, tmp_path: Path) -> None:
        """WHEN policy file does not exist THEN PolicyError is raised."""
        missing_file = tmp_path / "nonexistent.yaml"
        loader = PolicyLoader(missing_file)

        with pytest.raises(PolicyError, match="Policy file not found"):
            loader.load()

    def test_missing_allowed_repos_raises_error(self, tmp_path: Path) -> None:
        """WHEN allowed_repos is missing THEN PolicyError is raised."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(
            yaml.dump(
                {
                    "allowed_actions": ["create_branch"],
                    "protected_branches": [],
                }
            )
        )

        loader = PolicyLoader(policy_file)
        with pytest.raises(PolicyError, match="allowed_repos"):
            loader.load()

    def test_missing_allowed_actions_raises_error(self, tmp_path: Path) -> None:
        """WHEN allowed_actions is missing THEN PolicyError is raised."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(
            yaml.dump(
                {
                    "allowed_repos": ["owner/repo"],
                    "protected_branches": [],
                }
            )
        )

        loader = PolicyLoader(policy_file)
        with pytest.raises(PolicyError, match="allowed_actions"):
            loader.load()

    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """WHEN YAML is malformed THEN PolicyError is raised."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("not: valid: yaml: [")

        loader = PolicyLoader(policy_file)
        with pytest.raises(PolicyError, match="Invalid YAML"):
            loader.load()

    def test_empty_policy_file_raises_error(self, tmp_path: Path) -> None:
        """WHEN policy file is empty THEN PolicyError is raised."""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text("")

        loader = PolicyLoader(policy_file)
        with pytest.raises(PolicyError):
            loader.load()


class TestPolicy:
    """Tests for policy validation methods."""

    @pytest.fixture
    def policy(self) -> Policy:
        """Create a sample policy for testing."""
        return Policy(
            allowed_repos=["owner/repo1", "owner/repo2"],
            allowed_actions=["create_branch", "commit_files", "create_pr"],
            protected_branches=["release/*", "main", "master"],  # includes implicit
        )

    def test_is_repo_allowed_true(self, policy: Policy) -> None:
        """WHEN repo is in allowed_repos THEN is_repo_allowed returns True."""
        assert policy.is_repo_allowed("owner/repo1") is True
        assert policy.is_repo_allowed("owner/repo2") is True

    def test_is_repo_allowed_false(self, policy: Policy) -> None:
        """WHEN repo is not in allowed_repos THEN is_repo_allowed returns False."""
        assert policy.is_repo_allowed("owner/other") is False
        assert policy.is_repo_allowed("different/repo") is False

    def test_is_action_allowed_true(self, policy: Policy) -> None:
        """WHEN action is in allowed_actions THEN is_action_allowed returns True."""
        assert policy.is_action_allowed("create_branch") is True
        assert policy.is_action_allowed("commit_files") is True
        assert policy.is_action_allowed("create_pr") is True

    def test_is_action_allowed_false(self, policy: Policy) -> None:
        """WHEN action is not in allowed_actions THEN is_action_allowed returns False."""
        assert policy.is_action_allowed("delete_branch") is False
        assert policy.is_action_allowed("merge_pr") is False

    def test_is_branch_protected_explicit(self, policy: Policy) -> None:
        """WHEN branch is in protected_branches THEN is_branch_protected returns True."""
        assert policy.is_branch_protected("release/*") is True

    def test_is_branch_protected_implicit_main(self, policy: Policy) -> None:
        """WHEN branch is 'main' THEN is_branch_protected returns True (implicit)."""
        assert policy.is_branch_protected("main") is True

    def test_is_branch_protected_implicit_master(self, policy: Policy) -> None:
        """WHEN branch is 'master' THEN is_branch_protected returns True (implicit)."""
        assert policy.is_branch_protected("master") is True

    def test_is_branch_protected_false(self, policy: Policy) -> None:
        """WHEN branch is not protected THEN is_branch_protected returns False."""
        assert policy.is_branch_protected("feature/my-feature") is False
        assert policy.is_branch_protected("bugfix/issue-123") is False

    def test_protected_branches_case_sensitive(self, policy: Policy) -> None:
        """WHEN branch has different case THEN it does not match protected branches."""
        assert policy.is_branch_protected("Main") is False
        assert policy.is_branch_protected("MASTER") is False

    def test_exact_match_only(self, policy: Policy) -> None:
        """WHEN protected branch uses exact match THEN partial matches are not protected."""
        # "release/*" is protected, but we use exact match per clarification #4
        assert policy.is_branch_protected("release/v1.0") is False
        assert policy.is_branch_protected("release/*") is True
