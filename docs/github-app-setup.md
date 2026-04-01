# GitHub App Setup Guide

This guide explains how to configure the GitHub App required by the proxy to authenticate with the GitHub API.

## Why a GitHub App Is Required

The proxy uses **two separate authentication layers**:

| Layer | Purpose | Configuration |
|------|---------|---------------|
| Client -> Proxy | Authenticates the caller to the proxy | `Authorization: Bearer <API_KEY>` matched against `PROXY_API_KEY` |
| Proxy -> GitHub | Authenticates the proxy to GitHub | `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY`, `GITHUB_INSTALLATION_ID` |

The Bearer token is **not enough** for GitHub operations by itself. The proxy also needs a configured GitHub App installation so it can mint installation tokens per request.

## What You Need to Configure

The proxy expects these environment variables:

```bash
export GITHUB_APP_ID="your-github-app-id"
export GITHUB_PRIVATE_KEY="$(cat path/to/private-key.pem)"
export GITHUB_INSTALLATION_ID="your-installation-id"
```

Where they come from:

- `GITHUB_APP_ID`: the numeric App ID of your GitHub App
- `GITHUB_PRIVATE_KEY`: the PEM private key generated for that GitHub App
- `GITHUB_INSTALLATION_ID`: the numeric installation ID of that app after it is installed on a user/org account or repository set

## Recommended GitHub App Permissions

For the current proxy endpoints, the GitHub App should have at least these repository permissions:

| Permission | Recommended Access | Why |
|-----------|--------------------|-----|
| Contents | Read and write | Needed to read refs/commits and create blobs, trees, commits, and branch ref updates |
| Pull requests | Read and write | Needed to create pull requests |
| Metadata | Read-only | Standard repository metadata access |

Notes:
- If you do not use `POST /create-pr`, you may be able to omit Pull requests permission.
- The proxy currently supports branch creation, file commits, and PR creation, so `Contents` and `Pull requests` are the practical baseline.
- Grant access only to the repositories the proxy actually needs.

## Recommended Repository Access

When creating/installing the app, prefer:

- **Only selected repositories** instead of all repositories
- repositories that also appear in `config/policy.yaml`

The GitHub App installation scope and the proxy policy should both be restricted. They protect different layers:

- **GitHub App installation scope** limits what GitHub itself allows
- **`config/policy.yaml`** limits what the proxy allows

## Step-by-Step Setup

### 1. Create the GitHub App

In GitHub:

1. Go to **Settings** -> **Developer settings** -> **GitHub Apps**
2. Click **New GitHub App**
3. Choose a name for the app
4. Configure repository access as **Only selected repositories** when possible
5. Set the repository permissions described above
6. Create the app

### 2. Generate a Private Key

After creating the app:

1. Open the app settings page
2. Generate a **private key**
3. Download the `.pem` file
4. Store it securely

The proxy needs the **content** of that PEM file in `GITHUB_PRIVATE_KEY`, not the file path.

Example:

```bash
export GITHUB_PRIVATE_KEY="$(cat path/to/private-key.pem)"
```

If using `.env.example`, store it as a single quoted/string value with `\n` escapes.

### 3. Install the App

Install the GitHub App on the account/organization and repositories the proxy needs to access.

Important:
- the app must be installed before the proxy can obtain installation tokens
- the installation must cover the repositories you expect to allow in `config/policy.yaml`

### 4. Capture the App ID

Copy the GitHub App's numeric **App ID** into:

```bash
export GITHUB_APP_ID="123456"
```

### 5. Capture the Installation ID

After installation, capture the numeric **installation ID** and set:

```bash
export GITHUB_INSTALLATION_ID="12345678"
```

Common ways to obtain the installation ID:

- from the GitHub UI for the installed app
- from the installation URL if GitHub shows it there
- from the GitHub API if you already have an app/JWT-based setup flow

## Minimal Local Setup Example

```bash
cp .env.example .env
cp config/policy.yaml.example config/policy.yaml

# edit .env
# - PROXY_API_KEY
# - GITHUB_APP_ID
# - GITHUB_PRIVATE_KEY
# - GITHUB_INSTALLATION_ID

# edit config/policy.yaml
# - allowed_repos
# - allowed_actions
# - protected_branches

uv run uvicorn app.main:app --reload --env-file .env
```

## How to Tell GitHub App Setup Is Missing or Broken

Typical symptoms:

- `401 unauthorized`: usually the client Bearer token does not match `PROXY_API_KEY`
- `403 forbidden`: usually the proxy policy blocked the repo/action/branch
- `500 server_error`: often indicates missing/invalid GitHub App credentials or an upstream GitHub API failure

If requests authenticate to the proxy but fail when the proxy calls GitHub, verify:

- `GITHUB_APP_ID` is correct
- `GITHUB_PRIVATE_KEY` contains valid PEM content
- `GITHUB_INSTALLATION_ID` is correct
- the app is installed on the target repository
- the app has the required permissions

## Security Recommendations

- Store the private key in a secret manager or protected deployment environment
- Rotate GitHub App private keys periodically
- Use **Only selected repositories** for app installation when possible
- Keep `config/policy.yaml` aligned with the app installation scope
- Do not treat the client Bearer token as a replacement for GitHub App credentials

## Related Documentation

- [README](../README.md)
- [API Reference](api.md)
- [Policy Configuration](policy.md)
- [Agent Integration](agent-integration.md)
