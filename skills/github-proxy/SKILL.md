---
name: github-proxy
description: Create branches, commit files, and open pull requests via GitHub Agent Proxy
version: 1.0.0
author: Carlos Gomes
license: MIT
metadata:
  hermes:
    tags: [github, git, branch, commit, pull-request, code]
    related_skills: []
required_environment_variables:
  - name: GITHUB_PROXY_URL
    prompt: "GitHub Proxy URL (e.g., http://localhost:8000)"
    help: "The URL where the GitHub Agent Proxy is running"
    required_for: "All proxy operations"
  - name: GITHUB_PROXY_API_KEY
    prompt: "GitHub Proxy API Key"
    help: "The client-side API key value that must match the proxy service's PROXY_API_KEY environment variable"
    required_for: "Authentication with the proxy"
---

# GitHub Agent Proxy

Interact with GitHub repositories through a security proxy that enforces branch protection policies.

## When to Use

Use this skill when you need to:
- Create a new branch in a GitHub repository
- Commit files to a branch (NOT main/master/staging)
- Create a pull request for code review

**Do NOT use for:**
- Direct commits to `main`, `master`, or other protected branches
- Bypassing code review processes
- Reading repository contents (use GitHub API directly)

## Security Rules

⚠️ **CRITICAL: These rules are enforced by the proxy**

1. **Protected branches**: `main`, `master`, and any configured protected branches cannot receive direct commits
2. **Branch naming**: Use descriptive names like `feature/...`, `fix/...`, `hermes/...`
3. **PR workflow**: All changes to protected branches must go through pull requests

## Quick Reference

| Command | Description |
|---------|-------------|
| `create-branch` | Create a new branch from a base |
| `commit-files` | Commit files to a non-protected branch |
| `create-pr` | Create a pull request |

## Environment Setup

Client-side variables used by this skill:

```bash
export GITHUB_PROXY_URL="http://localhost:8000"
export GITHUB_PROXY_API_KEY="your-api-key-here"
```

Or copy the tracked client example file:

```bash
cp .env.client.example .env.client
source .env.client
```

If you also operate the proxy service, the proxy process itself must be configured separately with variables such as `PROXY_API_KEY`, `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`, and `GITHUB_INSTALLATION_ID`. The proxy policy is configured separately in `config/policy.yaml` (starter example: `config/policy.yaml.example`).

The proxy does **not** auto-load a `.env` file by itself. Load `.env` before startup or run Uvicorn with `--env-file .env`.

## CLI Usage

The skill provides a CLI tool at `scripts/github_proxy_cli.py`.

### Create Branch

```bash
python3 scripts/github_proxy_cli.py create-branch \
  --repo owner/repo \
  --branch feature/my-feature \
  --base main
```

### Commit Files

```bash
python3 scripts/github_proxy_cli.py commit-files \
  --repo owner/repo \
  --branch feature/my-feature \
  --message "Add new feature" \
  --file path/to/file.py:content_here
```

For multi-line content, use heredoc or write to a temp file first.

### Create Pull Request

```bash
python3 scripts/github_proxy_cli.py create-pr \
  --repo owner/repo \
  --title "Add new feature" \
  --head feature/my-feature \
  --base main \
  --body "Description of the feature"
```

## Standard Workflow

Follow this sequence for all code changes:

### Step 1: Create Feature Branch

```bash
python3 scripts/github_proxy_cli.py create-branch \
  --repo <owner>/<repo> \
  --branch <feature-branch> \
  --base main
```

**Verify:** Output should show `{"status": "success", "branch": "..."}`

### Step 2: Commit Files

```bash
python3 scripts/github_proxy_cli.py commit-files \
  --repo <owner>/<repo> \
  --branch <feature-branch> \
  --message "<descriptive message>" \
  --file <path>:<content>
```

**Multiple files:** Use `--file` multiple times or commit separately.

### Step 3: Create Pull Request

```bash
python3 scripts/github_proxy_cli.py create-pr \
  --repo <owner>/<repo> \
  --title "<PR title>" \
  --head <feature-branch> \
  --base main \
  --body "<PR description>"
```

**Verify:** Output should include `number` and `url` fields.

## Error Handling

### 403 Forbidden - Protected Branch

```json
{"error": "forbidden", "message": "Branch 'main' is protected"}
```

**Solution:** Create a feature branch first, then commit to it.

### 403 Forbidden - Unauthorized Repo

```json
{"error": "forbidden", "message": "Repository 'owner/repo' is not allowed"}
```

**Solution:** The repository is not in the proxy's `allowed_repos`. Ask the user to update the policy.

### 401 Unauthorized

```json
{"error": "unauthorized", "message": "Invalid or missing API key"}
```

**Solution:** Check `GITHUB_PROXY_API_KEY` environment variable.

### 422 Validation Error

```json
{"error": "validation_error", "message": "..."}
```

**Solution:** Check required fields in the request.

## Branch Naming Conventions

Use descriptive prefixes:

| Prefix | Purpose |
|--------|---------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `hermes/` | Changes made by Hermes agent |
| `refactor/` | Code refactoring |
| `docs/` | Documentation updates |

Example: `hermes/add-user-authentication`

## Examples

### Example 1: Add a New File

```bash
# 1. Create branch
python3 scripts/github_proxy_cli.py create-branch \
  --repo myorg/myproject \
  --branch hermes/add-config \
  --base main

# 2. Commit the file
python3 scripts/github_proxy_cli.py commit-files \
  --repo myorg/myproject \
  --branch hermes/add-config \
  --message "Add configuration file" \
  --file config/settings.json:'{"debug": false}'

# 3. Create PR
python3 scripts/github_proxy_cli.py create-pr \
  --repo myorg/myproject \
  --title "Add configuration file" \
  --head hermes/add-config \
  --base main \
  --body "Adds initial configuration file with debug setting."
```

### Example 2: Fix a Bug

```bash
# 1. Create branch
python3 scripts/github_proxy_cli.py create-branch \
  --repo myorg/myproject \
  --branch fix/null-pointer-exception \
  --base main

# 2. Read the file to fix (use terminal tool)
# ... read src/main.py ...

# 3. Commit the fix
python3 scripts/github_proxy_cli.py commit-files \
  --repo myorg/myproject \
  --branch fix/null-pointer-exception \
  --message "Fix null pointer exception in main" \
  --file src/main.py:"<fixed content>"

# 4. Create PR
python3 scripts/github_proxy_cli.py create-pr \
  --repo myorg/myproject \
  --title "Fix null pointer exception" \
  --head fix/null-pointer-exception \
  --base main \
  --body "Fixes NPE when user is not logged in."
```

## Verification Checklist

After completing a workflow, verify:

- [ ] Branch was created successfully (`status: success`)
- [ ] Files were committed (`sha` in response)
- [ ] PR was created (`number` and `url` in response)
- [ ] PR targets the correct base branch
- [ ] PR title and body are descriptive

## Pitfalls

1. **Committing to main**: Will fail with 403. Always create a feature branch first.
2. **Head == Base in PR**: Will fail with 422. Use different branches.
3. **Empty files array**: Will fail with 422. Include at least one file.
4. **Missing auth**: Will fail with 401. Ensure `GITHUB_PROXY_API_KEY` is set.
5. **Repo not in policy**: Will fail with 403. Ask user to update `config/policy.yaml`.
