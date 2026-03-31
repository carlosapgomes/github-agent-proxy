## ADDED Requirements

### Requirement: Repository code and tests pass mypy
The repository SHALL keep checked-in code and tests compliant with the configured mypy type-check run.

#### Scenario: Current mypy baseline errors are removed
- **WHEN** `uv run mypy .` is executed against the repository
- **THEN** it completes successfully without reporting the current baseline typing errors
