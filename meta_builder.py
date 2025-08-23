#!/usr/bin/env python3
"""
Meta Config Builder
- Walk a project folder OR parse structure.txt + contents.txt
- Extracts:
  - modules, functions, classes, methods, signatures, docstrings/JSDoc
  - web routes (Flask/FastAPI/Express), CLI commands (click / argparse)
  - simple "agent" and "tool" hints (file names, decorators, keywords)
  - dependency hints from package.json / pyproject.toml / requirements*.txt
- Emits meta.config.json (LLM-friendly) and optional meta.config.yaml
"""

from __future__ import annotations
import os, re, json, sys, argparse, ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------- Utilities

PY_EXT = {".py"}
JS_EXT = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}

ROUTE_HINTS_PY = [
    r"@app\.route\((?P<args>.+)\)",
    r"@(?:api|router)\.(?:get|post|put|patch|delete)\((?P<args>.+)\)",
    r"@(?:fastapi\.)?APIRouter\(\).(?:get|post|put|patch|delete)\((?P<args>.+)\)",
]
ROUTE_HINTS_JS = [
    r"\bapp\.(get|post|put|patch|delete)\s*\(\s*(?P<path>['\"`][^'\"`]+['\"`])",
    r"\brouter\.(get|post|put|patch|delete)\s*\(\s*(?P<path>['\"`][^'\"`]+['\"`])",
    r"\bexpress\.Router\(\)\.(get|post|put|patch|delete)\s*\(\s*(?P<path>['\"`][^'\"`]+['\"`])",
]
CLI_HINTS_PY = [
    r"@click\.command\(",
    r"\bargparse\.ArgumentParser\(",
]
AGENT_TOOL_HINTS = [
    r"\bagent\b",
    r"\btool\b",
    r"@tool\b",
    r"\bOpenAI\b",
    r"\bAnthropic\b",
    r"\bChatOpenAI\b",
    r"\bfunction_call(ing)?\b",
    r"\bassist(?:ant)?_tools?\b",
]

JS_FUNC_RE = re.compile(
    r"""
    (?:
        /\*\*([\s\S]*?)\*/\s*      # JSDoc block (group 1)
    )?
    (?:
        export\s+(?:default\s+)?function\s+(?P<fn1>[A-Za-z0-9_$]+)\s*\((?P<sig1>[^)]*)\) |
        export\s+const\s+(?P<fn2>[A-Za-z0-9_$]+)\s*=\s*\((?P<sig2>[^)]*)\)\s*=> |
        function\s+(?P<fn3>[A-Za-z0-9_$]+)\s*\((?P<sig3>[^)]*)\)
    )
    """,
    re.VERBOSE,
)

JS_CLASS_RE = re.compile(
    r"""
    (?:
        /\*\*([\s\S]*?)\*/\s*      # JSDoc block (group 1)
    )?
    export\s+class\s+(?P<cls1>[A-Za-z0-9_$]+)\s*|
    class\s+(?P<cls2>[A-Za-z0-9_$]+)\s*
    """,
    re.VERBOSE,
)


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def safe_json_load(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:
        return None


def detect_language(path: Path) -> str:
    if path.suffix in PY_EXT:
        return "python"
    if path.suffix in JS_EXT:
        return "javascript" if path.suffix in {".js", ".mjs", ".cjs", ".jsx"} else "typescript"
    return "other"


# ---------- Parsers: Python

def parse_python_file(path: Path) -> Dict[str, Any]:
    src = read_text(path)
    out: Dict[str, Any] = {
        "path": str(path.as_posix()),
        "language": "python",
        "functions": [],
        "classes": [],
        "routes": [],
        "cli": [],
        "agent_tool_hints": [],
        "doc": extract_module_docstring(src),
    }
    try:
        tree = ast.parse(src)
    except Exception:
        # If AST fails, still try regex routes/CLI and hints
        return fill_py_with_regex(out, src)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            out["functions"].append(extract_py_function(node))
            # decorator-based route discovery
            route = extract_py_route_from_decorators(node)
            if route:
                out["routes"].append(route)
        elif isinstance(node, ast.ClassDef):
            out["classes"].append(extract_py_class(node))

    # module-level route or CLI hints
    out["routes"].extend(find_regex_matches(src, ROUTE_HINTS_PY, kind="python"))
    out["cli"].extend(find_regex_matches(src, CLI_HINTS_PY, kind="cli"))
    out["agent_tool_hints"].extend(find_regex_matches(src, AGENT_TOOL_HINTS, kind="hint"))
    return out


def extract_module_docstring(src: str) -> Optional[str]:
    try:
        return ast.get_docstring(ast.parse(src))
    except Exception:
        return None


def extract_py_function(fn: ast.AST) -> Dict[str, Any]:
    assert isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
    args = []
    for a in fn.args.args:
        if a.arg != "self":
            args.append(a.arg)
    # *args / **kwargs
    if fn.args.vararg:
        args.append("*" + fn.args.vararg.arg)
    if fn.args.kwarg:
        args.append("**" + fn.args.kwarg.arg)

    decorators = []
    for d in fn.decorator_list:
        try:
            decorators.append(ast.unparse(d))
        except Exception:
            decorators.append(type(d).__name__)

    return {
        "name": fn.name,
        "kind": "async_function" if isinstance(fn, ast.AsyncFunctionDef) else "function",
        "signature": f"({', '.join(args)})",
        "doc": ast.get_docstring(fn),
        "decorators": decorators,
    }


def extract_py_class(cls: ast.ClassDef) -> Dict[str, Any]:
    methods = []
    for n in cls.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(extract_py_function(n))
    bases = []
    for b in cls.bases:
        try:
            bases.append(ast.unparse(b))
        except Exception:
            bases.append(type(b).__name__)
    return {
        "name": cls.name,
        "bases": bases,
        "doc": ast.get_docstring(cls),
        "methods": methods,
    }


def extract_py_route_from_decorators(fn: ast.AST) -> Optional[Dict[str, Any]]:
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    for d in fn.decorator_list:
        try:
            s = ast.unparse(d)
        except Exception:
            continue
        if ".route(" in s or re.search(r"\.(get|post|put|patch|delete)\(", s):
            return {"handler": getattr(fn, "name", "unknown"), "decorator": s}
    return None


def fill_py_with_regex(out: Dict[str, Any], src: str) -> Dict[str, Any]:
    out["routes"].extend(find_regex_matches(src, ROUTE_HINTS_PY, kind="python"))
    out["cli"].extend(find_regex_matches(src, CLI_HINTS_PY, kind="cli"))
    out["agent_tool_hints"].extend(find_regex_matches(src, AGENT_TOOL_HINTS, kind="hint"))
    return out


# ---------- Parsers: JS/TS

def parse_js_like_file(path: Path) -> Dict[str, Any]:
    src = read_text(path)
    lang = detect_language(path)
    out: Dict[str, Any] = {
        "path": str(path.as_posix()),
        "language": lang,
        "functions": [],
        "classes": [],
        "routes": [],
        "cli": [],
        "agent_tool_hints": [],
        "doc": None,
        "exports": [],
    }

    # Functions & JSDoc
    for m in JS_FUNC_RE.finditer(src):
        jsdoc = (m.group(1) or "").strip() or None
        name = m.group("fn1") or m.group("fn2") or m.group("fn3")
        sig = m.group("sig1") or m.group("sig2") or m.group("sig3") or ""
        out["functions"].append({"name": name, "signature": f"({sig})", "doc": jsdoc})
        if "export" in src[m.start(): m.end()]:
            out["exports"].append(name)

    # Classes
    for m in JS_CLASS_RE.finditer(src):
        jsdoc = (m.group(1) or "").strip() or None
        name = m.group("cls1") or m.group("cls2")
        out["classes"].append({"name": name, "doc": jsdoc})
        if "export" in src[m.start(): m.end()]:
            out["exports"].append(name)

    # Routes
    for pat in ROUTE_HINTS_JS:
        for m in re.finditer(pat, src):
            p = (m.groupdict().get("path") or "").strip().strip("`'\"")
            out["routes"].append({"path": p, "framework": "express_like"})

    # CLI (basic)
    if re.search(r"\byargs\b|\bcommander\b|\bcaporal\b|\bnpx\b", src):
        out["cli"].append({"hint": "cli_lib_detected"})

    # Agent/tool hints
    out["agent_tool_hints"].extend(find_regex_matches(src, AGENT_TOOL_HINTS, kind="hint"))
    return out


# ---------- Regex helpers

def find_regex_matches(src: str, patterns: List[str], kind: str) -> List[Dict[str, Any]]:
    hits = []
    for pat in patterns:
        for m in re.finditer(pat, src, flags=re.IGNORECASE):
            snippet = src[max(0, m.start()-60): m.end()+60]
            if kind == "python":
                hits.append({"decorator": m.group(0), "context": snippet.strip()})
            elif kind == "cli":
                hits.append({"match": m.group(0), "context": snippet.strip()})
            else:
                hits.append({"match": m.group(0)})
    return hits


# ---------- Dependency discovery

def discover_dependencies(root: Path) -> Dict[str, Any]:
    deps: Dict[str, Any] = {}
    # Node
    pkg = root / "package.json"
    if pkg.exists():
        data = safe_json_load(read_text(pkg)) or {}
        deps["node"] = {
            "name": data.get("name"),
            "version": data.get("version"),
            "dependencies": data.get("dependencies", {}),
            "devDependencies": data.get("devDependencies", {}),
            "scripts": data.get("scripts", {}),
        }
    # Python
    reqs = {}
    for f in ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]:
        p = root / f
        if p.exists():
            reqs[f] = [ln.strip() for ln in read_text(p).splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if reqs:
        deps["python_requirements"] = reqs
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        deps["pyproject_toml_hint"] = True
    return deps


# ---------- Structure/Contents.txt mode

def parse_structure_and_contents(structure_txt: Path, contents_txt: Path, project_root: Path) -> List[Dict[str, Any]]:
    """
    structure.txt: output of a tree-like listing (best effort)
    contents.txt: concatenated files with headers like:
        >>> FILE: relative/path/to/file.py
        <file content...>
        >>> END
    """
    files: List[Path] = []

    if structure_txt.exists():
        for ln in read_text(structure_txt).splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"): 
                continue
            # naive: collect lines that look like files with extensions
            if re.search(r"\.[a-zA-Z0-9]{1,5}$", ln) and not ln.endswith(("/", "\\")):
                files.append(project_root / ln)

    file_blobs: Dict[Path, str] = {}
    if contents_txt.exists():
        blob = read_text(contents_txt)
        # split by headers
        for m in re.finditer(r">>>\s*FILE:\s*(.+)\n", blob):
            start = m.end()
            path_rel = m.group(1).strip()
            end_m = re.search(r"\n>>> END\b", blob[start:], re.MULTILINE)
            end = start + (end_m.start() if end_m else 0)
            file_blobs[project_root / path_rel] = blob[start:end]

    # Parse each discovered file
    modules = []
    seen = set()
    for p in sorted(set(files) | set(file_blobs.keys())):
        lang = detect_language(p)
        src = file_blobs.get(p, "")
        if not src:
            # If we have a real file on disk, load it
            if p.exists():
                src = read_text(p)
            else:
                # skip unknown
                continue

        # temp-write in memory path? We can parse from string directly for py/js
        if lang == "python":
            modules.append(parse_python_source_virtual(p, src))
        elif lang in {"javascript", "typescript"}:
            modules.append(parse_js_source_virtual(p, src, lang))
        else:
            # keep a minimal record
            modules.append({"path": str(p.as_posix()), "language": lang, "bytes": len(src)})
        seen.add(p.as_posix())
    return modules


def parse_python_source_virtual(path: Path, src: str) -> Dict[str, Any]:
    out = {
        "path": str(path.as_posix()),
        "language": "python",
        "functions": [],
        "classes": [],
        "routes": [],
        "cli": [],
        "agent_tool_hints": [],
        "doc": extract_module_docstring(src)
    }
    try:
        tree = ast.parse(src)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out["functions"].append(extract_py_function(node))
                route = extract_py_route_from_decorators(node)
                if route:
                    out["routes"].append(route)
            elif isinstance(node, ast.ClassDef):
                out["classes"].append(extract_py_class(node))
        out["routes"].extend(find_regex_matches(src, ROUTE_HINTS_PY, kind="python"))
        out["cli"].extend(find_regex_matches(src, CLI_HINTS_PY, kind="cli"))
        out["agent_tool_hints"].extend(find_regex_matches(src, AGENT_TOOL_HINTS, kind="hint"))
    except Exception:
        out = fill_py_with_regex(out, src)
    return out


def parse_js_source_virtual(path: Path, src: str, lang: str) -> Dict[str, Any]:
    out = {
        "path": str(path.as_posix()),
        "language": lang,
        "functions": [],
        "classes": [],
        "routes": [],
        "cli": [],
        "agent_tool_hints": [],
        "doc": None,
        "exports": [],
    }
    for m in JS_FUNC_RE.finditer(src):
        jsdoc = (m.group(1) or "").strip() or None
        name = m.group("fn1") or m.group("fn2") or m.group("fn3")
        sig = m.group("sig1") or m.group("sig2") or m.group("sig3") or ""
        out["functions"].append({"name": name, "signature": f"({sig})", "doc": jsdoc})
        if "export" in src[m.start(): m.end()]:
            out["exports"].append(name)
    for m in JS_CLASS_RE.finditer(src):
        jsdoc = (m.group(1) or "").strip() or None
        name = m.group("cls1") or m.group("cls2")
        out["classes"].append({"name": name, "doc": jsdoc})
        if "export" in src[m.start(): m.end()]:
            out["exports"].append(name)
    for pat in ROUTE_HINTS_JS:
        for m in re.finditer(pat, src):
            p = (m.groupdict().get("path") or "").strip().strip("`'\"")
            out["routes"].append({"path": p, "framework": "express_like"})
    if re.search(r"\byargs\b|\bcommander\b|\bcaporal\b|\bnpx\b", src):
        out["cli"].append({"hint": "cli_lib_detected"})
    out["agent_tool_hints"].extend(find_regex_matches(src, AGENT_TOOL_HINTS, kind="hint"))
    return out


# ---------- Main build

def build_meta(project_root: Path,
               structure_txt: Optional[Path],
               contents_txt: Optional[Path]) -> Dict[str, Any]:
    project_root = project_root.resolve()
    meta: Dict[str, Any] = {
        "project": project_root.name,
        "root": str(project_root.as_posix()),
        "modules": [],
        "agents": [],
        "tools": [],
        "routes": [],
        "cli_commands": [],
        "dependencies": discover_dependencies(project_root),
        "notes": {
            "generated_by": "meta_builder.py",
            "purpose": "LLM-friendly config for code understanding and agent wiring",
            "version": 1
        }
    }

    modules: List[Dict[str, Any]] = []

    # Mode 2: structure+contents
    if structure_txt and contents_txt and structure_txt.exists() and contents_txt.exists():
        modules = parse_structure_and_contents(structure_txt, contents_txt, project_root)
    else:
        # Mode 1: walk filesystem
        for p in project_root.rglob("*"):
            if p.is_file():
                if p.suffix in PY_EXT:
                    modules.append(parse_python_file(p))
                elif p.suffix in JS_EXT:
                    modules.append(parse_js_like_file(p))

    # Aggregate top-level routes/cli and agent/tool hints
    meta["modules"] = modules
    for m in modules:
        for r in m.get("routes", []):
            meta["routes"].append({"module": m["path"], **r})
        for c in m.get("cli", []):
            meta["cli_commands"].append({"module": m["path"], **c})
        for h in m.get("agent_tool_hints", []):
            # very light heuristic to surface likely agent/tool files
            if re.search(r"tool|agent", json.dumps(h), flags=re.I):
                meta["tools"].append({"module": m["path"], "hint": h})

    # De-dupe lists
    def dedupe(seq):
        seen = set()
        out = []
        for x in seq:
            key = json.dumps(x, sort_keys=True)
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out

    meta["routes"] = dedupe(meta["routes"])
    meta["cli_commands"] = dedupe(meta["cli_commands"])
    meta["tools"] = dedupe(meta["tools"])

    return meta


def main():
    ap = argparse.ArgumentParser(description="Build meta config for a project")
    ap.add_argument("--root", default=".", help="Project root directory")
    ap.add_argument("--structure", default=None, help="Path to structure.txt (optional)")
    ap.add_argument("--contents", default=None, help="Path to contents.txt (optional)")
    ap.add_argument("--yaml", action="store_true", help="Also write meta.config.yaml")
    args = ap.parse_args()

    root = Path(args.root)
    structure = Path(args.structure) if args.structure else None
    contents = Path(args.contents) if args.contents else None

    meta = build_meta(root, structure, contents)
    out_json = root / "meta.config.json"
    out_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_json}")

    if args.yaml:
        try:
            import yaml  # type: ignore
            out_yaml = root / "meta.config.yaml"
            out_yaml.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), encoding="utf-8")
            print(f"Wrote {out_yaml}")
        except Exception:
            print("PyYAML not installed; skipped YAML output.", file=sys.stderr)


if __name__ == "__main__":
    main()
