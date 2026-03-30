# Agent Integration Guide

This guide explains how to configure Hermes (or any AI coding agent) to connect to and use the GitHub Agent Proxy.

## Overview

The GitHub Agent Proxy sits between your AI agent and GitHub, enforcing security policies on all operations.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Hermes    │────▶│  GitHub Agent    │────▶│   GitHub    │
│   Agent     │     │     Proxy        │     │    API      │
└─────────────┘     └──────────────────┘     └─────────────┘
```

## Prerequisites

Before configuring the agent, ensure:

1. ✅ GitHub Agent Proxy is deployed and running
2. ✅ You have the proxy URL (e.g., `http://localhost:8000` or `https://proxy.yourdomain.com`)
3. ✅ You have an API key configured in the proxy
4. ✅ Policy is configured for your repositories (`config/policy.yaml`)

## Environment Variables

### Required for the Agent

Set these environment variables in your agent's configuration:

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_PROXY_URL` | Base URL of the GitHub Agent Proxy | `http://localhost:8000` |
| `GITHUB_PROXY_API_KEY` | API key for authentication | `sk-proxy-abc123...` |

### Optional for the Agent

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_PROXY_TIMEOUT` | Request timeout in seconds | `30` |

## Configuration

### Hermes Configuration

Add the following to your Hermes configuration (typically in `.hermes/config.yaml` or environment):

```yaml
# .hermes/config.yaml

github:
  # Point Hermes to the proxy instead of GitHub directly
  proxy_url: ${GITHUB_PROXY_URL}
  proxy_api_key: ${GITHUB_PROXY_API_KEY}
  
  # Disable direct GitHub access
  direct_access: false
```

### Environment Setup

```bash
# In your agent's environment or .env file

# Proxy connection
GITHUB_PROXY_URL=http://localhost:8000
GITHUB_PROXY_API_KEY=your-api-key-here

# Optional: Request timeout
GITHUB_PROXY_TIMEOUT=30
```

### Shell Profile (bash/zsh)

```bash
# Add to ~/.bashrc or ~/.zshrc

export GITHUB_PROXY_URL="http://localhost:8000"
export GITHUB_PROXY_API_KEY="your-api-key-here"
```

## API Endpoints

The agent should use these endpoints instead of GitHub's API:

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

## Example: Python Client

```python
import os
import httpx

class GitHubProxyClient:
    """Client for interacting with GitHub Agent Proxy."""
    
    def __init__(self):
        self.base_url = os.environ.get("GITHUB_PROXY_URL", "http://localhost:8000")
        self.api_key = os.environ.get("GITHUB_PROXY_API_KEY")
        
        if not self.api_key:
            raise ValueError("GITHUB_PROXY_API_KEY environment variable is required")
        
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
        )
        response.raise_for_status()
        return response.json()
    
    def commit_files(self, repo: str, branch: str, message: str, files: list) -> dict:
        """Commit files to a branch."""
        response = httpx.post(
            f"{self.base_url}/commit-files",
            headers=self.headers,
            json={"repo": repo, "branch": branch, "message": message, "files": files},
        )
        response.raise_for_status()
        return response.json()
    
    def create_pr(self, repo: str, title: str, head: str, base: str, body: str = None) -> dict:
        """Create a pull request."""
        payload = {"repo": repo, "title": title, "head": head, "base": base}
        if body:
            payload["body"] = body
        
        response = httpx.post(
            f"{self.base_url}/create-pr",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


# Usage example
if __name__ == "__main__":
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
            {"path": "tests/test_feature.py", "content": "# Test awesome feature\npass"},
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

# Expected success response:
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
1. Verify `GITHUB_PROXY_API_KEY` is set
2. Check the API key matches the one in the proxy's `API_KEY` environment variable
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
1. Increase `GITHUB_PROXY_TIMEOUT`
2. Check GitHub API status
3. Check proxy logs for errors

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

## Production Checklist

Before deploying to production:

- [ ] API key is securely stored (not in code)
- [ ] Proxy URL uses HTTPS
- [ ] Policy is configured for production repositories
- [ ] GitHub App has correct permissions
- [ ] Audit logging is enabled
- [ ] Network access is restricted appropriately
- [ ] Agent timeout is configured appropriately
- [ ] Error handling is tested

## Related Documentation

- [API Reference](api.md) - Complete endpoint documentation
- [Policy Configuration](policy.md) - Policy file configuration
- [README](../README.md) - Project overview and setup
