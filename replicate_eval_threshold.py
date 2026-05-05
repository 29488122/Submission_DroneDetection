# replicate_eval_threshold.py
# Exactly reproduce the original eval_threshold calibration set from eval_manifest.csv.
#
# Instead of running the dynamic allocation algorithm (generateThresholdEval.py),
# this script reads the manifest and copies each file from its source dataset
# folder into Datasets/eval_threshold/ under the exact prefixed filename recorded
# in the manifest.  Result is bit-for-bit identical to the original calibration set.
#
# Usage:
#   python replicate_eval_threshold.py             # dry-run (default)
#   python replicate_eval_threshold.py --execute   # actually copy files
#
# Requirements:
#   - eval_manifest.csv must be present next to this script (project root)
#   - Source datasets must be populated under Datasets/ (run build steps first)

import argparse
import csv
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR    = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "eval_manifest.csv"
DATASETS_DIR  = SCRIPT_DIR / "Datasets"
DEST_ROOT     = DATASETS_DIR / "eval_threshold"

# Extra fallback search roots for datasets that live outside Datasets/
# (e.g. H-2 after XML conversion but before the copy step)
EXTRA_SEARCH_ROOTS: list[Path] = [
    SCRIPT_DIR / "datasets_raw" / "H-2_converted",
]

# Slug prefix pattern:  e.g. "Wonjun-a75dc4_"  or  "Yi et al-3f9a12_"
SLUG_RE = re.compile(r'^.+-[0-9a-f]{6}_', re.IGNORECASE)

# H-2 recording-batch suffix added during original processing: _B1, _B2, _C1 …
H2_BATCH_RE = re.compile(r'_[A-Z]\d+$', re.IGNORECASE)

# ESC-50: original files are .ogg with no trailing class-number in the stem.
# The manifest stored them as .wav with a trailing -NN class suffix
# e.g. "1-100032-A-0.wav" (manifest)  →  "1-100032-A.ogg" (actual file)
ESC50_CLASS_RE = re.compile(r'-\d+$')          # strip trailing -NN from stem
ESC50_EXTS = ('.ogg', '.wav', '.flac')


def strip_slug(name: str) -> str:
    m = SLUG_RE.match(name)
    return name[m.end():] if m else name


def lookup_file(lookup: dict[str, Path], original_name: str,
                prefixed_name: str = "") -> Path | None:
    """Try exact match, then dataset-specific fallbacks."""
    # 1. Exact match
    hit = lookup.get(original_name)
    if hit:
        return hit

    p = Path(original_name)

    # 2. H-2: strip _B1/_C1 style batch suffix  e.g. "06-FF-Mi1_B1.wav" → "06-FF-Mi1.wav"
    h2_stem = H2_BATCH_RE.sub('', p.stem)
    if h2_stem != p.stem:
        hit = lookup.get(h2_stem + p.suffix)
        if hit:
            return hit

    # 3. ESC-50: strip trailing class-number suffix and try .ogg/.wav/.flac
    #    e.g. "1-100032-A-0.wav" → try "1-100032-A.ogg" etc.
    esc_stem = ESC50_CLASS_RE.sub('', p.stem)
    if esc_stem != p.stem:
        for ext in ESC50_EXTS:
            hit = lookup.get(esc_stem + ext)
            if hit:
                return hit

    # 4. Partial slug retained in filename: e.g. manifest slug "AuthorsCollection-e26d30_"
    #    was stored on disk as "e26d30_<original>" (dataset name stripped, hash kept).
    if prefixed_name:
        hash_m = re.search(r'-([0-9a-f]{6})_', prefixed_name, re.IGNORECASE)
        if hash_m:
            hash_prefix = hash_m.group(1) + "_"
            hit = lookup.get(hash_prefix + original_name)
            if hit:
                return hit

    return None


def build_source_lookup(datasets_dir: Path, extra_roots: list[Path]) -> dict[str, Path]:
    """Scan Datasets/ class subfolders, then any extra fallback roots."""
    lookup: dict[str, Path] = {}

    # Primary: Datasets/<name>/yes_drone|unknown|drone
    for ds_dir in sorted(datasets_dir.iterdir()):
        if not ds_dir.is_dir() or ds_dir.name == "eval_threshold":
            continue
        for class_folder in ("yes_drone", "unknown", "drone"):
            cf = ds_dir / class_folder
            if not cf.is_dir():
                continue
            for f in cf.iterdir():
                if f.is_file() and f.name not in lookup:
                    lookup[f.name] = f

    # Fallback: extra roots (e.g. datasets_raw/H-2_converted) — walk recursively
    for root in extra_roots:
        if not root.is_dir():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if fname not in lookup:
                    lookup[fname] = Path(dirpath) / fname

    return lookup


def main():
    parser = argparse.ArgumentParser(
        description="Replicate eval_threshold exactly from eval_manifest.csv."
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually transfer files. Without this flag the script runs as a dry-run."
    )
    parser.add_argument(
        "--move", action="store_true",
        help="Move files instead of copying (recommended — keeps source datasets clean "
             "and avoids duplicating large datasets on disk). Only used with --execute."
    )
    args = parser.parse_args()
    dry_run  = not args.execute
    do_move  = args.move

    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    # ── Read manifest ─────────────────────────────────────────────────────────
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Manifest: {len(rows):,} entries in {MANIFEST_PATH.name}")

    # ── Build source lookup ───────────────────────────────────────────────────
    print(f"Scanning {DATASETS_DIR} for source files …")
    lookup = build_source_lookup(DATASETS_DIR, EXTRA_SEARCH_ROOTS)
    active_extras = [r for r in EXTRA_SEARCH_ROOTS if r.is_dir()]
    if active_extras:
        print(f"  + fallback roots: {', '.join(str(r) for r in active_extras)}")
    print(f"  {len(lookup):,} unique filenames indexed.")

    # ── Prepare destination folders ───────────────────────────────────────────
    dest_yes  = DEST_ROOT / "yes_drone"
    dest_unkn = DEST_ROOT / "unknown"
    if not dry_run:
        dest_yes.mkdir(parents=True, exist_ok=True)
        dest_unkn.mkdir(parents=True, exist_ok=True)

    # ── Process each manifest row ─────────────────────────────────────────────
    copied = skipped = missing = 0
    missing_list: list[str] = []

    for row in rows:
        prefixed_name = row["filename"].strip()
        class_label   = row["class"].strip().lower()       # "yes_drone" or "unknown"
        original_name = strip_slug(prefixed_name)

        dest_dir  = dest_yes if "drone" in class_label else dest_unkn
        dest_file = dest_dir / prefixed_name

        if dest_file.exists():
            skipped += 1
            continue

        src = lookup_file(lookup, original_name, prefixed_name)
        if src is None:
            missing_list.append(f"[{class_label}]  {original_name}  (manifest: {prefixed_name})")
            missing += 1
            continue

        if dry_run:
            copied += 1
        else:
            try:
                if do_move:
                    shutil.move(str(src), dest_file)
                else:
                    shutil.copy2(src, dest_file)
                copied += 1
            except Exception as e:
                print(f"  ERROR {'moving' if do_move else 'copying'} {original_name}: {e}")
                missing += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    dest_total = (
        sum(1 for _ in dest_yes.iterdir() if _.is_file()) +
        sum(1 for _ in dest_unkn.iterdir() if _.is_file())
    ) if DEST_ROOT.exists() else 0

    tag = "[DRY RUN] " if dry_run else ""
    mode_tag = "moved" if do_move else "copied"
    print(f"\n{tag}Done.")
    print(f"  {mode_tag.capitalize()} / to {mode_tag}: {copied:,}")
    print(f"  Already present  : {skipped:,}")
    print(f"  Missing (no src) : {missing:,}")
    print(f"  Dest total now   : {dest_total:,} files  ({dest_yes}: {sum(1 for _ in dest_yes.iterdir() if _.is_file()) if dest_yes.exists() else 0}, "
          f"{dest_unkn.name}: {sum(1 for _ in dest_unkn.iterdir() if _.is_file()) if dest_unkn.exists() else 0})")

    if missing_list:
        print(f"\nMissing source files (first 20):")
        for line in missing_list[:20]:
            print(f"  {line}")
        if len(missing_list) > 20:
            print(f"  … and {len(missing_list)-20} more.")
        print("\nTip: make sure all source datasets are populated (see README Dataset Setup).")
        sys.exit(1)

    if not dry_run and missing == 0:
        action = "moved" if do_move else "copied"
        print(f"\n✓ eval_threshold replicated exactly from eval_manifest.csv ({action}).")

    if dry_run:
        print(f"\nRe-run with --execute --move to move files (recommended),")
        print(f"or --execute alone to copy instead.")


if __name__ == "__main__":
    main()

