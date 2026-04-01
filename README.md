# GitHub Agent Proxy

Security middleware between Hermes agent and GitHub API.

## Overview

The GitHub Agent Proxy provides a controlled interface for AI agents to interact with GitHub repositories. It enforces security policies and prevents direct writes to protected branches.

### Key Features

- **Policy-based Authorization**: Control which repositories and actions are allowed
- **Protected Branch Enforcement**: No direct writes to main, master, or configured protected branches
- **Audit Logging**: All operations are logged for security review
- **GitHub App Authentication**: Per-request installation tokens for GitHub API access

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /create-branch` | Create a new branch |
| `POST /commit-files` | Commit files to a branch |
| `POST /create-pr` | Create a pull request |

## Quick Start

### Prerequisites

- Python 3.12+
- uv package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/carlosapgomes/github-agent-proxy.git
cd github-agent-proxy

# Install dependencies
uv sync
```

### Configuration

1. Review `config/policy.yaml` and adjust allowed repositories, actions, and protected branches for your environment.

   A tracked starter example is also available at `config/policy.yaml.example`.

2. Set proxy service environment variables:
```bash
export PROXY_API_KEY="your-api-key"
export GITHUB_APP_ID="your-github-app-id"
export GITHUB_PRIVATE_KEY="$(cat path/to/private-key.pem)"
export GITHUB_INSTALLATION_ID="your-installation-id"

# Optional: fixed Git author metadata for proxy-created commits
export GITHUB_COMMIT_AUTHOR_NAME="Your Name"
export GITHUB_COMMIT_AUTHOR_EMAIL="123456+your-login@users.noreply.github.com"
```

Or copy the tracked example file and edit it:
```bash
cp .env.example .env
```

Notes:
- The proxy reads configuration from process environment variables via `os.environ`.
- The proxy does **not** auto-load a `.env` file from the current directory.
- If you want to use a `.env` file, load it before startup (for example, `source .env`) or let Uvicorn load it with `--env-file .env`.
- `GITHUB_PRIVATE_KEY` must contain the PEM key content, not a file path.
- In `.env.example`, `GITHUB_PRIVATE_KEY` is represented as a single quoted value with `\n` escapes.
- See [GitHub App Setup](docs/github-app-setup.md) for how to create the app, install it, and obtain `GITHUB_APP_ID` / `GITHUB_INSTALLATION_ID`.

### Running

```bash
uv run uvicorn app.main:app --reload
```

With `.env` loaded by Uvicorn:

```bash
uv run uvicorn app.main:app --reload --env-file .env
```

### Quick Start Local

Use this sequence for a first local run:

```bash
# 1. Create local config files from the tracked examples
cp config/policy.yaml.example config/policy.yaml
cp .env.example .env

# 2. Edit both files for your environment
# - config/policy.yaml: allowed_repos, allowed_actions, protected_branches
# - .env: PROXY_API_KEY, GITHUB_APP_ID, GITHUB_PRIVATE_KEY, GITHUB_INSTALLATION_ID

# 3. Start the proxy
uv run uvicorn app.main:app --reload --env-file .env
```

In another terminal, verify the server is up:

```bash
curl http://localhost:8000/docs
```

Then test an authenticated request with a repository that exists in `config/policy.yaml`:

```bash
export GITHUB_PROXY_URL="http://localhost:8000"
export GITHUB_PROXY_API_KEY="replace-with-the-same-value-as-PROXY_API_KEY"

curl -X POST "${GITHUB_PROXY_URL}/create-branch" \
  -H "Authorization: Bearer ${GITHUB_PROXY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/allowed-repo",
    "branch": "test/local-quickstart",
    "base": "main"
  }'
```

Expected outcomes:
- `200` with a JSON success response if your GitHub App credentials are valid and the repo is allowed.
- `401` if the Bearer token does not match `PROXY_API_KEY`.
- `403` if the repository or action is blocked by `config/policy.yaml`.
- `500` if GitHub App credentials are missing/invalid or the upstream GitHub request fails.

## Documentation

- [API Reference](docs/api.md) - Complete API documentation
- [Policy Configuration](docs/policy.md) - Policy file configuration guide
- [GitHub App Setup](docs/github-app-setup.md) - How to create/install the GitHub App and obtain runtime credentials
- [Agent Integration](docs/agent-integration.md) - How to configure Hermes and other agents
- [Hermes Skill](skills/github-proxy/SKILL.md) - Built-in skill for Hermes agent
- [AGENTS.md](AGENTS.md) - Development guidelines
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) - Project context and architecture

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Hermes    │────▶│  GitHub Agent    │────▶│   GitHub    │
│   Agent     │     │     Proxy        │     │    API      │
└─────────────┘     └──────────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Policy     │
                    │  Enforcement │
                    └──────────────┘
```

### Request Flow

1. Agent sends request with a Bearer token (API key)
2. Proxy validates authentication
3. Proxy checks policy (repo, action, branch)
4. Proxy obtains GitHub App installation token
5. Proxy calls GitHub API
6. Proxy logs operation and returns result

## Security

### Protected Branches

The following branches are ALWAYS protected:
- `main`
- `master`

Additional protected branches can be configured in `policy.yaml`.

### No Passthrough

The proxy does NOT provide generic GitHub API passthrough. Only the three defined endpoints are available.

### Audit Trail

All operations are logged with:
- Timestamp
- Agent identity
- Repository
- Action
- Status (success/denied)

## Development

### Running Tests

```bash
# All tests
uv run pytest -q

# Unit tests only
uv run pytest tests/unit -q

# Integration tests
uv run pytest tests/integration -q

# Security tests
uv run pytest tests/security -q
```

### Quality Gates

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .
```

## Project Structure

```
github-agent-proxy/
├── app/
│   ├── main.py           # FastAPI application
│   ├── auth.py           # Authentication guard
│   ├── policy.py         # Policy loader and validation
│   ├── github_client.py  # GitHub API client
│   ├── audit.py          # Audit logging
│   └── services.py       # Business logic services
├── config/
│   ├── policy.yaml         # Active policy configuration
│   └── policy.yaml.example # Starter policy example
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── security/         # Security tests
└── docs/
    ├── api.md            # API reference
    └── policy.md         # Policy configuration
```

## License

MIT
