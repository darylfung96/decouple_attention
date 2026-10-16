# Source material

Two files matter here, and neither is a `.md` we own:

| File | Where | What it is |
|---|---|---|
| `Q1_Journal_Technical_Review_and_Revision_Plan.pdf` | repo root | The 12-page AI-generated review (16 October 2026) that the R, C and S tasks come from. The original, unchanged. |
| `q1_review_text.txt` | this folder | A plain-text extraction of that PDF (625 lines, page markers `===== PAGE n =====`). Every citation in this folder points into this file by line number, so the references stay checkable if the PDF is moved or re-exported. |

## Caveat that matters when you quote it

The review's own page references ("Manuscript, p. 8, §4.2") identify **the 27-page draft it was given**,
not the current paper. So a review citation to a manuscript page and a citation to the PDF's own page are
two different numbers; the mapping table in `../README.md` always uses the PDF's page. If you need to find
what the review saw, search the draft it names (`NewTransformer.pdf`) — the current `paper/main.tex` is
31 pages and the section numbers have shifted.

## How the citations are written

Every task file opens with a line in this shape:

> **Source:** Q1 review §2 "Isolate routing resolution and verify what actually changes" (PDF p. 3;
> `source/q1_review_text.txt` lines 115–152), item "R3. Fixed top-k is not a fixed information budget"
> (line 117).

That is enough to go from the task to the exact paragraph in three steps, with no interpretation
required: section title in case the pagination changes, page and line range, and the item heading.

## Provenance

- Extracted from the PDF on 2026-10-16; the extraction is verbatim apart from line wrapping.
- The PDF's checksum is `5c8550bae71984a5bd0a0ffb515a80a4`; the extraction's is
  `a5e23bfd31e4b64fcc70d5e5365eaf0f`. If either changes, the line-number citations in the task files must
  be checked before they are trusted.
- Tasks labelled **S1** and **N** have no entry here: S1 comes from the journal's Guide for Authors, and N
  is this folder's own necessity audit, not the review.
