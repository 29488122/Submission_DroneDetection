"""Common constants and label mappings shared across CNN-LSTM pipeline.

Keep a single source of truth for label maps and audio/spectrogram parameters.
"""
from pathlib import Path
from typing import Dict, Tuple

# Root of the Datasets directory, resolved relative to this file's location
# (CNN_LSTM/ -> submission_123/ -> Datasets/)
_DATASETS_ROOT = Path(__file__).resolve().parent.parent / "Datasets"
def _ds(subpath: str) -> str:
    """Return a forward-slash string path under the Datasets root."""
    return (_DATASETS_ROOT / subpath).as_posix()

# Label mappings
LABEL2ID: Dict[str, int] = {"unknown": 0, "yes_drone": 1}
ID2LABEL: Dict[int, str] = {v: k for k, v in LABEL2ID.items()}

def get_label_mappings() -> Tuple[Dict[str, int], Dict[int, str]]:
    """Return label-to-id and id-to-label mappings."""
    return LABEL2ID, ID2LABEL

# Audio and spectrogram parameters
SAMPLE_RATE: int = 16000
N_MELS: int = 128
N_FFT: int = 1024
HOP_LENGTH: int = 256

# Description is optional, but label override should be set depending on if you have only one label: drone or unknown (see below)
TRAIN_SET = _ds("TrainingDatasets/Al-Emadi")
CALIBRATION_SET = _ds("eval_threshold")
DATASETS = {
    "H-2": {
        "path": _ds("H-2"),
        "description": "Mixed dataset with folder structure"
    },
    "DronePrint": {
        "path": _ds("DronePrint/yes_drone"),
        "description": "All drone samples",
        "label_override": "yes_drone"
    },
    "Authors": {
        "path": _ds("AuthorsCompiledSounds"),
        "description": "Mixed dataset with folder structure"
    },
    "S&E": {
        "path": _ds("Svanstrom & Englund"),
        "description": "Mixed dataset with folder structure"
    },
    "Emo": {
        "path": _ds("EmoSoundscapes"),
        "description": "All environmental sounds",
        "label_override": "unknown"
    },
    "ESC-50": {
        "path": _ds("ESC-50-master/unknown"),
        "description": "All environmental sounds",
        "label_override": "unknown"
    },
    "UrbanSound": {
        "path": _ds("UrbanSound8K"),
        "description": "All urban sounds",
        "label_override": "unknown"
    },
    "WonjunYi": {
        "path": _ds("Yi et al"),
        "description": "All drone samples",
        "label_override": "yes_drone"
    },
    "CalibrationDataset": {
        "path": _ds("eval_threshold"),
        "description": "Mixed dataset with folder structure"
    },
}

## Decimal notation for the .csv outputs for the evaluation script
def format_decimal(value: float, decimals: int = 6) -> str:
    """Format a float without scientific notation, fixed decimals.

    Useful for writing CSVs where exponential notation is undesirable.
    """
    fmt = f"{{0:.{decimals}f}}"
    return fmt.format(float(value))
