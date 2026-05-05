# build_Yi_dataset.py
# Copy the exact Yi et al. files used in this project into the dataset folder.
#
# Usage:
#   python build_Yi_dataset.py <path_to_Yi_C_split>
#
# Example:
#   python build_Yi_dataset.py "C:/path/to/datasets_raw/Yi/C"
#
# Reads yi_et_al_manifest.csv (next to this script), finds each listed file
# inside the provided Yi\C directory, and copies it to:
#   <project_root>\Datasets\Yi et al\yes_drone\
#
# Nothing outside the destination folder is modified.

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MANIFEST   = SCRIPT_DIR / "yi_et_al_manifest.csv"
DEST       = SCRIPT_DIR / "Datasets" / "Yi et al" / "yes_drone"


def main():
    parser = argparse.ArgumentParser(
        description="Copy Yi et al. (config C) samples into Datasets/Yi et al/yes_drone."
    )
    parser.add_argument(
        "yi_c_path",
        help='Path to the Yi dataset C-split folder (contains train/, test/, valid/).'
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be copied without actually copying anything."
    )
    args = parser.parse_args()

    yi_c = Path(args.yi_c_path).resolve()
    if not yi_c.is_dir():
        print(f"ERROR: Yi\\C directory not found: {yi_c}", file=sys.stderr)
        sys.exit(1)

    if not MANIFEST.exists():
        print(f"ERROR: manifest not found: {MANIFEST}", file=sys.stderr)
        sys.exit(1)

    # ── Build lookup: filename -> full path inside Yi\C ──────────────────────
    print(f"Scanning {yi_c} …")
    yi_lookup: dict[str, Path] = {}
    for dirpath, _, filenames in os.walk(yi_c):
        for fname in filenames:
            if fname not in yi_lookup:
                yi_lookup[fname] = Path(dirpath) / fname
    print(f"  {len(yi_lookup):,} unique filenames found.")

    # ── Read manifest ─────────────────────────────────────────────────────────
    with MANIFEST.open(encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))
    print(f"  {len(manifest_rows):,} files listed in manifest.")

    # ── Copy ──────────────────────────────────────────────────────────────────
    if not args.dry_run:
        DEST.mkdir(parents=True, exist_ok=True)

    copied = skipped = missing = errors = 0

    for row in manifest_rows:
        name = row["filename"]
        dest_file = DEST / name

        if dest_file.exists():
            skipped += 1
            continue

        src = yi_lookup.get(name)
        if src is None:
            print(f"  NOT FOUND: {name}")
            missing += 1
            continue

        if args.dry_run:
            copied += 1
        else:
            try:
                shutil.copy2(src, dest_file)
                copied += 1
            except Exception as e:
                print(f"  ERROR {name}: {e}")
                errors += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    dest_total = len(list(DEST.iterdir())) if DEST.exists() else 0
    tag = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{tag}Done.")
    print(f"  Copied   : {copied:,}")
    print(f"  Skipped  : {skipped:,}  (already present)")
    print(f"  Missing  : {missing:,}  (not found in Yi\\C — check your path)")
    print(f"  Errors   : {errors:,}")
    print(f"  Dest     : {DEST}  ({dest_total:,} files total)")

    if missing:
        print("\nWARNING: some files were not found. Make sure you are pointing")
        print("  at the C-split folder (the one containing train/, test/, valid/).")
        sys.exit(1)


if __name__ == "__main__":
    main()


