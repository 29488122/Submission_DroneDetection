"""
generate_yi_manifest.py
-----------------------
One-time script: produce yi_et_al_manifest.csv listing the exact 79,466 files
that were originally sampled from Yi\C for this project.

Sources for the filename list:
  - Wonjun\yes_drone          (78,966 files  – filenames = original Yi\C names)
  - eval_threshold manifest   (    500 files  – strip slug prefix to recover name)

CSV columns:
  filename      original Yi\C filename (no path, no prefix)
  yi_c_subdir   relative subfolder inside Yi\C where the file lives (for reference)
"""

import csv
import os
import re
from pathlib import Path

WONJUN        = Path(r"C:\Users\Authors\Desktop\Aineistot\Wonjun\yes_drone")
EVAL_MANIFEST = Path(r"C:\Users\Authors\Desktop\Aineistot\eval_threshold\eval_manifest.csv")
YI_C          = Path(r"C:\Users\Authors\Desktop\Replication\submission_123\datasets_raw\Yi\C")
OUT_CSV       = Path(r"C:\Users\Authors\Desktop\Replication\submission_123\yi_et_al_manifest.csv")

PREFIX_RE = re.compile(r'^[A-Za-z0-9]+-[a-f0-9]+_')

# Build Yi\C lookup: filename -> relative subfolder
print("Scanning Yi\\C …")
yi_lookup: dict[str, str] = {}
for dirpath, _, filenames in os.walk(YI_C):
    rel = str(Path(dirpath).relative_to(YI_C))
    for fname in filenames:
        if fname not in yi_lookup:
            yi_lookup[fname] = rel
print(f"  {len(yi_lookup):,} unique filenames.")

# Collect target filenames
target: dict[str, str] = {}   # filename -> yi_c_subdir

for f in WONJUN.iterdir():
    if f.is_file() and f.name in yi_lookup:
        target[f.name] = yi_lookup[f.name]

with EVAL_MANIFEST.open(encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if 'yi' in row.get('dataset_proper', '').lower():
            original = PREFIX_RE.sub('', row['filename'], count=1)
            if original in yi_lookup:
                target[original] = yi_lookup[original]

print(f"  {len(target):,} unique target files collected.")

# Write CSV
with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["filename", "yi_c_subdir"])
    for name in sorted(target):
        writer.writerow([name, target[name]])

print(f"  Manifest written to: {OUT_CSV}")

