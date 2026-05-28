"""Verify HTML output: counts, title, TOC presence, labels, callouts, mermaid."""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_FILES = [
    r"D:\Projects\Guide\CustomFootIK\Html\FootPlacement_Learning.html",
    r"D:\Projects\Guide\CustomFootIK\Html\FootPlacement_ImplementationReference.html",
    r"D:\Projects\Guide\CustomFootIK\Html\FootPlacement_Troubleshooting.html",
]


def report(path: str) -> None:
    p = Path(path)
    if not p.exists():
        print(f"-- SKIP (missing): {path}")
        return
    text = p.read_text(encoding="utf-8")
    print(f"\n== {p.name} ==")
    print(f"  size            : {len(text):>7,} chars")

    m = re.search(r"<title>(.*?)</title>", text)
    print(f"  title           : {m.group(1) if m else '?'}")

    for level in (1, 2, 3, 4):
        cnt = len(re.findall(rf"<h{level}\b", text))
        print(f"  h{level} count        : {cnt}")

    print(f"  pre count       : {len(re.findall(r'<pre[ >]', text))}")
    print(f"  table count     : {len(re.findall(r'<table>', text))}")
    print(f"  label badges    : {len(re.findall(r'class=\"label label-', text))}")
    print(f"  callout boxes   : {len(re.findall(r'class=\"callout ', text))}")
    print(f"  mermaid blocks  : {len(re.findall(r'class=\"mermaid\"', text))}")

    toc_items = re.findall(r'<a class="toc-(h[23])" href="#[^\"]+">([^<]+)</a>', text)
    if toc_items:
        print(f"  toc entries     : {len(toc_items)}")
        for cls, label in toc_items[:6]:
            indent = "    " if cls == "h3" else ""
            print(f"    {indent}- {label}")
        if len(toc_items) > 6:
            print(f"    ... (+{len(toc_items)-6} more)")
    else:
        print("  toc entries     : NONE")

    doc_nav = re.findall(r'<a class="(active|)"[^>]*>([^<]+?)<span', text)
    if doc_nav:
        print(f"  doc nav         : {len(doc_nav)}")
        for active, name in doc_nav:
            marker = "*" if active == "active" else " "
            print(f"    {marker} {name}")


if __name__ == "__main__":
    paths = sys.argv[1:] or DEFAULT_FILES
    for p in paths:
        report(p)
