# Policy Configuration Guide

The GitHub Agent Proxy uses a YAML policy file to control authorization.

## Policy File Location

Active policy file: `config/policy.yaml`

Starter example: `config/policy.yaml.example`

## Getting Started

If you want a clean starting point, copy the example file:

```bash
cp config/policy.yaml.example config/policy.yaml
```

Then edit `config/policy.yaml` for your environment.

## Policy Structure

```yaml
# Repositories that the agent can interact with
allowed_repos:
  - owner/repo1
  - owner/repo2

# Actions that the agent can perform
allowed_actions:
  - create_branch
  - commit_files
  - create_pr

# Branches that cannot receive direct writes
protected_branches:
  - staging
  - release/*
```

## Fields

### `allowed_repos`

List of repositories the agent can access.

**Format:** `owner/repo` (GitHub repository path)

**Examples:**
```yaml
allowed_repos:
  - myorg/frontend-app
  - myorg/backend-api
  - myorg/shared-libraries
```

### `allowed_actions`

List of actions the agent can perform.

**Available Actions:**
| Action | Endpoint | Description |
|--------|----------|-------------|
| `create_branch` | POST /create-branch | Create new branches |
| `commit_files` | POST /commit-files | Commit files to branches |
| `create_pr` | POST /create-pr | Create pull requests |

**Examples:**
```yaml
# Full access
allowed_actions:
  - create_branch
  - commit_files
  - create_pr

# Limited access (branch creation only)
allowed_actions:
  - create_branch
```

### `protected_branches`

Branches that cannot receive direct writes.

**Implicit Protection:** `main` and `master` are ALWAYS protected, even if not listed.

**Examples:**
```yaml
protected_branches:
  - staging          # Exact match
  - release/*        # Stored literally; matching is exact only
  - production
```

## Protected Branch Rules

### What is Blocked on Protected Branches?

| Operation | Protected as Target | Protected as Source |
|-----------|---------------------|---------------------|
| create-branch | ❌ BLOCKED | N/A |
| commit-files | ❌ BLOCKED | N/A |
| create-pr | ✅ ALLOWED (base) | ❌ BLOCKED (head) |

### Examples

**❌ Blocked: Creating main branch**
```json
{ "repo": "owner/repo", "branch": "main", "base": "develop" }
// → 403 Forbidden: Branch 'main' is protected
```

**❌ Blocked: Committing to main**
```json
{ "repo": "owner/repo", "branch": "main", "files": [...] }
// → 403 Forbidden: Branch 'main' is protected
```

**❌ Blocked: Creating PR from main**
```json
{ "repo": "owner/repo", "head": "main", "base": "develop" }
// → 403 Forbidden: Branch 'main' is protected
```

**✅ Allowed: Creating PR to main**
```json
{ "repo": "owner/repo", "head": "feature/test", "base": "main" }
// → 200 OK: PR created
```

## Sample Configurations

### Minimal Configuration

```yaml
allowed_repos:
  - myorg/my-project

allowed_actions:
  - create_branch
  - commit_files
  - create_pr

protected_branches: []
# main and master are still protected implicitly
```

### Production Configuration

```yaml
allowed_repos:
  - myorg/frontend
  - myorg/backend
  - myorg/infrastructure

allowed_actions:
  - create_branch
  - commit_files
  - create_pr

protected_branches:
  - staging
  - production
```

### Restricted Configuration (Branch Creation Only)

```yaml
allowed_repos:
  - myorg/exploration-repo

allowed_actions:
  - create_branch

protected_branches:
  - main
  - develop
```

## Policy Validation

The policy is validated at startup. Missing required fields will cause an error:

```
PolicyError: Missing required field: allowed_repos
```

### Required Fields

- `allowed_repos` (can be empty list)
- `allowed_actions` (can be empty list)
- `protected_branches` (optional, defaults to empty list)

## Security Considerations

1. **Principle of Least Privilege:** Only grant access to repositories the agent needs.

2. **Protected Branches:** Always ensure critical branches are protected. Remember that `main` and `master` are always protected.

3. **Action Restriction:** If the agent only needs to explore, restrict to `create_branch` only.

4. **Audit Logging:** All operations (success and denied) are logged for security review.

## Changing Policy

1. Edit `config/policy.yaml`
2. Restart the proxy server (the policy is loaded at startup)

```bash
# After editing policy
uv run uvicorn app.main:app --reload
```

## Troubleshooting

### "Repository not allowed"

The repository is not in `allowed_repos`. Add it to the list.

### "Action not allowed"

The action is not in `allowed_actions`. Add it to the list.

### "Branch is protected"

The target branch is protected (either explicitly in `protected_branches` or implicitly as `main`/`master`). Use a different branch or create a PR instead.

### Policy not updating

Restart the server after changing the policy file. The policy is loaded at startup, not dynamically.
