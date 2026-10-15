"""Fail if tracked runtime imports introduce non-stdlib dependencies.

Static import boundary, not a vulnerability or dynamic-import proof.
OS and bundled Python vulnerabilities are assessed by the image scanner.
"""
import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
modules = sorted((root / "maildemo").rglob("*.py"))
if not modules:
    raise SystemExit("Missing runtime source")
allowed = set(sys.stdlib_module_names) | {"maildemo"}
unknown = set()
for path in modules:
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            unknown.update(a.name.split(".")[0] for a in node.names if a.name.split(".")[0] not in allowed)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            name = node.module.split(".")[0]
            if name not in allowed:
                unknown.add(name)
if unknown:
    raise SystemExit("Unreviewed runtime dependency: " + ", ".join(sorted(unknown)))
print("PASS: static runtime imports remain within Python stdlib and maildemo")
