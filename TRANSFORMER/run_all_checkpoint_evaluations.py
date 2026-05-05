#!/usr/bin/env python3
"""
Wrapper that evaluates every checkpoint inside each wav2vec2-Final-* model folder.

For each model folder it:
  1. Discovers checkpoint-* subdirectories.
  2. Calls cli.py multi-model --checkpoint-dir <model_folder> so each checkpoint
     is evaluated as a separate model entry against all ENHANCED_DATASETS.
  3. Writes results to eval_results/checkpoints/<model_name>/.

Edit the SETTINGS block, then run:
    cd C:\\Users\\user\\Desktop\\Drone_DT_ML_SC\\TRANSFORMER
    python run_all_checkpoint_evaluations.py
"""

import sys
import subprocess
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
TRANSFORMER_DIR = Path(__file__).parent          # folder containing cli.py
OUTPUT_BASE     = TRANSFORMER_DIR / "eval_results" / "checkpoints"

STRATEGY        = "file"          # "file" or "clip"
CALIBRATE       = True            # calibrate threshold per checkpoint run
CALIBRATION_KEY = "Calibration"   # key in ENHANCED_DATASETS
FORCE_RECAL     = False           # set True to ignore saved threshold.json
VERBOSE         = False

MODEL_PREFIX    = "wav2vec2-Final-"

# Set to a set of step numbers to only evaluate specific checkpoints,
# e.g. KEEP_STEPS = {523, 2615, 5230, 7845, 10460}
# Set to None to evaluate all checkpoints found.
KEEP_STEPS = None
# ---------------------------------------------------------------------------


def discover_model_folders():
    folders = []
    for entry in sorted(TRANSFORMER_DIR.iterdir()):
        if entry.is_dir() and entry.name.startswith(MODEL_PREFIX):
            checkpoints = [c for c in entry.iterdir()
                           if c.is_dir() and c.name.startswith("checkpoint-")]
            if checkpoints:
                folders.append(entry)
            else:
                print(f"  Skipping {entry.name} — no checkpoint-* subdirs found")
    return folders


def run_evaluation(model_folder):
    model_name = model_folder.name
    output_dir = OUTPUT_BASE / model_name

    cmd = [
        sys.executable, str(TRANSFORMER_DIR / "cli.py"),
        "multi-model",
        "--checkpoint-dir", str(model_folder),
        "--base-strategy",  STRATEGY,
        "--output-dir",     str(output_dir),
        "--force-output-dir",
    ]

    if CALIBRATE:
        cmd += ["--calibrate", "--calibration-key", CALIBRATION_KEY]
    if FORCE_RECAL:
        cmd.append("--force-recalibrate")
    if VERBOSE:
        cmd.append("--verbose")

    print(f"\n{'='*70}")
    print(f"  Model : {model_name}")
    print(f"  Output: {output_dir}")
    print(f"{'='*70}")

    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(TRANSFORMER_DIR))
    elapsed = time.time() - t0

    success = result.returncode == 0
    status  = "OK" if success else f"FAILED (rc={result.returncode})"
    print(f"  [{status}]  {elapsed/3600:.2f}h  ({elapsed:.0f}s)")
    return success


def main():
    print("=" * 70)
    print("Checkpoint Evaluation Wrapper")
    print(f"  TRANSFORMER_DIR : {TRANSFORMER_DIR}")
    print(f"  OUTPUT_BASE     : {OUTPUT_BASE}")
    print(f"  STRATEGY        : {STRATEGY}")
    print(f"  CALIBRATE       : {CALIBRATE}")
    print(f"  KEEP_STEPS      : {KEEP_STEPS if KEEP_STEPS else 'all'}")
    print("=" * 70)

    model_folders = discover_model_folders()
    if not model_folders:
        print("No model folders found — check MODEL_PREFIX setting.")
        sys.exit(1)

    print(f"\nFound {len(model_folders)} model folder(s) with checkpoints:")
    for f in model_folders:
        ckpts = sorted(f.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
        if KEEP_STEPS:
            ckpts = [c for c in ckpts if int(c.name.split("-")[1]) in KEEP_STEPS]
        print(f"  {f.name}  ->  {len(ckpts)} checkpoint(s): "
              f"{', '.join(c.name for c in ckpts)}")

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    overall_start = time.time()
    run_results = {}

    for model_folder in model_folders:
        run_results[model_folder.name] = run_evaluation(model_folder)

    total = time.time() - overall_start
    print("\n" + "=" * 70)
    print(f"All evaluations complete in {total/3600:.2f}h ({total:.0f}s)")
    print("=" * 70)
    for name, ok in run_results.items():
        print(f"  [{'OK':^6}]  {name}" if ok else f"  [{'FAIL':^6}]  {name}")

    failed = [n for n, ok in run_results.items() if not ok]
    if failed:
        print(f"\n{len(failed)} run(s) failed.")
        sys.exit(1)
    else:
        print("\nAll runs succeeded.")


if __name__ == "__main__":
    main()