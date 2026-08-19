# _c2_html2txt.py -- strip arXiv HTML to readable text for targeted reading
import html as h, re, sys

def convert(src, dst):
    t = open(src, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", t)
    t = re.sub(r"<(h[1-6]|p|div|li|tr|section|table|caption)[^>]*>", "\n\n", t)
    t = re.sub(r"<br\s*/?>|</(h[1-6]|p|div|li|tr|section|table)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = h.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    open(dst, "w", encoding="utf-8").write(t)
    print(dst, len(t.split()), "words")

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
