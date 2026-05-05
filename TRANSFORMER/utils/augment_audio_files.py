"""
Simple Audio Augmentation Script
Run once to permanently augment audio files in the specified folders.

Usage:
    # Dry-run: show what would be processed (no changes)
    python augment_audio_files.py --dry-run

    # Run all 5 standard augmentation folders
    python augment_audio_files.py --all

    # Run a specific named augmentation folder
    python augment_audio_files.py --mode all_augments
    python augment_audio_files.py --mode clipped
    python augment_audio_files.py --mode gaussian_bandpass
    python augment_audio_files.py --mode bandpass
    python augment_audio_files.py --mode gaussian

    # Run on a custom directory (auto-detects mode from folder name)
    python augment_audio_files.py --dir "path/to/folder"

Augmentation Modes:
    all_augments      → Gaussian Noise + BandPass Filter + Random Cropping
    clipped           → Random Cropping only
    gaussian_bandpass → Gaussian Noise + BandPass Filter (no cropping)
    bandpass          → BandPass Filter only
    gaussian          → Gaussian Noise only

NOTE: This script modifies files IN-PLACE. Ensure Augmented_Datasets_Alemadi/
contains COPIES of the Al-Emadi dataset, not the originals.
The in-pipeline augmentation in main_transformers.py has a known bug with
augmentation method selection — use this script instead.
"""

import argparse
import os
import csv
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import soundfile as sf
from audiomentations import AddGaussianNoise, BandPassFilter, Compose
import matplotlib.pyplot as plt
import librosa
import librosa.display

# --- Paths (resolved relative to this script's location) ---
# Script lives at TRANSFORMER/utils/augment_audio_files.py
# Project root is two levels up.
_SCRIPT_DIR  = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
_AUG_BASE    = _PROJECT_ROOT / "Datasets" / "Augmented_Datasets_Alemadi"

# Standard augmentation folders and their processing modes
AUGMENTATION_FOLDERS = {
    "all_augments":      _AUG_BASE / "Binary_Drone_Audio_AllAugments",
    "bandpass":          _AUG_BASE / "Binary_Drone_Audio_BandPassed",
    "clipped":           _AUG_BASE / "Binary_Drone_Audio_Clipped",
    "gaussian_bandpass": _AUG_BASE / "Binary_Drone_Audio_GaussianAndBandPass",
    "gaussian":          _AUG_BASE / "Binary_Drone_Audio_GaussianNoise",
}

# --- Augmentation settings (matching data_transformers.py) ---
GAUSSIAN_NOISE_CONFIG = {
    "min_amplitude": 0.001,
    "max_amplitude": 0.05,
    "p": 0.5  # 50% probability
}

BANDPASS_CONFIG = {
    "min_center_freq": 200,
    "max_center_freq": 4000,
    "min_bandwidth_fraction": 0.1,
    "max_bandwidth_fraction": 0.8,
    "p": 0.3  # 30% probability
}

# --- Audio Cropping settings (matching main_transformers.py and data_transformers.py) ---
# Cropping randomly cuts from START, END, or BOTH ends (equal probability)
CROP_CONFIG = {
    "min_length_ratio": 0.5,   # Minimum 50% of original length
    "max_length_ratio": 0.75,  # Maximum 75% of original length
    "min_duration_seconds": 0.01  # Minimum fraction of a second
}


def find_audio_files(folder):
    """Find all .wav files recursively in folder."""
    audio_files = []
    folder_path = Path(folder)

    if not folder_path.exists():
        print(f"[ERROR] Folder does not exist: {folder}")
        return audio_files

    for file_path in folder_path.rglob("*.wav"):
        audio_files.append(file_path)

    # Also check uppercase
    for file_path in folder_path.rglob("*.WAV"):
        if file_path not in audio_files:
            audio_files.append(file_path)

    return audio_files


def random_crop_audio(audio_array, sample_rate):
    """
    Randomly crop audio by cutting from ONE or BOTH ends.

    Three modes (randomly chosen):
      1. Cut from START only: [X...100] -> keep end portion
      2. Cut from END only: [0...X] -> keep start portion
      3. Cut from BOTH ends: [X...Y] -> keep middle portion

    Example with 100 samples, keeping 60:
      - cut_from_start: [40:100]
      - cut_from_end: [0:60]
      - cut_from_both: [15:75] (cut 15 from start, 25 from end - random split)

    Args:
        audio_array: numpy array of audio samples
        sample_rate: sampling rate

    Returns:
        tuple: (cropped_audio, metadata_dict)
    """
    original_length = len(audio_array)
    min_samples = int(sample_rate * CROP_CONFIG["min_duration_seconds"])

    # Calculate target length (what remains after cutting)
    length_ratio = np.random.uniform(
        CROP_CONFIG["min_length_ratio"],
        CROP_CONFIG["max_length_ratio"]
    )
    target_length = int(original_length * length_ratio)

    # Ensure minimum length
    target_length = max(target_length, min_samples)

    # If target >= original, return original
    if target_length >= original_length:
        return audio_array, {
            "cropped": False,
            "original_length": original_length,
            "final_length": original_length,
            "length_ratio": 1.0,
            "crop_start": 0,
            "crop_end": original_length,
            "crop_mode": "none"
        }

    # Total samples to remove
    total_to_cut = original_length - target_length

    # Randomly decide: cut from START, END, or BOTH
    crop_mode_choice = np.random.choice(["cut_from_start", "cut_from_end", "cut_from_both"])

    if crop_mode_choice == "cut_from_start":
        # Cut from the beginning: [X...100] -> keep the end portion
        crop_start = total_to_cut
        crop_end = original_length
        crop_mode = "cut_from_start"

    elif crop_mode_choice == "cut_from_end":
        # Cut from the end: [0...X] -> keep the start portion
        crop_start = 0
        crop_end = target_length
        crop_mode = "cut_from_end"

    else:  # cut_from_both
        # Cut from both ends: randomly split the amount to cut
        # Random split: how much to cut from start (rest goes to end)
        cut_from_start_amount = np.random.randint(1, total_to_cut)  # At least 1 from each side
        cut_from_end_amount = total_to_cut - cut_from_start_amount

        crop_start = cut_from_start_amount
        crop_end = original_length - cut_from_end_amount
        crop_mode = "cut_from_both"

    cropped_audio = audio_array[crop_start:crop_end]

    metadata = {
        "cropped": True,
        "original_length": original_length,
        "final_length": len(cropped_audio),
        "length_ratio": len(cropped_audio) / original_length,
        "crop_start": crop_start,
        "crop_end": crop_end,
        "crop_mode": crop_mode
    }

    return cropped_audio, metadata


def create_gaussian_transform():
    """Create Gaussian Noise transform."""
    return AddGaussianNoise(
        min_amplitude=GAUSSIAN_NOISE_CONFIG["min_amplitude"],
        max_amplitude=GAUSSIAN_NOISE_CONFIG["max_amplitude"],
        p=GAUSSIAN_NOISE_CONFIG["p"]
    )


def create_bandpass_transform():
    """Create BandPass Filter transform."""
    return BandPassFilter(
        min_center_freq=BANDPASS_CONFIG["min_center_freq"],
        max_center_freq=BANDPASS_CONFIG["max_center_freq"],
        min_bandwidth_fraction=BANDPASS_CONFIG["min_bandwidth_fraction"],
        max_bandwidth_fraction=BANDPASS_CONFIG["max_bandwidth_fraction"],
        p=BANDPASS_CONFIG["p"]
    )


def create_combined_transform():
    """Create combined Gaussian + BandPass transform."""
    return Compose([
        create_gaussian_transform(),
        create_bandpass_transform()
    ])


def process_folder_all_augments(folder):
    """
    Apply all augmentations: Gaussian Noise + BandPass Filter + Random Cropping.
    Processes files in-place.
    """
    print(f"\n{'='*70}")
    print(f"Processing ALL AUGMENTS (Gaussian + BandPass + Cropping): {folder}")
    print(f"Gaussian Noise Probability: {GAUSSIAN_NOISE_CONFIG['p']} (50%)")
    print(f"BandPass Filter Probability: {BANDPASS_CONFIG['p']} (30%)")
    print(f"Cropping: {CROP_CONFIG['min_length_ratio']*100:.0f}%-{CROP_CONFIG['max_length_ratio']*100:.0f}% of original")
    print(f"{'='*70}")

    transform = create_combined_transform()
    audio_files = find_audio_files(folder)
    print(f"Found {len(audio_files)} audio files")

    if len(audio_files) == 0:
        return

    # CSV log
    csv_path = os.path.join(folder, f"augmentation_log_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    csv_rows = []

    for i, file_path in enumerate(audio_files):
        try:
            # Read
            audio, sr = sf.read(file_path)

            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)

            audio = audio.astype(np.float32)
            original = audio.copy()

            # Step 1: Apply random cropping
            cropped_audio, crop_metadata = random_crop_audio(audio, sr)

            # Step 2: Apply Gaussian + BandPass
            augmented = transform(samples=cropped_audio, sample_rate=sr)

            # Check if audio augmentation was applied (compare to cropped, not original)
            augmentation_applied = np.max(np.abs(cropped_audio - augmented)) > 1e-10

            # Overwrite file
            sf.write(file_path, augmented, sr)

            csv_rows.append({
                "file": str(file_path),
                "processed": True,
                "cropped": crop_metadata["cropped"],
                "original_length": crop_metadata["original_length"],
                "final_length": crop_metadata["final_length"],
                "length_ratio": f"{crop_metadata['length_ratio']:.3f}",
                "audio_augmented": augmentation_applied,
                "error": ""
            })

            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(audio_files)} files...")

        except Exception as e:
            csv_rows.append({
                "file": str(file_path),
                "processed": False,
                "cropped": False,
                "original_length": 0,
                "final_length": 0,
                "length_ratio": "0",
                "audio_augmented": False,
                "error": str(e)
            })
            print(f"  Error: {file_path} - {e}")

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["file", "processed", "cropped", "original_length",
                                                "final_length", "length_ratio", "audio_augmented", "error"])
        writer.writeheader()
        writer.writerows(csv_rows)

    # Summary
    cropped_count = sum(1 for row in csv_rows if row.get("cropped"))
    augmented_count = sum(1 for row in csv_rows if row.get("audio_augmented"))
    print(f"\nDone! Processed {len(audio_files)} files")
    print(f"Cropped: {cropped_count}/{len(audio_files)} ({100*cropped_count/len(audio_files):.1f}%)")
    print(f"Audio augmented: {augmented_count}/{len(audio_files)} ({100*augmented_count/len(audio_files):.1f}%)")
    print(f"Log saved: {csv_path}")


def process_folder_clipping_only(folder):
    """
    Apply only random cropping (no audio augmentation).
    Processes files in-place.
    """
    print(f"\n{'='*70}")
    print(f"Processing CLIPPING ONLY: {folder}")
    print(f"Cropping: {CROP_CONFIG['min_length_ratio']*100:.0f}%-{CROP_CONFIG['max_length_ratio']*100:.0f}% of original")
    print(f"Crop Mode: Random (start, end, or both - 33% each)")
    print(f"{'='*70}")

    audio_files = find_audio_files(folder)
    print(f"Found {len(audio_files)} audio files")

    if len(audio_files) == 0:
        return

    # CSV log
    csv_path = os.path.join(folder, f"augmentation_log_clipped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    csv_rows = []

    for i, file_path in enumerate(audio_files):
        try:
            # Read
            audio, sr = sf.read(file_path)

            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)

            audio = audio.astype(np.float32)

            # Apply random cropping
            cropped_audio, crop_metadata = random_crop_audio(audio, sr)

            # Overwrite file
            sf.write(file_path, cropped_audio, sr)

            csv_rows.append({
                "file": str(file_path),
                "processed": True,
                "cropped": crop_metadata["cropped"],
                "original_length": crop_metadata["original_length"],
                "final_length": crop_metadata["final_length"],
                "length_ratio": f"{crop_metadata['length_ratio']:.3f}",
                "crop_start": crop_metadata["crop_start"],
                "crop_end": crop_metadata["crop_end"],
                "crop_mode": crop_metadata.get("crop_mode", "none"),
                "error": ""
            })

            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(audio_files)} files...")

        except Exception as e:
            csv_rows.append({
                "file": str(file_path),
                "processed": False,
                "cropped": False,
                "original_length": 0,
                "final_length": 0,
                "length_ratio": "0",
                "crop_start": 0,
                "crop_end": 0,
                "crop_mode": "error",
                "error": str(e)
            })
            print(f"  Error: {file_path} - {e}")

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["file", "processed", "cropped", "original_length",
                                                "final_length", "length_ratio", "crop_start", "crop_end", "crop_mode", "error"])
        writer.writeheader()
        writer.writerows(csv_rows)

    # Summary
    cropped_count = sum(1 for row in csv_rows if row.get("cropped"))
    avg_ratio = np.mean([float(row["length_ratio"]) for row in csv_rows if row.get("processed")])
    print(f"\nDone! Processed {len(audio_files)} files")
    print(f"Cropped: {cropped_count}/{len(audio_files)} ({100*cropped_count/len(audio_files):.1f}%)")
    print(f"Average length ratio: {avg_ratio:.3f}")
    print(f"Log saved: {csv_path}")


def process_folder_bandpass_only(folder):
    """
    Apply BandPass Filter only (no Gaussian noise, no cropping).
    Processes files in-place.
    """
    print(f"\n{'='*70}")
    print(f"Processing BANDPASS ONLY: {folder}")
    print(f"BandPass Filter Probability: {BANDPASS_CONFIG['p']} (30%)")
    print(f"{'='*70}")

    transform = BandPassFilter(
        min_center_freq=BANDPASS_CONFIG["min_center_freq"],
        max_center_freq=BANDPASS_CONFIG["max_center_freq"],
        min_bandwidth_fraction=BANDPASS_CONFIG["min_bandwidth_fraction"],
        max_bandwidth_fraction=BANDPASS_CONFIG["max_bandwidth_fraction"],
        p=BANDPASS_CONFIG["p"]
    )
    audio_files = find_audio_files(folder)
    print(f"Found {len(audio_files)} audio files")

    if len(audio_files) == 0:
        return

    csv_path = os.path.join(folder, f"augmentation_log_bandpass_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    csv_rows = []

    for i, file_path in enumerate(audio_files):
        try:
            audio, sr = sf.read(file_path)
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            audio = audio.astype(np.float32)
            original = audio.copy()
            augmented = transform(samples=audio, sample_rate=sr)
            was_augmented = np.max(np.abs(original - augmented)) > 1e-10
            sf.write(file_path, augmented, sr)
            csv_rows.append({"file": str(file_path), "processed": True,
                              "was_augmented": was_augmented, "error": ""})
            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(audio_files)} files...")
        except Exception as e:
            csv_rows.append({"file": str(file_path), "processed": False,
                              "was_augmented": False, "error": str(e)})
            print(f"  Error: {file_path} - {e}")

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["file", "processed", "was_augmented", "error"])
        writer.writeheader()
        writer.writerows(csv_rows)

    augmented_count = sum(1 for row in csv_rows if row.get("was_augmented"))
    print(f"\nDone! Processed {len(audio_files)} files")
    print(f"Actually augmented: {augmented_count}/{len(audio_files)} ({100*augmented_count/len(audio_files):.1f}%)")
    print(f"Log saved: {csv_path}")


def process_folder_gaussian_only(folder):
    """
    Apply Gaussian Noise only (no BandPass, no cropping).
    Processes files in-place.
    """
    print(f"\n{'='*70}")
    print(f"Processing GAUSSIAN NOISE ONLY: {folder}")
    print(f"Gaussian Noise Probability: {GAUSSIAN_NOISE_CONFIG['p']} (50%)")
    print(f"{'='*70}")

    transform = AddGaussianNoise(
        min_amplitude=GAUSSIAN_NOISE_CONFIG["min_amplitude"],
        max_amplitude=GAUSSIAN_NOISE_CONFIG["max_amplitude"],
        p=GAUSSIAN_NOISE_CONFIG["p"]
    )
    audio_files = find_audio_files(folder)
    print(f"Found {len(audio_files)} audio files")

    if len(audio_files) == 0:
        return

    csv_path = os.path.join(folder, f"augmentation_log_gaussian_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    csv_rows = []

    for i, file_path in enumerate(audio_files):
        try:
            audio, sr = sf.read(file_path)
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            audio = audio.astype(np.float32)
            original = audio.copy()
            augmented = transform(samples=audio, sample_rate=sr)
            was_augmented = np.max(np.abs(original - augmented)) > 1e-10
            sf.write(file_path, augmented, sr)
            csv_rows.append({"file": str(file_path), "processed": True,
                              "was_augmented": was_augmented, "error": ""})
            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(audio_files)} files...")
        except Exception as e:
            csv_rows.append({"file": str(file_path), "processed": False,
                              "was_augmented": False, "error": str(e)})
            print(f"  Error: {file_path} - {e}")

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["file", "processed", "was_augmented", "error"])
        writer.writeheader()
        writer.writerows(csv_rows)

    augmented_count = sum(1 for row in csv_rows if row.get("was_augmented"))
    print(f"\nDone! Processed {len(audio_files)} files")
    print(f"Actually augmented: {augmented_count}/{len(audio_files)} ({100*augmented_count/len(audio_files):.1f}%)")
    print(f"Log saved: {csv_path}")


def process_folder_gaussian_and_bandpass(folder):
    """
    Apply Gaussian Noise + BandPass Filter (no cropping).
    Processes files in-place.
    """
    print(f"\n{'='*70}")
    print(f"Processing GAUSSIAN + BANDPASS (no cropping): {folder}")
    print(f"Gaussian Noise Probability: {GAUSSIAN_NOISE_CONFIG['p']} (50%)")
    print(f"BandPass Filter Probability: {BANDPASS_CONFIG['p']} (30%)")
    print(f"{'='*70}")

    transform = create_combined_transform()
    audio_files = find_audio_files(folder)
    print(f"Found {len(audio_files)} audio files")

    if len(audio_files) == 0:
        return

    # CSV log
    csv_path = os.path.join(folder, f"augmentation_log_gaussian_bandpass_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    csv_rows = []

    for i, file_path in enumerate(audio_files):
        try:
            # Read
            audio, sr = sf.read(file_path)

            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)

            audio = audio.astype(np.float32)
            original = audio.copy()

            # Apply Gaussian + BandPass (probability determines if it actually applies)
            augmented = transform(samples=audio, sample_rate=sr)

            # Check if augmentation was applied
            was_augmented = np.max(np.abs(original - augmented)) > 1e-10

            # Overwrite file
            sf.write(file_path, augmented, sr)

            csv_rows.append({
                "file": str(file_path),
                "processed": True,
                "was_augmented": was_augmented,
                "error": ""
            })

            if (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{len(audio_files)} files...")

        except Exception as e:
            csv_rows.append({
                "file": str(file_path),
                "processed": False,
                "was_augmented": False,
                "error": str(e)
            })
            print(f"  Error: {file_path} - {e}")

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["file", "processed", "was_augmented", "error"])
        writer.writeheader()
        writer.writerows(csv_rows)

    # Summary
    augmented_count = sum(1 for row in csv_rows if row.get("was_augmented"))
    print(f"\nDone! Processed {len(audio_files)} files")
    print(f"Actually augmented: {augmented_count}/{len(audio_files)} ({100*augmented_count/len(audio_files):.1f}%)")
    print(f"Log saved: {csv_path}")


def generate_sample_spectrogram(folder, augment_type, output_dir="./augmentation_samples"):
    """
    Generate a sample spectrogram showing original vs augmented audio.

    Args:
        folder: Folder containing audio files
        augment_type: One of "all", "clipped", "gaussian_bandpass"
        output_dir: Where to save the spectrograms
    """
    os.makedirs(output_dir, exist_ok=True)

    audio_files = find_audio_files(folder)
    if len(audio_files) == 0:
        print(f"No audio files found in {folder}")
        return

    # Pick a random sample file
    sample_file = np.random.choice(audio_files)
    print(f"\nGenerating spectrogram sample for {augment_type}: {sample_file}")

    # Read original audio
    audio, sr = sf.read(sample_file)
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    audio = audio.astype(np.float32)
    original = audio.copy()

    # Apply augmentation based on type
    if augment_type == "all":
        # Cropping + Gaussian + BandPass
        cropped, _ = random_crop_audio(audio, sr)
        transform = create_combined_transform()
        augmented = transform(samples=cropped, sample_rate=sr)
        title = "All Augments (Crop + Gaussian + BandPass)"

    elif augment_type == "clipped":
        # Just cropping
        augmented, _ = random_crop_audio(audio, sr)
        title = "Clipping Only"

    elif augment_type == "gaussian_bandpass":
        # Gaussian + BandPass, no cropping
        transform = create_combined_transform()
        augmented = transform(samples=audio, sample_rate=sr)
        title = "Gaussian + BandPass (No Cropping)"
    else:
        print(f"Unknown augment_type: {augment_type}")
        return

    # Create figure with 2 rows (waveform + spectrogram for each)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Augmentation Sample: {title}\nFile: {sample_file.name}', fontsize=12)

    # Original waveform
    axes[0, 0].plot(np.linspace(0, len(original)/sr, len(original)), original, color='blue', alpha=0.7)
    axes[0, 0].set_title(f'Original Waveform ({len(original)/sr:.3f}s)')
    axes[0, 0].set_xlabel('Time (s)')
    axes[0, 0].set_ylabel('Amplitude')
    axes[0, 0].set_ylim(-1, 1)

    # Augmented waveform
    axes[0, 1].plot(np.linspace(0, len(augmented)/sr, len(augmented)), augmented, color='red', alpha=0.7)
    axes[0, 1].set_title(f'Augmented Waveform ({len(augmented)/sr:.3f}s)')
    axes[0, 1].set_xlabel('Time (s)')
    axes[0, 1].set_ylabel('Amplitude')
    axes[0, 1].set_ylim(-1, 1)

    # Original spectrogram
    S_orig = librosa.feature.melspectrogram(y=original, sr=sr, n_mels=128)
    S_orig_db = librosa.power_to_db(S_orig, ref=np.max)
    img1 = librosa.display.specshow(S_orig_db, x_axis='time', y_axis='mel', sr=sr, ax=axes[1, 0])
    axes[1, 0].set_title('Original Mel Spectrogram')
    fig.colorbar(img1, ax=axes[1, 0], format='%+2.0f dB')

    # Augmented spectrogram
    S_aug = librosa.feature.melspectrogram(y=augmented, sr=sr, n_mels=128)
    S_aug_db = librosa.power_to_db(S_aug, ref=np.max)
    img2 = librosa.display.specshow(S_aug_db, x_axis='time', y_axis='mel', sr=sr, ax=axes[1, 1])
    axes[1, 1].set_title('Augmented Mel Spectrogram')
    fig.colorbar(img2, ax=axes[1, 1], format='%+2.0f dB')

    plt.tight_layout()

    # Save figure
    output_path = os.path.join(output_dir, f"sample_{augment_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Spectrogram saved: {output_path}")
    return output_path


_MODE_PROCESSORS = {
    "all_augments":      process_folder_all_augments,
    "clipped":           process_folder_clipping_only,
    "gaussian_bandpass": process_folder_gaussian_and_bandpass,
    "bandpass":          process_folder_bandpass_only,
    "gaussian":          process_folder_gaussian_only,
}

_SPECTROGRAM_TYPES = {
    "all_augments":      "all",
    "clipped":           "clipped",
    "gaussian_bandpass": "gaussian_bandpass",
    "bandpass":          "gaussian_bandpass",   # closest visual match
    "gaussian":          "gaussian_bandpass",
}

def _infer_mode_from_path(folder: Path) -> str | None:
    """Guess augmentation mode from folder name."""
    name = folder.name.lower()
    if "allaugment" in name or "all_augment" in name:
        return "all_augments"
    if "bandpassedonly" in name or name.endswith("bandpassed"):
        return "bandpass"
    if "clipped" in name:
        return "clipped"
    if "gaussianandbandpass" in name or "gaussian_and" in name:
        return "gaussian_bandpass"
    if "gaussiannoise" in name or "gaussian_noise" in name or name.endswith("gaussian"):
        return "gaussian"
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Permanently augment audio files in Augmented_Datasets_Alemadi/ subfolders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python augment_audio_files.py --dry-run          # preview all folders, no changes
  python augment_audio_files.py --all              # augment all 5 standard folders
  python augment_audio_files.py --mode clipped     # only the Clipped folder
  python augment_audio_files.py --dir path/to/dir  # custom directory (mode auto-detected)
  python augment_audio_files.py --spectrogram      # generate sample spectrograms only
        """
    )
    parser.add_argument("--all",        action="store_true", help="Process all 5 standard augmentation folders.")
    parser.add_argument("--mode",       choices=list(_MODE_PROCESSORS.keys()), help="Process one named folder.")
    parser.add_argument("--dir",        metavar="PATH", help="Process a custom directory (mode auto-detected from folder name).")
    parser.add_argument("--dry-run",    action="store_true", help="Show what would be processed without making any changes.")
    parser.add_argument("--spectrogram", action="store_true", help="Generate sample spectrograms only (no augmentation).")
    parser.add_argument("--yes",        action="store_true", help="Skip interactive confirmation prompt.")
    args = parser.parse_args()

    if not (args.all or args.mode or args.dir or args.dry_run or args.spectrogram):
        parser.print_help()
        sys.exit(0)

    # ── Build job list ────────────────────────────────────────────────────────
    jobs: list[tuple[Path, str]] = []   # (folder, mode)

    if args.all or args.dry_run:
        for mode, folder in AUGMENTATION_FOLDERS.items():
            jobs.append((folder, mode))
    elif args.mode:
        jobs.append((AUGMENTATION_FOLDERS[args.mode], args.mode))
    elif args.dir:
        folder = Path(args.dir)
        mode   = _infer_mode_from_path(folder)
        if mode is None:
            print(f"WARNING: Could not auto-detect mode for '{folder.name}'. Defaulting to 'all_augments'.")
            mode = "all_augments"
        else:
            print(f"Auto-detected mode: {mode}")
        jobs.append((folder, mode))

    # ── Dry-run summary ───────────────────────────────────────────────────────
    print("\nAudio Augmentation Script")
    print("=" * 70)
    print(f"Project root : {_PROJECT_ROOT}")
    print(f"Aug base     : {_AUG_BASE}")
    print()
    print("Planned jobs:")
    for folder, mode in jobs:
        n = len(find_audio_files(folder)) if folder.is_dir() else 0
        exists = "✓" if folder.is_dir() else "✗ MISSING"
        print(f"  [{exists}]  {mode:<20s}  {n:>6,} files  →  {folder}")

    if args.dry_run:
        print("\n[DRY RUN] No files have been modified.")
        sys.exit(0)

    if args.spectrogram:
        print("\nGenerating sample spectrograms …")
        spec_dir = str(_PROJECT_ROOT / "augmentation_samples")
        for folder, mode in jobs:
            if folder.is_dir():
                generate_sample_spectrogram(str(folder), _SPECTROGRAM_TYPES.get(mode, "all"), spec_dir)
        print(f"\nSpectrograms saved to: {spec_dir}")
        sys.exit(0)

    # ── Confirm ───────────────────────────────────────────────────────────────
    print()
    print("WARNING: This will PERMANENTLY modify audio files in-place.")
    print("         Ensure Augmented_Datasets_Alemadi/ contains COPIES, not originals.")
    if not args.yes:
        confirm = input("\nProceed? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)

    # ── Execute ───────────────────────────────────────────────────────────────
    for folder, mode in jobs:
        if not folder.is_dir():
            print(f"\nSKIPPING (folder missing): {folder}")
            continue
        _MODE_PROCESSORS[mode](str(folder))

    print("\n" + "=" * 70)
    print("ALL DONE!")
    print("=" * 70)
