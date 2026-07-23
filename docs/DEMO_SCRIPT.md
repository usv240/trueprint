# Trueprint — 3-minute demo video script

Target: **≤ 3:00**, screen recording + voiceover. No copyrighted music (use silence or a
CC0 track). No third-party logos on screen beyond plain text names. Record at 1080p.

**Prep:** backend running; browser at the landing page; a second tab on `/app`; have the
downloaded `restored.png` ready for the verify beat; a text editor with a copy of the
restored file for the "tamper" beat (or flip one byte).

---

### 0:00–0:20 · The hook (problem)
*Screen: the colorized Lincoln fills the frame.*
> "This is a colorized photo of Abraham Lincoln. It's beautiful. But here's the problem — the AI didn't *recover* these colors. It *invented* them. His skin, his eyes, the color of his tie — all a plausible guess. And once a fake like this circulates, the historical record is quietly corrupted. The Library of Congress is literally asking for a fix."

### 0:20–0:35 · What Trueprint is
*Screen: scroll the landing page hero + the B2/Genblaze/EU-AI-Act badges.*
> "Trueprint restores old photos like the best AI tools — but it also proves exactly what's real and what the AI invented, with a verifiable record stored on Backblaze B2."

### 0:35–1:20 · Restore (show the pipeline = Genblaze)
*Screen: `/app`. Pick Lincoln, tick "Run live", click Restore. Let the steps light up (speed-ramp the wait to keep it tight).*
> "I'll restore this photo live. Trueprint runs a Genblaze pipeline: it ingests the original as an immutable master on B2… a vision model reads the photo and flags which colors can't be known… then it colorizes it — twice, independently — through Genblaze."
*Steps complete; restored image appears.*
> "Here's the restoration. And now the part nobody else does."

### 1:20–2:05 · Reveal (the authenticity map — the wow)
*Screen: toggle to "Authenticity", then "Confidence".*
> "This is the authenticity view. The structure is one hundred percent preserved — we lock the AI's color onto the *original's* luminance, so we never invent the photo itself. Only color is inferred."
*Toggle "Confidence" — the teal/vermilion heatmap.*
> "And this is the confidence map. We colorized twice and compared. Teal is where the two agree — grounded. Vermilion is where they *disagree* — that's the AI guessing. Look: it lights up on the wrinkles, the hairline, the old plate scratches. Nothing else in restoration shows you this."
*Point at the provenance panel.*
> "Every choice is disclosed in plain language — 'colors of the suit and tie are guesses' — with the models used and cryptographic hashes."

### 2:05–2:45 · Prove it (C2PA + B2 + Verify)
*Screen: the provenance panel — point at the green "C2PA Content Credential embedded" badge. Click "Download signed (C2PA)."*
> "Every restoration is signed with a real, embedded C2PA Content Credential — the industry standard behind Adobe, the BBC and the New York Times. It declares the AI color edit in machine-readable form, which is exactly what the EU AI Act now requires."
*Screen: click the Collection tab — the B2 ledger grid, each card showing color %, confidence, ✓ faithful, C2PA.*
> "And every restoration is a durable record on Backblaze B2 — a queryable provenance ledger of masters, restorations, and signed manifests. This is the system of record."
*Screen: drop the signed file into contentcredentials.org/verify (or our /verify).*
> "I can verify it anywhere — here in Adobe's own Content Credentials tool — and it shows what AI did."
*Our `/verify`: green.* Then flip one byte / drop a different file → *red.*
> "Trust travels with the file. Tamper with even one byte…" *(red)* "…and it's caught."

### 2:40–3:00 · Close
*Screen: back to the authenticity view.*
> "Trueprint: restoration you can actually cite. Faithful by construction, honest about every guess, and provable on Backblaze B2 — orchestrated end to end with Genblaze. Thanks for watching."

---

## Recording tips
- **Speed-ramp** the ~90s live run to ~10s (or pre-run once, then start the recording just before completion). Keep the *stages visibly lighting up* — that's the Genblaze story.
- Use the **instant cached** samples for the reveal/verify beats so nothing stalls on camera.
- Keep the cursor deliberate; pause 1s on the confidence heatmap — it's the money shot.
- End screen: repo URL + "Backblaze B2 · Genblaze · GMI Cloud".
