# Rename Audit: "CSA" → "DRRA" (2026-08-12)

Method label retired: bare "CSA" (no expansion was used in any doc; acronym collides with DeepSeek-V4's Compressed Sparse Attention) → **"DRRA" / "Dual-Rate Routed Attention"** (expansion introduced by this rename). Prose and doc titles only.

## Per-file replacement counts (bare "CSA" → "DRRA"; "Dual-Rate Routed Attention" expansion introduced on first use)

| File | CSA→DRRA | Notes |
|---|---|---|
| RESULTS.md | 8 | Definition sentence + 3 table-row + 4 prose; expansion introduced by this rename (none existed pre-rename) |
| WRITEUP.md | 6 | Subtitle, prose, headings, glossary row; expansion introduced by this rename (none existed pre-rename) |
| PUBLICATION.md | 5 | Abstract sentence + 4 table rows; expansion introduced by this rename (none existed pre-rename) |
| plan/next_step.md | 0 | No replacements needed; file already used DRRA pre-rename (roadmap refs: 2× DRRA, 3× expansion) |
| plan/REPRO.md | 0 | No "CSA" occurrences at all |
| plan/gates/gate1/gate1_task.md | 0 | No "CSA" occurrences at all |

## Deliberately NOT renamed

- **Historical audit logs** — `gate0_changes.md` (7 CSA hits: lines 21, 27, 49, 50, 52, 53, 71), `plan/gates/gate1/gate1_causality_report.md` (2 hits: lines 5, 17 — variant list `CSA, ModifiedCSA, …` and per-variant PASS/FAIL row), and `plan/gates/gate1/gate1_changes.md` (0 CSA hits; listed for completeness) — intentionally NOT renamed; dated records written when the label was CSA. Nothing added.
- **Code identifiers** — `CSATimeSeriesModel` (×2), `CSAAttention` (×3 standalone: WRITEUP.md:8,156,377; +1 occurrence embedded inside `` `BaseCSAAttention` `` at WRITEUP.md:377 — counting convention: standalone occurrences only), `BaseCSAAttention` (×1) kept verbatim inside backticks/code references. No `ModifiedCSA*` present in these docs.
- **File paths** — `attention.py`, `model.py`, `expert_plus_plus_attention.py`, etc. unchanged; code blocks (markdown fenced) untouched verbatim.
- **plan/next_step.md** — the 3 "CSA" mentions (lines 33, 38, 253) are quoted references to the old label being retired ("Retire 'CSA' label…"; "CSA label retired and DRRA adopted" in the §3 DONE note; "Do not claim 'CSA' novelty"), not prose uses of the label as the method name; renaming would corrupt meaning ("Retire 'DRRA' label" contradicts the adopting-DRRA line). Kept as historical checklist references.
- **gate0_manifest.json** — not a doc; skipped per instruction. **plan/gates/gate2/gate2_results.jsonl / gate2_sweep.log** — untouched (live training sweep).

## Remaining `\bCSA\b` hits (all legitimate)

| File:line | Hit | Why kept |
|---|---|---|
| plan/next_step.md:33 | `Retire "CSA" label (DeepSeek-V4 already uses Compressed Sparse Attention)` | Quoted old-label reference; "Compressed Sparse Attention" names DeepSeek-V4's term, a factual collision note |
| plan/next_step.md:38 | `CSA label retired and DRRA adopted` (inside §3 DONE blockquote) | Quoted retired-label reference in the completion note; meta-reference, not method-name use |
| plan/next_step.md:253 | `Do not claim "CSA" novelty` | Quoted historical label in a warning; meta-reference, not method-name usage |
| RESULTS.md:134 | `(retired label "CSA", colliding with DeepSeek-V4)` | Quoted retired-label reference inside the DRRA definition sentence (added by Part-2 fix); same class as `next_step.md:33/:253` — explains why the label was dropped, not a method-name use |

No `\bCSA\b` hits remain in WRITEUP.md, PUBLICATION.md, plan/REPRO.md, or plan/gates/gate1/gate1_task.md; the only RESULTS.md hit is the documented quoted exception above (RESULTS.md:134). `DRRA` present: RESULTS.md ×8, WRITEUP.md ×7, PUBLICATION.md ×5 (rename landed; WRITEUP 6 from Part 1 + 1 from Part-2 reframe §1 rewrite).

---

## Reframe (part 2) — two-axis design study (2026-08-12)

Follow-up to the label rename: contribution repositioned from "novel sparse-attention mechanism" to a **two-axis design study** of the compressed-and-indexed attention family (c_KV × c_R) on the frozen ETTh1 direct-96 task.

**Files touched:**
- `PUBLICATION.md` — added the same freeze-supersession pointer as WRITEUP/RESULTS (its pilot numbers previously read as current results); §1.2 "Headline:" → "Central finding (pre-freeze pilot)" with the goal-contract framing retired ("proves" → "supports"); §2 contribution classification rewritten to the (a)–(d) contribution list (controlled 2×2 factorial design, decoupled-rate finding, honest efficiency/accuracy characterization incl. limitations, reproducibility artifacts) + secondary items; "What it is not" now explicitly includes "not a novel sparse-attention mechanism".
- `WRITEUP.md` — §1 summary: "The headline result" → "The central finding (pre-freeze pilot; superseded, §2.2)"; "three attention mechanisms" → "three attention variants"; internal "target was ≥1.30×" goal framing retired in the summary. All technical sections untouched.
- `RESULTS.md` — no changes (checked: no novelty claims; it is a results file, not positioning).
- `plan/lit_audit.md` — **created** (this part's second deliverable): overlap landscape vs DeepSeek-V4 CSA (verified arXiv:2606.19348), NSA (arXiv:2502.11089), Routing Transformer (arXiv:2003.05997), RADLADS (arXiv:2505.03005), FAR (ambiguous, [NEEDS VERIFICATION]); 4 title candidates leaning design-study framing; pre-submission checklist.

**No numbers changed anywhere; no invented citations; `plan/gates/gate2/gate2_*` untouched (live sweep).**
