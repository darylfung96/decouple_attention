# _c2_arxiv.py -- C2 sweep helpers: arXiv API + Semantic Scholar (stdlib only)
import json, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET

NS = {"a": "http://www.w3.org/2005/Atom"}

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "c2-lit-sweep/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def arxiv_query(query, max_results=100, out=None):
    """arXiv full search; returns list of dicts {id,title,published,summary}."""
    url = ("https://export.arxiv.org/api/query?search_query="
           + urllib.parse.quote(query)
           + f"&start=0&max_results={max_results}"
           + "&sortBy=submittedDate&sortOrder=descending")
    root = ET.fromstring(_fetch(url))
    rows = []
    for e in root.findall("a:entry", NS):
        rows.append({
            "id": e.find("a:id", NS).text.strip(),
            "title": " ".join(e.find("a:title", NS).text.split()),
            "published": e.find("a:published", NS).text[:10],
            "summary": " ".join(e.find("a:summary", NS).text.split())[:300],
        })
    if out:
        with open(out, "w") as f:
            json.dump(rows, f, indent=2)
    return rows

def arxiv_by_id(id_list, out=None):
    """Exact-id fetch for citation verification (title/authors/date)."""
    url = "https://export.arxiv.org/api/query?id_list=" + ",".join(id_list)
    root = ET.fromstring(_fetch(url))
    rows = []
    for e in root.findall("a:entry", NS):
        authors = [a.find("a:name", NS).text for a in e.findall("a:author", NS)]
        rows.append({
            "id": e.find("a:id", NS).text.strip(),
            "title": " ".join(e.find("a:title", NS).text.split()),
            "published": e.find("a:published", NS).text[:10],
            "authors": authors,
        })
    if out:
        with open(out, "w") as f:
            json.dump(rows, f, indent=2)
    return rows

def s2_citations(arxiv_id, limit=100, out=None):
    """Semantic Scholar citations of an arXiv paper (forward citation chase)."""
    url = (f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
           f"/citations?fields=title,year,externalIds&limit={limit}")
    data = json.loads(_fetch(url))
    rows = [{"title": c["citingPaper"].get("title"),
             "year": c["citingPaper"].get("year"),
             "arxiv": (c["citingPaper"].get("externalIds") or {}).get("ArXiv")}
            for c in data.get("data", [])]
    if out:
        with open(out, "w") as f:
            json.dump(rows, f, indent=2)
    return rows

if __name__ == "__main__":
    q = sys.argv[1]
    for r in arxiv_query(q):
        print(f"{r['published']}  {r['id']}  {r['title'][:95]}")
