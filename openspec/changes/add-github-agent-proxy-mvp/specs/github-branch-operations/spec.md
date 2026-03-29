## ADDED Requirements

### Requirement: Create branch endpoint creates a new branch from a base reference
The proxy SHALL expose `POST /create-branch` with payload `{ repo, branch, base }` and SHALL create `branch` from `base` in the target repository when policy checks pass.

#### Scenario: Successful branch creation
- **WHEN** the request contains an allowed `repo`, allowed action `create_branch`, a non-protected `branch`, and an existing `base`
- **THEN** the proxy creates the branch via GitHub API and returns success

#### Scenario: Repository is not allowed
- **WHEN** `repo` is not listed in `allowed_repos`
- **THEN** the proxy returns `403 Forbidden` and does not call GitHub APIs

#### Scenario: Action is not allowed by policy
- **WHEN** `create_branch` is not listed in `allowed_actions`
- **THEN** the proxy returns `403 Forbidden` and does not call GitHub APIs

#### Scenario: Attempt to create protected branch name
- **WHEN** `branch` matches a protected branch in `protected_branches`
- **THEN** the proxy returns `403 Forbidden` and does not create the branch

### Requirement: Create branch uses GitHub App installation token per request
The proxy SHALL authenticate to GitHub using a GitHub App installation token generated for each request.

#### Scenario: Branch creation request to GitHub
- **WHEN** the proxy executes a valid create-branch operation
- **THEN** the proxy obtains a fresh installation token for that request before calling GitHub
