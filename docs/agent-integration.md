# Agent Integration Guide

This guide explains how to configure agents to connect to and use the GitHub Agent Proxy.

## Overview

The GitHub Agent Proxy sits between your AI agent and GitHub, enforcing security policies on all operations.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Agent     │────▶│  GitHub Agent    │────▶│   GitHub    │
│             │     │     Proxy        │     │    API      │
└─────────────┘     └──────────────────┘     └─────────────┘
```

## Integration Methods

| Method | Recommended For | Description |
|--------|-----------------|-------------|
| **Hermes Skill + CLI** | Hermes agent users | Built-in skill with deterministic CLI |
| **Python Client** | Other agents, CI/CD, scripts | Direct HTTP client integration |

---

## Method 1: Hermes Skill + CLI (Recommended)

If you're using Hermes agent, use the built-in skill located at `skills/github-proxy/`.

### Why Use the Skill?

| Benefit | Description |
|---------|-------------|
| **Zero configuration** | Skill auto-loads when needed |
| **Deterministic output** | JSON responses, explicit exit codes |
| **Secure by default** | Protected branch rules enforced |
| **No dependencies** | CLI uses Python stdlib only |
| **Progressive disclosure** | Common workflow first, edge cases later |

### Prerequisites

1. ✅ GitHub Agent Proxy is deployed and running
2. ✅ You have the proxy URL (e.g., `http://localhost:8000`)
3. ✅ You have a Bearer token configured for the proxy
4. ✅ Policy is configured for your repositories (`config/policy.yaml`)

### Environment Variables

There are two separate environments involved:

#### 1. Agent/Hermes environment

Set these in your Hermes environment (Hermes will prompt securely if missing):

```bash
# Required on the client/agent side
export GITHUB_PROXY_URL="http://localhost:8000"
export GITHUB_PROXY_API_KEY="your-api-key-here"
```

Or copy the tracked client example file:

```bash
cp .env.client.example .env.client
source .env.client
```

`GITHUB_PROXY_API_KEY` is the client-side Bearer token value sent in `Authorization: Bearer ...`.

#### 2. Proxy service environment

If you operate the proxy yourself, configure these on the **proxy service** process:

```bash
export PROXY_API_KEY="your-api-key-here"
export GITHUB_APP_ID="your-github-app-id"
export GITHUB_PRIVATE_KEY="$(cat path/to/private-key.pem)"
export GITHUB_INSTALLATION_ID="your-installation-id"
```

Or copy the tracked proxy example file and edit it:

```bash
cp .env.example .env
```

For policy setup, you can also start from the tracked example:

```bash
cp config/policy.yaml.example config/policy.yaml
```

Optional commit author attribution on the proxy service:

```bash
export GITHUB_COMMIT_AUTHOR_NAME="Your Name"
export GITHUB_COMMIT_AUTHOR_EMAIL="123456+your-login@users.noreply.github.com"
```

Notes:
- The proxy reads these values from process environment variables via `os.environ`.
- The proxy does **not** auto-load a `.env` file from the current directory.
- If you use a `.env` file for the proxy, load it before startup or start Uvicorn with `--env-file .env`.
- `GITHUB_PRIVATE_KEY` must contain the PEM private key content, not a file path.
- In `.env.example`, `GITHUB_PRIVATE_KEY` is represented as a single quoted value with `\n` escapes.
- Both author variables must be configured together.
- Use an email already associated with your GitHub account (your verified address or GitHub `noreply` address).
- See [GitHub App Setup](github-app-setup.md) for app creation, permissions, installation, and installation ID guidance.

### CLI Reference

The skill provides a CLI at `skills/github-proxy/scripts/github_proxy_cli.py`.

#### Create Branch

```bash
python3 skills/github-proxy/scripts/github_proxy_cli.py create-branch \
  --repo owner/repo \
  --branch feature/my-feature \
  --base main
```

**Output:**
```json
{"status": "success", "branch": "feature/my-feature", "ref": "refs/heads/feature/my-feature"}
```

#### Commit Files

```bash
python3 skills/github-proxy/scripts/github_proxy_cli.py commit-files \
  --repo owner/repo \
  --branch feature/my-feature \
  --message "Add new feature" \
  --file src/main.py:"print('hello')"
```

**Multiple files:**
```bash
python3 skills/github-proxy/scripts/github_proxy_cli.py commit-files \
  --repo owner/repo \
  --branch feature/my-feature \
  --message "Add multiple files" \
  --file src/main.py:"content1" \
  --file src/utils.py:"content2"
```

**Output:**
```json
{"status": "success", "sha": "abc123...", "message": "Add new feature"}
```

#### Create Pull Request

```bash
python3 skills/github-proxy/scripts/github_proxy_cli.py create-pr \
  --repo owner/repo \
  --title "Add new feature" \
  --head feature/my-feature \
  --base main \
  --body "Description of the feature"
```

**Output:**
```json
{"status": "success", "number": 42, "url": "https://github.com/owner/repo/pull/42"}
```

### Standard Workflow

Follow this sequence for all code changes:

**Step 1: Create Feature Branch**
```bash
python3 skills/github-proxy/scripts/github_proxy_cli.py create-branch \
  --repo myorg/myproject \
  --branch hermes/add-feature \
  --base main
```

**Step 2: Commit Files**
```bash
python3 skills/github-proxy/scripts/github_proxy_cli.py commit-files \
  --repo myorg/myproject \
  --branch hermes/add-feature \
  --message "Add new feature" \
  --file src/feature.py:"# New feature\npass"
```

**Step 3: Create Pull Request**
```bash
python3 skills/github-proxy/scripts/github_proxy_cli.py create-pr \
  --repo myorg/myproject \
  --title "Add new feature" \
  --head hermes/add-feature \
  --base main \
  --body "This PR adds a new feature."
```

### Error Handling

All errors are returned as JSON with exit code 1:

```json
{"error": "forbidden", "message": "Branch 'main' is protected"}
```

| Error Code | Meaning | Solution |
|------------|---------|----------|
| `unauthorized` | Missing/invalid API key | Check `GITHUB_PROXY_API_KEY` |
| `forbidden` | Policy violation | Use feature branch, check policy |
| `validation_error` | Invalid request | Check required fields |
| `http_error` | Proxy/GitHub error | Check logs, retry |
| `connection_error` | Cannot reach proxy | Check `GITHUB_PROXY_URL` |

### Branch Naming Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New features | `feature/user-auth` |
| `fix/` | Bug fixes | `fix/null-pointer` |
| `hermes/` | Hermes changes | `hermes/add-config` |
| `refactor/` | Code refactoring | `refactor/auth-module` |
| `docs/` | Documentation | `docs/api-reference` |

---

## Method 2: Python Client (Code Integration)

For other agents, CI/CD pipelines, or custom scripts, use direct HTTP integration.

### When to Use

- Non-Hermes agents (Claude, GPT, etc.)
- CI/CD pipelines (GitHub Actions, GitLab CI)
- Custom automation scripts
- Integration into existing Python codebases

### Prerequisites

1. ✅ Python 3.12+
2. ✅ `httpx` installed (`pip install httpx`)
3. ✅ Proxy URL and API key

### Environment Variables

```bash
export GITHUB_PROXY_URL="http://localhost:8000"
export GITHUB_PROXY_API_KEY="your-api-key-here"
```

### Client Implementation

```python
import os
import httpx


class GitHubProxyClient:
    """Client for interacting with GitHub Agent Proxy."""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.environ.get("GITHUB_PROXY_URL", "http://localhost:8000")
        self.api_key = api_key or os.environ.get("GITHUB_PROXY_API_KEY")
        
        if not self.api_key:
            raise ValueError("GITHUB_PROXY_API_KEY is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def create_branch(self, repo: str, branch: str, base: str) -> dict:
        """Create a new branch."""
        response = httpx.post(
            f"{self.base_url}/create-branch",
            headers=self.headers,
            json={"repo": repo, "branch": branch, "base": base},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    
    def commit_files(self, repo: str, branch: str, message: str, files: list) -> dict:
        """Commit files to a branch.
        
        Args:
            repo: Repository (owner/repo)
            branch: Target branch
            message: Commit message
            files: List of {"path": "...", "content": "..."}
        """
        response = httpx.post(
            f"{self.base_url}/commit-files",
            headers=self.headers,
            json={"repo": repo, "branch": branch, "message": message, "files": files},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    
    def create_pr(
        self,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = None
    ) -> dict:
        """Create a pull request."""
        payload = {"repo": repo, "title": title, "head": head, "base": base}
        if body:
            payload["body"] = body
        
        response = httpx.post(
            f"{self.base_url}/create-pr",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
```

### Usage Example

```python
from github_proxy_client import GitHubProxyClient

# Initialize client
client = GitHubProxyClient()

# Create a feature branch
result = client.create_branch(
    repo="myorg/myrepo",
    branch="feature/awesome-feature",
    base="main"
)
print(f"Created branch: {result['branch']}")

# Commit files
result = client.commit_files(
    repo="myorg/myrepo",
    branch="feature/awesome-feature",
    message="Add awesome feature",
    files=[
        {"path": "src/feature.py", "content": "# Awesome feature\npass"},
        {"path": "tests/test_feature.py", "content": "# Test feature\npass"},
    ]
)
print(f"Committed: {result['sha']}")

# Create PR
result = client.create_pr(
    repo="myorg/myrepo",
    title="Add awesome feature",
    head="feature/awesome-feature",
    base="main",
    body="This PR adds an awesome feature."
)
print(f"Created PR: {result['url']}")
```

### Error Handling

```python
import httpx

try:
    result = client.commit_files(...)
except httpx.HTTPStatusError as e:
    error = e.response.json()
    print(f"Error: {error['error']} - {error['message']}")
    
    if error['error'] == 'forbidden':
        # Handle policy violation
        if 'protected' in error['message']:
            print("Cannot commit to protected branch")
        elif 'not allowed' in error['message']:
            print("Repository or action not in policy")
    elif error['error'] == 'unauthorized':
        print("Check API key")
```

---

## API Endpoints Reference

For direct HTTP integration, use these endpoints:

### Create Branch

```http
POST ${GITHUB_PROXY_URL}/create-branch
Authorization: Bearer ${GITHUB_PROXY_API_KEY}
Content-Type: application/json

{
  "repo": "owner/repo",
  "branch": "feature/new-feature",
  "base": "main"
}
```

### Commit Files

```http
POST ${GITHUB_PROXY_URL}/commit-files
Authorization: Bearer ${GITHUB_PROXY_API_KEY}
Content-Type: application/json

{
  "repo": "owner/repo",
  "branch": "feature/new-feature",
  "message": "Add new feature",
  "files": [
    {"path": "src/main.py", "content": "print('hello')"}
  ]
}
```

### Create Pull Request

```http
POST ${GITHUB_PROXY_URL}/create-pr
Authorization: Bearer ${GITHUB_PROXY_API_KEY}
Content-Type: application/json

{
  "repo": "owner/repo",
  "title": "Add new feature",
  "body": "Description of the feature",
  "head": "feature/new-feature",
  "base": "main"
}
```

---

## Testing the Connection

### 1. Health Check

```bash
# Check if proxy is running
curl ${GITHUB_PROXY_URL}/docs

# Should return the OpenAPI documentation page
```

### 2. Authentication Test

```bash
# Test authentication with a simple request
curl -X POST ${GITHUB_PROXY_URL}/create-branch \
  -H "Authorization: Bearer ${GITHUB_PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"repo": "owner/repo", "branch": "test-connection", "base": "main"}'

# Expected success:
# {"status": "success", "branch": "test-connection", "ref": "refs/heads/test-connection"}

# Expected auth failure:
# {"error": "unauthorized", "message": "Invalid or missing API key"}
```

### 3. Policy Test

```bash
# Test policy enforcement (should fail if repo not allowed)
curl -X POST ${GITHUB_PROXY_URL}/create-branch \
  -H "Authorization: Bearer ${GITHUB_PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"repo": "unauthorized/repo", "branch": "test", "base": "main"}'

# Expected response:
# {"error": "forbidden", "message": "Repository 'unauthorized/repo' is not allowed"}
```

### 4. Protected Branch Test

```bash
# Test protected branch enforcement (should always fail)
curl -X POST ${GITHUB_PROXY_URL}/commit-files \
  -H "Authorization: Bearer ${GITHUB_PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/allowed-repo",
    "branch": "main",
    "message": "Direct commit to main",
    "files": [{"path": "test.txt", "content": "test"}]
  }'

# Expected response:
# {"error": "forbidden", "message": "Branch 'main' is protected"}
```

---

## Troubleshooting

### Connection Refused

```
Error: Connection refused to http://localhost:8000
```

**Solution:** Ensure the proxy is running:
```bash
uv run uvicorn app.main:app --reload
```

### Unauthorized (401)

```
{"error": "unauthorized", "message": "Invalid or missing API key"}
```

**Solutions:**
1. Verify `GITHUB_PROXY_API_KEY` is set on the client/agent side
2. Check the API key matches the proxy's `PROXY_API_KEY` environment variable
3. Ensure the header format is `Authorization: Bearer <key>`

### Forbidden (403)

```
{"error": "forbidden", "message": "Repository 'owner/repo' is not allowed"}
```

**Solutions:**
1. Add the repository to `allowed_repos` in `config/policy.yaml`
2. Ensure the action is in `allowed_actions`
3. If branch-related, ensure the branch is not protected

### Timeout

```
Error: Request timed out after 30 seconds
```

**Solutions:**
1. Increase timeout in client
2. Check GitHub API status
3. Check proxy logs for errors

---

## Security Best Practices

### API Key Management

1. **Never commit API keys** to version control
2. **Use environment variables** or a secrets manager
3. **Rotate keys periodically**
4. **Use different keys** for different environments (dev, staging, prod)

### Network Security

1. **Use HTTPS** in production
2. **Restrict access** via firewall rules or VPN
3. **Consider mTLS** for additional security in production

### Policy Configuration

1. **Principle of least privilege** - only allow necessary repos and actions
2. **Review policy regularly** - remove unused permissions
3. **Audit logs** - monitor for suspicious activity

---

## Production Checklist

Before deploying to production:

- [ ] API key is securely stored (not in code)
- [ ] Proxy URL uses HTTPS
- [ ] Policy is configured for production repositories
- [ ] GitHub App has correct permissions
- [ ] Audit logging is enabled
- [ ] Network access is restricted appropriately
- [ ] Timeout is configured appropriately
- [ ] Error handling is tested

---

## Related Documentation

- [API Reference](api.md) - Complete endpoint documentation
- [Policy Configuration](policy.md) - Policy file configuration
- [GitHub App Setup](github-app-setup.md) - GitHub App creation, installation, and permissions
- [Hermes Skill](../skills/github-proxy/SKILL.md) - Built-in skill documentation
- [README](../README.md) - Project overview and setup
