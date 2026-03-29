## ADDED Requirements

### Requirement: Bearer API key authentication is mandatory
The proxy SHALL require `Authorization: Bearer <API_KEY>` on every write endpoint request and SHALL reject requests without a valid bearer token.

#### Scenario: Missing Authorization header
- **WHEN** a client calls any proxy endpoint without an `Authorization` header
- **THEN** the proxy returns `401 Unauthorized` and does not call GitHub APIs

#### Scenario: Invalid bearer token
- **WHEN** a client calls any proxy endpoint with an invalid API key value
- **THEN** the proxy returns `401 Unauthorized` and does not call GitHub APIs

#### Scenario: Unsupported authorization scheme
- **WHEN** a client uses a non-bearer auth scheme (for example `Basic`)
- **THEN** the proxy returns `401 Unauthorized` and does not call GitHub APIs

### Requirement: Authenticated identity is represented as Hermes agent
The proxy SHALL attribute authenticated requests to the Hermes agent identity for audit logging.

#### Scenario: Valid API key request
- **WHEN** a request is authenticated with the configured API key
- **THEN** the request context contains agent identity `hermes` for audit records
