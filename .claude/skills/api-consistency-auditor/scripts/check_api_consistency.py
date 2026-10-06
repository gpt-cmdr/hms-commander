#!/usr/bin/env python3
"""Report-only static check of hms-commander API conventions.

Parses Python source with ``ast`` (nothing is imported or executed) and reports
findings for the automatable HMS-API rules described in
``../references/api-rules.md``. Exceptions are read from the repository
``.auditor.yaml``. Standard library only; PyYAML is used when installed.

Usage (from the repository root):
    python .claude/skills/api-consistency-auditor/scripts/check_api_consistency.py
    python .claude/skills/api-consistency-auditor/scripts/check_api_consistency.py hms_commander/HmsBasin.py --format json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SEVERITY_ORDER = {"suggestion": 1, "minor": 2, "major": 3}
PATH_PARAM = re.compile(r"(^|_)(path|file|dir|directory|folder)$")
DISCOURAGED_PROJECT_PARAMS = {"ras_object", "project", "hms_prj", "prj", "project_obj", "hms_project"}
DISCOURAGED_NAME = re.compile(r"(^|_)(num|geom)(_|$)")
NUMPY_PARAMS = re.compile(r"^\s*Parameters\s*\n\s*-{3,}", re.M)


@dataclass
class Finding:
    rule: str
    severity: str
    path: str
    line: int
    symbol: str
    message: str


def decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def load_config(path: Path | None) -> dict[str, set[str]]:
    """Return {section: {names}} for the sections this checker uses."""
    sections = ("exception_classes", "classmethod_classes", "log_call_exempt", "path_str_exempt")
    config: dict[str, set[str]] = {name: set() for name in sections}
    if path is None or not path.is_file():
        return config
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        for section in sections:
            for entry in data.get(section) or []:
                value = entry.get("class_name") or entry.get("qualname")
                if value:
                    config[section].add(str(value))
        return config
    except ImportError:
        pass
    current = None
    for line in text.splitlines():
        top = re.match(r"^([A-Za-z_][\w]*):\s*$", line)
        if top:
            current = top.group(1)
            continue
        if line and not line[0].isspace():
            current = None
            continue
        item = re.match(r"^\s*-?\s*(class_name|qualname):\s*['\"]?([\w.]+)", line)
        if item and current in config:
            config[current].add(item.group(2))
    return config


def find_config(start: Path) -> Path | None:
    for directory in [start, *start.parents]:
        candidate = directory / ".auditor.yaml"
        if candidate.is_file():
            return candidate
    return None


def package_exports(module_path: Path) -> set[str]:
    """Names listed in __all__ of every package __init__ above the module."""
    exports: set[str] = set()
    directory = module_path.parent
    while (directory / "__init__.py").is_file():
        tree = ast.parse((directory / "__init__.py").read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
            ):
                try:
                    exports.update(ast.literal_eval(node.value))
                except ValueError:
                    pass
        directory = directory.parent
    return exports


def class_kind(node: ast.ClassDef) -> str:
    decorators = {decorator_name(d) for d in node.decorator_list}
    bases = [ast.unparse(b) for b in node.bases]
    if "dataclass" in decorators:
        return "dataclass"
    if any(re.search(r"(Error|Exception|Warning)$", b) for b in bases):
        return "exception"
    if any(re.search(r"(Enum|TypedDict|NamedTuple|Protocol|ABC)$", b) for b in bases):
        return "special"
    return "plain"


def is_private_module(path: Path) -> bool:
    return any(part.startswith("_") and part != "__init__.py" for part in path.parts)


def check_function_contract(func, qual, rel, public_api, findings, path_exempt=frozenset()):
    args = [a for a in func.args.posonlyargs + func.args.args + func.args.kwonlyargs if a.arg not in ("self", "cls")]
    defaults = {}
    positional = func.args.posonlyargs + func.args.args
    for arg, default in zip(positional[len(positional) - len(func.args.defaults):], func.args.defaults):
        defaults[arg.arg] = default
    for arg, default in zip(func.args.kwonlyargs, func.args.kw_defaults):
        if default is not None:
            defaults[arg.arg] = default

    def add(rule, severity, message):
        findings.append(Finding(rule, severity, rel, func.lineno, qual, message))

    for arg in args:
        if arg.arg in DISCOURAGED_PROJECT_PARAMS:
            add("HMS-API-05", "major", f"project context parameter '{arg.arg}' should be 'hms_object=None'")
        if arg.arg == "hms_object":
            default = defaults.get("hms_object")
            if default is None or ast.unparse(default) != "None":
                add("HMS-API-05", "major", "'hms_object' must default to None (global hms project)")
        if not public_api:
            continue
        if DISCOURAGED_NAME.search(arg.arg):
            add("HMS-API-06", "minor", f"parameter '{arg.arg}' uses a discouraged abbreviation (num/geom)")
        annotation = ast.unparse(arg.annotation) if arg.annotation else ""
        if f"{qual}.{arg.arg}" in path_exempt:
            continue
        if PATH_PARAM.search(arg.arg) and annotation in ("str", "Path", "pathlib.Path", "Optional[Path]", "Optional[str]"):
            add("HMS-API-07", "minor", f"path parameter '{arg.arg}: {annotation}' should accept Union[str, Path]")
    if not public_api:
        return
    if func.returns is None:
        add("HMS-API-08", "suggestion", "public method has no return annotation")
    doc = ast.get_docstring(func)
    if not doc:
        add("HMS-API-09", "minor", "public method has no docstring")
    elif NUMPY_PARAMS.search(doc):
        add("HMS-API-09", "suggestion", "NumPy-style 'Parameters' section; repository convention is Google-style 'Args:'")


def check_file(path: Path, root: Path, config: dict[str, set[str]], include_private: bool) -> list[Finding]:
    findings: list[Finding] = []
    rel = path.resolve().relative_to(root.resolve()).as_posix() if path.resolve().is_relative_to(root.resolve()) else path.as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    private_module = is_private_module(Path(rel))
    public_api = include_private or not private_module
    exports = package_exports(path) if public_api else set()

    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or class_kind(node) != "plain":
            continue
        name = node.name
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        instance_class = name in config["exception_classes"]
        if instance_class:
            for method in methods:
                if not method.name.startswith("_"):
                    check_function_contract(method, f"{name}.{method.name}", rel, public_api, findings,
                                            config["path_str_exempt"])
            continue
        if public_api and not name.startswith("_") and exports and name not in exports:
            findings.append(Finding("HMS-API-10", "minor", rel, node.lineno, name,
                                    "public class is not listed in the package __all__"))
        for method in methods:
            decorators = [decorator_name(d) for d in method.decorator_list]
            qual = f"{name}.{method.name}"
            if method.name == "__init__":
                findings.append(Finding("HMS-API-01", "major", rel, method.lineno, qual,
                                        "static namespace class defines __init__; list it in .auditor.yaml exception_classes if instance state is required"))
                continue
            if method.name.startswith("_") or "property" in decorators:
                continue
            if "staticmethod" not in decorators:
                if "classmethod" in decorators and name in config["classmethod_classes"]:
                    pass
                elif "classmethod" in decorators:
                    findings.append(Finding("HMS-API-02", "major", rel, method.lineno, qual,
                                            "@classmethod in a static class not listed in .auditor.yaml classmethod_classes"))
                else:
                    findings.append(Finding("HMS-API-02", "major", rel, method.lineno, qual,
                                            "public method in static class lacks @staticmethod (instance method)"))
            if "log_call" in decorators:
                for wrapper in ("staticmethod", "classmethod"):
                    if wrapper in decorators and decorators.index("log_call") < decorators.index(wrapper):
                        findings.append(Finding("HMS-API-03", "major", rel, method.lineno, qual,
                                                f"@log_call is above @{wrapper}; place @{wrapper} first"))
            elif public_api and qual not in config["log_call_exempt"]:
                findings.append(Finding("HMS-API-04", "minor", rel, method.lineno, qual,
                                        "public method lacks @log_call"))
            check_function_contract(method, qual, rel, public_api, findings, config["path_str_exempt"])
    return findings


def iter_python_files(targets: list[Path]):
    for target in targets:
        if target.is_dir():
            for path in sorted(target.rglob("*.py")):
                if "__pycache__" in path.parts or path.name == "__init__.py":
                    continue
                yield path
        elif target.suffix == ".py":
            yield target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", type=Path, default=[Path("hms_commander")])
    parser.add_argument("--config", type=Path, help="Exception file (default: nearest .auditor.yaml)")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Root for reported relative paths")
    parser.add_argument("--include-private", action="store_true",
                        help="Apply public-API rules (04-10) to private modules too")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--fail-on", choices=("none", "suggestion", "minor", "major"), default="none",
                        help="Exit 1 when a finding at or above this severity exists (default: report only)")
    args = parser.parse_args(argv)

    config_path = args.config or find_config(args.root.resolve())
    config = load_config(config_path)
    findings: list[Finding] = []
    files = list(iter_python_files(args.targets))
    for path in files:
        findings.extend(check_file(path, args.root, config, args.include_private))

    if args.format == "json":
        print(json.dumps({"config": str(config_path) if config_path else None, "files": len(files),
                          "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: {f.rule} [{f.severity}] {f.symbol}: {f.message}")
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.rule] = counts.get(f.rule, 0) + 1
        summary = ", ".join(f"{rule}={count}" for rule, count in sorted(counts.items())) or "no findings"
        print(f"\n{len(files)} files checked; config: {config_path or 'none'}; {summary}")

    if args.fail_on != "none":
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[f.severity] >= threshold for f in findings):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
