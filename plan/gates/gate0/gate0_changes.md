# Gate 0 — Documentation Audit Log

Audit against verified ground-truth registry (`gate0_registry.json`). Every edit below: `FILE | OLD STRING | NEW STRING` (one line each). No model code or `gen_registry.py`/`gate0_registry.json` was touched.

## RESULTS.md

- RESULTS.md | `| Model | Val MSE | Test MSE | Params | Fwd (ms)* | Perf/Spd* |` → `| Model | Val MSE | Test MSE | Params (attn / full) | Fwd (ms)* | Perf/Spd* |`
- RESULTS.md | `| **Normal (256 KV)** | **0.1083** 🥇 | 0.1637 | 0.10M | 38.31 | 241.0 |` → `| **Normal (256 cols)** | **0.1083** 🥇 | 0.1637 | 102,496 (269,415) | 38.31 | 241.0 |`
- RESULTS.md | `| **Flat (64 KV)** | 0.1085 🥈 | **0.1617** 🥇 | 0.14M | 29.66 | 310.7 |` → `| **Flat (96 cols)** | 0.1085 🥈 | **0.1617** 🥇 | 144,548 (311,467) | 29.66 | 310.7 |`
- RESULTS.md | `| Modified (128 KV) | 0.1088 🥉 | 0.1624 | 0.14M | 52.19 | 176.1 |` → `| Modified (160 cols) | 0.1088 🥉 | 0.1624 | 144,552 (311,471) | 52.19 | 176.1 |`
- RESULTS.md | `| FlatPlus (64 KV) | 0.1098 | 0.1635 | 0.15M | 39.44 | 230.9 |` → `| FlatPlus (96 cols) | 0.1098 | 0.1635 | 152,492 (319,411) | 39.44 | 230.9 |`
- RESULTS.md | `| **ExpertPlusPlus (52 KV)** | 0.1099 | 0.1654 | **0.10M** 🥇 | **22.42** 🥇 | **405.9** 🥇 |` → `| **ExpertPlusPlus (48+1 cols)** | 0.1099 | 0.1654 | **95,652 (262,571)** 🥇 | **22.42** 🥇 | **405.9** 🥇 |`
- RESULTS.md | `| ExpertFlat (68 KV) | 0.1102 | 0.1645 | 0.15M | 28.88 | 314.3 |` → `| ExpertFlat (64+1 cols) | 0.1102 | 0.1645 | 145,060 (311,979) | 28.88 | 314.3 |`
- RESULTS.md | `| Stacked (64 KV) | 0.1116 | 0.1665 | 0.15M | 34.31 | 261.2 |` → `| Stacked (legacy) | 0.1116 | 0.1665 | N/A (no source) | 34.31 | 261.2 |`
- RESULTS.md | (after Perf/Spd footnote) → add `**Column-count convention** (verified registry): content cols = KV blocks + window; the "+1" is the single sink softmax column (4 scalar logits, one per head) — sinks are NOT KV tokens. Detail: Flat/FlatPlus 96 = 64 KV + 32 win; Modified 160 = 128 KV + 32 win; ExpertFlat 64 = 32 KV + 32 win; EPP 48 = 32 KV + 16 win; Normal 256 (no sink).` and `**Stacked**: legacy numbers; no runnable source in repo (missing from model.py/compare.py). Its parameter and column counts are N/A (no source); only legacy run results are shown. Params listed as attention params, full model in parentheses.`
- RESULTS.md | `| Params | — | **0.096M (−34%)** | ✅ bonus |` → `| Params | — | **95,652 (−33.8% vs Flat)** | ✅ bonus |`
- RESULTS.md | `| O projection | slim \`o_lora_rank=64\` | 34% fewer params overall |` → `| O projection | slim \`o_lora_rank=64\` | 33.8% fewer params overall (vs Flat) |`
- RESULTS.md | `4:1 routing on 8:1 blocks — dense attention over 64 columns |` → `4:1 routing on 8:1 blocks — dense attention over 48 columns (32 KV blocks + 16 window) |`
- RESULTS.md | `**Why dense beats sparse here:** the sparse-gather v1 was 5× slower on CPU; dense GEMMs over 64 columns with masking are dramatically faster on Apple Silicon.` → `**Why dense beats sparse here:** the sparse-gather v1 was 5× slower on CPU; dense GEMMs over 48 columns (32 KV blocks + 16 window) with masking are dramatically faster on Apple Silicon.`
- RESULTS.md | `| Model | Val MSE | Test MSE | Params | Fwd(ms)† | Perf/Spd† | vs Flat | vs EPP |` + 9 data rows → same header, rows relabeled `Normal (256 cols)/Flat (96 cols)/Modified (160 cols)/FlatPlus (96 cols)/ExpertPlusPlus (48+1 cols)/ExpertFlat (64+1 cols)/Stacked (legacy)` and main-model Params cells replaced with `102,496 (269,415) / 144,548 (311,467) / 144,552 (311,471) / 152,492 (319,411) / 95,652 (262,571) / 145,060 (311,979) / N/A (no source)` (surrogate rows unchanged)
- RESULTS.md | `\* Surrogate MSEs from **5+1-epoch** distillation runs (teacher Normal at 5 ep ≈ 0.1213 val) — NOT apples-to-apples with the 10-epoch CSA numbers above. With 10-epoch Phase-1 they would land closer to ~0.11.` → `\* Surrogate MSEs from **5+1-epoch** distillation runs (code defaults: teacher = **ExpertPlusPlus**, 5 Phase-1 epochs + 1 fine-tune epoch). Teacher val is printed at runtime, so it is **not re-derivable from code**; recorded run value: **0.1264** for the 5+1-epoch teacher snapshot (the earlier "teacher Normal at 5 ep ≈ 0.1213" claim does not stand — the code's default teacher is ExpertPlusPlus, not Normal). NOT apples-to-apples with the 10-epoch CSA numbers above. With 10-epoch Phase-1 they would land closer to ~0.11.`
- RESULTS.md | (after † footnote) → add `Note: main-model Params = attention params, full model in parentheses (verified registry); surrogate rows are attention-only. **Stacked**: legacy numbers; no runnable source in repo (missing from model.py/compare.py) — parameter and column counts N/A (no source).`
- RESULTS.md | `Teacher = Normal (or ExpertPlusPlus via \`--teacher\`).` → `Teacher = **ExpertPlusPlus** (code default; \`--teacher normal\` also available).`
- RESULTS.md | `Val 0.1269 vs teacher 0.1264 at 5+1 ep — ~0.4% gap (v1 was +18%). Test 0.1817 **beats** teacher 0.1868.` → `Val 0.1269 vs teacher (ExpertPlusPlus, code default) 0.1264 at 5+1 ep — ~0.4% gap (v1 was +18%); teacher val is runtime-printed, so not re-derivable from code (recorded value 0.1264 stands). Test 0.1817 **beats** teacher 0.1868.`
- RESULTS.md | `| KV tokens (S=256) | 256 | 64 | 32 + 32 win + 4 sinks = 68 | **32 + 16 win + 4 sinks = 52** |` → `| Content cols (S=256) | 256 (no sink; 0 KV + 0 win) | 96 (64 KV + 32 win) + 1 sink = 97 | 64 (32 KV + 32 win) + 1 sink = 65 | **48 (32 KV + 16 win) + 1 sink = 49** |`
- RESULTS.md | `| Params | 0.10M | 0.14M | 0.15M | **0.096M** |` → `| Params (attn / full) | 102,496 (269,415) | 144,548 (311,467) | 145,060 (311,979) | **95,652 (262,571)** |`
- RESULTS.md | (after architecture table) → add `Sinks: each CSA variant has **1 sink softmax column** = 4 scalar params (one per head) — sinks are not KV tokens and are not counted in content columns.`
- RESULTS.md | `### ❌ Stacked 2:1→2:1 refinement (same 64 KV tokens)` → `### ❌ Stacked 2:1→2:1 refinement (legacy; no runnable source in repo)`
- RESULTS.md | `- **ExpertPlusPlus wins the contract**: 1.32× faster forward than Flat (≥30% target ✅) with val 0.1099 vs 0.1085 — statistically tied, 34% fewer parameters.` → `- **ExpertPlusPlus wins the contract**: 1.32× faster forward than Flat (≥30% target ✅) with val 0.1099 vs 0.1085 — statistically tied, 33.8% (≈34%) fewer parameters than Flat ((144,548 − 95,652)/144,548).`

## WRITEUP.md

- WRITEUP.md | `| Attention columns per query (S=256) | 256 (all) | 96 (32 window + 64 KV) | 48 (16 window + 32 KV) |` → `| Attention columns per query (S=256) | 256 (all; no sink) | 96 (64 KV + 32 win) + 1 sink = 97 | 48 (32 KV + 16 win) + 1 sink = 49 |`
- WRITEUP.md | `| Sink tokens | none | 4 learnable logits | 4 learnable logits |` → `| Sink column | none | 1 softmax column (4 scalar logits) | 1 softmax column (4 scalar logits) |`
- WRITEUP.md | `| Params (attention only) | 102,496 | 144,548 | **95,652** (smallest) |` → `| Params (attn / full) | 102,496 (269,415) | 144,548 (311,467) | **95,652 (262,571)** (smallest) |`
- WRITEUP.md | `while having **34% fewer parameters** than Flat and — notably — **fewer parameters than even Normal**.` → `while having **33.8% fewer parameters** than Flat ((144,548 − 95,652)/144,548) and — notably — **fewer attention parameters than even Normal** (95,652 vs 102,496).`
- WRITEUP.md | (after `- EPP − Flat = −48,896, from exactly four deltas: ... +256.`) → add `- Full model (incl. shared block + MLP): Normal 269,415, Flat 311,467, EPP 262,571.`
- WRITEUP.md | `- **EPP (95,652) has 6.7% *fewer* parameters than Normal (102,496)** — the slim O more than pays for the compression machinery.` → `- **EPP (95,652) has 6.7% *fewer* attention parameters than Normal (102,496)** — (102,496 − 95,652)/102,496 = 6.7% — **and 33.8% fewer than Flat (144,548)** — (144,548 − 95,652)/144,548 = 33.8% (the "≈34%" headline). The slim O more than pays for the compression machinery.`
- WRITEUP.md | `| Stacked (ref) | 0.1116 | 0.1665 | +0.0031 | +0.0048 |` → `| Stacked (ref, legacy) | 0.1116 | 0.1665 | +0.0031 | +0.0048 |` + new line `*Stacked: legacy numbers; no runnable source in repo (missing from model.py/compare.py) — its parameter and column counts are N/A (no source); only legacy run results are shown.*`
- WRITEUP.md | `### 7.2 Parameter counts (measured, attention module only)` + `| Model | Params | vs Flat |` + rows `102,496`/`144,548`/`**95,652**` → `### 7.2 Parameter counts (measured; attention module only, full model in parentheses)` + `| Model | Params (attn / full) | vs Flat (attn) |` + rows `102,496 (269,415)`/`144,548 (311,467)`/`**95,652 (262,571)**`
- WRITEUP.md | `- **❌ Stacked 2:1→2:1 (same 64 KV tokens)** — extra level-1 parameters hurt at 10 epochs (0.1116).` → `- **❌ Stacked 2:1→2:1 (legacy; no runnable source in repo)** — no current source in \`model.py\`/\`compare.py\`, so its parameter/column counts are N/A (no source); extra level-1 parameters hurt at 10 epochs (0.1116, legacy run result).`
- WRITEUP.md | `(4) parameter counts Flat=0.145M, EPP=0.096M.` → `(4) parameter counts Flat=144,548, EPP=95,652.`

## PUBLICATION.md

- PUBLICATION.md | `~0.1M params, CPU-only Apple Silicon, fp32, AdamW 1e-4, 10 epochs, seed 42` → `attention params 95,652–152,492 — full model 262,571–319,411 — CPU-only Apple Silicon, fp32, AdamW 1e-4, 10 epochs, seed 42`
- PUBLICATION.md | `| Model | Attention | KV tokens (S=256) | Val MSE | Fwd (ms)* |` → `| Model | Attention | Content cols (KV + window; S=256) | Val MSE | Fwd (ms)* |`
- PUBLICATION.md | `| **Normal** | Full O(S²) causal | 256 |` → `| **Normal** | Full O(S²) causal | 256 (no sink) |`
- PUBLICATION.md | `| **Flat** | CSA 4:1 (two-series compressor + flat indexer) | 64 |` → `| **Flat** | CSA 4:1 (two-series compressor + flat indexer) | 96 (64 KV + 32 win) + 1 sink |`
- PUBLICATION.md | `| Modified | CSA 4:1 + hierarchical indexer | 128 |` → `| Modified | CSA 4:1 + hierarchical indexer | 160 (128 KV + 32 win) + 1 sink |`
- PUBLICATION.md | `| FlatPlus | 4:1 + linear-pool indexer / gated residual KV | 64 |` → `| FlatPlus | 4:1 + linear-pool indexer / gated residual KV | 96 (64 KV + 32 win) + 1 sink |`
- PUBLICATION.md | `| **ExpertPlusPlus** | CSA **8:1 KV + 4:1 routing**, shared-Q, slim O, window 16 | **52** |` → `| **ExpertPlusPlus** | CSA **8:1 KV + 4:1 routing**, shared-Q, slim O, window 16 | 48 (32 KV + 16 win) + 1 sink |`
- PUBLICATION.md | `| ExpertFlat | CSA 8:1 on **both** axes | 68 |` → `| ExpertFlat | CSA 8:1 on **both** axes | 64 (32 KV + 32 win) + 1 sink |`
- PUBLICATION.md | `| Stacked | 2:1→2:1 stacked compression | 64 |` → `| Stacked (legacy) | 2:1→2:1 stacked compression | N/A (no source) |`
- PUBLICATION.md | (after §1.1 footnote) → add `**Content cols = KV blocks + window; the "+1 sink" is a single softmax column of 4 scalar logits (one per head) — NOT a KV token (verified registry). Stacked: legacy numbers; no runnable source in repo (missing from model.py/compare.py) — parameter and column counts N/A (no source).**`
- PUBLICATION.md | `and with **34% fewer parameters** (0.096M — *fewer than even the full-attention Normal model*).` → `and with **33.8% fewer parameters than Flat** ((144,548 − 95,652)/144,548; 95,652 attention params — full model 262,571 — *fewer than even the full-attention Normal model's 102,496 attention / 269,415 full*).`
- PUBLICATION.md | `**ExpertFlat** (8:1 on *both* axes) was fastest-but-least-accurate (0.1102), showing that coarsening the router — not the content — is what costs accuracy.` → `**ExpertFlat** (8:1 on *both* axes) — fastest of the variants predating EPP, but 2nd-worst accuracy (0.1102; the least accurate overall is Stacked at 0.1116 — legacy numbers — and the fastest overall remains ExpertPlusPlus at 22.42 ms) — showing that coarsening the router — not the content — is what costs accuracy.`
- PUBLICATION.md | `val 0.1269 vs teacher 0.1264 at 5+1 epochs (~0.4% gap), test MSE actually beats the teacher.**` → `val 0.1269 vs teacher 0.1264 at the recorded 5+1-epoch run (~0.4% gap), test MSE actually beats the teacher.** The teacher is **ExpertPlusPlus** (the code's default); its val is printed at runtime, so it is **not re-derivable from code** — the recorded value 0.1264 stands. These 5+1-epoch surrogate numbers are **not apples-to-apples with the 10-epoch main results**.`
- PUBLICATION.md | `- **Parameter efficiency** — EPP (0.096M) is smaller than even the full-attention baseline, which is a clean headline.` → `- **Parameter efficiency** — EPP (95,652 attention / 262,571 full) is smaller than even the full-attention baseline (Normal: 102,496 attention / 269,415 full), which is a clean headline.`
- PUBLICATION.md | `| 4 | **Tiny scale + CPU-only** | 0.1M params, hidden 128, fp32 CPU.` → `| 4 | **Tiny scale + CPU-only** | 95,652–152,492 attention params (262,571–319,411 full model), hidden 128, fp32 CPU.`
- PUBLICATION.md | `| 10 | **Absolute numbers are small** | 22 ms vs 30 ms on CPU for a 0.1M model —` → `| 10 | **Absolute numbers are small** | 22 ms vs 30 ms on CPU for a 95,652-attention-param model (EPP; 262,571 total) —`

## Source of truth for fix 4 (surrogate teacher)

`train_surrogate.py` (read-only, not edited): default `--teacher expertplusplus`, default `--epochs 5`, default `--finetune-epochs 1`; teacher val/test MSE are printed at runtime (`val(teacher)` per Phase-1 epoch, final `val_teacher`/`test_teacher`), so the exact teacher val is **not re-derivable from code**. Recorded-run values that stand: teacher val 0.1264 and teacher test 0.1868 at the 5+1-epoch snapshot. The "teacher Normal at 5 ep ≈ 0.1213" claim does not stand (code default teacher is ExpertPlusPlus, and 0.1213 is not the final snapshot).

## Round 2 (evaluator follow-up — arithmetic fixes)

- RESULTS.md | `**0.017M params (88% fewer than EPP)**` → `**0.017M params (~82% fewer than EPP)**` (v2 = 16,936 from surrogate_attention.py; (95,652 − 16,936)/95,652 = 82.3%)
- RESULTS.md | `~0.4% gap (v1 was +18%)` → `~0.4% gap (v1 was +13% vs the standing teacher value 0.1264)` ((0.1424 − 0.1264)/0.1264 = 12.7%)
- RESULTS.md | `CSA variants live at val 0.108–0.112 / 1.0–1.2×` → `CSA variants live at val 0.108–0.112 / 0.88–1.21×` (table vs-Flat column range: Stacked 0.88× … ExpertFlat 1.21×)
- PUBLICATION.md | `**0.017M params (88% fewer than EPP), 2.18× faster than Flat, ...` → `**0.017M params (~82% fewer than EPP), 2.18× faster than Flat, ...` (comparator = EPP)
- PUBLICATION.md | `student with 88% parameter reduction is a modest` → `student with ~82% parameter reduction (vs EPP) is a modest` (comparator = EPP, per §1.3)
