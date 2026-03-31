## ADDED Requirements

### Requirement: Repository-shipped helper scripts pass Ruff linting
The repository SHALL keep checked-in helper scripts and related tests compliant with the configured Ruff lint rules.

#### Scenario: Current helper-script lint errors are cleaned up
- **WHEN** `uv run ruff check .` is executed against the repository
- **THEN** it completes successfully without reporting the current helper-script violations

### Requirement: Repository-shipped helper scripts pass Ruff formatting checks
The repository SHALL keep checked-in helper scripts and related tests compliant with the configured Ruff formatter.

#### Scenario: Current helper-script formatting drift is removed
- **WHEN** `uv run ruff format --check .` is executed against the repository
- **THEN** it completes successfully without requesting reformatting for the current helper-script files
