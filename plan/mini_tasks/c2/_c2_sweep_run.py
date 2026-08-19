# _c2_sweep_run.py -- run the 10 keyword sweeps, cache results, print merged list
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _c2_arxiv import arxiv_query

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c2_sweep_cache")
os.makedirs(CACHE, exist_ok=True)

QUERIES = [
    'all:"routed attention" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"routing attention" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"compressed attention" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"sparse attention" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"top-k attention" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"block attention" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"token compression" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"selective attention" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"efficient attention" AND all:"time series" AND submittedDate:[202401010000 TO 202608312359]',
    'all:"sparse attention" AND all:"forecasting" AND submittedDate:[202401010000 TO 202608312359]',
]

merged = {}
for i, q in enumerate(QUERIES):
    rows = arxiv_query(q, max_results=200)
    json.dump(rows, open(os.path.join(CACHE, f"sweep_{i}.json"), "w"), indent=2)
    for r in rows:
        aid = r["id"].split("/abs/")[-1].split("v")[0]
        merged.setdefault(aid, {"id": aid, "title": r["title"], "published": r["published"], "summary": r["summary"], "sweeps": []})
        merged[aid]["sweeps"].append(i)

print(f"total unique papers across sweeps: {len(merged)}")
for aid in sorted(merged, key=lambda k: merged[k]["published"], reverse=True):
    m = merged[aid]
    print(f"{m['published']}  arXiv:{aid}  sweeps:{m['sweeps']}  {m['title'][:90]}")
json.dump(list(merged.values()), open(os.path.join(CACHE, "merged.json"), "w"), indent=2)
print("cache written to", os.path.join(CACHE, "merged.json"))
