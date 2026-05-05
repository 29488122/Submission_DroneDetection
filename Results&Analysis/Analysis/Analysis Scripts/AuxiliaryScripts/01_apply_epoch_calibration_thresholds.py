#!/usr/bin/env python3
"""
Calibrate threshold per epoch (using CalibrationDataset) and apply to all detailed CSVs in that epoch.

Workflow per epoch directory:
1) Find calibration CSV.
2) Require both classes in calibration data.
3) Optimize threshold by maximizing F1 using scipy.optimize.minimize_scalar (bounded Brent-like search).
4) Apply optimized threshold to all *_detailed_files.csv files in that same epoch.

Supports preview mode (no writes) and apply mode.
"""

import argparse
import glob
import os
import re
import sys
from collections import defaultdict
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


REQUIRED_COLS = {"true_label", "drone_probability", "aggregation_threshold"}
DETAIL_PATTERN = "*_detailed_files.csv"
RESNET_PATTERN = "*_results_*.csv"


def extract_epoch_dir(csv_filepath: str) -> Optional[str]:
    """
    Extract epoch directory from path.
    Handles: .../Model/100Epoch/... or .../Model/Epoch10/...
    """
    parts = csv_filepath.split(os.sep)
    for i, part in enumerate(parts):
        if re.match(r"^(\d+)epoch$|^epoch(\d+)$", part, re.IGNORECASE):
            return os.sep.join(parts[: i + 1])
    return None


def find_all_detailed_csv_files(root_dir: str) -> List[str]:
    csv_files = []
    for root, _, files in os.walk(root_dir):
        for name in files:
            if name.endswith("_detailed_files.csv"):
                csv_files.append(os.path.join(root, name))
            elif re.match(r".+_results_\d{8}_\d{6}\.csv$", name):
                # ResNet evaluation naming: DatasetName_results_YYYYMMDD_HHMMSS.csv
                csv_files.append(os.path.join(root, name))
    return csv_files


def find_calibration_file(epoch_dir: str) -> Optional[str]:
    patterns = [
        os.path.join(epoch_dir, "CalibrationDataset_detailed_files.csv"),
        os.path.join(epoch_dir, "Calibration*_detailed_files.csv"),
        os.path.join(epoch_dir, "datasets", "CalibrationDataset_detailed_files.csv"),
        os.path.join(epoch_dir, "datasets", "Calibration*_detailed_files.csv"),
        os.path.join(epoch_dir, "CalibrationDataset", "*_detailed_files.csv"),
        os.path.join(epoch_dir, "Calibration*", "*_detailed_files.csv"),
        # ResNet naming
        os.path.join(epoch_dir, "CalibrationDataset", "CalibrationDataset_results_*.csv"),
        os.path.join(epoch_dir, "CalibrationDataset_results_*.csv"),
    ]
    for p in patterns:
        matches = glob.glob(p)
        for m in matches:
            if os.path.exists(m):
                return m
    return None


def optimize_threshold_f1(true_labels: np.ndarray, probs: np.ndarray) -> Tuple[float, float]:
    from sklearn.metrics import f1_score
    from scipy.optimize import minimize_scalar

    probs = np.asarray(probs, dtype=float)
    true_labels = np.asarray(true_labels, dtype=int)

    def negative_f1(threshold: float) -> float:
        preds = (probs >= threshold).astype(int)
        return -f1_score(true_labels, preds, zero_division=0)

    # Adapt bounds to observed probability range instead of fixed [0.02, 0.98]
    eps = 1e-9
    lower = max(eps, float(np.min(probs)) - eps)
    upper = min(1.0 - eps, float(np.max(probs)) + eps)
    if not (lower < upper):
        lower, upper = 0.02, 0.98

    result = minimize_scalar(negative_f1, bounds=(lower, upper), method="bounded")

    # Refine on actual probability cut-points (F1 only changes at real values)
    unique_probs = np.unique(probs)
    idx = int(np.searchsorted(unique_probs, float(result.x)))
    neighbor_idxs = {max(0, idx - 2), max(0, idx - 1),
                     min(len(unique_probs) - 1, idx),
                     min(len(unique_probs) - 1, idx + 1),
                     min(len(unique_probs) - 1, idx + 2)}
    best_threshold = float(result.x)
    best_f1 = float(-result.fun)
    for t in [float(unique_probs[i]) for i in neighbor_idxs]:
        f = -negative_f1(t)
        if f > best_f1:
            best_f1 = f
            best_threshold = t

    best_threshold = float(round(best_threshold, 12))

    if best_threshold >= 0.95 or best_threshold <= 0.005:
        import warnings
        warnings.warn(f"Extreme threshold selected ({best_threshold:.8f}); probabilities may be very low/high range")

    return best_threshold, best_f1


def load_calibration_arrays(calibration_csv: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], str]:
    try:
        df = pd.read_csv(calibration_csv)
    except Exception as exc:
        return None, None, f"failed to read calibration CSV: {exc}"

    missing = [c for c in ["true_label", "drone_probability"] if c not in df.columns]
    if missing:
        return None, None, f"missing required columns in calibration CSV: {missing}"

    y = pd.to_numeric(df["true_label"], errors="coerce")
    p = pd.to_numeric(df["drone_probability"], errors="coerce")
    valid = y.notna() & p.notna()
    y = y[valid].astype(int).to_numpy()
    p = p[valid].astype(float).to_numpy()

    if len(y) == 0:
        return None, None, "calibration CSV has no valid rows after numeric coercion"

    uniq = np.unique(y)
    if len(uniq) < 2:
        return None, None, f"calibration is single-class ({uniq.tolist()}); need both classes for F1 optimization"

    return y, p, "ok"


def apply_threshold_to_csv(csv_path: str, threshold: float, dry_run: bool) -> Tuple[bool, str]:
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        return False, f"read error: {exc}"

    if "aggregation_threshold" not in df.columns:
        return False, "missing aggregation_threshold column"

    if not dry_run:
        df["aggregation_threshold"] = float(threshold)
        df.to_csv(csv_path, index=False, float_format="%.15f")

    return True, "updated" if not dry_run else "would update"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Optimize threshold on CalibrationDataset per epoch and apply to all *_detailed_files.csv files."
    )
    parser.add_argument("root_dir", help="Root directory to scan recursively")
    parser.add_argument("--apply", action="store_true", help="Write changes to files")
    parser.add_argument("--dry-run", action="store_true", help="Preview only (default behavior)")
    parser.add_argument(
        "--exclude-calibration-from-apply",
        action="store_true",
        help="Do not rewrite calibration file itself (still used for optimization)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.root_dir):
        print(f"ERROR: directory does not exist: {args.root_dir}")
        return 1

    dry_run = not args.apply or args.dry_run
    print(f"Mode: {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Root: {args.root_dir}")
    print("-" * 80)

    all_csv = find_all_detailed_csv_files(args.root_dir)
    if not all_csv:
        print("No *_detailed_files.csv found.")
        return 0

    # Group by epoch
    epoch_files = defaultdict(list)
    no_epoch = []
    for f in all_csv:
        ep = extract_epoch_dir(f)
        if ep is None:
            no_epoch.append(f)
        else:
            epoch_files[ep].append(f)

    print(f"Found {len(all_csv)} detailed CSV files")
    print(f"Found {len(epoch_files)} epoch directories")
    if no_epoch:
        print(f"Warning: {len(no_epoch)} files not mapped to an epoch directory")

    epochs_ok = 0
    epochs_failed = 0
    files_updated = 0
    files_failed = 0

    for epoch_dir in sorted(epoch_files.keys()):
        print(f"\n[Epoch] {os.path.relpath(epoch_dir, args.root_dir)}")

        calibration_csv = find_calibration_file(epoch_dir)
        if calibration_csv is None:
            print("  ERROR: no calibration file found")
            epochs_failed += 1
            files_failed += len(epoch_files[epoch_dir])
            continue

        y, p, msg = load_calibration_arrays(calibration_csv)
        if y is None or p is None:
            print(f"  ERROR: {msg}")
            epochs_failed += 1
            files_failed += len(epoch_files[epoch_dir])
            continue

        try:
            threshold, f1 = optimize_threshold_f1(y, p)
            if threshold >= 0.95 or threshold <= 0.05:
                print(f"  WARNING: extreme threshold selected ({threshold:.6f}); check calibration score distribution")
        except Exception as exc:
            print(f"  ERROR: threshold optimization failed: {exc}")
            epochs_failed += 1
            files_failed += len(epoch_files[epoch_dir])
            continue

        print(f"  Calibration file: {os.path.basename(calibration_csv)}")
        print(f"  Optimized threshold: {threshold:.12f} (F1={f1:.4f})")

        # Apply to all detailed CSVs in this epoch
        updated_this_epoch = 0
        failed_this_epoch = 0

        for csv_path in sorted(epoch_files[epoch_dir]):
            base = os.path.basename(csv_path)

            if args.exclude_calibration_from_apply and os.path.abspath(csv_path) == os.path.abspath(calibration_csv):
                print(f"    SKIP {base} (calibration excluded by flag)")
                continue

            ok, status = apply_threshold_to_csv(csv_path, threshold, dry_run=dry_run)
            if ok:
                updated_this_epoch += 1
                print(f"    OK   {base} -> {status}")
            else:
                failed_this_epoch += 1
                print(f"    FAIL {base} -> {status}")

        print(f"  Epoch result: updated={updated_this_epoch}, failed={failed_this_epoch}")
        files_updated += updated_this_epoch
        files_failed += failed_this_epoch
        epochs_ok += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Epochs processed successfully: {epochs_ok}")
    print(f"Epochs failed: {epochs_failed}")
    print(f"Files updated: {files_updated}")
    print(f"Files failed: {files_failed}")

    # Non-zero exit if any epoch failed
    return 2 if epochs_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())