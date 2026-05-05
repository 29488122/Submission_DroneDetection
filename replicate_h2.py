#!/usr/bin/env python3
import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def normalize_name(name: str, case_insensitive: bool) -> str:
    n = (name or "").strip()
    return n.lower() if case_insensitive else n


def load_targets(csv_path: Path, case_insensitive: bool) -> List[Tuple[str, str]]:
    """
    Returns list of (source_folder, missing_base_name).
    source_folder is kept for reporting; matching is done by missing_base_name.
    """
    rows: List[Tuple[str, str]] = []
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"source_folder", "missing_base_name"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"CSV must contain headers: source_folder,missing_base_name. Found: {reader.fieldnames}"
            )

        for r in reader:
            source_folder = normalize_name(r.get("source_folder", ""), case_insensitive)
            base = normalize_name(r.get("missing_base_name", ""), case_insensitive)
            if not base:
                continue
            rows.append((source_folder, base))
    return rows


def build_stem_index(root: Path, case_insensitive: bool) -> Dict[str, List[Path]]:
    """
    Index files by file stem only (base name, no extension), recursively.
    """
    idx: Dict[str, List[Path]] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        stem = normalize_name(p.stem, case_insensitive)
        idx.setdefault(stem, []).append(p)
    return idx


def write_log_header(log_csv: Path) -> None:
    log_csv.parent.mkdir(parents=True, exist_ok=True)
    with log_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "timestamp",
            "source_folder",
            "missing_base_name",
            "matched_file_path",
            "status",   # deleted | dry_run | not_found | error
            "message",
        ])


def append_log(
    log_csv: Path,
    source_folder: str,
    missing_base_name: str,
    matched_file_path: str,
    status: str,
    message: str,
) -> None:
    with log_csv.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            datetime.now().isoformat(timespec="seconds"),
            source_folder,
            missing_base_name,
            matched_file_path,
            status,
            message,
        ])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete files by CSV list using missing_base_name (stem), recursively."
    )
    parser.add_argument("root_dir", help="Root directory to search recursively.")
    parser.add_argument("targets_csv", help="CSV with headers: source_folder,missing_base_name")
    parser.add_argument(
        "-o", "--log-csv",
        default="deletion_log.csv",
        help="Output CSV log (default: deletion_log.csv)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not delete files; only report what would be deleted."
    )
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="Case-insensitive matching for missing_base_name."
    )
    parser.add_argument(
        "--delete-all-duplicates",
        action="store_true",
        help="If multiple files share same base name, delete all. Default: delete first match only."
    )
    args = parser.parse_args()

    root = Path(args.root_dir).resolve()
    targets_csv = Path(args.targets_csv).resolve()
    log_csv = Path(args.log_csv).resolve()

    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Root directory not found: {root}")
    if not targets_csv.exists():
        raise FileNotFoundError(f"Targets CSV not found: {targets_csv}")

    print(f"Root directory: {root}")
    print(f"Targets CSV:    {targets_csv}")
    print(f"Log CSV:        {log_csv}")
    print(f"Dry run:        {args.dry_run}")
    print(f"Case-insensitive: {args.case_insensitive}")
    print(f"Delete all duplicates: {args.delete_all_duplicates}")

    targets = load_targets(targets_csv, args.case_insensitive)
    if not targets:
        print("No valid rows found in target CSV.")
        return

    write_log_header(log_csv)
    stem_index = build_stem_index(root, args.case_insensitive)

    deleted = 0
    not_found = 0
    errors = 0
    matches = 0

    for source_folder, base_name in targets:
        matched_files = stem_index.get(base_name, [])

        if not matched_files:
            not_found += 1
            append_log(
                log_csv,
                source_folder,
                base_name,
                "",
                "not_found",
                "No file matched missing_base_name"
            )
            continue

        # Default behavior: delete only first match (safer).
        # Use --delete-all-duplicates to remove all matches.
        files_to_process = matched_files if args.delete_all_duplicates else [matched_files[0]]

        for fp in files_to_process:
            matches += 1
            if args.dry_run:
                append_log(
                    log_csv,
                    source_folder,
                    base_name,
                    str(fp),
                    "dry_run",
                    "Would delete matched file by missing_base_name"
                )
                continue

            try:
                fp.unlink()
                deleted += 1
                append_log(
                    log_csv,
                    source_folder,
                    base_name,
                    str(fp),
                    "deleted",
                    "File deleted by missing_base_name"
                )
            except Exception as e:
                errors += 1
                append_log(
                    log_csv,
                    source_folder,
                    base_name,
                    str(fp),
                    "error",
                    f"Delete failed: {e}"
                )

    print("\nDone.")
    print(f"Target rows:        {len(targets)}")
    print(f"Matched files:      {matches}")
    print(f"Deleted files:      {deleted}")
    print(f"Not found rows:     {not_found}")
    print(f"Delete errors:      {errors}")
    print(f"Log written to:     {log_csv}")


if __name__ == "__main__":
    main()