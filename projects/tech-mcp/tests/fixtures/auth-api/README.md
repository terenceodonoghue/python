# Auth API

WebAuthn/passkey authentication service written in Go.

## Endpoints

### Registration

- `POST /api/register/begin` — Start passkey registration for a new user
- `POST /api/register/finish` — Complete passkey registration

### Authentication

- `POST /api/login/begin` — Start passkey login
- `POST /api/login/finish` — Complete passkey login and create session
- `POST /api/logout` — Invalidate current session

### Token Management

- `GET /api/tokens` — List all API tokens for the current user
- `POST /api/tokens` — Create a new API token
- `PATCH /api/tokens/{id}` — Update a token (rename, rotate)
- `DELETE /api/tokens/{id}` — Revoke a token

### Introspection

- `POST /api/introspect` — Validate a token and return user info (used by Caddy forward auth)

## Stack

- Go stdlib `net/http` router
- PostgreSQL via `pgx/v5` for user and credential storage
- Redis for session management
- WebAuthn library for passkey protocol

## Configuration

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_ADDR` | Redis address (host:port) |
| `RP_ID` | WebAuthn relying party ID (e.g. `codebydesign.dev`) |
| `RP_ORIGINS` | Allowed origins for WebAuthn |
| `ADDR` | Listen address (default `:8081`) |
