# Trueprint — Master Build Plan

> **Provenance-preserving restoration for the world's archives.**
> AI restoration doesn't *recover* history — it *invents a plausible guess*. Trueprint is the first restoration pipeline that records, at generation time, exactly which pixels, frequencies, and details are **original**, **enhanced**, or **AI-fabricated** — and seals that record into a tamper-evident, hash-verified provenance manifest stored durably on Backblaze B2.

*Name: **Trueprint** — the *true print* of a restored image, carried with its verifiable *fingerprint*. Ties photographic "prints" to cryptographic hashes.*

Backblaze Generative Media Hackathon · Deadline **Aug 3, 2026, 5:00pm EDT** · Judging Aug 5–11 · Today: Jul 23 (~11 days)

---

## 0. The one-sentence pitch

Trueprint restores old photos and audio like the best AI tools — but unlike any of them, it hands you a **cryptographically verifiable authenticity map** proving what's real and what the AI invented, so archives, museums, journalists, and families can trust and *cite* the result. Built on Genblaze orchestration + Backblaze B2 as the system of record.

---

## 1. Why this wins (the strategic thesis)

- **Validated, uncrowded gap.** The Library of Congress issued a April 2026 *"Call to Action"* for exactly this: tools that distinguish "artistic colorization from historically verified restoration." Consumer tools (Remini, MyHeritage, Palette.fm) are provenance-blind toys. No product does provenance-first restoration. We're building the thing institutions are publicly asking for.
- **Bullseye on these judges.** They're Backblaze engineers who *built* Genblaze's provenance system, serving archives as core B2 customers. We make their hero feature the star, aimed at their core customer, around a problem their ecosystem is worried about.
- **Structurally not a wrapper.** The product isn't "a restored photo." It's the **authenticity record** — a region-level ledger of what's real vs. fabricated, only possible because we *orchestrate each step* (Genblaze) and *archive masters + derivatives + manifests durably* (B2). A single diffusion call cannot produce it.
- **Timely.** EU AI Act **Article 50** transparency obligations begin enforcement **Aug 2, 2026** (the day before the deadline). Our auto-generated disclosure statement is machine-readable AI-content labeling — we're compliant-by-design.

---

## 2. The 10/10 attack plan — how each criterion is maxed and exceeded

The four criteria are **equally weighted**. We engineer each to a defensible 10, plus an "exceed" move.

### 2.1 Real-World Utility → 10
- **Two audiences, one product.** (a) Institutions: archives, museums, libraries, historical societies. (b) Fast movers who need it *today*: genealogists/families, documentary filmmakers, journalists, estate lawyers. Same trust layer, immediate use.
- **Validated demand:** the LoC white paper is cited directly in our pitch.
- **Plain-language "Restoration Disclosure Statement"** auto-generated per asset — usable by a museum label, a documentary credit, or a family scrapbook caption.
- **Exceed:** align the disclosure with EU AI Act Article 50 machine-readable labeling → the tool isn't just useful, it's *compliance infrastructure*.

### 2.2 Use of Genblaze → 10
- **Multi-provider, multi-modal orchestration** across image *and* audio: analyze → repair/inpaint → face-restore → colorize → upscale → (audio) denoise/restore.
- **Fallback chains** (`fallback_models=[...]`) on every generative step → real reliability.
- **Parent→child lineage** (`.from_result(...)`) for iterative refinement passes.
- **Embedded, hash-verified manifests** (Genblaze's core) written into the output files.
- **Exceed — the novel bit:** **multi-provider corroboration for confidence.** We run colorization across 2–3 independent providers; where they *agree* on color = higher-confidence inference, where they *diverge* = flagged low-confidence "guess." This turns Genblaze's fan-out into an uncertainty-quantification engine — something no restoration tool does.

### 2.3 B2 Storage + Data Orchestration → 10
- **OAIS-style dual archive:** immutable **masters** (originals, never altered) + **derivatives** (restorations) + **manifests**, in a hierarchical, queryable key layout.
- **B2 Object Lock** on masters → provably immutable originals (tamper-evident archive, production-grade integrity).
- **Queryable catalog index** on B2 (lineage search, verify a hash, list a derivative's full step history).
- **Serve + verify from B2:** `genblaze verify` / `replay` reconstruct and validate any derivative straight from stored manifests.
- **Exceed:** the public **Verify page** reads the manifest embedded in *any* downloaded file and re-checks it against the B2 record → tamper detection that works even off-platform.

### 2.4 Production Readiness → 10 (the historic weak point — attacked directly)
- **Closed verification loop (LLM-as-judge):** after restoration, a vision model compares restored↔original and flags *historically implausible fabrications* (added people, altered sign text, invented objects). Flagged regions are marked high-risk or the step retries with conservative params. **This is the eval loop that turns a demo into a workflow.**
- **Fallbacks + retries + timeouts + cost caps** on every provider call.
- **Deployed working URL** with a seeded test account and sample assets (judging requirement).
- **Reproducibility:** every result is replayable/verifiable from its manifest.
- **Narrow, flawless scope** (see §4): photo restoration done impeccably end-to-end; audio as the multimodal flourish. Depth over breadth.

---

## 3. The technical core — the Authenticity Map (make-or-break)

This is the claim a sharp judge will probe. It must be **real and reproducible**, not theater. Our key insight:

> **Because we orchestrate every step, provenance is *recorded at generation time*, not reverse-engineered.** Each step knows exactly what it changed and where.

### 3.1 Three-class per-region classification
Every pixel of a restored image is classified as one of:
- **ORIGINAL** — signal preserved from the master (unchanged within tolerance).
- **ENHANCED** — original signal adjusted (denoise, contrast, sharpening) — real data, cleaned.
- **FABRICATED** — invented content with no original basis (inpainted damage, colorized chroma, hallucinated super-res detail, restored faces).

### 3.2 How each is computed (per operation, honestly)
| Operation | What's fabricated | How we know / mark it |
|---|---|---|
| **Damage inpainting** | Content filling holes/scratches/tears | The **damage mask** fed *into* the inpaint step *is* the fabrication region for that step — recorded directly. |
| **Colorization** of B&W | **All chroma** — by definition a guess | Original is grayscale → 100% of color is inferred. Honest, defensible statement. |
| **Super-resolution** | High-frequency detail absent in the master | Region where restored has structure the (upsampled) master lacks → frequency-domain diff. |
| **Face restoration** | Facial detail rebuilt from a face prior | The face-detection bbox/mask for that step = high-fabrication region. |
| **Denoise / clean** | Nothing invented — signal preserved | Marked **ENHANCED**, not fabricated. |

### 3.3 Composite map + confidence
- **Composite authenticity map** = union of per-step operation masks, each tagged with `{operation, model, provider, step_id}`. Exported as (a) a color-coded PNG overlay and (b) structured JSON in the manifest.
- **Confidence heatmap (the exceed move):** for inferred regions (color, detail), run 2–3 providers and compute per-pixel variance. Low variance = models agree = higher confidence; high variance = "the AI is guessing" = flagged. Stored as a grayscale confidence layer.
- **Summary stats:** `% original / % enhanced / % fabricated` + a plain-language sentence ("~38% of this image is AI-inferred; all color is inferred; one face was reconstructed").

### 3.4 Why this is bulletproof in the demo
We can *show the receipts*: toggle each step's mask, point to the exact damage mask that became the inpaint region, and show two colorizers disagreeing on a dress → that disagreement literally *is* the uncertainty. Reproducible from the manifest.

---

## 4. Scope — ruthlessly narrow (this is how we protect the 10s)

**IN (must be flawless):**
1. **Photo restoration** end-to-end: ingest → damage analysis → inpaint → face-restore → colorize (multi-provider) → upscale → authenticity map → manifest → B2.
2. **Authenticity view** UI (slider + toggleable heatmap + per-region tooltips + provenance panel).
3. **Provenance manifest** (Genblaze) + **B2 dual archive** + **public Verify page**.
4. **Audio restoration** as the *one* multimodal flourish (denoise/restore a crackly clip → its own mini authenticity/provenance record).
5. **Landing page** + **deployed app** + **seeded demo assets**.

**OUT (explicitly deferred — say so in the README as "roadmap"):**
- Video/film restoration (expensive, slow, flaky — name-drop as roadmap only).
- Batch/institutional dashboard (mention as roadmap).
- Full C2PA signing infra (we do C2PA-*aligned* export; full cert chain is roadmap).

> **Rule:** if a feature threatens the reliability of the core photo demo, it's cut. Depth beats breadth.

---

## 5. Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────┐     ┌──────────────┐
│  Frontend   │     │            Backend (FastAPI, Python)       │     │ Backblaze B2 │
│ Next.js +   │────▶│  ┌────────────────────────────────────┐   │     │ (S3 compat)  │
│ Tailwind    │     │  │ Genblaze Pipeline Orchestrator     │   │     │              │
│             │     │  │  step: analyze (vision LLM)        │   │────▶│ masters/     │
│ - Landing   │◀────│  │  step: inpaint  (+fallbacks)       │   │     │  (ObjectLock)│
│ - App/Upload│ SSE │  │  step: face-restore                │   │     │ derivatives/ │
│ - Auth View │prog │  │  step: colorize ×N (corroboration) │   │     │ index/       │
│ - Verify    │     │  │  step: upscale                     │   │     │ manifests    │
└─────────────┘     │  │  step: audio-restore (flourish)    │   │     └──────────────┘
                    │  └────────────────────────────────────┘   │
                    │  Authenticity engine (OpenCV/numpy):      │
                    │   op-masks → composite map → confidence   │
                    │  LLM-judge verification loop              │
                    │  Manifest assembler (Genblaze) + C2PA-ish │
                    └──────────────────────────────────────────┘
```

- **Genblaze does the orchestration + lineage + manifest.** Our code adds the authenticity engine + verification loop + B2 archive layout on top.
- **Backend is Python** (Genblaze is a Python SDK) — FastAPI, async, Server-Sent Events for live step progress in the UI.

---

## 6. The Genblaze pipeline (concrete)

Providers via **GMICloud** (hackathon credits) plus others the SDK supports. Exact model IDs get pinned during Phase 1 against the live model library; the *shape* is fixed:

```python
# pseudocode — real API pinned in Phase 1
result = (
    Pipeline("trueprint-restore")
    .step(analyze,   provider=GMICloudChat,  model="<vision-llm>",   # damage + scene description, returns masks
          fallback_models=["<alt-vision>"])
    .step(inpaint,   provider=GMICloudImage, model="<img2img>",      # damage mask → repaired
          fallback_models=["<alt-img2img>"], modality=IMAGE)
    .step(face,      provider=GMICloudImage, model="<face-restore>", modality=IMAGE)   # conditional on faces
    .fanout(colorize, providers=[P1, P2, P3], model=..., modality=IMAGE)  # corroboration
    .step(upscale,   provider=..., model="<super-res>", modality=IMAGE)
    .step(audio,     provider=ElevenLabs/MiniMax, model="<denoise>", modality=AUDIO)   # flourish
    .run(sink=B2ObjectStorageSink(...), timeout=..., retries=...)
)
```

- **Fallbacks** on each step = reliability + criterion 2.2.
- **`.from_result()`** links refinement passes (e.g., a second, gentler inpaint) → lineage graph.
- **Fan-out colorize** feeds the confidence heatmap.
- **Manifest** auto-produced, hash-verified, embedded into the output PNG/MP3.

### 6.1 Fallback/degradation strategy
If a model/provider is down or a step fails after retries: mark that step **skipped** in the manifest (honest provenance), continue the pipeline, and surface it in the UI ("upscale unavailable — skipped, recorded"). The archive never lies.

---

## 7. Provenance manifest (what we store)

Genblaze's native manifest, extended with our authenticity block. C2PA-*aligned* field names for interop.

```jsonc
{
  "asset_id": "…",
  "master": { "sha256": "…", "b2_key": "masters/…/original.tif", "object_lock": true },
  "derivative": { "sha256": "…", "b2_key": "derivatives/…/restored.png" },
  "pipeline": [
    { "step": "inpaint", "provider": "…", "model": "…", "input_sha256": "…",
      "output_sha256": "…", "operation": "FABRICATED", "region_mask": "steps/…/mask.png",
      "params": {…}, "duration_ms": …, "status": "ok" }
    // … one per step, in order
  ],
  "authenticity": {
    "pct_original": 0.55, "pct_enhanced": 0.07, "pct_fabricated": 0.38,
    "map_png": "authenticity_map.png",
    "confidence_png": "confidence.png",
    "notes": ["All color is AI-inferred.", "1 face reconstructed.", "Sign text region: low confidence."]
  },
  "verification": { "llm_judge": "passed_with_flags", "flags": ["dress color low-agreement"] },
  "disclosure_statement": "This image was digitally restored with AI. ~38% of pixels are AI-inferred, including all color and one reconstructed face. Original master preserved unaltered (hash …).",
  "genblaze_version": "…", "created": "…", "signature": "…"
}
```

- Embedded into the output file (Genblaze `Mp4Handler`/PNG handler) **and** stored alongside in B2.
- `disclosure_statement` doubles as EU AI Act Article 50 machine-readable label.

---

## 8. Backblaze B2 layout (the system of record)

```
b2://trueprint/
  masters/{asset_id}/original.{ext}        # immutable; B2 Object Lock (compliance/retention)
  masters/{asset_id}/master.json           # ingest metadata + sha256
  derivatives/{asset_id}/{run_id}/restored.png
  derivatives/{asset_id}/{run_id}/authenticity_map.png
  derivatives/{asset_id}/{run_id}/confidence.png
  derivatives/{asset_id}/{run_id}/manifest.json
  derivatives/{asset_id}/{run_id}/steps/{n}_{op}/{input,output,mask}.png   # replay/audit
  index/catalog.jsonl                      # append-only lineage catalog (queryable)
```

- **Object Lock** on `masters/` → originals are provably never altered.
- **catalog.jsonl** enables lineage queries ("show every derivative of asset X", "find all runs that used model Y", "verify hash Z").
- Demonstrates *store + organize + serve + manage + provenance* — the full criterion-2.3 sweep.

---

## 9. Frontend (Next.js + Tailwind)

### 9.1 Landing page (`/`) — **yes, we have one, and it's a weapon**
- Hero: *"AI restoration invents history. Trueprint proves what's real."*
- The problem, with the **LoC Call to Action** quote as social proof.
- 3-panel "how it works": Restore → Reveal (authenticity map) → Verify.
- Live before/after slider with the heatmap toggle (real sample).
- Trust badges: "Provenance on Backblaze B2 · Genblaze orchestration · EU AI Act Article 50 aligned · C2PA-compatible."
- CTA → app. Footer: GitHub, demo video, verify link.
- **Purpose:** in 5 seconds a judge reads "this is production infrastructure, not a toy."

### 9.2 App (`/app`)
- Upload (drag-drop; seeded sample assets for one-click demo).
- **Live pipeline progress** via SSE — each Genblaze step lights up with its provider/model (visibly multi-provider, multi-modal).
- **Authenticity View:** O↔R comparison slider; toggle the fabrication heatmap; toggle the confidence heatmap; hover a region → "AI-fabricated · colorize · models disagree · low confidence."
- **Provenance panel:** ordered steps, models, hashes, `% original/enhanced/fabricated`, disclosure statement, LLM-judge flags.
- Download restored file (manifest embedded) + a one-click **Provenance Certificate** (PDF).

### 9.3 Verify page (`/verify`) — the trust endpoint
- Drop any file (even one downloaded elsewhere) → extract embedded manifest → re-verify hashes against the B2 record → render full provenance + a green/red **tamper verdict**. Works off-platform. Demo mic-drop.

---

## 10. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | **Genblaze** (`genblaze-core`, `-s3`, `-gmicloud`, provider adapters) | Required; hero feature |
| Backend | **Python + FastAPI**, async, SSE | Genblaze is Python |
| Auth-map engine | **OpenCV, NumPy, Pillow** | Real diff/mask/frequency work |
| Storage | **Backblaze B2** (S3 API) via `genblaze-s3` | Required; system of record |
| Providers | **GMICloud** (credits) + fallbacks | Image/audio/vision models |
| Frontend | **Next.js + Tailwind**, deploy **Vercel** | Fast, credible, free |
| Backend host | **Render / Railway / Fly.io** | Long-running pipeline jobs |
| Cert export | **reportlab** (PDF), C2PA-aligned JSON | Interop / polish |

---

## 11. Build phases (Jul 23 → Aug 3)

- **Phase 0 — Setup (Day 1, Jul 23–24):** B2 bucket + Object Lock, GMICloud creds, Genblaze install, repo scaffold (backend + frontend), pin real model IDs against the live library, gather 6–8 public-domain damaged sample photos + 1–2 archival audio clips. **Star the Genblaze repo.**
- **Phase 1 — Core pipeline (Day 2–4):** ingest → analyze → inpaint → colorize (single provider) → manifest → B2 write. One photo, end-to-end, ugly but real.
- **Phase 2 — Authenticity engine (Day 4–6):** operation masks → composite map; multi-provider colorize + confidence heatmap; LLM-judge verification loop; fallback chains; catalog index.
- **Phase 3 — Frontend app (Day 6–8):** upload, SSE progress, Authenticity View, provenance panel, Verify page.
- **Phase 4 — Multimodal + landing (Day 8–9):** audio restoration flourish; landing page; certificate PDF.
- **Phase 5 — Harden + deploy (Day 9–10):** error handling, cost caps, timeouts, seed demo account, deploy FE+BE+B2, dry-run the full demo.
- **Phase 6 — Submit (Day 10–11):** record 3-min demo video, write README (setup + B2/Genblaze usage + models list), grant `b2genblaze` repo access if private, file **SDK feedback issue** (Feedback Prize — free bonus), submit on Devpost **before Aug 3, 5pm EDT**.

> Buffer built in. If we slip, cut audio (Phase 4) first — photo core must ship.

---

## 12. Demo video script (~3 min — judged, keep tight)

1. **0:00–0:25** — Problem. A stunning AI-colorized 1920s photo. "Beautiful. But is that dress color *real*? No — the AI guessed. And once this circulates, the record is corrupted. The Library of Congress is asking for a fix." 
2. **0:25–0:40** — Landing page; one line on the mission + the B2/Genblaze/EU-AI-Act badges.
3. **0:40–1:40** — Upload a damaged photo. Watch the **Genblaze pipeline** run live — call out the multiple providers/models and the fallback. Result appears.
4. **1:40–2:20** — **Authenticity View.** Toggle the heatmap: "Everything red is AI-fabricated. All color is inferred. This face was rebuilt." Toggle confidence: "Two colorizers disagreed on the dress — so we flag it as a guess." Show the disclosure statement.
5. **2:20–2:45** — **B2 + Verify.** Show the dual archive on B2 (immutable master + derivative + manifest). Download the file, go to **/verify**, drop it in → green "verified, untampered." Tamper the file → red.
6. **2:45–3:00** — Close: "Restoration you can *cite*. Provenance on Backblaze B2, orchestrated by Genblaze." Audio clip flash to prove multimodal.

---

## 13. Devpost submission checklist

- [ ] Working app URL (with seeded test account + sample assets, no restrictions).
- [ ] Public GitHub repo (or private + grant `https://github.com/b2genblaze` access) with README: setup, **how it uses B2**, **how it uses Genblaze**, **providers/models list**.
- [ ] ~3-min demo video on YouTube/Vimeo (public), no copyrighted music, no third-party marks.
- [ ] Text description: features, B2 + Genblaze usage, models used.
- [ ] **Feedback issue** filed on the Genblaze repo (Feedback Prize eligibility).
- [ ] Submitted before **Aug 3, 2026, 5:00pm EDT**.

---

## 14. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Authenticity map looks like theater | Kills trust premise | Record masks at generation time; show the receipts live; reproducible from manifest |
| Restoration models slow/flaky/costly | Bad demo, blown budget | Fallback chains, timeouts, cost caps, pre-warmed seeded results for the video, small image sizes |
| Scope creep (video/batch) | Everything half-works | Hard scope freeze (§4); cut audio before photo |
| No suitable restoration model in Genblaze providers | Core blocked | Phase-0 spike to pin models; fallback to img2img with masks; worst case use a hosted restore model behind a Genblaze custom provider |
| B2 Object Lock config friction | Lost integrity story | Enable at bucket creation Day 1; fallback to versioning + hash if needed |
| Judges skip testing | Miss the wow | Front-load everything into the 3-min video and landing page |

---

## 15. "Exceed expectations" — beyond 10/10

- **Multi-provider confidence heatmap** — genuinely novel uncertainty quantification; nobody in restoration does this.
- **C2PA-aligned export** — interoperable with the industry standard, not just our own manifest.
- **EU AI Act Article 50 disclosure** — the tool ships regulatory-grade labeling on Aug 2 enforcement day.
- **B2 Object Lock immutable masters** — production-grade archival integrity, not a demo hack.
- **Off-platform tamper detection** via the Verify page — trust that travels with the file.
- **Provenance Certificate PDF** — a citable artifact a museum or court could file.
- **SDK feedback issue** — bags the Feedback Prize (mentorship) alongside the overall prize.

---

## 16. Immediate next actions (to start now)

1. Create Backblaze B2 account + bucket (`trueprint`) with **Object Lock** enabled; grab S3 keys.
2. Create GMICloud account + submit credits form; note available restore/vision/image/audio model IDs.
3. `pip install genblaze genblaze-s3 genblaze-gmicloud …`; **star the Genblaze repo**; run the hello-world pipeline to a B2 write.
4. Scaffold repo: `/backend` (FastAPI + Genblaze), `/frontend` (Next.js), `/plan` (this file), `/assets` (samples).
5. Collect 6–8 public-domain damaged photos + 1–2 archival audio clips (Library of Congress / Wikimedia public domain).
6. Phase-1 spike: one photo, analyze→inpaint→colorize→manifest→B2, end-to-end.

---

*This plan is engineered so that every one of the four equally-weighted criteria lands at a defensible 10, with a novel technical contribution (the authenticity map + multi-provider confidence) and a compliance/interop story that pushes past the ceiling. The single highest-leverage thing we build is the authenticity map — protect it, prove it, and the grand prize is in range.*
