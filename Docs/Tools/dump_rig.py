"""Dump CR_Mage_FootIK graph in structured form. One-shot helper."""
import json
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(path: str, mode: str = "all") -> None:
    d = json.loads(Path(path).read_text(encoding="utf-8"))

    if mode in ("all", "summary"):
        print("=== TOP-LEVEL ===")
        print(f"asset_path = {d.get('asset_path')}")
        print(f"graph_name = {d.get('graph_name')}")
        print(f"node_count = {d.get('node_count')}")
        print(f"link_count = {d.get('link_count')}")
        print()

    if mode in ("all", "nodes"):
        print("=== NODES (name | struct_name | node_class) ===")
        for n in d["nodes"]:
            name = n.get("name", "?")
            sn = n.get("struct_name", "")
            nc = n.get("node_class", "")
            sp = n.get("struct_path", "")
            line = f"  {name:30s} | struct={sn or '-':40s} | class={nc or '-'}"
            print(line)
            if sp and sp != sn:
                print(f"  {'':30s} | path={sp}")
        print()

    if mode in ("all", "pins"):
        print("=== NODE PINS (with defaults / metadata) ===")
        for n in d["nodes"]:
            name = n.get("name", "?")
            pins = n.get("pins") or []
            print(f"-- {name}  ({n.get('struct_name') or n.get('node_class')}) --")
            for p in pins:
                pname = p.get("name", "?")
                pdir = p.get("direction", "?")
                ptype = p.get("type", "?")
                dv = p.get("default_value")
                extra = {k: v for k, v in p.items()
                        if k not in ("name", "direction", "type", "default_value", "connected_to", "id")}
                line = f"    [{pdir:>6s}] {pname:30s} : {ptype}"
                if dv is not None and dv != "":
                    line += f"  = {dv!r}"
                print(line)
                if extra:
                    print(f"           extra={extra}")
            print()
        print()

    if mode in ("all", "links"):
        print("=== LINKS ===")
        for i, l in enumerate(d["links"]):
            src = l.get("source") or l.get("from") or l.get("source_pin")
            dst = l.get("target") or l.get("to") or l.get("target_pin")
            print(f"  [{i:02d}] {src}  ->  {dst}")
        print()

    if mode == "by_var":
        # Group VariableNodes by which variable they read/write
        print("=== VARIABLE NODES ===")
        for n in d["nodes"]:
            if n.get("node_class") != "VariableNode":
                continue
            name = n.get("name")
            pins = n.get("pins") or []
            for p in pins:
                print(f"  {name:24s}  pin={p.get('name')}  type={p.get('type')}  dir={p.get('direction')}  default={p.get('default_value')!r}")
            print()


if __name__ == "__main__":
    file_arg = sys.argv[1] if len(sys.argv) > 1 else (
        r"C:\Users\bong9\.claude\projects\D--Projects-Guide-CustomFootIK\6125f4d6-cfef-4941-a565-2f2e64179c57\tool-results\mcp-monolith-animation_query-1779938450516.txt"
    )
    mode_arg = sys.argv[2] if len(sys.argv) > 2 else "all"
    main(file_arg, mode_arg)
