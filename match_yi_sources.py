"""
match_yi_sources.py
-------------------
Match filenames in yes_drone exactly to their source subfolder inside Yi\C.

All yes_drone files start with 'C_', so they originate from configuration C.
Naming conventions differ per split:
  - train:      filename already contains _mic1_ / _mic2_  (e.g. C_B_MF1_mic1_52_…)
  - test/valid: filename does NOT contain mic token         (e.g. C_B_PC1_67_…)

No renaming is applied – filenames are matched as-is.
"""

import os
from collections import defaultdict
from pathlib import Path

YES_DRONE = Path(r"C:\Users\Authors\Desktop\Aineistot\Wonjun\yes_drone")
YI_C      = Path(r"C:\Users\Authors\Desktop\Replication\submission_123\datasets_raw\Yi\C")

# ── 1. Build exact-name lookup across Yi\C ──────────────────────────────────
print("Building lookup from Yi\\C …")
yi_lookup: dict[str, list[str]] = defaultdict(list)

for dirpath, dirnames, filenames in os.walk(YI_C):
    rel = str(Path(dirpath).relative_to(YI_C))
    for fname in filenames:
        yi_lookup[fname].append(rel)

total_yi = sum(len(v) for v in yi_lookup.values())
print(f"  {len(yi_lookup):,} unique filenames, {total_yi:,} total entries in Yi\\C.")

# ── 2. Load yes_drone filenames ──────────────────────────────────────────────
yes_drone_files = [f for f in os.listdir(YES_DRONE)
                   if os.path.isfile(YES_DRONE / f)]
print(f"  {len(yes_drone_files):,} files in yes_drone.")

# ── 3. Exact-match each yes_drone file ──────────────────────────────────────
results: dict[str, int] = defaultdict(int)   # subfolder -> matched count
unmatched: list[str] = []

for fname in yes_drone_files:
    folders = yi_lookup.get(fname, [])
    if folders:
        for folder in folders:
            results[folder] += 1
    else:
        unmatched.append(fname)

# ── 4. Report ────────────────────────────────────────────────────────────────
print("\n=== Raw folder hit counts (Yi\\C) ===")
print("  (test/valid files without mic token appear in BOTH mic1 & mic2,")
print("   so their count is doubled here)\n")
for folder, count in sorted(results.items(), key=lambda x: (-x[1], x[0])):
    print(f"  {count:>7,}  {folder}")

# Deduplicate: for each yes_drone file, pick the FIRST matched folder
# to get a true unique count per split/mic
unique_results: dict[str, int] = defaultdict(int)
for fname in yes_drone_files:
    folders = yi_lookup.get(fname, [])
    if folders:
        unique_results[folders[0]] += 1

print("\n=== Unique yes_drone files per source (first-match, deduplicated) ===")
for folder, count in sorted(unique_results.items(), key=lambda x: (-x[1], x[0])):
    print(f"  {count:>7,}  {folder}")

matched_unique = sum(unique_results.values())
print(f"\nUniquely matched : {matched_unique:,} / {len(yes_drone_files):,}")
print(f"Unmatched        : {len(unmatched):,}")

# Split-level summary (ignore mic1/mic2 distinction for test/valid)
from pathlib import PurePosixPath
split_summary: dict[str, int] = defaultdict(int)
for fname in yes_drone_files:
    folders = yi_lookup.get(fname, [])
    if folders:
        # normalise: treat test/valid mic1 and mic2 as the same split
        parts = Path(folders[0]).parts  # e.g. ('train', 'mic1') or ('valid', 'mic2')
        split = parts[0] if parts else folders[0]
        split_summary[split] += 1

print("\n=== Summary by split ===")
for split, count in sorted(split_summary.items(), key=lambda x: -x[1]):
    print(f"  {count:>7,}  {split}")

if unmatched:
    print(f"\nFirst 10 unmatched filenames:")
    for f in unmatched[:10]:
        print(f"  {f}")

