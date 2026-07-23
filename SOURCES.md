# Sources, Citations & IP Safety

This file documents every external claim, statistic, standard, and reference Trueprint relies on — where it came from, how confident we are in it, and how it's used. It is the single source of truth for citations that must also appear in the **README** and (in paraphrased, attributed form) on the **landing page**.

**Accessed:** 2026-07-23. **Rule we follow:** never present a synthesized/paraphrased sentence as a verbatim quotation; label paraphrases as such; mark demo numbers as illustrative.

---

## 1. Reference list

| # | Claim / how we use it | Source | Verification status |
|---|---|---|---|
| R1 | Library of Congress "call to action" urging libraries/archives/museums to keep AI-affected content authentic, transparent, verifiable from creation through access. Used as the motivating problem statement (landing quote bar, README, pitch). | *Content Authenticity and Provenance in the Age of AI: A Call-to-Action for the LAMs Community*, The Signal, Library of Congress, 2026 — [blog](https://blogs.loc.gov/thesignal/2026/04/content-authenticity-and-provenance-in-the-age-of-artificial-intelligence-a-call-to-action-for-the-libraries-archives-and-museums-community/) · [PDF](https://blogs.loc.gov/thesignal/files/2026/04/Call-to-Action-CAP-for-LAMs.pdf) | **Document confirmed** (title, ~2026, LoC/The Signal, co-author Kate Murray). **Exact wording NOT independently verified** (page returns 403 to automated fetch). → We use a **labeled paraphrase**, never a verbatim quote. |
| R2 | AI colorization/restoration *invents plausible detail* rather than recovering true historical color; risk of silently corrupting the documentary record. Used in the "Problem" section. | Reporting/analysis on AI colorization authenticity, e.g. [AI Understanding — Colorizing Historical Photos](https://aiunderstanding.org/learn/ai-in-colorizing-historical-photos-and-film); commentary "How AI Photo Restoration is Silently Erasing Our History" (Medium). | **Widely-supported characterization**, not a single authoritative stat. Framed as reasoning, not a hard figure. |
| R3 | EU AI Act **Article 50** transparency obligations begin enforcement **Aug 2, 2026**; require machine-readable disclosure of AI-generated/manipulated media; fines up to ~3% global turnover; extraterritorial reach. Used for the compliance angle. | [Pebblous — EU AI content labeling & Article 50](https://blog.pebblous.ai/blog/eu-ai-content-labeling-article-50-provenance/en/); [TechTimes, 2026-07-21](https://www.techtimes.com/articles/321174/20260721/eu-finalizes-ai-disclosure-rules-watermarking-mandate-outpaces-technology.htm) | **Corroborated across multiple sources.** Article 50 + Aug 2 2026 date consistent. Penalty %/scope stated conservatively ("up to ~3%"). |
| R4 | **C2PA** is a cryptographically signed content-provenance standard backed by Adobe, BBC, New York Times, Microsoft and others; the mature path to machine-readable AI labeling. We claim manifest *alignment*, not certification. | [C2PA overview / RightsDocket](https://www.rightsdocket.com/insights/what-is-c2pa); [SoftwareSeni — EU AI Act & C2PA](https://www.softwareseni.com/eu-ai-act-and-content-provenance-regulations-making-c2pa-urgent-in-2026/) | **Well-established.** We say "C2PA-aligned," not "C2PA-certified" (we do not ship a full signing cert chain in the hackathon build). |
| R5 | **OAIS** is the reference model for long-term digital preservation (distinct masters / derivatives / metadata). Used to describe the B2 archive layout. | ISO 14721 (OAIS) — standard reference. | **Established standard.** |
| R6 | **Backblaze B2 Object Lock** makes stored objects immutable for a retention period; B2 is S3-compatible. Used for "immutable masters." | [Backblaze B2 docs](https://www.backblaze.com/cloud-storage) | **Vendor feature, confirmed.** |
| R7 | **Genblaze** capabilities: unified multi-provider Pipeline API; fallback chains; parent→child lineage; SHA-256 provenance manifests embedded into media; `verify`/`replay`/`extract`. Basis for our orchestration/provenance claims. | [Genblaze repo](https://github.com/backblaze-labs/genblaze) | **Confirmed from official repo.** Pin exact API + model IDs during Phase 1. |
| R8 | Synthetic-data / restoration incumbents named for competitive context (Remini, MyHeritage, Palette.fm as provenance-blind consumer tools; Parallel Domain, Rendered.ai, NVIDIA/Gretel in synthetic data — *not* used in final direction). | Vendor sites; [Edge AI+Vision Alliance](https://www.edge-ai-vision.com/2025/07/synthetic-data-for-computer-vision/); [AI Magazine](https://aimagazine.com/news/top-10-synthetic-data-tools) | **Factual/company references.** We characterize their *provenance* gap accurately; no disparaging false claims. |
| R9 | The **Ansel Adams Trust publicly condemned an undisclosed AI-colorized photo** (2026) — used as a real-world proof point that undisclosed AI colorization causes genuine harm/backlash. | [AI Weekly](https://aiweekly.co/alerts/ansel-adams-trust-blasts-gallery-over-ai-colorized-photo) | **Reported event.** Cited as an example; we state it as reported, not as legal fact. |
| R10 | Emerging GLAM-sector AI standards: **AI4LAM**, the **FLAME** preparedness guidelines (Feb 2026), and the **UVA Archival AI Protocol** — used to support "institutions are formalizing AI-provenance practice." | [The Signal / LoC AI4LAM](https://blogs.loc.gov/thesignal/2026/06/library-of-congress-and-ai4lam/); [UVA Library](https://library.virginia.edu/news/2026/protecting-what-remains-introducing-uva-archival-ai-protocol) | **Corroborated across sources.** |
| R11 | **C2PA** Content Credentials — the standard we embed and sign; the `c2pa-python` library and `digitalSourceType: compositeWithTrainedAlgorithmicMedia` for AI edits. | [contentauth/c2pa-python](https://github.com/contentauth/c2pa-python); [C2PA usage docs](https://opensource.contentauthenticity.org/docs/c2pa-python/docs/usage/) | **Official library/spec.** Our dev cert is self-signed → verifiers report "untrusted signer," disclosed honestly. |

> Several summaries above were gathered via web search with an AI summarizer. Where a claim is load-bearing for the pitch (R1, R3), treat the table's "verification status" as binding: **verify wording at the primary source before quoting; otherwise paraphrase and attribute.**

---

## 2. Where each citation must appear

- **README** — a "References" section reproducing R1–R7 with links; a "Providers & models used" list (hackathon requirement); a "How we use B2 and Genblaze" section.
- **Landing page** — R1 as a labeled paraphrase with a source link (done); footer pointer to this file; badges (C2PA-aligned, EU AI Act) are directional claims backed by R3/R4.
- **Demo video / description** — when we state the LoC or EU AI Act framing, say "referenced in our sources," not a hard quote.

---

## 3. IP & legal safety checklist

**Our code & submission**
- [ ] All code is **original work** by the team (hackathon requirement). Any open-source we build on is used per its license and we **add substantial new functionality** on top (required by the rules).
- [ ] Respect open-source licenses of Genblaze and every dependency; keep a `LICENSES`/`NOTICE` as needed. Confirm Genblaze's license before redistributing any of its code.
- [ ] Repo README includes setup instructions; if the repo is private, **grant `https://github.com/b2genblaze` access** for judging.

**Sample media (critical — no copyrighted images/audio)**
- [ ] Every demo/sample asset is **public domain or openly licensed**, with attribution recorded. Preferred sources:
  - Library of Congress — Prints & Photographs (no known restrictions)
  - U.S. National Archives (NARA) — public domain
  - Wikimedia Commons — filter to **CC0 / Public Domain**
  - Flickr **Commons** ("no known copyright restrictions")
- [ ] Keep an `assets/CREDITS.md` listing each file, its source URL, and license.
- [ ] Do **not** upload personal photos of real identifiable people without rights/consent for a public demo.

**Demo video (Devpost rules)**
- [ ] **No copyrighted music** unless licensed; use CC0 / royalty-free or silence.
- [ ] **No third-party trademarks/logos** shown without permission (careful with provider logos — prefer plain text names).
- [ ] ≤ 3 minutes, public on YouTube/Vimeo, in English.

**Honesty / claims hygiene**
- [ ] No verbatim quotes we haven't verified at the primary source (see R1).
- [ ] Demo manifest numbers (e.g., "38% fabricated") are **illustrative** and labeled as such until produced by a real run.
- [ ] "C2PA-aligned," not "C2PA-certified." "Article 50-ready," not "legally compliant / certified."
- [ ] Competitor mentions stay factual (their lack of provenance manifests) — no false or disparaging statements.

**Data & keys**
- [ ] Secrets (B2 keys, provider API keys) live in `.env`, which is **git-ignored** and never committed. Provide `.env.example` with blank placeholders.
- [ ] Test/judge account credentials in the submission are scoped and safe to share.

---

*Keep this file updated as new sources are added. If a claim can't be verified, either verify it or soften it to what the evidence supports.*
