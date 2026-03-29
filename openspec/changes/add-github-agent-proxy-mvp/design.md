## Context

This change creates the first production-facing version of `github-agent-proxy`, a security middleware between Hermes and GitHub. The main requirement is to constrain all automated write operations to explicit, auditable, policy-checked API endpoints.

Current state:
- No proxy contract exists yet.
- No OpenSpec capability baseline exists yet.
- We must start with high-rigor artifacts (HIGH/ARCH), because the system controls source code write operations.

Key constraints:
- No direct writes to `main` or any protected branch.
- No generic GitHub passthrough.
- Authorization policy must come from YAML (no implicit defaults that expand permissions).
- Logging must support basic auditability.
- Scope is MVP only: branch creation, file commits, and PR creation.

Stakeholders:
- Hermes agent (client)
- Repository maintainers / reviewers
- Security and platform owners of GitHub App credentials

## Goals / Non-Goals

**Goals:**
- Provide a minimal, secure proxy API with exactly three write capabilities.
- Enforce API key authentication for Hermes requests.
- Enforce repository/action/branch policy from YAML for every request.
- Use GitHub App installation token per request.
- Guarantee branch protection constraints for all write paths.
- Emit structured JSON logs for traceability.
- Organize implementation tasks as endpoint-oriented vertical slices to support TDD delivery.

**Non-Goals:**
- Generic GitHub proxy behavior.
- Arbitrary GitHub API exposure.
- Runtime execution or sandboxing of agent-generated code.
- Advanced policy features (quotas, per-file limits, rate limiting) in this MVP.

## Decisions

1. **Proxy API contract with three explicit endpoints**
   - Decision: expose only `/create-branch`, `/commit-files`, `/create-pr`.
   - Rationale: fixed contract reduces attack surface and simplifies audit and review.
   - Alternatives considered:
     - Generic `/github/*` passthrough (rejected: too permissive).
     - One multiplexed endpoint with `action` field (rejected: harder to secure and validate cleanly).

2. **Authentication model: static API key bearer token**
   - Decision: authenticate Hermes with `Authorization: Bearer <API_KEY>`.
   - Rationale: simple, deterministic integration for MVP and low operational overhead.
   - Alternatives considered:
     - mTLS client certs (rejected for MVP complexity).
     - OAuth between Hermes and proxy (rejected as unnecessary for single trusted caller initially).

3. **Authorization model: YAML allowlists**
   - Decision: evaluate `allowed_repos`, `allowed_actions`, `protected_branches` on every request.
   - Rationale: transparent and auditable policy source, easy to review in version control.
   - Alternatives considered:
     - Hardcoded policy in code (rejected: poor operational maintainability).
     - DB-backed policy (rejected: unnecessary infra for MVP).

4. **GitHub authentication via installation token per request**
   - Decision: generate GitHub App installation token each request path that calls GitHub.
   - Rationale: least privilege and short-lived credentials reduce blast radius.
   - Alternatives considered:
     - Cached long-lived token (rejected: higher credential risk).

5. **Branch protection guardrail as hard validation**
   - Decision: reject operations targeting protected branches for commit flows, and reject PR head/base misuse when violating policy intent.
   - Rationale: enforce non-negotiable constraint (`no write to main/master/protected branches`).
   - Alternatives considered:
     - Rely only on GitHub branch protections (rejected: defense in depth requires proxy-side enforcement too).

6. **Implementation approach: endpoint-based vertical slices with TDD**
   - Decision: implement and validate end-to-end by endpoint (`create-branch` first, then `commit-files`, then `create-pr`).
   - Rationale: each slice delivers user value and executable policy checks while reducing integration risk.
   - Alternatives considered:
     - Horizontal layering first (all auth, then all GitHub client, then all routes) rejected because it delays end-to-end validation.

## Risks / Trade-offs

- **[Risk] Misconfigured YAML may block valid operations or allow unintended ones** → Mitigation: strict schema validation at startup and fail-fast behavior.
- **[Risk] GitHub API/network failures break requests** → Mitigation: deterministic error mapping and clear retry guidance for caller.
- **[Risk] API key leakage enables unauthorized calls** → Mitigation: secret management outside repo and immediate key rotation procedure.
- **[Risk] Agent can still create risky code inside PRs** → Mitigation: human review remains mandatory gate.
- **[Trade-off] Simple API key auth is less robust than stronger identity solutions** → Accepted for MVP; revisit in future iterations.

## Migration Plan

1. Create OpenSpec artifacts for proposal, specs, design, tasks (this change).
2. Implement proxy in endpoint vertical slices with tests first (RED→GREEN→REFACTOR).
3. Configure GitHub App credentials and policy YAML in deployment environment.
4. Dry-run with test repositories in `allowed_repos`.
5. Enable Hermes traffic progressively.
6. Rollback strategy:
   - Disable proxy route / deployment.
   - Revoke GitHub App credentials if compromise suspected.
   - Preserve logs for forensic audit.

## Open Questions

- Should `create-pr` allow protected branches as `base` (typical GitHub workflow), while still forbidding direct commits to them? (Design assumes yes; direct writes remain blocked.)
- For `commit-files`, should commit operation support file deletion in MVP, or only create/update semantics?
- What exact error body schema should be standardized for downstream Hermes automation?
