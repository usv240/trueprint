# Trueprint

**Provenance-preserving restoration for the world's archives.**

AI restoration doesn't *recover* history — it *invents a plausible guess*. Trueprint restores old photos and audio like the best AI tools, then emits a **cryptographically verifiable authenticity map** proving exactly which pixels are **original**, **enhanced**, or **AI-fabricated** — sealed into a tamper-evident, hash-verified provenance manifest and archived durably on **Backblaze B2**.

Built for the **Backblaze Generative Media Hackathon** on **Backblaze B2 + Genblaze**.

> ⚠️ Work in progress. See [PLAN.md](PLAN.md) for the full build plan and [SOURCES.md](SOURCES.md) for citations and IP/legal notes.

---

## What it does

1. **Restore** — a Genblaze pipeline chains specialist models: analyze damage → inpaint → recolor → (audio) restore, with fallback models and retries.
2. **Reveal** — an authenticity map classifies every region as original / enhanced / fabricated, recorded *at generation time* (not guessed after), with a multi-provider confidence heatmap.
3. **Verify** — every result carries a hash-verified provenance manifest, embedded in the file and stored on B2 next to an immutable original master (Object Lock). A public Verify page detects tampering even off-platform.

## How it uses Backblaze B2

- **Dual OAIS-style archive:** immutable `masters/` (Object Lock) + `derivatives/` (restorations) + `manifests/`, in a hierarchical, queryable key layout.
- **System of record**, not a blob store: a lineage catalog indexes every derivative's full step history; results are served, verified, and replayed from B2.

## How it uses Genblaze

- Multi-provider, multi-modal orchestration (image + audio) with `fallback_models` and retries.
- Hash-verified provenance manifests embedded into output media.
- Parent→child run lineage for iterative refinement.
- Multi-provider corroboration (running colorization across independent models) to quantify confidence.

## Providers & models used

| Role | Provider | Model (current) |
|---|---|---|
| Vision / analysis / LLM-judge | GMI Cloud | `google/gemini-3.6-flash` |
| Damage inpaint / fill | GMI Cloud (Bria) | `bria-genfill` |
| Restoration | GMI Cloud (Bria) | `bria-fibo-restore` |
| Recolor / colorize | GMI Cloud (Bria) | `bria-fibo-recolor` |
| Colorize (corroboration) | GMI Cloud | `hunyuan-image-to-image`, `seededit-3-0-i2i-250628` |
| Audio restore (flourish) | GMI Cloud | _TBD (Phase 4)_ |
| Storage | Backblaze B2 (S3) | — |

_Model IDs are validated against the live GMI model library during setup and may be adjusted._

## Setup

```bash
# 1. Python 3.11+ environment
python -m venv .venv && ./.venv/Scripts/activate    # Windows
pip install -r backend/requirements.txt

# 2. Configure secrets
cp .env.example .env       # then fill in B2 + GMI values (see .env.example)

# 3. Validate connections
python scripts/test_b2.py          # round-trips a file through B2
python scripts/test_gmi.py         # calls the GMI vision model

# 4. Run the backend
uvicorn backend.app.main:app --reload
```

`.env` is git-ignored — never commit real keys. See `.env.example` for the full list.

## References

Regulatory, archival, and platform claims are documented with sources in [SOURCES.md](SOURCES.md) — including the Library of Congress LAMs call-to-action, EU AI Act Article 50, C2PA, and OAIS. Demo figures are illustrative until produced by a real run.

## License

MIT — see [LICENSE](LICENSE).
