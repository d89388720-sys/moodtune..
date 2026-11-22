# Deployment checklist (Python backend)

This project is not deployed yet. No cloud account or production credentials were available when this ZIP was prepared.

## Cloud Run outline

1. Push the source to GitHub; exclude all `.env` files and user data.
2. Create a managed PostgreSQL instance and database. Copy its private connection URL into the service's `DATABASE_URL` setting. Do not use SQLite on an ephemeral container filesystem for persistent accounts.
3. Build/deploy the included Dockerfile to Cloud Run. The container listens on `$PORT` (default 8080) and starts `gunicorn app:app`.
4. Set `SECRET_KEY` to a strong random value and `COOKIE_SECURE=true`.
5. For facial/text AI, privately configure `EMERGENT_API_KEY`. If using Google Gemini directly, the application code must first be adapted: Google AI Studio's own `GEMINI_API_KEY` is not an Emergent key.
6. For Spotify OAuth, privately set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI` to the deployed callback URL.
7. In the Spotify Developer Dashboard, allowlist the exact HTTPS callback URL, including path and capitalization.
8. Verify health/startup, registration, sign-in after logout, DB persistence, profile isolation, HTTPS cookies, and every configured external-service error path.

## Secrets required from the owner

- Cloud project access and permission to deploy Cloud Run / enable billing.
- Durable PostgreSQL instance and connection string.
- A strong application `SECRET_KEY`.
- Emergent API key if retaining the Emergent integration.
- Spotify Client Secret. The Client ID (`7af72ceb266241e69b21ebd46a48ff08`) was present in the supplied prompt.
- Deployed Spotify redirect URL after Cloud Run assigns a service URL.

Never paste secrets into chat, browser code, a public repository, or this ZIP. Add them in the host's secret manager.

## Verification status

The JavaScript file passed `node --check` while preparing this bundle. Python and pytest could not be run in the preparation environment because no working Python interpreter was available. Treat deployment as unverified until the included test suite and live integration checks pass.
