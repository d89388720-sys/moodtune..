# Use this project with Google AI Studio

## Important runtime difference

This repository's backend is Python Flask. Google AI Studio Build currently creates web apps with a React frontend and a **Node.js server runtime**. It can import a GitHub repository, but it does not execute this Flask backend as its runtime. So import is useful for having AI Studio inspect/refine the project, but a Python app still needs a Python host such as Cloud Run (using the included Dockerfile) or another Python service. Google documents GitHub import and the Node server runtime in its [Build mode guide](https://ai.google.dev/gemini-api/docs/aistudio-build-mode).

## Put the ZIP into GitHub

1. Download and extract `MoodTunes-GitHub-ready.zip` on your computer.
2. Create a new **private** GitHub repository named `moodtunes` (private is a sensible default while settings and integrations are being completed).
3. Upload the extracted project files and folders to the repository root. Include dotfiles such as `.gitignore` and `.env.example`.
4. Do **not** upload `.env`, database files, Spotify Client Secret, Gemini/Emergent keys, or real user data. The `.gitignore` excludes these.
5. In Google AI Studio, open **Build**, choose **Add files (+) → Import from GitHub**, authorize GitHub if prompted, and select this repository.

## Prompt to give AI Studio after import

```text
Inspect this repository before changing it. It is a Python 3.11 Flask + SQLAlchemy app with an HTML/CSS/JavaScript frontend. Preserve Python as the primary backend and preserve existing profile isolation, password hashing, CSRF checks, privacy rules for camera frames, manual mood fallback, and the Spotify Client ID environment-variable setup.

Do not claim this Flask app runs in AI Studio's Node server. Do not silently replace the backend with a mock or hardcoded-data prototype. First report which files and routes you inspected. Then help me deploy the existing Python backend as a container to Google Cloud Run using the included Dockerfile, and explain which secrets I must add server-side. Use a durable PostgreSQL database for production; do not use ephemeral SQLite on Cloud Run.

Before modifying the app, list gaps you find in the source. Specifically verify live Gemini/Emergent calls, OAuth callback and refresh behavior, persistent theme settings, playlist CRUD, mobile camera use, and whether all buttons are wired. Do not fabricate Gemini results, Spotify playback, tracks, artwork, song audio, or test results. Keep missing integrations visibly unavailable until configured. Provide a deployment checklist and ask me to run the included tests in a Python 3.11 environment if this environment cannot run them.
```

## Recommended publishing path while keeping Python

Use Google AI Studio to inspect/refine the code or generate a compatible interface, then deploy the actual Flask container to **Cloud Run**. Use the repository's `Dockerfile`; configure `SECRET_KEY`, `DATABASE_URL`, `COOKIE_SECURE=true`, and integration credentials in Cloud Run's server-side secret/environment configuration. Create a durable PostgreSQL database first. When deploying, select a region, enable billing if Google requires it, and review expected charges.

Set the production URL as `SPOTIFY_REDIRECT_URI` and add the exact same URI to the Spotify Developer Dashboard allowlist. For example: `https://YOUR-SERVICE-URL/spotify/callback`.

## Gemini key note

This version expects `EMERGENT_API_KEY` and calls the Emergent integrations package. Google AI Studio's `GEMINI_API_KEY` is a different credential and does not automatically substitute for an Emergent key. If you want to use Google's Gemini API directly instead, ask AI Studio to implement a server-side Gemini API adapter using a server secret, retain safe failure/manual fallback behavior, and never expose the key to browser code.

## Spotify and music note

The project includes the Spotify Client ID supplied in the master prompt in `.env.example`. A Client ID is public app identification; OAuth token exchange still requires the Client Secret, which you must privately configure in the server. The catalog CSV contains a small set of track metadata and Spotify links, not the songs themselves. Spotify streams the music in Spotify. Do not upload copyrighted audio into GitHub. Full playback control depends on Spotify's current API access rules and Premium-account requirements.
