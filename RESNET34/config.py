from pathlib import Path

# Root of the Datasets directory, resolved relative to this file's location
# (RESNET34/ -> submission_123/ -> Datasets/)
_DATASETS_ROOT = Path(__file__).resolve().parent.parent / "Datasets"
def _ds(subpath: str) -> str:
    return (_DATASETS_ROOT / subpath).as_posix()

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
TRAIN_SET = _ds("TrainingDatasets/Al-Emadi")
CALIBRATION_SET = _ds("eval_threshold")

#For specific epoch runs.
RUNS = [1, 5, 10, 20, 50, 100]
SAMPLE_RATE = 16000