## Why

Hermes currently needs to interact with GitHub, but direct repository access creates a high-risk trust boundary and weak policy enforcement. We need a secure proxy that strictly limits what Hermes can do and guarantees all code changes go through Pull Requests.

## What Changes

- Introduce a FastAPI-based proxy service that exposes only three write operations for Hermes:
  - `POST /create-branch`
  - `POST /commit-files`
  - `POST /create-pr`
- Enforce agent authentication via static API key in `Authorization: Bearer <API_KEY>`.
- Enforce authorization and policy checks from YAML config:
  - allowed repositories
  - allowed actions
  - protected branches
- Integrate with GitHub App authentication by generating an installation token per request.
- Block direct writes to protected branches (including `main` and `master`) for all write flows.
- Add structured JSON audit logs for each request action.
- Define endpoint contracts and failure behavior for denied actions, invalid payloads, and GitHub API failures.

## Capabilities

### New Capabilities

- `agent-authentication`: Authenticate Hermes requests using API key bearer token.
- `github-branch-operations`: Create non-protected branches from a base branch in allowed repositories.
- `github-file-commit-operations`: Commit file changes to non-protected branches only.
- `github-pull-request-operations`: Create pull requests from working branches into base branches.
- `policy-authorization-and-audit-logging`: Enforce YAML-driven action/repository/branch policy and emit JSON audit logs.

### Modified Capabilities

- None.

## Impact

- **APIs**: Adds three public proxy endpoints for Hermes.
- **Security boundary**: Removes direct GitHub access from Hermes; proxy becomes the single write gateway.
- **Dependencies**: Requires GitHub App credentials and outbound connectivity to GitHub API.
- **Configuration**: Introduces required YAML policy file for repository/action/branch allowlists.
- **Operations**: Adds structured logs for basic auditability and incident tracing.
