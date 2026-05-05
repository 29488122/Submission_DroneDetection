"""
count_samples.py - count audio files in a directory tree and report per-folder stats.

Usage:
    python count_samples.py <directory> [--depth N] [--csv output.csv]

Examples:
    python count_samples.py Datasets
    python count_samples.py Datasets --depth 2
    python count_samples.py Datasets --depth 3 --csv counts.csv
"""

import argparse
import csv
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"}


def count_audio(directory: Path):
    """Return the number of audio files directly in this directory (non-recursive)."""
    return sum(
        1 for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )


def count_audio_recursive(directory: Path):
    """Return the total number of audio files anywhere under this directory."""
    return sum(
        1 for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )


def walk(root: Path, max_depth: int, current_depth: int = 0):
    """
    Yield (depth, path, direct_count, total_count) for each subdirectory up to max_depth.
    """
    if not root.is_dir():
        return

    direct = count_audio(root)
    total  = count_audio_recursive(root)
    yield (current_depth, root, direct, total)

    if current_depth < max_depth:
        try:
            children = sorted(p for p in root.iterdir() if p.is_dir())
        except PermissionError:
            return
        for child in children:
            yield from walk(child, max_depth, current_depth + 1)


def format_row(depth: int, path: Path, root: Path, direct: int, total: int) -> str:
    indent  = "  " * depth
    rel     = path.relative_to(root.parent)
    marker  = " *" if direct > 0 else ""
    return f"{indent}{rel}  |  direct: {direct:>6,}  |  total: {total:>6,}{marker}"


def main():
    parser = argparse.ArgumentParser(
        description="Count audio samples in directories and subdirectories."
    )
    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument(
        "--depth", type=int, default=3,
        help="How many directory levels to show (default: 3)"
    )
    parser.add_argument(
        "--csv", metavar="FILE", help="Also write results to a CSV file"
    )
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.exists():
        print(f"ERROR: Directory does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    rows = list(walk(root, max_depth=args.depth))

    # ── terminal output ──────────────────────────────────────────────────────
    col_w = max(len(format_row(d, p, root, 0, 0).split("|")[0]) for d, p, _, _ in rows) + 2
    header = f"{'Directory':<{col_w}}| {'Direct':>8} | {'Total':>8}"
    print()
    print(header)
    print("-" * len(header))
    for depth, path, direct, total in rows:
        indent = "  " * depth
        rel    = path.relative_to(root.parent)
        marker = " *" if direct > 0 else ""
        label  = f"{indent}{rel}{marker}"
        print(f"{label:<{col_w}}| {direct:>8,} | {total:>8,}")

    grand_total = rows[0][3] if rows else 0
    print("-" * len(header))
    print(f"{'TOTAL':<{col_w}}| {'':>8} | {grand_total:>8,}")
    print()
    print("  * = folder contains audio files directly (not only in subfolders)")
    print()

    # ── optional CSV output ──────────────────────────────────────────────────
    if args.csv:
        csv_path = Path(args.csv)
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["depth", "path", "direct_count", "total_count"])
            for depth, path, direct, total in rows:
                writer.writerow([depth, str(path), direct, total])
        print(f"CSV saved to: {csv_path.resolve()}")


if __name__ == "__main__":
    main()

