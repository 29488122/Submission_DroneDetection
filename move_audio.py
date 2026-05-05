"""
move_audio.py - recursively move audio files from a source directory to an output directory.

Usage:
    python move_audio.py <source> -o <output> [--dry-run]

Examples:
    python move_audio.py datasets_raw/ESC-50 -o Datasets/ESC-50-master/unknown --dry-run
    python move_audio.py datasets_raw/ESC-50 -o Datasets/ESC-50-master/unknown
"""

import argparse
import shutil
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"}


def unique_dest(output_dir: Path, filename: str) -> Path:
    """Return a collision-free destination path, appending _1, _2 … if needed."""
    dest = output_dir / filename
    if not dest.exists():
        return dest
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        dest = output_dir / f"{stem}_{counter}{suffix}"
        if not dest.exists():
            return dest
        counter += 1


def main():
    parser = argparse.ArgumentParser(
        description="Recursively move audio files from SOURCE to OUTPUT directory."
    )
    parser.add_argument("source", help="Source directory to search recursively")
    parser.add_argument("-o", "--output", required=True, help="Destination directory")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview moves without touching files"
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output).resolve()

    if not source.exists():
        print(f"ERROR: Source path does not exist: {source}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN — no files will be moved.")
    else:
        output.mkdir(parents=True, exist_ok=True)

    print(f"  Source : {source}")
    print(f"  Output : {output}")
    print()

    audio_files = sorted(
        f for f in source.rglob("*")
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )

    if not audio_files:
        print("No audio files found.")
        sys.exit(0)

    moved = 0
    for f in audio_files:
        dest = unique_dest(output, f.name)
        if args.dry_run:
            print(f"  Preview: {f} -> {dest}")
        else:
            shutil.move(str(f), dest)
            print(f"  Moved:   {f.name} -> {dest}")
        moved += 1

    print()
    verb = "would be moved" if args.dry_run else "moved"
    print(f"Done. {moved} file(s) {verb}.")


if __name__ == "__main__":
    main()


