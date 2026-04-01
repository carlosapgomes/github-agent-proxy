# GitHub Agent Proxy - API Reference

Security middleware between Hermes agent and GitHub API.

## Overview

The GitHub Agent Proxy exposes three write endpoints for agent operations:

| Endpoint | Purpose |
|----------|---------|
| `POST /create-branch` | Create a new branch in a repository |
| `POST /commit-files` | Commit files to a branch |
| `POST /create-pr` | Create a pull request |

All endpoints require authentication and are subject to policy-based authorization.

## Optional Commit Author Attribution

`POST /commit-files` can attach a fixed Git `author` identity when the proxy is started with both of these environment variables:

```bash
export GITHUB_COMMIT_AUTHOR_NAME="Your Name"
export GITHUB_COMMIT_AUTHOR_EMAIL="123456+your-login@users.noreply.github.com"
```

Notes:
- Both variables must be set together or the proxy fails fast at startup.
- The configured email must already be associated with your GitHub account for commits to count toward your profile.
- This changes the Git `author` metadata only; GitHub App authentication and protected-branch enforcement stay the same.

## Authentication

All endpoints require a Bearer token in the `Authorization` header:

```http
Authorization: Bearer <API_KEY>
```

`<API_KEY>` is the client-side Bearer token value. On the proxy service, this must match the `PROXY_API_KEY` environment variable.

### Proxy Runtime Configuration

The proxy service reads configuration from process environment variables:

```bash
export PROXY_API_KEY="your-api-key"
export GITHUB_APP_ID="your-github-app-id"
export GITHUB_PRIVATE_KEY="$(cat path/to/private-key.pem)"
export GITHUB_INSTALLATION_ID="your-installation-id"
```

Or copy the tracked proxy example file and edit it:

```bash
cp .env.example .env
```

The authorization policy is read from `config/policy.yaml`. A starter example is available at `config/policy.yaml.example`.

Notes:
- The proxy does **not** auto-load a `.env` file from the current directory.
- If you use a `.env` file, load it before startup or start Uvicorn with `--env-file .env`.
- `GITHUB_PRIVATE_KEY` must contain the PEM private key content, not a file path.
- In `.env.example`, `GITHUB_PRIVATE_KEY` is represented as a single quoted value with `\n` escapes.

### Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| 401 | `unauthorized` | Missing or invalid authentication |

```json
{
  "error": "unauthorized",
  "message": "Invalid or missing API key"
}
```

---

## POST /create-branch

Create a new branch in a repository.

### Request

```http
POST /create-branch
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

```json
{
  "repo": "owner/repo",
  "branch": "feature/new-feature",
  "base": "main"
}
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo` | string | Yes | Repository in format `owner/repo` |
| `branch` | string | Yes | New branch name |
| `base` | string | Yes | Base branch to create from |

### Success Response (200)

```json
{
  "status": "success",
  "branch": "feature/new-feature",
  "ref": "refs/heads/feature/new-feature"
}
```

### Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| 403 | `forbidden` | Repository not allowed, action not allowed, or branch is protected |
| 422 | `validation_error` | Missing required fields |
| 500 | `server_error` | GitHub API error |

### Policy Constraints

- `repo` must be in `allowed_repos`
- `create_branch` must be in `allowed_actions`
- `branch` must NOT be protected (main, master, or configured protected branches)

---

## POST /commit-files

Commit files to a branch.

### Request

```http
POST /commit-files
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

```json
{
  "repo": "owner/repo",
  "branch": "feature/new-feature",
  "message": "Add new feature files",
  "files": [
    {
      "path": "src/main.py",
      "content": "print('hello world')"
    },
    {
      "path": "README.md",
      "content": "# My Project"
    }
  ]
}
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo` | string | Yes | Repository in format `owner/repo` |
| `branch` | string | Yes | Target branch name |
| `message` | string | Yes | Commit message |
| `files` | array | Yes | List of files to commit |
| `files[].path` | string | Yes | File path in repository |
| `files[].content` | string | Yes | File content |

### Success Response (200)

```json
{
  "status": "success",
  "sha": "abc123def456...",
  "message": "Add new feature files"
}
```

### Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| 403 | `forbidden` | Repository not allowed, action not allowed, or branch is protected |
| 422 | `validation_error` | Missing required fields or empty files array |
| 500 | `server_error` | GitHub API error |

### Policy Constraints

- `repo` must be in `allowed_repos`
- `commit_files` must be in `allowed_actions`
- `branch` must NOT be protected (main, master, or configured protected branches)

---

## POST /create-pr

Create a pull request.

### Request

```http
POST /create-pr
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

```json
{
  "repo": "owner/repo",
  "title": "Add new feature",
  "body": "This PR adds a new feature",
  "head": "feature/new-feature",
  "base": "main"
}
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo` | string | Yes | Repository in format `owner/repo` |
| `title` | string | Yes | Pull request title |
| `body` | string | No | Pull request description |
| `head` | string | Yes | Head branch (source) |
| `base` | string | Yes | Base branch (target) |

### Success Response (200)

```json
{
  "status": "success",
  "number": 42,
  "url": "https://github.com/owner/repo/pull/42"
}
```

### Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| 403 | `forbidden` | Repository not allowed, action not allowed, or head branch is protected |
| 422 | `validation_error` | Missing required fields or head == base |
| 500 | `server_error` | GitHub API error |

### Policy Constraints

- `repo` must be in `allowed_repos`
- `create_pr` must be in `allowed_actions`
- `head` must NOT be protected (main, master, or configured protected branches)
- `base` CAN be protected (normal PR workflow to main is allowed)

---

## Error Format

All errors follow a consistent JSON format:

```json
{
  "error": "error_code",
  "message": "Human-readable error description"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `unauthorized` | 401 | Authentication required or invalid |
| `forbidden` | 403 | Policy violation |
| `validation_error` | 422 | Request validation failed |
| `server_error` | 500 | Internal server or GitHub API error |

---

## Audit Logging

All operations are logged with structured JSON including:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "agent": "hermes",
  "repo": "owner/repo",
  "action": "create_branch",
  "status": "success"
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `success` | Operation completed successfully |
| `denied` | Operation denied by policy or GitHub API error |

---

## Typical Workflow

1. **Create a feature branch** from main
2. **Commit files** to the feature branch
3. **Create a pull request** targeting main

```
POST /create-branch   → branch: feature/my-feature, base: main
POST /commit-files    → branch: feature/my-feature, files: [...]
POST /create-pr       → head: feature/my-feature, base: main
```

This workflow ensures no direct writes to protected branches (main, master).
