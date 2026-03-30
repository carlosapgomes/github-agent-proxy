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

1. Copy the example policy:
```bash
cp config/policy.yaml.example config/policy.yaml
```

2. Edit `config/policy.yaml` to configure allowed repositories and actions.

3. Set environment variables:
```bash
export API_KEY="your-api-key"
export GITHUB_APP_ID="your-github-app-id"
export GITHUB_APP_PRIVATE_KEY_PATH="path/to/private-key.pem"
```

### Running

```bash
uv run uvicorn app.main:app --reload
```

## Documentation

- [API Reference](docs/api.md) - Complete API documentation
- [Policy Configuration](docs/policy.md) - Policy file configuration guide
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

1. Agent sends request with API key
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
│   └── policy.yaml       # Policy configuration
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
