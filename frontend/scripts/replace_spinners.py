from pathlib import Path
import re

root = Path(__file__).resolve().parents[1] / "src"
files = list(root.rglob("*.jsx")) + list(root.rglob("*.js"))

replacements = [
    (
        re.compile(
            r'<div className="py-5 text-center"><div className="spinner-border text-primary" role="status"\s*/?></div></div>',
            re.I,
        ),
        '<PageLoader label="Loading…" />',
    ),
    (
        re.compile(
            r'<div className="py-5 text-center"><div className="spinner-border text-primary"\s*/?></div></div>',
            re.I,
        ),
        '<PageLoader label="Loading…" />',
    ),
    (
        re.compile(
            r'<div className="py-4 text-center"><div className="spinner-border text-primary" role="status"\s*/?></div></div>',
            re.I,
        ),
        '<PageLoader label="Loading…" compact />',
    ),
    (
        re.compile(
            r'<div className="py-4 text-center"><div className="spinner-border spinner-border-sm text-primary" role="status"\s*/?></div></div>',
            re.I,
        ),
        '<PageLoader label="Loading…" size="sm" compact />',
    ),
    (
        re.compile(
            r'return <div className="py-5 text-center"><div className="spinner-border text-primary" role="status"\s*/?></div></div>;',
            re.I,
        ),
        'return <PageLoader label="Loading…" />;',
    ),
    (
        re.compile(
            r'<div className="spinner-border text-primary" role="status"\s*/?>',
            re.I,
        ),
        '<ApexLoader label="Loading…" />',
    ),
    (
        re.compile(
            r'<div className="spinner-border text-primary"\s*/?>',
            re.I,
        ),
        '<ApexLoader label="Loading…" />',
    ),
    (
        re.compile(
            r'<div className="spinner-border spinner-border-sm text-primary" role="status"\s*/?>',
            re.I,
        ),
        '<ApexLoader size="sm" label="Loading…" showDots={false} />',
    ),
    (
        re.compile(
            r'<div className="spinner-border spinner-border-sm"\s*/?>',
            re.I,
        ),
        '<ApexLoader size="sm" showDots={false} />',
    ),
    (
        re.compile(
            r'<div className="spinner-border text-danger" role="status"\s*/?>',
            re.I,
        ),
        '<ApexLoader label="Loading…" />',
    ),
    (
        re.compile(
            r'<div className="spinner-border spinner-border-sm text-danger" role="status"\s*/?>',
            re.I,
        ),
        '<InlineLoader label="Loading" />',
    ),
    (
        re.compile(
            r'<span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"\s*/?>',
            re.I,
        ),
        '<InlineLoader />',
    ),
]


def import_path_for(path: Path) -> str:
    rel = path.relative_to(root)
    depth = len(rel.parts) - 1
    if path.name == "App.jsx":
        return "./components/ApexLoader"
    if depth == 1:
        return "./ApexLoader"
    if depth == 2:
        return "../components/ApexLoader"
    return "../../components/ApexLoader"


def ensure_import(text: str, path: Path) -> str:
    uses = []
    for name in ("ApexLoader", "PageLoader", "InlineLoader"):
        if name in text:
            uses.append(name)
    if not uses:
        return text
    if "ApexLoader" in text and re.search(r"from ['\"].*ApexLoader['\"]", text):
        # merge missing named imports if any
        m = re.search(r"import\s*\{([^}]+)\}\s*from\s*['\"][^'\"]*ApexLoader['\"]", text)
        if m:
            existing = {x.strip() for x in m.group(1).split(",") if x.strip()}
            missing = [n for n in uses if n not in existing]
            if missing:
                new_names = ", ".join(sorted(existing.union(uses)))
                text = text[: m.start(1)] + f" {new_names} " + text[m.end(1) :]
            return text
    imp = f"import {{ {', '.join(uses)} }} from '{import_path_for(path)}';\n"
    lines = text.splitlines(True)
    last_imp = 0
    for i, line in enumerate(lines):
        if line.startswith("import "):
            last_imp = i
    lines.insert(last_imp + 1, imp)
    return "".join(lines)


changed = []
unchanged = []
for path in files:
    text = path.read_text(encoding="utf-8")
    if "spinner-border" not in text:
        continue
    orig = text
    for rx, rep in replacements:
        text = rx.sub(rep, text)
    if text == orig:
        unchanged.append(str(path.relative_to(root)))
        continue
    text = ensure_import(text, path)
    path.write_text(text, encoding="utf-8")
    changed.append(str(path.relative_to(root)))

print("changed", len(changed))
for c in changed:
    print(" ", c)
print("unchanged_with_spinner", len(unchanged))
for u in unchanged:
    print(" ", u)

rem = []
for path in files:
    if "spinner-border" in path.read_text(encoding="utf-8"):
        rem.append(str(path.relative_to(root)))
print("remaining", rem)
