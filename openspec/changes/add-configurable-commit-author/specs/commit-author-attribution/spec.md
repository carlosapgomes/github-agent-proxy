## ADDED Requirements

### Requirement: Configurable commit author attribution
The proxy SHALL allow operators to configure a fixed Git commit author identity for `POST /commit-files` using environment variables.

#### Scenario: Author attribution is configured
- **WHEN** `GITHUB_COMMIT_AUTHOR_NAME` and `GITHUB_COMMIT_AUTHOR_EMAIL` are both configured
- **THEN** the proxy includes that identity as the Git `author` when creating commits in GitHub

#### Scenario: Author attribution is not configured
- **WHEN** neither `GITHUB_COMMIT_AUTHOR_NAME` nor `GITHUB_COMMIT_AUTHOR_EMAIL` is configured
- **THEN** the proxy creates commits without explicit author metadata and preserves existing behavior

### Requirement: Incomplete commit author configuration is rejected
The proxy MUST fail fast during startup when only one of the commit author environment variables is configured.

#### Scenario: Only author name is configured
- **WHEN** `GITHUB_COMMIT_AUTHOR_NAME` is set and `GITHUB_COMMIT_AUTHOR_EMAIL` is empty
- **THEN** application initialization fails with a configuration error before serving requests

#### Scenario: Only author email is configured
- **WHEN** `GITHUB_COMMIT_AUTHOR_EMAIL` is set and `GITHUB_COMMIT_AUTHOR_NAME` is empty
- **THEN** application initialization fails with a configuration error before serving requests
