#!/usr/bin/env python3
"""Manuscript verification battery. Run before every paper commit:
~/.uv_env/py311/bin/python paper/scripts/verify_manuscript.py
Checks: no stale as-run values, all v2 values present, no internal names,
braces/$ balance, labels/refs/cites/figures resolve. Exit nonzero on failure.
(Vowed after repeated 'verified'-then-missed episodes, 2026-10-01.)
"""
import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAPER = REPO / "paper"
SEC = PAPER / "sections"

files = sorted(glob.glob(str(SEC / "*.tex"))) + [str(PAPER / "main.tex")]
text = {f: open(f).read() for f in files}
ALL = "\n".join(text.values())
fails = []


def check_missing(v, label):
    if v not in ALL:
        fails.append(f"MISSING {label}: [{v}]")


def check_stale(v, label):
    if v in ALL:
        fails.append(f"STALE PRESENT {label}: [{v}]")


# --- v2 values that must be present ---------------------------------------
for v in ["0.6148", "0.6190", "0.6810", "0.6128", "0.8389", "0.8771", "0.8440",
          "0.9496", "0.8505", "-0.0320", "+0.0300", "-0.0724", "+0.0620",
          "0.0074", "0.62", "95/100", "0.5909", "1.7817", "0.4121", "0.9326",
          "0.3775", "0.5907", "0.4448", "3.1364", "0.1693", "0.1276", "5.9733",
          "0.2894", "0.5810", "0.8100", "0.6122", "0.8586", "5.22", "1.18",
          "1.22", "49.3", "52.5", "76.9", "-0.1217", "-0.1446", "0.0058",
          "16/25", "12/25", "8/12", "-7.5", "-0.0331", "0.032"]:
    check_missing(v, "v2")
# --- as-run values that must be gone ---------------------------------------
for v in ["0.6575", "0.6994", "0.6347", "0.9368", "0.9243", "0.9184",
          "96 of the 100", "96/100", "0.0032", "0.093", "7/12", "0.6332",
          "1.3624", "0.3965", "0.9964", "0.3798", "0.5838", "0.4469", "3.1166",
          "0.1721", "5.9677", "-0.0516", "+0.0288", "-0.0262", "0.908$",
          "+5.9%", "-8.9%", "0.0804", "0.080$", "7/10", "5.3$"]:
    check_stale(v, "stale")
# --- internal names (workflow rule 8) --------------------------------------
for pat in [r"gate-1\d", r"gate 1\d", r"stage-[01]", r"stage [01]", r"plan/",
            r"pre-publication", r"\bQ-[0-9]\b", r"\bSTATUS\.md\b", r"\bHANDOVER\.md\b"]:
    for f, t in text.items():
        for m in re.finditer(pat, t, re.IGNORECASE):
            if "frozen task" in t[max(0, m.start()-20):m.start()].lower():
                continue
            fails.append(f"INTERNAL NAME {f.split('/')[-1]}: [{m.group(0)}]")
# --- braces / math-mode dollars ---------------------------------------------
for f, t in text.items():
    u = re.sub(r"(?m)^%.*$", "", t)
    u = re.sub(r"(?<!\\)%.*$", "", u)
    u2 = u.replace("\\$", "")
    if u.count("{") - u.count("}") != 0:
        fails.append(f"BRACES {f.split('/')[-1]}")
    if u2.count("$") % 2 != 0:
        fails.append(f"DOLLARS {f.split('/')[-1]}")
# --- labels / refs / cites / figures -----------------------------------------
labels, refs = set(), set()
for t in text.values():
    labels.update(re.findall(r"\\label\{([^}]*)\}", t))
    refs.update(re.findall(r"\\ref\{([^}]*)\}", t))
for r in sorted(refs - labels):
    fails.append(f"UNRESOLVED REF [{r}]")
cites = set()
for t in text.values():
    for x in re.findall(r"\\cite[pt]?\{([^}]*)\}", t):
        cites.update(k.strip() for k in x.split(","))
keys = set(re.findall(r"@\w+\{([^,]*),", open(PAPER / "references.bib").read()))
for c in sorted(cites - keys):
    fails.append(f"CITE MISSING FROM BIB [{c}]")
for inc in sorted(set(re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", ALL))):
    if not (PAPER / inc).exists():
        fails.append(f"MISSING FIGURE [{inc}]")

print(f"FAILURES: {len(fails)}")
for f in fails:
    print(" ", f)
sys.exit(1 if fails else 0)
