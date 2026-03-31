## Context

`github-agent-proxy` currently creates commits with GitHub App credentials and without explicit Git author metadata. That keeps the write path secure, but it prevents operators from configuring a stable author identity that GitHub can attribute to their contribution graph. The change must preserve the existing security model: the proxy still authenticates upstream with a GitHub App installation token, still blocks protected-branch writes, and still exposes only the existing endpoints.

## Goals / Non-Goals

**Goals:**
- Allow fixed commit author attribution through environment variables.
- Keep the `/commit-files` request and response contracts unchanged.
- Preserve GitHub App-based execution while setting only Git `author` metadata.
- Fail fast on incomplete author configuration to avoid ambiguous attribution.

**Non-Goals:**
- Per-request author impersonation.
- Changing PR or branch creation behavior.
- Overriding Git `committer` metadata.
- Discovering GitHub user identity automatically from repository ownership or runtime environment.

## Decisions

1. **Use environment variables for author identity**
   - Decision: add optional `GITHUB_COMMIT_AUTHOR_NAME` and `GITHUB_COMMIT_AUTHOR_EMAIL` environment variables.
   - Rationale: this matches the existing runtime configuration style and satisfies the single-operator use case without widening the API surface.
   - Alternatives considered:
     - Add author fields to `/commit-files` requests (rejected: raises spoofing risk and changes public API).
     - Derive author from repository owner or machine user (rejected: unreliable and often not a human identity).

2. **Require both name and email together**
   - Decision: treat author attribution as enabled only when both variables are present; raise startup error if only one is configured.
   - Rationale: partial metadata is easy to misconfigure and does not reliably produce GitHub profile attribution.
   - Alternatives considered:
     - Ignore partial configuration silently (rejected: hides operator mistakes).

3. **Set only `author`, not `committer`**
   - Decision: include the configured identity in the GitHub commit creation payload under `author` only.
   - Rationale: this supports GitHub contribution attribution while keeping the actual technical writer identity aligned with the GitHub App installation.
   - Alternatives considered:
     - Also override `committer` (rejected: less honest operationally and unnecessary for contribution graphs).

## Risks / Trade-offs

- **[Risk] Misconfigured email still will not count toward the intended GitHub profile** → Mitigation: document that the configured email must already be associated with the target GitHub account.
- **[Risk] Startup now fails for partial configuration** → Mitigation: keep the validation rule simple and explicit in docs.
- **[Trade-off] Fixed environment configuration only supports one author identity per deployment** → Accepted for this change; multi-user attribution can be considered separately later.

## Migration Plan

1. Add tests for configured author payload and partial configuration failure.
2. Implement author configuration loading in app startup.
3. Pass optional author metadata into GitHub commit creation.
4. Document required environment variables and GitHub profile attribution behavior.
5. Run quality gates and update change tasks.

## Open Questions

- None for this scoped change.
