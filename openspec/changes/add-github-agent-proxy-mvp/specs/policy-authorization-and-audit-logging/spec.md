## ADDED Requirements

### Requirement: YAML configuration defines authorization boundaries
The proxy SHALL load authorization policy from YAML with fields:
- `allowed_repos`
- `allowed_actions`
- `protected_branches`

The proxy SHALL deny operations outside this policy.

#### Scenario: Allowed policy combination
- **WHEN** request action and repository are both listed in YAML policy
- **THEN** the proxy continues to endpoint-specific validation and execution

#### Scenario: Action not listed in allowed_actions
- **WHEN** requested operation is not listed in `allowed_actions`
- **THEN** the proxy returns `403 Forbidden`

#### Scenario: Repository not listed in allowed_repos
- **WHEN** requested repository is not listed in `allowed_repos`
- **THEN** the proxy returns `403 Forbidden`

### Requirement: Protected branch policy is enforced globally for write safety
The proxy SHALL enforce protected branch restrictions for all write operations that modify branch contents.

#### Scenario: Write operation targets protected branch
- **WHEN** a write operation (such as commit) targets a protected branch
- **THEN** the proxy rejects the request with `403 Forbidden`

### Requirement: Audit logging emits structured JSON records
The proxy SHALL emit one structured JSON audit log per handled request, including at minimum:
- `timestamp`
- `agent`
- `repo`
- `action`

#### Scenario: Successful commit request logging
- **WHEN** `commit_files` operation succeeds
- **THEN** a JSON log event is emitted containing timestamp, agent `hermes`, repo, and action `commit_files`

#### Scenario: Denied request logging
- **WHEN** a request is denied by policy or authentication
- **THEN** a JSON log event is still emitted with timestamp, agent (if known), repo (if provided), and action
