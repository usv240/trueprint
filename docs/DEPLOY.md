# Deploying Trueprint

One container serves the landing page, the `/app`, the `/verify` page, and the API.
**No login/auth** — judges can use it directly (satisfies the "free, no restriction" rule).

## Option A — Render (recommended, uses `render.yaml`)
1. Push the repo to GitHub (already done: `usv240/trueprint`).
2. Render → **New +** → **Blueprint** → pick the repo. It reads `render.yaml`.
3. Set the four **secret** env vars in the dashboard: `B2_KEY_ID`, `B2_APP_KEY`, `GMI_API_KEY`, `GOOGLE_API_KEY` (from your `.env`).
4. Deploy. The health check is `/api/health`. Your URL will be `https://trueprint-XXXX.onrender.com`.

## Option B — Railway
1. Railway → **New Project** → **Deploy from GitHub repo** → pick the repo (it auto-detects the `Dockerfile`).
2. Add the env vars (Variables tab) — same list as `render.yaml` (the 4 secrets + the config values).
3. Deploy; Railway assigns a public URL.

## Option C — Local Docker (to test the image)
```bash
docker build -t trueprint .
docker run -p 8000:8000 --env-file .env trueprint
# open http://localhost:8000/
```

## Required environment variables
| Secret (set privately) | Config (safe to set as plain values) |
|---|---|
| `B2_KEY_ID`, `B2_APP_KEY` | `B2_BUCKET`, `B2_S3_ENDPOINT`, `B2_REGION` |
| `GMI_API_KEY` | `GMI_CHAT_BASE_URL`, `GMI_IMAGE_BASE_URL`, `GMI_MODEL_VISION`, `GMI_MODEL_RECOLOR` |
| `GOOGLE_API_KEY` | `GOOGLE_MODEL_IMAGE` |

Optional guards: `TP_RATE_PER_IP_HOUR`, `TP_MAX_CONCURRENT`, `TP_DAILY_CAP`, `TP_MAX_UPLOAD_MB`, `B2_MASTER_LOCK_MODE`.

## Notes
- The C2PA dev signing cert is **self-provisioned at runtime** (`backend/certs/` is git-ignored and regenerated on first sign) — nothing to configure.
- **Cached sample restorations are instant and free**; only live uploads call the paid APIs, and those are rate-limited + capped by the guards above.
- After deploy, put the URL in the Devpost submission and in `docs/SUBMISSION.md` (Links section).
