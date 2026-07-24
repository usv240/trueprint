# Trueprint

**Provenance-preserving restoration for the world's archives.**

AI restoration doesn't *recover* history — it *invents a plausible guess*. Trueprint restores old photos and audio like the best AI tools, then emits a **cryptographically verifiable authenticity map** proving exactly which pixels are **original**, **enhanced**, or **AI-fabricated** — sealed into a tamper-evident, hash-verified provenance manifest and archived durably on **Backblaze B2**.

Built for the **Backblaze Generative Media Hackathon** on **Backblaze B2 + Genblaze**.

> ⚠️ Work in progress. See [PLAN.md](PLAN.md) for the full build plan and [SOURCES.md](SOURCES.md) for citations and IP/legal notes.

---

## What it does

1. **Restore** — a Genblaze pipeline: ingest → **analyze** (vision LLM describes the photo, dates it, flags damage and *which colors are unknowable*) → **colorize** (multiple independent generations via Genblaze) → **authenticity engine** → durable archive.
2. **Reveal** — colorization is **luminance-locked** (the AI's color is recombined with the *original's* luminance in LAB space), so the result is provably faithful in structure. Running colorization across independent samples yields a **confidence heatmap** — where the samples agree the inference is grounded; where they disagree, the color is flagged as a guess. Reported on two honest axes: **structure** (kept / enhanced / fabricated) vs **color** (100% inferred).
3. **Verify** — every restoration is signed with a **real, embedded C2PA Content Credential** (readable in Adobe Content Credentials / any C2PA viewer) that declares the AI color edit as `compositeWithTrainedAlgorithmicMedia` — the **EU AI Act Article 50** machine-readable AI marking — plus a hash-verified provenance manifest stored on B2 next to an immutable master (Object Lock). The **Verify** page checks a file two ways: it reads the **embedded C2PA credential** (trust travels in the file, off-platform) *and* hashes it against the B2 catalog. Refusals are recorded too: if an image model declines a photo (content policy), that is written into provenance rather than hidden.

> The dev signing cert is self-signed (self-provisioned at runtime), so strict verifiers report the *signer* as untrusted — disclosed honestly; a production archive swaps in a CA cert on the C2PA trust list.

## How it uses Backblaze B2

- **Dual OAIS-style archive:** immutable `masters/` (Object Lock) + `derivatives/` (restorations) + `manifests/`, in a hierarchical, queryable key layout.
- **System of record**, not a blob store: a lineage catalog indexes every derivative's full step history; results are served, verified, and replayed from B2.

## How it uses Genblaze

- **Orchestration** of each restoration through the Genblaze `Pipeline` (steps, inputs, provider abstraction).
- A **custom provider** (`TrueprintImageProvider`, subclassing `GMICloudImageProvider`) emits the request-queue payload the image model expects — keeping all of Genblaze's Pipeline / manifest / lineage machinery.
- **Multi-provider corroboration** — colorization runs across two independent providers (Google Gemini + OpenAI gpt-image), both orchestrated via Genblaze; their per-pixel disagreement is the confidence heatmap. Gemini (aspect-preserving, reliable) drives the final image.
- **LLM-as-judge verification** — a `CallableEvaluator` producing a Genblaze `EvaluationResult` compares the restoration to the master and flags historically-implausible fabrication (this caught, and drove the fix for, a real ghosting artifact during development).
- **Provenance manifests** from each run are folded into Trueprint's manifest, hash-verified, and archived on B2.

## Providers & models used

| Role | Provider | Model | Notes |
|---|---|---|---|
| Vision analysis + uncertain-color detection + LLM-judge | GMI Cloud | `google/gemini-3.6-flash` | multimodal, OpenAI-compatible chat API |
| **Colorization — primary** (drives the final) | **Google** | `gemini-3.1-flash-image` | image-to-image, aspect-preserving, reliable |
| **Colorization — 2nd provider** (confidence) | GMI Cloud | `gpt-image-2-edit` | independent second opinion (OpenAI family) |
| Storage / system of record | Backblaze B2 (S3) | — | masters + derivatives + manifests + catalog |

_Colorization is luminance-locked in the authenticity engine (OpenCV/NumPy) so the AI supplies color only; the original structure is preserved. Two independent providers colorize each photo — **Google Gemini** (primary; aspect-preserving) and **OpenAI gpt-image** (via GMI) — and their disagreement forms the confidence map. `gpt-image-2-edit` declines photos containing minors (provider policy); Trueprint records such refusals in provenance and degrades gracefully. When only one provider is configured, the pipeline falls back to two independent samples of it._

## Setup

```bash
# 1. Python 3.11+ environment
python -m venv .venv && ./.venv/Scripts/activate    # Windows
pip install -r backend/requirements.txt

# 2. Configure secrets
cp .env.example .env       # then fill in B2 + GMI values (see .env.example)

# 3. Validate connections
python scripts/validate.py          # B2 round-trip + GMI reachability

# 4. (optional) pre-cache sample restorations for an instant demo
python scripts/precache.py

# 5. Run the app (serves landing, /app, and the API)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
#   landing  http://localhost:8000/
#   app      http://localhost:8000/app
#   verify   http://localhost:8000/verify

# 6. Tests (pure-CV authenticity engine + helpers; no credentials needed)
pytest -q
```

`.env` is git-ignored — never commit real keys. See `.env.example` for the full list.

## References

Regulatory, archival, and platform claims are documented with sources in [SOURCES.md](SOURCES.md) — including the Library of Congress LAMs call-to-action, EU AI Act Article 50, C2PA, and OAIS. Demo figures are illustrative until produced by a real run.

## License

MIT — see [LICENSE](LICENSE).
