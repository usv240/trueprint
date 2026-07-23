# Trueprint — Devpost submission text

**Tagline:** AI restoration invents history. Trueprint proves what's real — provenance-preserving photo restoration on Backblaze B2 + Genblaze.

---

## Inspiration
AI photo restoration is everywhere, but it doesn't *recover* the past — it *invents a plausible guess*. A colorized 1920s photo isn't the real color of that dress; it's a beautiful fabrication. When those versions circulate, the documentary record is quietly corrupted — and no one can tell which parts were real. In 2026 the Library of Congress published a "Call-to-Action" for exactly this: tools that keep AI-affected collections authentic and verifiable. Consumer restoration apps are provenance-blind. We built the thing institutions are asking for.

## What it does
Give Trueprint a historical photo and it:
1. **Analyzes** it with a vision model (describes the scene, dates it, flags damage and *which colors are unknowable*).
2. **Restores** it — colorization is **luminance-locked**: we take the AI's color but keep the *original's* luminance, so the result is provably faithful in structure. We never invent the photo itself.
3. **Reveals** the truth on two honest axes — **structure** (kept/enhanced/fabricated) vs **color** (100% inferred) — plus a **confidence heatmap** built by colorizing multiple times and measuring where the results agree (grounded) vs disagree (a guess).
4. **Proves** it: every restoration is signed with a **real, embedded C2PA Content Credential** (readable in Adobe Content Credentials / any C2PA viewer) declaring the AI color edit as `compositeWithTrainedAlgorithmicMedia` — the **EU AI Act Article 50** machine-readable AI marking — plus a hash-verified provenance manifest on Backblaze B2 next to an immutable master. A **Verify** page checks a file two ways: it reads the embedded C2PA credential (trust travels in the file) *and* hashes it against the B2 catalog. Even provider *refusals* (an image model declining a photo by policy) are recorded as provenance rather than hidden.

## How it uses Backblaze B2
B2 is the **system of record**, not a blob store:
- **OAIS-style dual archive:** `masters/` (immutable originals, **Object Lock**) + `derivatives/` (restorations, authenticity maps, confidence maps) + `manifest.json` per run + per-step artifacts, in a hierarchical, queryable key layout.
- **Append-only lineage catalog** (`index/catalog.jsonl`) powers the Verify tamper-check by hash.
- Results are served and verified straight from B2 via presigned URLs; a `precache` map on B2 makes sample restorations load instantly.

## How it uses Genblaze
- Every restoration runs through the Genblaze **`Pipeline`** (steps, inputs, provider abstraction) with `S3StorageBackend.for_backblaze(...)`, `ObjectStorageSink`, and `ObjectLockConfig`.
- We wrote a **custom provider** (`TrueprintImageProvider`, subclassing `GMICloudImageProvider`) that emits the correct request-queue payload for the image model while keeping Genblaze's Pipeline / **Manifest** / lineage machinery.
- **Multi-sample corroboration:** independent colorizations are compared to quantify per-pixel confidence.
- Genblaze **provenance manifests** from each run are folded into Trueprint's own hash-verified manifest and archived on B2.

## Providers & models used
- **GMI Cloud — `google/gemini-3.6-flash`** (multimodal): damage/scene analysis + uncertain-color detection, via the OpenAI-compatible chat API.
- **GMI Cloud — `gpt-image-2-edit`** (instruction image-to-image): colorization, run twice per image for the confidence map, via the request queue.
- Evaluated and configurable in `.env`: `bria-fibo-restore`, `hunyuan-image-to-image`.
- **Backblaze B2** (S3-compatible): storage / provenance / system of record.
- Authenticity engine: OpenCV + NumPy (LAB luminance-lock, multi-sample confidence, region classification).

## How we built it
FastAPI backend (upload, **live SSE progress**, result, verify) serving a vanilla-JS app + landing page; Genblaze + `genblaze-gmicloud` + `genblaze-s3` for orchestration and B2; an OpenCV/NumPy authenticity engine. Restorations run in a background thread and stream progress to the browser.

## Challenges we ran into
- GMI's chat and image APIs use **different base URLs** but share one env var in the SDK — a misconfiguration made *every* media model look dead. Root-caused it and filed detailed SDK feedback.
- The bundled model registry was **stale** vs the live catalog; we pivoted to models that are actually callable and made them `.env`-configurable.
- `gpt-image-2-edit` **declines photos with minors** (provider policy). We turned that into a feature: refusals are recorded as provenance and the pipeline degrades gracefully.

## Accomplishments we're proud of
The **confidence heatmap** — real, computed from independent generations, lighting up exactly where the AI is guessing — is something no consumer restoration tool shows. "Structure 100% preserved, color 100% inferred" is not marketing; it's computed and provable. And our **LLM-as-judge faithfulness check** caught a real ghosting artifact in our own pipeline during development and drove the fix (aspect-matched generation) — the QA loop earning its keep. The whole thesis is timely: in 2026 the **Ansel Adams Trust publicly condemned an undisclosed AI-colorized photo** — exactly the harm provenance-first restoration prevents.

## Faithfulness &amp; honesty features
- **Documented vs. guessed color:** the vision model separates colors that are *historically knowable* (flags, insignia) from those that are *unknowable guesses* — surfaced in the disclosure.
- **LLM-as-judge:** every restoration is scored for implausible fabrication (added/removed/altered content) as a Genblaze `EvaluationResult`.
- **Refusals recorded:** content-policy declines are written into provenance, not hidden.

## What's next
A CA-issued signing cert on the C2PA trust list (dev build self-signs), generative damage-repair via masked inpainting models, audio restoration, IIIF/PREMIS metadata export, and a batch mode for institutional archives.

## Links
- **Repo:** https://github.com/usv240/trueprint
- **Live app:** _(after deploy)_ · **Demo video:** _(link)_
