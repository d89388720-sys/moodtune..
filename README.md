# MoodTunes

MoodTunes is a Python/Flask application for private mood check-ins, journaling, profile-separated preferences, small browser games, and linking out to Spotify. It includes optional Emergent Gemini analysis and Spotify OAuth integration. It is not a medical service and does not host copyrighted audio.

## Current feature boundaries

- Accounts use Werkzeug password hashing and Flask signed sessions. Check-ins, diary entries, favorites, playlists, game completions, and selected profile theme are stored in SQLAlchemy models. SQLite is the local default; a PostgreSQL URL works in production.
- Camera capture runs only after an explicit click. OpenCV checks that a face is present; the JPEG frame is held in request memory and sent to the configured Emergent integration. It is not written to disk or the database. The response is an estimate of visible expression, not a person's emotional state. Text analysis and camera use fail clearly if the service is unconfigured.
- The catalog has a small set of Spotify track IDs for search and Spotify links. MoodTunes does not stream audio. The sticky player opens Spotify; the app does not yet implement Web Playback SDK controls, Spotify playlist write APIs, token refresh, or disconnect.
- Audiobook cards link to Librivox catalog pages for public-domain recordings. The app does not proxy or host recordings.
- Quote copy is original MoodTunes copy, not externally attributed quotations. The currently displayed daily pool is small.
- Custom profile themes are saved, while full visual customization controls and all ten theme palettes are not yet fully applied.

This implementation is a functional foundation, not the complete production scope described in the master prompt. Read the deployment section before publishing.

## Requirements

- Python 3.11+
- Optional: Emergent API key with Gemini access
- Optional: Spotify Developer app and account
- For production: PostgreSQL, HTTPS, and a persistent hosting service

## Install locally

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a random `SECRET_KEY`. Leave optional AI/Spotify credentials blank to use manual moods and Spotify links. The SQLite database initializes automatically on startup. Never commit `.env`.

## Run

```powershell
python app.py
```

Open `http://127.0.0.1:5000`. Set `COOKIE_SECURE=true` only when serving HTTPS. Use a durable PostgreSQL `DATABASE_URL` for hosted use; the SQLite database inside an ephemeral host filesystem will not be durable.

## Emergent Gemini setup

Set `EMERGENT_API_KEY` in the server environment. The AI functions call the Emergent integrations Python client from the backend. No key is sent to the browser. On missing credentials or an upstream error, the app returns an error and leaves manual mood selection available. Camera permission is requested only after the user clicks **Turn camera on**.

## Spotify setup

Create/configure a Spotify Developer app and set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI`. Add the exact callback URI `<site-origin>/spotify/callback` to the Spotify app redirect allowlist. OAuth uses the Authorization Code flow, state validation, and server-side token storage. Web API playback endpoints require Premium, and the Web Playback SDK also requires Premium; playback controls are not implemented in this build. See Spotify's [authorization flow](https://developer.spotify.com/documentation/web-api/tutorials/code-flow) and [playback requirements](https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback).

## Tests

```powershell
python -m pytest
```

## Deployment

Use a Python-capable persistent host, set `DATABASE_URL` to managed PostgreSQL, set a strong `SECRET_KEY`, `COOKIE_SECURE=true`, and configure the optional integration secrets in the host's secret manager. Start command: `gunicorn app:app`. Set the production Spotify callback URL in both host settings and the Spotify dashboard. Run behind HTTPS and verify auth, database persistence, profile isolation, AI service errors, and OAuth callback on the deployed site.

No hosting account, deployment token, production database, or Emergent API key was available in the build workspace. Therefore no production instance was deployed and no public URL is claimed.

For the step-by-step Google AI Studio/GitHub import workflow and the Python-vs-Node runtime distinction, read [AI_STUDIO_GUIDE.md](AI_STUDIO_GUIDE.md). For the Cloud Run container checklist and required credentials, read [DEPLOYMENT.md](DEPLOYMENT.md). The repository includes a `Dockerfile` and `Procfile` for Python hosting.

The supplied Spotify Client ID is prefilled in `.env.example`; the Spotify Client Secret is intentionally blank and must be created/configured privately by the owner. `datasets/songs.csv` is a small metadata/link sample only. It does not include audio files. Spotify owns the licensed catalog and playback.

## Project layout

```text
app.py                 Flask app, database models, and REST endpoints
templates/index.html   Responsive application shell and page views
static/css/app.css     Responsive dark UI
static/js/app.js       Navigation, games, AI camera UX, and API calls
datasets/              Small Spotify metadata sample and MoodTunes quote dataset
AI_STUDIO_GUIDE.md     GitHub import and AI Studio workflow
DEPLOYMENT.md          Python backend deployment checklist
Dockerfile             Container configuration for Python hosting
requirements.txt       Python dependencies
.env.example           Environment variable names (no secrets)
tests/                 Flask test-client journeys
```
