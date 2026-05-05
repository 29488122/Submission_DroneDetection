# assemble_yi_dataset.py
# Assemble C:\Users\Authors\Desktop\Yi et al. dataset
# from the raw source: datasets_raw\Yi\C
#
# Step 1 – collect the 79,466 filenames that were originally sampled:
#   a) 78,966 from Wonjun\yes_drone  (filenames == original Yi\C names)
#   b)    500 from eval_manifest.csv (strip "Wonjun-a75dc4_" prefix → Yi\C name)
# Step 2 – locate every one of those files inside Yi\C and copy to DEST.
# The original datasets are never modified.

import csv
import os
import re
import shutil
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
WONJUN        = Path(r"C:\Users\Authors\Desktop\Aineistot\Wonjun\yes_drone")
EVAL_MANIFEST = Path(r"C:\Users\Authors\Desktop\Aineistot\eval_threshold\eval_manifest.csv")
YI_C          = Path(r"C:\Users\Authors\Desktop\Replication\submission_123\datasets_raw\Yi\C")
DEST          = Path(r"C:\Users\Authors\Desktop\Yi et al. dataset")

DRY_RUN = True   # flip to False to actually copy

PREFIX_RE = re.compile(r'^[A-Za-z0-9]+-[a-f0-9]+_')  # "Wonjun-a75dc4_"

# ── 1. Build Yi\C lookup: filename -> full path ───────────────────────────────
print("Building Yi\\C lookup …")
yi_lookup: dict[str, Path] = {}
for dirpath, _, filenames in os.walk(YI_C):
    for fname in filenames:
        if fname not in yi_lookup:   # first occurrence wins (mic1 before mic2)
            yi_lookup[fname] = Path(dirpath) / fname
print(f"  {len(yi_lookup):,} unique filenames indexed.")

# ── 2. Collect the 79,466 target filenames ────────────────────────────────────
target_names: set[str] = set()

# 2a. Wonjun filenames ARE the original Yi\C names
for f in WONJUN.iterdir():
    if f.is_file():
        target_names.add(f.name)

print(f"  {len(target_names):,} names from Wonjun\\yes_drone.")

# 2b. Eval manifest Yi entries (strip slug prefix)
with EVAL_MANIFEST.open(encoding="utf-8") as f:
    eval_rows = [r for r in csv.DictReader(f)
                 if 'yi' in r.get('dataset_proper', '').lower()]

for row in eval_rows:
    original = PREFIX_RE.sub('', row['filename'], count=1)
    target_names.add(original)

print(f"  {len(target_names):,} total unique target names (Wonjun + {len(eval_rows)} eval).")

# ── 3. Copy from Yi\C → DEST ──────────────────────────────────────────────────
if not DRY_RUN:
    DEST.mkdir(parents=True, exist_ok=True)

copied = skipped = missing = errors = 0

for name in sorted(target_names):
    dest_file = DEST / name
    if dest_file.exists():
        skipped += 1
        continue
    src = yi_lookup.get(name)
    if src is None:
        print(f"  NOT FOUND in Yi\\C: {name}")
        missing += 1
        continue
    if DRY_RUN:
        copied += 1
    else:
        try:
            shutil.copy2(src, dest_file)
            copied += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            errors += 1

# ── 4. Summary ────────────────────────────────────────────────────────────────
dest_total = len(list(DEST.iterdir())) if DEST.exists() else 0
print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}Done.")
print(f"  To copy  : {copied:,}")
print(f"  Skipped  : {skipped:,}  (already in destination)")
print(f"  Missing  : {missing:,}  (not found in Yi\\C)")
print(f"  Errors   : {errors:,}")
print(f"  Dest now : {dest_total:,} files  →  {DEST}")




