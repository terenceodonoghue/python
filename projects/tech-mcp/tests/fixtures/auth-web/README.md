# Auth Web

SolidJS single-page application for passkey-based sign-in and registration.

## Overview

This is the frontend for the [auth-api](../auth-api) Go service. It provides
a browser-based UI for WebAuthn/passkey registration and authentication.

## API Integration

The app communicates with the Go API server at these endpoints:

- `POST /api/register/begin` and `POST /api/register/finish` for new user signup
- `POST /api/login/begin` and `POST /api/login/finish` for returning users
- `POST /api/logout` to end a session

All API calls use `fetch` with `credentials: "include"` for cookie-based sessions.

## Stack

- SolidJS 1.9 with SolidJS Router
- Vite for build tooling
- CSS Modules for styling
- Deployed as a static Docker image served by Caddy

## Development

```sh
bun install
bun run dev
```

The dev server proxies `/api/*` requests to the Go API at `http://localhost:8081`.
