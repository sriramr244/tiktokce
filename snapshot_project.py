#!/usr/bin/env python3
"""
snapshot_project.py
Create two portable snapshots of a codebase:

1) structure.txt  – a tree-like listing (stable, sorted)
2) contents.txt   – concatenated file contents with clear FILE/END markers

Features
- Include/exclude globs (multiple) and extension filters
- Skips binaries by default; size limits with per-file override
- Secrets redaction (API keys, tokens, .env values) before writing
- Deterministic ordering for reproducible snapshots
- UTF-8 read with safe fallback; if not decodable => note and skip

Usage
  python snapshot_project.py --root ./tiktokce
  python snapshot_project.py --root . --out-structure structure.txt --out-contents contents.txt \
      --include-ext .py,.txt,.md,.json,.yaml,.yml,.toml \
      --exclude '**/.git/**' '**/dist/**' '**/build/**' '**/__pycache__/**' '**/.DS_Store' '**/data/*.mp4' '**/data/*.mp3' \
      --max-bytes 200000

Tip: After generating the two files, run the meta builder:
  python meta_builder.py --root ./tiktokce --structure structure.txt --contents contents.txt --yaml
"""

from __future__ import annotations
import argparse, fnmatch, hashlib, io, os, re, sys
from pathlib import Path
from typing import Iterable, List, Tuple

DEFAULT_EXCLUDES = [
    "**/.git/**", "**/.github/**", "**/.idea/**", "**/.vscode/**", "**/__pycache__/**",
    "**/node_modules/**", "**/dist/**", "**/build/**", "**/*.egg-info/**",
    "**/.DS_Store", "**/*.pyc", "**/*.pyo", "**/.pytest_cache/**",
    "**/*.whl", "**/*.tar.gz", "**/*.zip",
    "**/coverage/**", "**/.mypy_cache/**",
    # large media by default
    "**/*.mp4", "**/*.mp3", "**/*.mov", "**/*.wav", "**/*.gif", "**/*.png", "**/*.jpg", "**/*.jpeg",
    # notebooks can be huge/noisy; include if you want
    "**/*.ipynb",
]

DEFAULT_INCLUDE_EXT = [
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".env.example",
    ".sh", ".bat", ".ps1", ".dockerfile", ".Dockerfile",
]

# Very light secret redaction patterns (best-effort; extend as needed)
SECRET_PATTERNS = [
    # OpenAI keys
    r"(?i)(OPENAI_API_KEY\s*=\s*)(['\"]?)(sk-[\w\-]{10,})\2",
    r"(?i)(OPENAI_API_KEY\s*[:=]\s*)(['\"]?)(sk-proj-[\w\-]{10,})\2",
    # Bearer tokens, generic API tokens
    r"(?i)(Authorization\s*:\s*Bearer\s+)([A-Za-z0-9\.\-_]{10,})",
    r"(?i)(api[_\- ]?key\s*[:=]\s*)(['\"]?)([A-Za-z0-9\-_]{16,})\2",
    # AWS-ish
    r"(?i)(AWS_ACCESS_KEY_ID\s*=\s*)(['\"]?)(AKIA[0-9A-Z]{12,})\2",
    r"(?i)(AWS_SECRET_ACCESS_KEY\s*=\s*)(['\"]?)([A-Za-z0-9/+=]{30,})\2",
]

REDACTION = r"\1\2***REDACTED***\2"

BINARY_SNIFF_BYTES = 2048


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(BINARY_SNIFF_BYTES)
        if b"\x00" in chunk:
            return True
        # Heuristic: lots of non-text bytes
        text_like = sum(c in b"\t\r\n\f\b" or 32 <= c <= 126 for c in chunk)
        return text_like / max(1, len(chunk)) < 0.85
    except Exception:
        return False


def normalize_globs(globs: Iterable[str]) -> List[str]:
    return [g.strip() for g in globs if g and g.strip()]


def matches_any(path: Path, globs: Iterable[str], root: Path) -> bool:
    # Use posix form for stable matching
    s = path.relative_to(root).as_posix()
    for g in globs:
        if fnmatch.fnmatch(s, g):
            return True
    return False


def should_include_file(path: Path, root: Path, include_exts: List[str], excludes: List[str]) -> bool:
    if matches_any(path, excludes, root):
        return False
    if include_exts:
        return path.suffix.lower() in {e.lower() for e in include_exts}
    return True


def read_text_lossy(p: Path, max_bytes: int) -> Tuple[str, bool]:
    try:
        raw = p.read_bytes()
    except Exception as e:
        return f"Could not read file {p.name}: {e}", False

    truncated = False
    if max_bytes and len(raw) > max_bytes:
        raw = raw[:max_bytes]
        truncated = True

    # try utf-8 first, fallback to latin-1
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            txt = raw.decode("latin-1")
        except Exception as e:
            return f"Could not decode file {p.name}: {e}", False

    return (txt + ("\n\n# [TRUNCATED]\n" if truncated else "")), True


def redact_secrets(text: str) -> str:
    redacted = text
    for pat in SECRET_PATTERNS:
        redacted = re.sub(pat, REDACTION, redacted)
    return redacted


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def build_structure(root: Path, files: List[Path]) -> str:
    # Render a simple, stable tree-only list
    out_lines = [f"{root.name}/"]
    for p in sorted(files, key=lambda x: x.as_posix()):
        rel = p.relative_to(root).as_posix()
        out_lines.append(f"    {rel if rel else '.'}")
    return "\n".join(out_lines) + "\n"


def build_contents(root: Path, files: List[Path], max_bytes: int) -> str:
    buf = io.StringIO()
    buf.write(f"{root.name}/\n")
    for p in sorted(files, key=lambda x: x.as_posix()):
        rel = p.relative_to(root).as_posix()
        buf.write(f"    {rel}\n\n")
        buf.write(f"    --- Content of {p.name} ---\n")
        if is_binary(p):
            buf.write(f"    Skipped binary file.\n")
            sha = hash_file(p)
            if sha:
                buf.write(f"    SHA256: {sha}\n")
        else:
            txt, ok = read_text_lossy(p, max_bytes)
            txt = redact_secrets(txt)
            # indent content body for readability
            indented = "\n".join(("    " + line) for line in txt.splitlines())
            buf.write(indented + ("\n" if not indented.endswith("\n") else ""))
        buf.write(f"\n    --- End of {p.name} ---\n\n")
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description="Create structure.txt and contents.txt snapshots for a project.")
    ap.add_argument("--root", required=True, help="Project root directory")
    ap.add_argument("--out-structure", default="structure.txt", help="Output path for structure snapshot")
    ap.add_argument("--out-contents", default="contents.txt", help="Output path for contents snapshot")
    ap.add_argument("--exclude", nargs="*", default=DEFAULT_EXCLUDES, help="Glob patterns to exclude")
    ap.add_argument("--include-ext", default=",".join(DEFAULT_INCLUDE_EXT),
                    help="Comma-separated list of extensions to include (leave empty to include all)")
    ap.add_argument("--max-bytes", type=int, default=300_000,
                    help="Per-file max bytes included in contents.txt (0 = unlimited)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[error] root not found: {root}", file=sys.stderr)
        sys.exit(1)

    include_exts = [e.strip() for e in (args.include_ext.split(",") if args.include_ext else []) if e.strip()]
    excludes = normalize_globs(args.exclude)

    # collect candidate files
    files: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if should_include_file(p, root, include_exts, excludes):
            files.append(p)

    # write structure
    structure = build_structure(root, files)
    Path(args.out_structure).write_text(structure, encoding="utf-8")
    print(f"[ok] wrote {args.out_structure} ({len(files)} files listed)")

    # write contents
    contents = build_contents(root, files, max_bytes=args.max_bytes)
    Path(args.out_contents).write_text(contents, encoding="utf-8")
    print(f"[ok] wrote {args.out_contents}")

if __name__ == "__main__":
    main()
