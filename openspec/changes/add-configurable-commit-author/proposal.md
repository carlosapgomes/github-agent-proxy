## Why

Commits created through `POST /commit-files` currently rely on the GitHub App installation identity, so they do not automatically appear on the operator's GitHub contribution graph. We need a safe, explicit way to configure commit author metadata so repository owners can attribute proxy-created commits to their own GitHub profile.

## What Changes

- Add fixed environment-based commit author configuration for commit creation.
- When both author name and author email are configured, include them as the Git author on `POST /commit-files` commit creation requests.
- Keep GitHub App authentication and protected-branch safeguards unchanged.
- Document how to configure author attribution so commits can count toward a user's GitHub profile.

## Capabilities

### New Capabilities
- `commit-author-attribution`: Configure a fixed Git author identity for proxy-created commits using environment variables.

### Modified Capabilities
- None.

## Impact

- Affected code: `app/main.py`, `app/github_client.py`, commit-related tests, and API/integration docs.
- APIs: No request/response contract changes.
- Configuration: Adds optional environment variables for commit author name and email.
- External behavior: GitHub commit metadata can be attributed to the configured user profile when the email is associated with that GitHub account.
