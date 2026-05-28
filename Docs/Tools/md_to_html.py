"""Convert FootPlacement_*.md -> standalone HTML (labels, callouts, Mermaid, sticky TOC, doc nav).

Usage:
    python md_to_html.py                       # convert the default doc set
    python md_to_html.py <src.md> <dest.html>  # convert a single doc
"""
from __future__ import annotations

import io
import re
import sys
import uuid
from pathlib import Path

import markdown


# Force UTF-8 stdout so callers do not need PYTHONIOENCODING / chcp wrappers
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Document set + cross-document navigation
# ---------------------------------------------------------------------------

DOC_SET = [
    {
        "slug": "learning",
        "title": "Learning",
        "subtitle": "Mental model first",
        "src": "Docs/FootPlacement_Learning.md",
        "out": "Html/FootPlacement_Learning.html",
    },
    {
        "slug": "reference",
        "title": "Implementation Reference",
        "subtitle": "Measured SSOT",
        "src": "Docs/FootPlacement_ImplementationReference.md",
        "out": "Html/FootPlacement_ImplementationReference.html",
    },
    {
        "slug": "troubleshooting",
        "title": "Troubleshooting",
        "subtitle": "Fixes & extensions",
        "src": "Docs/FootPlacement_Troubleshooting.md",
        "out": "Html/FootPlacement_Troubleshooting.html",
    },
]


# ---------------------------------------------------------------------------
# Label & callout maps
# ---------------------------------------------------------------------------

LABEL_MAP = {
    "verified": ("verified", "verified"),
    "inferred": ("inferred", "inferred"),
    "caution":  ("caution",  "caution"),
    "extend":   ("extend",   "extend"),
}

# Korean label tokens used inside the source markdown
LABEL_TOKENS = {
    "검증됨": "verified",
    "추론":   "inferred",
    "주의":   "caution",
    "확장":   "extend",
}

# Display text rendered inside the badge
LABEL_DISPLAY = {
    "verified": "검증됨",
    "inferred": "추론",
    "caution":  "주의",
    "extend":   "확장",
}

CALLOUT_MAP = {
    "verify":   ("확인해 보기", "callout-verify"),
    "caution":  ("주의",        "callout-caution"),
    "extend":   ("확장",        "callout-extend"),
    "note":     ("메모",        "callout-note"),
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
:root {
  color-scheme: light dark;
  --bg: #fbfaf6;
  --surface: #ffffff;
  --fg: #1f1f1f;
  --muted: #6a6a6a;
  --accent: #5b3eaa;
  --accent-soft: #efeaff;
  --rule: #e6e2d8;
  --code-bg: #f4f0e6;
  --code-fg: #2d2438;
  --table-head: #efeaff;
  --shadow: 0 1px 2px rgba(20, 20, 20, .05), 0 4px 12px rgba(20, 20, 20, .04);

  --label-verified-bg: #e6f4ea; --label-verified-fg: #1e6f3c;
  --label-inferred-bg: #efeaff; --label-inferred-fg: #5b3eaa;
  --label-caution-bg:  #fdecd6; --label-caution-fg:  #9a5b00;
  --label-extend-bg:   #def4f1; --label-extend-fg:   #186b62;

  --callout-verify-bg: #f0f9f3; --callout-verify-bd: #4caf72;
  --callout-caution-bg:#fff5e6; --callout-caution-bd:#e89000;
  --callout-extend-bg: #ecf7f5; --callout-extend-bd: #2aa395;
  --callout-note-bg:   #f4f4f4; --callout-note-bd:   #999;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14141a;
    --surface: #1c1c25;
    --fg: #e8e6e0;
    --muted: #9a98a3;
    --accent: #c3b3ff;
    --accent-soft: #2a2440;
    --rule: #2c2a35;
    --code-bg: #1a1923;
    --code-fg: #d8d3ee;
    --table-head: #2a2440;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 4px 12px rgba(0, 0, 0, .25);

    --label-verified-bg: #1d3a26; --label-verified-fg: #9ad8b1;
    --label-inferred-bg: #2a2247; --label-inferred-fg: #d2c2ff;
    --label-caution-bg:  #3a2a13; --label-caution-fg:  #f3c181;
    --label-extend-bg:   #14322f; --label-extend-fg:   #88d6cb;

    --callout-verify-bg: #18261d; --callout-verify-bd: #4caf72;
    --callout-caution-bg:#2a1f10; --callout-caution-bd:#e89000;
    --callout-extend-bg: #142624; --callout-extend-bd: #2aa395;
    --callout-note-bg:   #1f1e26; --callout-note-bd:   #777;
  }
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg); }
body {
  font-family: "Pretendard", "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 16px;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 0;
  max-width: 1260px;
  margin: 0 auto;
  padding: 32px;
}
.sidebar {
  position: sticky;
  top: 32px;
  align-self: start;
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  padding-right: 24px;
  border-right: 1px solid var(--rule);
}
.sidebar h2 {
  font-size: .82rem;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--muted);
  margin: 0 0 .6em;
  border: none;
  padding: 0;
}
.sidebar .doc-nav { list-style: none; padding: 0; margin: 0 0 28px; }
.sidebar .doc-nav li { margin: 0; }
.sidebar .doc-nav a {
  display: block;
  padding: 8px 12px;
  border-radius: 6px;
  color: var(--fg);
  text-decoration: none;
  border: 1px solid transparent;
  font-size: .92rem;
}
.sidebar .doc-nav a:hover { background: var(--accent-soft); }
.sidebar .doc-nav a.active {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}
.sidebar .doc-nav .sub {
  display: block;
  font-size: .76rem;
  color: var(--muted);
  font-weight: normal;
  margin-top: 2px;
}

.sidebar .toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border-left: 2px solid var(--rule);
}
.sidebar .toc-list li { margin: 0; }
.sidebar .toc-list a {
  display: block;
  padding: 4px 12px;
  margin-left: -2px;
  border-left: 2px solid transparent;
  color: var(--muted);
  text-decoration: none;
  font-size: .88rem;
  line-height: 1.4;
}
.sidebar .toc-list a:hover { color: var(--accent); }
.sidebar .toc-list a.toc-h3 { padding-left: 26px; font-size: .82rem; }

main { padding: 0 0 96px 40px; min-width: 0; }

h1, h2, h3, h4 {
  color: var(--fg);
  line-height: 1.3;
  margin: 1.8em 0 .5em;
  font-weight: 700;
}
h1 { font-size: 2.0rem; margin-top: 0; padding-bottom: .35em; border-bottom: 2px solid var(--accent); }
h2 { font-size: 1.5rem; padding-bottom: .25em; border-bottom: 1px solid var(--rule); scroll-margin-top: 24px; }
h3 { font-size: 1.15rem; color: var(--accent); scroll-margin-top: 24px; }
h4 { font-size: 1.02rem; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }

p { margin: .8em 0; }
ul, ol { padding-left: 1.5em; }
li { margin: .2em 0; }

a { color: var(--accent); text-decoration: none; border-bottom: 1px dashed currentColor; }
a:hover { border-bottom-style: solid; }

hr { border: none; border-top: 1px solid var(--rule); margin: 2em 0; }

blockquote {
  margin: 1.2em 0;
  padding: .8em 1.2em;
  border-left: 4px solid var(--accent);
  background: var(--accent-soft);
  color: var(--fg);
  border-radius: 0 6px 6px 0;
}
blockquote p:first-child { margin-top: 0; }
blockquote p:last-child  { margin-bottom: 0; }

code {
  font-family: "JetBrains Mono", "Cascadia Code", Consolas, "SF Mono", Menlo, monospace;
  font-size: .92em;
  background: var(--code-bg);
  color: var(--code-fg);
  padding: .12em .4em;
  border-radius: 4px;
}
pre {
  background: var(--code-bg);
  color: var(--code-fg);
  padding: 14px 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: .88rem;
  line-height: 1.55;
  box-shadow: var(--shadow);
  border: 1px solid var(--rule);
}
pre code { background: transparent; padding: 0; font-size: inherit; color: inherit; }

table {
  border-collapse: collapse;
  width: 100%;
  margin: 1.2em 0;
  font-size: .92rem;
  box-shadow: var(--shadow);
  border-radius: 6px;
  overflow: hidden;
  background: var(--surface);
}
th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--rule); }
th { background: var(--table-head); font-weight: 600; }
tr:last-child td { border-bottom: none; }

.label {
  display: inline-block;
  padding: 1px 8px;
  margin: 0 2px;
  border-radius: 999px;
  font-size: .76em;
  font-weight: 600;
  line-height: 1.55;
  vertical-align: 1px;
  user-select: none;
  white-space: nowrap;
}
.label-verified { background: var(--label-verified-bg); color: var(--label-verified-fg); }
.label-inferred { background: var(--label-inferred-bg); color: var(--label-inferred-fg); }
.label-caution  { background: var(--label-caution-bg);  color: var(--label-caution-fg); }
.label-extend   { background: var(--label-extend-bg);   color: var(--label-extend-fg); }

.callout {
  margin: 1.3em 0;
  padding: 14px 18px 6px 18px;
  border-left: 4px solid var(--callout-note-bd);
  background: var(--callout-note-bg);
  border-radius: 0 8px 8px 0;
}
.callout-title {
  font-weight: 700;
  font-size: .8rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin: 0 0 6px;
  color: var(--callout-note-bd);
}
.callout-verify  { border-left-color: var(--callout-verify-bd);  background: var(--callout-verify-bg); }
.callout-verify  .callout-title  { color: var(--callout-verify-bd); }
.callout-caution { border-left-color: var(--callout-caution-bd); background: var(--callout-caution-bg); }
.callout-caution .callout-title { color: var(--callout-caution-bd); }
.callout-extend  { border-left-color: var(--callout-extend-bd);  background: var(--callout-extend-bg); }
.callout-extend  .callout-title  { color: var(--callout-extend-bd); }
.callout-note    { border-left-color: var(--callout-note-bd);    background: var(--callout-note-bg); }
.callout p:first-child { margin-top: 0; }
.callout p:last-child  { margin-bottom: .8em; }

.mermaid-wrap {
  margin: 1.4em 0;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 8px;
  box-shadow: var(--shadow);
  overflow-x: auto;
  text-align: center;
}
.mermaid { line-height: 1.4; }

h2 .anchor, h3 .anchor, h4 .anchor {
  color: var(--muted);
  margin-left: .35em;
  font-weight: normal;
  opacity: 0;
  transition: opacity .15s;
  text-decoration: none;
  border: none;
  font-size: .75em;
}
h2:hover .anchor, h3:hover .anchor, h4:hover .anchor { opacity: 1; }

@media (max-width: 1000px) {
  .layout { grid-template-columns: 1fr; padding: 16px; }
  .sidebar { position: relative; top: 0; max-height: none; border-right: none; border-bottom: 1px solid var(--rule); padding-right: 0; padding-bottom: 16px; margin-bottom: 16px; }
  main { padding-left: 0; }
}
"""


HTML_SHELL = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <h2>문서 세트</h2>
    <ul class="doc-nav">
      {doc_nav}
    </ul>
    <h2>이 문서 목차</h2>
    {toc}
  </aside>
  <main>
    {body}
  </main>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (window.mermaid) {{
    mermaid.initialize({{
      startOnLoad: true,
      theme: prefersDark ? 'dark' : 'default',
      flowchart: {{ htmlLabels: true, curve: 'basis' }}
    }});
  }}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_placeholder() -> str:
    return "XMD2HTMLX" + uuid.uuid4().hex + "X"


def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s가-힣\-]", "", text, flags=re.UNICODE).strip().lower()
    s = re.sub(r"\s+", "-", s)
    return s or "section"


# ---------------------------------------------------------------------------
# Extraction passes (run BEFORE markdown library so it does not mangle them)
# ---------------------------------------------------------------------------

def extract_mermaid(src: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    pattern = re.compile(r"^```mermaid\s*\n(.*?)^```", re.S | re.M)

    def repl(match: re.Match) -> str:
        code = match.group(1).rstrip("\n")
        ph = make_placeholder()
        mapping[ph] = (
            '<div class="mermaid-wrap"><pre class="mermaid">'
            + html_escape(code)
            + "</pre></div>"
        )
        return "\n\n" + ph + "\n\n"

    return pattern.sub(repl, src), mapping


def extract_callouts(src: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    kinds = "|".join(CALLOUT_MAP.keys())
    pattern = re.compile(rf"^:::({kinds})\s*\n(.*?)^:::\s*$", re.S | re.M)

    def repl(match: re.Match) -> str:
        kind = match.group(1)
        body_md = match.group(2).strip()
        inner_html = markdown.markdown(
            body_md,
            extensions=["extra", "sane_lists", "smarty"],
            output_format="html5",
        )
        inner_html = inject_labels(inner_html)
        title, cls = CALLOUT_MAP[kind]
        m_title = re.match(r'\s*<p><strong>(.*?)</strong></p>\s*', inner_html, re.S)
        if m_title:
            title = re.sub(r"<.*?>", "", m_title.group(1))
            inner_html = inner_html[m_title.end():]
        ph = make_placeholder()
        mapping[ph] = (
            f'<aside class="callout {cls}">'
            f'<div class="callout-title">{title}</div>'
            f'{inner_html}'
            f'</aside>'
        )
        return "\n\n" + ph + "\n\n"

    return pattern.sub(repl, src), mapping


def restore_placeholders(html: str, *mappings: dict[str, str]) -> str:
    for m in mappings:
        for k, v in m.items():
            html = html.replace("<p>" + k + "</p>", v).replace(k, v)
    return html


def inject_labels(html: str) -> str:
    def repl(match: re.Match) -> str:
        token = match.group(1)
        key = LABEL_TOKENS.get(token)
        if not key:
            return match.group(0)
        display = LABEL_DISPLAY[key]
        return f'<span class="label label-{key}">{display}</span>'

    tokens = "|".join(re.escape(t) for t in LABEL_TOKENS)
    return re.sub(r"\{(" + tokens + r")\}", repl, html)


def build_toc(html: str) -> tuple[str, str]:
    items: list[tuple[int, str, str]] = []

    def inject(match: re.Match) -> str:
        level = int(match.group(1))
        text_html = match.group(2)
        text_plain = re.sub(r"<.*?>", "", text_html)
        sid = slugify(text_plain)
        items.append((level, text_plain, sid))
        return f'<h{level} id="{sid}">{text_html} <a class="anchor" href="#{sid}">#</a></h{level}>'

    new_html = re.sub(r'<h([23])>(.*?)</h\1>', inject, html, flags=re.S)
    if not items:
        return "", new_html

    lines = ['<ul class="toc-list">']
    for level, text, sid in items:
        cls = "toc-h2" if level == 2 else "toc-h3"
        lines.append(f'<li><a class="{cls}" href="#{sid}">{text}</a></li>')
    lines.append("</ul>")
    return "\n".join(lines), new_html


def build_doc_nav(active_slug: str) -> str:
    lines = []
    for doc in DOC_SET:
        slug = doc["slug"]
        cls = "active" if slug == active_slug else ""
        href = Path(doc["out"]).name
        lines.append(
            f'<li><a class="{cls}" href="{href}">{doc["title"]}'
            f'<span class="sub">{doc["subtitle"]}</span></a></li>'
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert(md_path: Path, out_path: Path, active_slug: str = "") -> int:
    md_src = md_path.read_text(encoding="utf-8")

    md_src, mermaid_map = extract_mermaid(md_src)
    md_src, callout_map = extract_callouts(md_src)

    md_html = markdown.markdown(
        md_src,
        extensions=["extra", "sane_lists", "smarty", "tables"],
        output_format="html5",
    )

    md_html = inject_labels(md_html)
    md_html = restore_placeholders(md_html, mermaid_map, callout_map)

    toc_html, md_html = build_toc(md_html)
    doc_nav_html = build_doc_nav(active_slug)

    m = re.search(r'<h1[^>]*>(.*?)</h1>', md_html, re.S)
    title = re.sub(r'<.*?>', '', m.group(1)).strip() if m else "Document"

    out_html = HTML_SHELL.format(
        title=title,
        css=CSS,
        doc_nav=doc_nav_html,
        toc=toc_html or "<p style='color:var(--muted);font-size:.85rem;'>없음</p>",
        body=md_html,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_html, encoding="utf-8")
    return len(out_html)


def convert_doc_set(project_root: Path) -> None:
    for doc in DOC_SET:
        src = project_root / doc["src"]
        out = project_root / doc["out"]
        size = convert(src, out, active_slug=doc["slug"])
        print(f"  [{doc['slug']:14s}] {src.name:50s} -> {out.name:50s} ({size:,} chars)")


if __name__ == "__main__":
    project_root = Path(r"D:\Projects\Guide\CustomFootIK")
    if len(sys.argv) >= 3:
        size = convert(Path(sys.argv[1]), Path(sys.argv[2]))
        print(f"Wrote {sys.argv[2]}  ({size:,} chars)")
    else:
        print("Converting doc set:")
        convert_doc_set(project_root)
