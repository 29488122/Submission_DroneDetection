#!/usr/bin/env python3
import argparse
import base64
import binascii
from pathlib import Path
import xml.etree.ElementTree as ET


def strip_data_uri_prefix(s: str) -> str:
    s = s.strip()
    if "," in s and s.lower().startswith("data:"):
        return s.split(",", 1)[1]
    return s


def looks_like_wav(data: bytes) -> bool:
    # WAV/RIFF signature
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def parse_xml_and_extract_binary(xml_path: Path):
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    # Find any element whose localname is "binary"
    binaries = []
    for elem in root.iter():
        tag = elem.tag
        local = tag.split("}", 1)[1] if "}" in tag else tag
        if local == "binary":
            binaries.append(elem)

    return binaries


def decode_base64_text(text: str) -> bytes:
    cleaned = strip_data_uri_prefix(text)
    # Remove whitespace/newlines safely
    cleaned = "".join(cleaned.split())
    return base64.b64decode(cleaned, validate=True)


def convert_one_file(xml_file: Path, out_dir: Path, overwrite: bool = False):
    binaries = parse_xml_and_extract_binary(xml_file)
    if not binaries:
        return []

    written = []
    for i, b in enumerate(binaries, start=1):
        btype = (b.attrib.get("type") or "").strip()
        bid = (b.attrib.get("id") or f"B{i}").strip()
        text = b.text or ""

        if not text.strip():
            continue

        try:
            raw = decode_base64_text(text)
        except (binascii.Error, ValueError) as e:
            print(f"[WARN] {xml_file}: binary id={bid} failed base64 decode: {e}")
            continue

        # Prefer WAV extension when header says RIFF/WAVE or type hints audio
        is_wav = looks_like_wav(raw) or "base64binarydatex2" in btype.lower()
        ext = ".wav" if is_wav else ".bin"

        stem = xml_file.stem
        # If multiple binaries in one XML, suffix them
        suffix = f"_{bid}" if len(binaries) > 1 else ""
        out_name = f"{stem}{suffix}{ext}"
        out_path = out_dir / out_name

        if out_path.exists() and not overwrite:
            print(f"[SKIP] Exists: {out_path}")
            written.append(out_path)
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(raw)
        print(f"[OK] {xml_file.name} -> {out_path.name} ({len(raw)} bytes)")
        written.append(out_path)

    return written


def main():
    parser = argparse.ArgumentParser(
        description="Convert XML files containing base64 audio payloads into audio files."
    )
    parser.add_argument("input", help="Input XML file or directory")
    parser.add_argument(
        "-o", "--output",
        default="converted_audio",
        help="Output directory (default: converted_audio)"
    )
    parser.add_argument(
        "--glob",
        default="*.xml",
        help="Glob for XML discovery when input is a directory (default: *.xml)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search XML files in input directory"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files"
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if in_path.is_file():
        files = [in_path]
    elif in_path.is_dir():
        if args.recursive:
            files = sorted(in_path.rglob(args.glob))
        else:
            files = sorted(in_path.glob(args.glob))
    else:
        raise FileNotFoundError(f"Input path not found: {in_path}")

    if not files:
        print("No XML files found.")
        return

    total_written = 0
    for f in files:
        try:
            written = convert_one_file(f, out_dir, overwrite=args.overwrite)
            total_written += len(written)
        except ET.ParseError as e:
            print(f"[WARN] Skipping invalid XML {f}: {e}")
        except Exception as e:
            print(f"[WARN] Failed on {f}: {e}")

    print(f"\nDone. Wrote {total_written} output file(s) to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()