#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

TIMEOUT_SECONDS = 60
INCLUDE_SUFFIXES = {".py", ".sh"}
EXCLUDE_NAME = "test.py"


def code_line_count(file_path: Path, start_time: float) -> int:
    count = 0
    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if time.monotonic() - start_time > TIMEOUT_SECONDS:
                raise TimeoutError("统计超时：超过 60 秒")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            count += 1
    return count


def collect_files(root: Path, start_time: float) -> Dict[Path, int]:
    result: Dict[Path, int] = {}
    for path in sorted(root.rglob("*")):
        if time.monotonic() - start_time > TIMEOUT_SECONDS:
            raise TimeoutError("统计超时：超过 60 秒")
        if not path.is_file():
            continue
        if path.suffix not in INCLUDE_SUFFIXES:
            continue
        if path.name == EXCLUDE_NAME and path.parent == root:
            continue
        result[path] = code_line_count(path, start_time)
    return result


def build_tree(files: Dict[Path, int], root: Path) -> Tuple[Dict[Path, int], Dict[Path, List[Tuple[str, int, bool]]]]:
    dir_totals: Dict[Path, int] = {}
    children: Dict[Path, List[Tuple[str, int, bool]]] = {}

    for file_path, lines in files.items():
        rel_parts = file_path.relative_to(root).parts
        current_dir = root
        for part in rel_parts[:-1]:
            next_dir = current_dir / part
            dir_totals[next_dir] = dir_totals.get(next_dir, 0) + lines
            current_dir = next_dir
        dir_totals[root] = dir_totals.get(root, 0) + lines

    all_dirs = {root}
    for file_path in files:
        rel = file_path.relative_to(root)
        current = root
        for part in rel.parts[:-1]:
            current = current / part
            all_dirs.add(current)

    for d in all_dirs:
        children[d] = []

    for d in all_dirs:
        for sub in sorted([x for x in all_dirs if x.parent == d and x != d], key=lambda p: p.name):
            children[d].append((sub.name, dir_totals.get(sub, 0), True))

    for file_path, lines in sorted(files.items(), key=lambda item: str(item[0].relative_to(root))):
        parent = file_path.parent
        children.setdefault(parent, []).append((file_path.name, lines, False))

    for d in children:
        children[d].sort(key=lambda item: (not item[2], item[0]))

    return dir_totals, children


def print_tree(root: Path, dir_totals: Dict[Path, int], children: Dict[Path, List[Tuple[str, int, bool]]]) -> None:
    def walk(directory: Path, prefix: str = "") -> None:
        items = children.get(directory, [])
        for idx, (name, lines, is_dir) in enumerate(items):
            is_last = idx == len(items) - 1
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{name}: {lines}")
            if is_dir:
                extension = "    " if is_last else "│   "
                walk(directory / name, prefix + extension)

    print(f"目录统计 ({root.resolve()}):")
    print(f"根目录合计: {dir_totals.get(root, 0)}")
    walk(root)
    print(f"代码总行数: {dir_totals.get(root, 0)}")


def main() -> int:
    start_time = time.monotonic()
    root = Path.cwd().resolve()

    if root.parent not in root.parents and root != Path("/"):
        print("ERROR: 非法目录", file=sys.stderr)
        return 1

    try:
        files = collect_files(root, start_time)
        dir_totals, children = build_tree(files, root)
        print_tree(root, dir_totals, children)
        return 0
    except TimeoutError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
