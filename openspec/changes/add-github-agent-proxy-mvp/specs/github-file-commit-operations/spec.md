## ADDED Requirements

### Requirement: Commit files endpoint writes file updates to a non-protected branch
The proxy SHALL expose `POST /commit-files` with payload `{ repo, branch, files[], message }` and SHALL commit provided file contents only to non-protected branches.

#### Scenario: Successful commit on working branch
- **WHEN** the request has allowed `repo`, allowed action `commit_files`, non-protected `branch`, at least one file entry, and valid commit message
- **THEN** the proxy creates a commit containing the provided file updates and returns success

#### Scenario: Commit to protected branch is rejected
- **WHEN** `branch` matches a protected branch in `protected_branches`
- **THEN** the proxy returns `403 Forbidden` and does not write any commit

#### Scenario: Empty files payload
- **WHEN** `files` is empty
- **THEN** the proxy returns `422 Unprocessable Entity` and does not call GitHub APIs

#### Scenario: Repository or action not authorized
- **WHEN** `repo` is not in `allowed_repos` or `commit_files` is not in `allowed_actions`
- **THEN** the proxy returns `403 Forbidden` and does not call GitHub APIs

### Requirement: Commit operation does not allow direct write to mainline branches
The proxy SHALL enforce that no commit operation writes directly to `main`, `master`, or any configured protected branch.

#### Scenario: Branch equals mainline
- **WHEN** commit request targets `main` or `master`
- **THEN** the proxy rejects the request with `403 Forbidden`
