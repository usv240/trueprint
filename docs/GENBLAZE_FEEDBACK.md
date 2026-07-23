# Genblaze SDK — feedback (draft for review before posting)

> Draft of the issue we'll file at https://github.com/backblaze-labs/genblaze/issues
> for the hackathon Feedback Prize. **Not yet posted.** Everything below is from
> building Trueprint (image restoration) on `genblaze` 0.4.4 / `genblaze-gmicloud`
> against GMI Cloud. Ordered by impact.

---

**Title:** Image-provider footguns on GMICloud: shared base-URL env var, stale bundled registry, and unknown-model payload mapping

**Environment:** `genblaze` 0.4.4, `genblaze-core` 0.3.7, `genblaze-s3` 0.3.6, `genblaze-gmicloud` 0.3.4, Python 3.12, Windows. Provider: GMI Cloud (chat + image request-queue).

Thank you for the SDK — the Pipeline + manifest + B2 sink model is exactly right, and provenance-first design is the reason we chose it. Four issues cost us real debugging time; each has a concrete suggestion.

## 1. Chat and image providers share `GMI_BASE_URL`, but need different base URLs (highest impact)
`GMICloudImageProvider` resolves `base_url` as `arg → os.environ["GMI_BASE_URL"] → _DEFAULT_BASE_URL`. The **chat** API lives at `https://api.gmi-serving.com/v1`, but the **image request-queue** lives at `https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey`. A perfectly reasonable setup — set `GMI_BASE_URL` to the (documented, OpenAI-compatible) chat URL — then silently breaks the image provider: the family probe `POST {base}/requests` hits `…/v1/requests` → 404 → **every image/video/audio model reports `DEAD`/`NOT_FOUND`**. It looks exactly like an account-entitlement failure, so we spent a long time chasing the wrong thing.

**Suggestion:** use provider-specific env vars (`GMI_CHAT_BASE_URL`, `GMI_IMAGE_BASE_URL`) and/or refuse to apply a `…/v1`-shaped base URL to the request-queue provider with a clear error. At minimum, document that the two surfaces have different base URLs.

## 2. Bundled image registry is stale vs the live GMI catalog
`build_image_registry()` ships `reve-edit-*` and `reve-remix-*` (now `NOT_FOUND` upstream) and omits models that are live and callable today (`gpt-image-2-edit`, `bria-fibo-restore`, `seedream-5.0-*`, `hunyuan-image-to-image`, …). Worse, `validate_model()` returns `ok_authoritative` for a slug that is in the registry but **404s on real submit** (`seededit-3-0-i2i-250628`: "you do not have access"), so preflight passes and the job fails at dispatch.

**Suggestion:** a discovery/refresh path from the upstream catalog, or clearly separate "known in bundled registry" from "verified callable for this key" in `ValidationResult`. The empty-payload probe (`400 → LIVE`) is a good signal but only proves the slug's *param schema* exists, not that the key can dispatch it.

## 3. Unknown-model payload mapping is rejected by the request queue
For models not in the registry (e.g. `gpt-image-2-edit`, "permissive fallback applies"), the generic `prepare_payload` produces a body the queue rejects with `400 "Generation rejected; please review the prompt and parameters"`. The queue actually wants a small, flat `{ "prompt": ..., "image": <url> }`. We solved it by subclassing `GMICloudImageProvider` and overriding `prepare_payload`, which works well and keeps the Pipeline/manifest machinery — but it's non-obvious.

**Suggestion:** for unknown image models, emit a minimal pass-through payload (`prompt` + first input asset URL under a documented key like `image`), and/or document the override recipe. A per-model param-mapping hook that doesn't require subclassing would be ideal.

## 4. Minor: presigned input URLs warn about unstable manifest hashes
Passing an `Asset(url=<B2 presigned URL>)` logs a warning that the canonical hash/step-cache key will be unstable because the URL rotates. Understood, but for the very common "upload to B2 → presign → feed to model" flow it's noisy. The warning helpfully suggests precomputing `sha256`; making that a first-class `Asset(..., sha256=...)` path (it exists) plus a doc example would smooth this.

## What worked really well
- `S3StorageBackend.for_backblaze(...)` + `ObjectStorageSink` + `ObjectLockConfig` — clean, and Object Lock on masters is exactly what an archival product needs.
- `Pipeline.step(...).run(...)` ergonomics and the `PipelineResult` / `Manifest` model.
- The provenance manifest concept is the core of our product; please keep investing there (e.g. first-class support for recording *provider refusals* in the manifest — we now log content-policy declines as provenance, and SDK support would help).

Happy to share the Trueprint repo (a provenance-preserving photo-restoration app) if useful as a reference integration.
