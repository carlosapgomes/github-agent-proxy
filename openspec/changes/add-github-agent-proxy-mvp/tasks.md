## 1. Foundation and policy primitives

- [x] 1.1 Define YAML policy loader and validation for `allowed_repos`, `allowed_actions`, and `protected_branches`
- [x] 1.2 Define request auth guard for `Authorization: Bearer <API_KEY>` with 401 behavior
- [ ] 1.3 Define GitHub App installation-token provider abstraction (token per request)
- [ ] 1.4 Define structured JSON audit logging contract (`timestamp`, `agent`, `repo`, `action`)

## 2. Vertical Slice A — `POST /create-branch`

- [ ] 2.1 RED: Add failing API tests for success and denial paths (unauthenticated, unauthorized repo/action, protected branch)
- [ ] 2.2 GREEN: Implement minimal `POST /create-branch` endpoint to satisfy tests with policy enforcement
- [ ] 2.3 GREEN: Integrate per-request GitHub App token generation and branch creation call
- [ ] 2.4 REFACTOR: Clean route/service boundaries and keep tests green
- [ ] 2.5 Add audit log assertions for successful and denied `create_branch` requests

## 3. Vertical Slice B — `POST /commit-files`

- [ ] 3.1 RED: Add failing API tests for commit success and blocking cases (protected branch, empty files, unauthorized repo/action)
- [ ] 3.2 GREEN: Implement minimal `POST /commit-files` endpoint with payload validation and policy checks
- [ ] 3.3 GREEN: Implement GitHub commit flow for file updates on non-protected branches
- [ ] 3.4 REFACTOR: Isolate commit orchestration logic and preserve API behavior
- [ ] 3.5 Add audit log assertions for `commit_files` success and denial events

## 4. Vertical Slice C — `POST /create-pr`

- [ ] 4.1 RED: Add failing API tests for PR success and validation denials (`head == base`, protected `head`, unauthorized repo/action)
- [ ] 4.2 GREEN: Implement minimal `POST /create-pr` endpoint with policy + payload validation
- [ ] 4.3 GREEN: Implement GitHub PR creation with per-request installation token
- [ ] 4.4 REFACTOR: Consolidate shared policy checks while preserving endpoint-specific constraints
- [ ] 4.5 Add audit log assertions for `create_pr` success and denial events

## 5. Final verification and release readiness

- [ ] 5.1 Add integration tests for full workflow: create-branch → commit-files → create-pr
- [ ] 5.2 Validate no direct write path exists for `main`/`master`/protected branches
- [ ] 5.3 Document API contracts and policy file usage in project docs
- [ ] 5.4 Run project quality gate and record evidence in change artifacts
