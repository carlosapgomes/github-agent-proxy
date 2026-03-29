## ADDED Requirements

### Requirement: Create PR endpoint opens pull requests from working branches
The proxy SHALL expose `POST /create-pr` with payload `{ repo, title, body, head, base }` and SHALL create a pull request in GitHub when policy checks pass.

#### Scenario: Successful PR creation to protected base branch
- **WHEN** request has allowed `repo`, allowed action `create_pr`, non-protected `head`, and valid `base` branch (including protected base such as `main`)
- **THEN** the proxy creates the pull request and returns success

#### Scenario: Unauthorized repository or action
- **WHEN** `repo` is not in `allowed_repos` or `create_pr` is not in `allowed_actions`
- **THEN** the proxy returns `403 Forbidden` and does not call GitHub APIs

#### Scenario: Invalid PR branch pairing
- **WHEN** `head` equals `base`
- **THEN** the proxy returns `422 Unprocessable Entity` and does not call GitHub APIs

#### Scenario: PR head is a protected branch
- **WHEN** `head` matches a protected branch in `protected_branches`
- **THEN** the proxy returns `403 Forbidden`

### Requirement: PR creation follows branch-first workflow
The proxy SHALL support the sequence create-branch → commit-files → create-pr and SHALL not provide direct merge or direct push endpoints.

#### Scenario: Hermes requests PR after commit flow
- **WHEN** a branch with committed changes is provided as `head`
- **THEN** the proxy creates a pull request as the final write operation in the workflow
