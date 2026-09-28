# J — Venue strategy + open questions

Status: TODO (decision after P0) | Updated: 2026-09-28 | Evidence: none yet | Depends: J-1 needs A + B2 verdict

Reviewer §5 (scope-based, not odds):

| Journal | Fit | Our gate |
|---|---|---|
| Neurocomputing | Validated routing study + beyond-minimal backbone. Preferred after substantial revision. | P0 + D-3 + E-2 + F-3 |
| Neural Computing and Applications | Architectures/benchmarks/forecasting; practical + deployment. | P0 + F + G |
| Applied Soft Computing | Real-life value, not mainly ablation. Conditional. | E-2 + applied eval |
| Machine Learning | Empirical + methodology; broader explanation. Ambitious now. | H-sweep |
| Scientific Reports | Soundness over importance; bounded study fallback. | P0 + P1 only |

Reviewer bottom line (agree): keep project; audit compute + learning before expansion; reanalyse + transfer test. Title: `00_title.md` option 1. Citeability = reliable when/how to control two quantities + reusable impl.

## Tasks

- [ ] **J-1.** Choose target AFTER P0 verdict: audits-support → Neurocomputing track (full Stage-2); bounded → NCA / Sci Rep (P1 + minimal Stage-2).

## Open questions for manager (decide before Stage-2 compute)

- [ ] **Q-1.** E-2 backbone: acceptable "credible temporal-attention backbone"? Who funds GPU/CPU for wide sets (solar/electricity/traffic PatchTST ~3–13h/seed CPU)?
- [ ] **Q-2.** Router scope (B2-2a disclose vs 2b redesign + re-train)?
- [ ] **Q-3.** Venue ambition (full vs bounded)? Sets D-3/F-3/H scope.
- [ ] **Q-4.** Surrogate fate (I-7): separate paper now vs appendix?

## Log

- 2026-09-28: Created from review §5; header added.
