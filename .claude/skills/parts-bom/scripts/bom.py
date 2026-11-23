#!/usr/bin/env python3
"""Draft a bill of materials for a VequIR product or library assembly.

    python bom.py <product or assembly directory>     e.g. products/LS1

Run it from the root of the repository that holds the directory, with the
other vequir repositories cloned beside it (as libraries.txt expects).
Standard library only: it reads the scripts, it does not run them.

Two sources, merged per library item:
  - schematic.json, when the product has one: one line per value (1k, 4k7),
    with its references. These counts are exact.
  - every assembly.py under it, following load_part and load_library into
    sub-assemblies (the wiring board, the 18650 holder): each `.add(...)` of
    an item. An add inside a `for` loop, or of a shape picked at run time,
    cannot be counted without running the script: it is listed with
    "count": null and where to look, so the count can be read from the code.

Prints JSON: {"product", "lines": [...], "made": [...], "unresolved": [...]}.
"""
import json
import re
import sys
from pathlib import Path

LOAD = re.compile(r'^(\w+)\s*=\s*load_(library|part)\("([^"]+)"\)', re.M)
ADD = re.compile(r'\.add\(\s*([\w.\[\]]+)')


def repo_root(path):
    for p in [path, *path.parents]:
        if (p / ".git").exists() or (p / "libraries.txt").exists() and (p / "products").exists():
            return p
    raise SystemExit(f"{path} is not inside a vequir repository")


def libraries(root):
    libs = [root / "library"]
    lt = root / "libraries.txt"
    if lt.exists():
        for line in lt.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                libs.append((root / line.split()[0]).resolve())
    return [lib for lib in libs if lib.is_dir()]


def repo_of(path):
    for p in path.parents:
        if p.name.startswith("vequir-"):
            return p.name
    return "?"


def title(item_dir):
    for name in ("description.md", "assembly.md", "product.md"):
        f = item_dir / name
        if f.exists():
            text = f.read_text().strip()
            if text.startswith("#"):
                return text.splitlines()[0].lstrip("# ").strip()
            first = re.split(r"(?<=[.:])\s", " ".join(text.split()), maxsplit=1)[0]
            return first[:100]
    return item_dir.name


def indent(line):
    return len(line) - len(line.lstrip())


def in_loop(lines, i):
    """Whether line i sits in the body of a for or while loop."""
    level = indent(lines[i])
    for j in range(i - 1, -1, -1):
        s = lines[j].strip()
        if not s or s.startswith("#"):
            continue
        if indent(lines[j]) < level:
            if re.match(r"(for|while)\b", s):
                return True
            level = indent(lines[j])
            if level == 0:
                return False
    return False


class Bom:
    def __init__(self, root):
        self.root = root
        self.libs = libraries(root)
        self.bought = {}     # item -> {"title", "repo", "count", "where": []}
        self.made = {}       # made-here parts -> same
        self.unresolved = []
        self.assemblies = set()  # items that are assemblies: their contents are counted instead

    def rel(self, path):
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(Path("..") / path.relative_to(self.root.parent))

    def find_library(self, name, here):
        for lib in self.libs:
            if (lib / name).is_dir():
                return lib / name
        raise SystemExit(f"{here}: load_library({name!r}) not found in {', '.join(map(str, self.libs))}")

    def key(self, item_dir):
        for lib in self.libs:
            try:
                return str(item_dir.relative_to(lib))
            except ValueError:
                pass
        return str(item_dir.relative_to(self.root))

    def note(self, table, item_dir, count, where):
        k = self.key(item_dir)
        e = table.setdefault(k, {"item": k, "title": title(item_dir), "repo": repo_of(item_dir),
                                 "count": 0, "where": []})
        if count is None or e["count"] is None:
            e["count"] = None
        else:
            e["count"] += count
        e["where"].append(where)

    def walk(self, directory, times, trail):
        """Count what directory's assembly.py places, `times` over; or the item itself."""
        script = directory / "assembly.py"
        if not script.exists():
            # a part: bought in if it lives in vequir-standard's library, else made here
            is_bought = repo_of(directory) == "vequir-standard" and "library" in directory.parts
            self.note(self.bought if is_bought else self.made, directory, times, trail)
            return
        self.assemblies.add(self.key(directory))
        text = script.read_text()
        lines = text.splitlines()
        loads = {}
        for m in LOAD.finditer(text):
            var, kind, name = m.groups()
            loads[var] = (self.find_library(name, script) if kind == "library"
                          else (directory / name).resolve())
        rel = self.rel(script)
        for i, line in enumerate(lines):
            for m in ADD.finditer(line):
                expr = m.group(1)
                var = expr.split(".")[0]
                where = f"{rel}:{i + 1}"
                if var not in loads or not expr.endswith(".result"):
                    self.unresolved.append({"where": where, "line": line.strip(),
                                            "why": "the shape is chosen at run time: read the code"})
                    continue
                if in_loop(lines, i):
                    n = None
                    self.unresolved.append({"where": where, "line": line.strip(),
                                            "why": "added in a loop: count the loop's items"})
                else:
                    n = 1
                self.walk(loads[var], None if times is None or n is None else times * n, where)


def schematic_lines(directory, bom):
    f = directory / "schematic.json"
    if not f.exists():
        return {}
    by = {}
    for c in json.loads(f.read_text()).get("components", []):
        item = c.get("item")
        if not item:
            continue
        k = (item, c.get("name", ""))
        by.setdefault(k, []).append(c["ref"])
    return by


def main(argv):
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(argv) == 2 else 2
    directory = Path(argv[1]).resolve()
    bom = Bom(repo_root(directory))
    bom.walk(directory, 1, "top")

    sch = schematic_lines(directory, bom)
    lines = []
    seen = set()
    for (item, value), refs in sorted(sch.items()):
        item_dir = bom.find_library(item, directory / "schematic.json")
        line = {"item": item, "value": value, "refs": sorted(refs), "count": len(refs),
                "count_from": "schematic", "title": title(item_dir),
                "bought": repo_of(item_dir) == "vequir-standard" and item not in bom.assemblies}
        if item in bom.assemblies:
            line["note"] = "an assembly: its parts are counted on their own lines"
        lines.append(line)
        seen.add(item)
    for item, e in sorted(bom.bought.items()):
        if item in seen:
            continue
        lines.append({"item": item, "value": "", "refs": [], "count": e["count"],
                      "count_from": "assembly" if e["count"] is not None else "read the code",
                      "title": e["title"], "bought": True, "where": e["where"]})
    made = [{"item": k, "title": e["title"], "count": e["count"], "where": e["where"]}
            for k, e in sorted(bom.made.items()) if k not in seen]
    out = {"product": str(directory.relative_to(bom.root)), "lines": lines, "made": made,
           "unresolved": bom.unresolved}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
