# Drone Audio Classification

A comprehensive audio classification pipeline for drone detection using three deep learning architectures: **CNN-LSTM**, **ResNet-34**, and **Transformer-based models**.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Dataset Setup](#dataset-setup)
  - [Step 1 — Environment and Auto-downloads](#step-1--environment-and-auto-downloads)
  - [Step 2 — Manual Downloads](#step-2--manual-downloads)
  - [Step 3 — Special Dataset Handling](#step-3--special-dataset-handling)
    - [Yi et al.](#yi-et-al-special-handling)
    - [H-2](#h-2-special-handling)
  - [Step 4 — Copy Datasets into Datasets/](#step-4--copy-processed-datasets-into-datasets)
  - [Step 5 — Calibration Dataset](#step-5--calibration-dataset-eval_threshold)
  - [Step 6 — Data Augmentation (optional)](#step-6--data-augmentation-optional)
  - [Expected Dataset Contents](#expected-dataset-contents)
- [Requirements](#requirements)
- [CNN-LSTM](#cnn-lstm)
- [ResNet-34](#resnet-34)
- [Transformer Pipeline](#transformer-pipeline)
- [Evaluation](#evaluation)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bat
:: Full first-time setup (run from the repo root in cmd)
setup_1_env.bat          :: Step 1: venv + auto-downloads + instructions
:: ...download manual datasets, run prepare_h2.ps1 for H-2...
setup_2_copy.bat         :: Step 2: copy all available datasets into Datasets/
```

All scripts are idempotent — safe to re-run if interrupted or after adding more datasets later.

---

## Dataset Setup

### Step 1 — Environment and Auto-downloads

Run **`setup_1_env.bat`** from the repo root. It will:

1. Create `Datasets/` directory structure with the correct `yes_drone`/`unknown` class subfolders
2. Create a Python 3.11 virtual environment (`.venv311/`) and install all `requirements.txt` files
3. Apply the `datasets` library formatting hotfix (see [Troubleshooting](#troubleshooting))
4. Auto-download these datasets directly (no account required):

| Dataset | Source |
|---------|--------|
| Al-Emadi DroneAudioDataset | GitHub (`saraalemadi/DroneAudioDataset`) |
| DronePrint | GitHub (`DronePrint/DronePrint`) |
| Svanström & Englund | GitHub (`DroneDetectionThesis/Drone-detection-dataset`) |
| Yi et al | Zenodo record 7779574 — **extra step required**, see [Yi et al. Special Handling](#yi-et-al-special-handling) |

At the end it prints download instructions for the 5 datasets below that require a manual step.

---

### Step 2 — Manual Downloads

Download each dataset and unpack it into the matching folder under `datasets_raw/`:

| Dataset | URL | Unpack into |
|---------|-----|-------------|
| Authors compiled drone sounds | https://www.kaggle.com/datasets/j28l298/compiled-drone-sounds | `datasets_raw\authorsCompiledDroneDataset\` |
| H-2 drone audio | https://mobilithek.info/offers/605778370199691264 | `datasets_raw\H-2\` |
| ESC-50 environmental sounds | https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/YDEPUT | `datasets_raw\ESC-50\` |
| EmoSoundscapes | https://www.metacreation.net/projects/emo-soundscapes | `datasets_raw\EmoSoundscapes\` |
| UrbanSound8K | https://urbansounddataset.weebly.com/urbansound8k.html | `datasets_raw\UrbanSound8K\` |

---

---

## Step 3 — Special Dataset Handling

### Yi et al. Special Handling

The Yi et al. dataset (Zenodo 7779574) contains three recording configurations (A, B, C), each with train/test/valid splits recorded from two microphones — 324,000 files in total.  
Only **configuration C** was used in this study: a specific subset of **79,466 files** selected across all splits and both microphones.

A manifest file (`yi_et_al_manifest.csv`) records the exact filenames used. After the Zenodo archive has been unpacked into `datasets_raw\Yi\`, run **`build_Yi_dataset.py`**:

```bash
# Preview (no files copied)
python build_Yi_dataset.py "datasets_raw\Yi\C" --dry-run

# Apply
python build_Yi_dataset.py "datasets_raw\Yi\C"
```

This copies the 79,466 listed files from `datasets_raw\Yi\C` (searching all subfolders) into `Datasets\Yi et al\yes_drone\`. Nothing else is touched.

| File | Purpose |
|------|---------|
| `yi_et_al_manifest.csv` | Canonical list of the 79,466 filenames used |
| `build_Yi_dataset.py` | Reads the manifest, locates each file in Yi\C, copies to `Datasets\Yi et al\yes_drone\` |

**Breakdown of the 79,466 files by source subfolder:**

| Yi\C subfolder | Files | Notes |
|----------------|------:|-------|
| `train\mic1` | 32,400 | Full train mic1 set |
| `train\mic2` | 32,400 | Full train mic2 set |
| `valid\mic1` | 10,600 | Subset of valid |
| `test\mic1` | 3,866 | Subset of test |
| **Total** | **79,466** | |

> **Note:** test/valid files have no mic token in the filename and are stored identically in both mic1 and mic2 subfolders — they are not counted twice.  
> An additional **500 files** from this same Yi\C pool were moved into the calibration set (`Datasets\eval_threshold\`); see `eval_manifest.csv` and [Step 5](#step-5--calibration-dataset-eval_threshold).

---

### H-2 Special Handling

The H-2 dataset stores audio as **base64-encoded payloads inside XML files** and also requires
a file-size filtering step to reproduce the exact subset used in the study.

After placing the raw H-2 files in `datasets_raw\H-2\`, run **`prepare_h2.ps1`**:

```powershell
# Preview (no changes made)
powershell -ExecutionPolicy Bypass -File .\prepare_h2.ps1 -DryRun

# Apply
powershell -ExecutionPolicy Bypass -File .\prepare_h2.ps1
```

The script performs three stages automatically:

| Stage | Script | What it does |
|-------|--------|--------------|
| 1 | `xml_to_audio.py` | Decodes each XML file and writes a `.wav` file to `datasets_raw\H-2_converted\` |
| 2 | `replicate_h2.py` | Deletes files listed in `files_removed_h2.csv` to match the exact set used in the original study |
| 3 | robocopy | Copies the remaining WAVs to `Datasets\H-2\yes_drone\` |

The two helper scripts can also be run independently if needed:

```bash
# Stage 1 only — convert XML to WAV
python xml_to_audio.py "datasets_raw\H-2" -o "datasets_raw\H-2_converted" --recursive

# Stage 2 only — apply file filter (dry-run first to check)
python replicate_h2.py "datasets_raw\H-2_converted" "files_removed_h2.csv" --dry-run
python replicate_h2.py "datasets_raw\H-2_converted" "files_removed_h2.csv"
```

---

### Step 4 — Copy Datasets into Datasets/

Once all desired datasets are in `datasets_raw/`, run **`setup_2_copy.bat`**:

```bat
setup_2_copy.bat             :: copy all available datasets
setup_2_copy.bat --dry-run   :: preview without making changes
```

This script:
- Reports which raw sources are **present** or **absent** before copying
- Copies each available dataset into its correct `Datasets/` subfolder
- **Skips missing datasets with a warning** (not a fatal error) so you can re-run later after adding more

The Al-Emadi dataset is automatically split 80 % / 20 % (alphabetical, deterministic) into
`Datasets\TrainingDatasets\Al-Emadi\train\` and `\validation\` for HuggingFace `audiofolder` loading
(used by CNN-LSTM and ResNet-34 training).

---

### Step 5 — Calibration Dataset (`eval_threshold`)

Two approaches are available:

#### Option A — Exact replication (recommended)

`replicate_eval_threshold.py` reads `eval_manifest.csv` and copies or **moves** each file
from its source dataset folder into `Datasets\eval_threshold\` under the **exact prefixed
filename** recorded in the manifest.
No randomness, no allocation logic — the result is identical to the original calibration set.

**Moving is the recommended mode** — it keeps the source dataset folders in the correct
state.

```bash
# Step 1 — preview (no files transferred)
python replicate_eval_threshold.py

# Step 2 — execute with move (recommended)
python replicate_eval_threshold.py --execute --move

# Alternative — copy instead of move (keeps source untouched)
python replicate_eval_threshold.py --execute
```

> **Note:** H-2 files will show as "missing" until `prepare_h2.ps1` has been run.  
> All other datasets must be populated first (Steps 1–3 above).

#### Option B — Dynamic generation

`generateThresholdEval.py` redistributes files fairly across all datasets using duration-balanced allocation.  
Use this if you want to regenerate the calibration set from scratch (e.g. after adding new datasets).  
It also prints a comparison against `eval_manifest.csv` at the end so you can see how close the new plan is to the original.

```bash
# Preview plan and manifest diff
python generateThresholdEval.py          # DRY_RUN = True (default)

# Apply (set DRY_RUN = False inside the script first)
python generateThresholdEval.py
```

---

---

## Dataset directory expected contents and structure for replication:

Emo soundscapes we use mixed sounds (613 sounds total)
\Datasets\EmoSoundscapes\unknown

Al-Emadi\yes_drone: 1332 samples
Al-Emadi\unknown: 10372 samples

Augmented_Datasets_Alemadi\"Augmentation"\yes_drone\1332 samples
Augmented_Datasets_Alemadi\"Augmentation"\unknown\10372 samples

AuthorsCompiledSounds\yes_drone\26 samples
AuthorsCompiledSoudns\unknown\4 samples

DronePrint\yes_drone\15 samples
DronePrint\yes_drone\0 samples

ESC-50-master\unknown\2000 samples


---

## Requirements

- **Python 3.11** (other versions not tested)
- Run `setup_1_env.bat` to create the venv and install all dependencies automatically.

### Manual torch install

If the automatic install picks the wrong CUDA version, install torch manually into the venv:

```bash
.venv311\Scripts\activate.bat
pip install torch==2.7.0+cu126 --index-url https://download.pytorch.org/whl/cu126
```

### Formatting fix

Due to a NumPy/datasets version incompatibility the `datasets` library needs a one-line patch
(applied automatically by `setup_1_env.bat`). If you reinstall packages and the error returns,
re-apply it manually:

```powershell
powershell -ExecutionPolicy Bypass -File .\Formatting_Fix\Formatting_Fix.ps1
```

The patch changes lines 196–197 in `datasets\formatting\formatting.py` to:
```python
return np.array(array, dtype=object)
return np.array(array)
```

---

## CNN-LSTM

### Configuration

| File | What to check |
|------|---------------|
| `CNN_LSTM\common.py` | `TRAIN_SET` — points to `Datasets\TrainingDatasets\Al-Emadi` by default (relative path, no edit needed) |
| `CNN_LSTM\common.py` | `DATASETS` — paths for evaluation datasets (all relative, no edit needed) |

### Training

```bash
.venv311\Scripts\activate.bat
cd CNN_LSTM
python main.py
```

---

## ResNet-34

### Configuration

| File | What to check |
|------|---------------|
| `RESNET34\config.py` | `TRAIN_SET`, `DATASETS` — all relative paths, no edit needed |
| `RESNET34\resnet_34.py` | Line ~294: training directory; Line ~313: model output path |

### Training

Configure `resnet_34.py` output path, then:

```bash
.venv311\Scripts\activate.bat
cd RESNET34
python resnet_34.py
```

---

## Transformer Pipeline

### Configuration

| File | What to check |
|------|---------------|
| `TRANSFORMER\config\dataset_config.py` | `ENHANCED_DATASETS` — all relative paths, no edit needed |
| `TRANSFORMER\main_transformers.py` | `TrainingConfig.data_dir` — points to `Datasets\Al-Emadi` (flat yes_drone/unknown, no train/val split needed here) |
| `TRANSFORMER\models\model_transformers.py` | `ModelConfig.OUTPUT_DIR` — output directory for saved checkpoints |

### Data augmentation

Offline augmentation is done via `TRANSFORMER\utils\augment_audio_files.py`.  
It modifies files **in-place**, so it must be run against the `Augmented_Datasets_Alemadi/` copies, **not** the originals.

The five augmentation variants map directly to the five subfolders:

| Folder | Mode flag | What is applied |
|---|---|---|
| `Binary_Drone_Audio_AllAugments` | `all_augments` | Gaussian noise + BandPass filter + random temporal cropping |
| `Binary_Drone_Audio_BandPassed` | `bandpass` | BandPass filter only |
| `Binary_Drone_Audio_Clipped` | `clipped` | Random temporal cropping only |
| `Binary_Drone_Audio_GaussianAndBandPass` | `gaussian_bandpass` | Gaussian noise + BandPass filter |
| `Binary_Drone_Audio_GaussianNoise` | `gaussian` | Gaussian noise only |

```bash
cd TRANSFORMER\utils

# Preview what would run (no changes)
python augment_audio_files.py --dry-run

# Augment all five folders at once
python augment_audio_files.py --all

# Augment a specific folder
python augment_audio_files.py --mode clipped
python augment_audio_files.py --mode all_augments

# Augment a custom directory (mode auto-detected from folder name)
python augment_audio_files.py --dir "path\to\folder"

# Generate sample before/after spectrograms without modifying any files
python augment_audio_files.py --spectrogram

# Skip the interactive confirmation prompt
python augment_audio_files.py --all --yes
```

> **Note:** The in-pipeline augmentation in `data\data_transformers.py` has a known bug with augmentation method selection. Keep `self.augment_data = False` in `main_transformers.py` and use the offline script above instead.

### Training

```bash
.venv311\Scripts\activate.bat
cd TRANSFORMER

#Single epoch only, you can use augmented data in path to get augmented model.
python .\main_transformers.py --data-dir "Path" --epochs 1
#Or you can choose to train the entire 20 epochs by omitting the --epochs flag, but it will take much longer.
```

---

## Evaluation

### Transformer (CLI — recommended)

Always run from the **repo root**:

```bash
# Single model
python -m TRANSFORMER.cli file --model-path <path\to\checkpoint>

# Multi-model
python -m TRANSFORMER.cli multi-model --base-strategy file

# With calibration
python -m TRANSFORMER.cli file --model-path <path> --calibrate --calibration-key CalibrationDataset
```
Despite the functionality of "clip" windowing option in the code, it's functionality hasnt been updated to match the pipeline yet. You should only use the "file" aggregation         

### CNN-LSTM and ResNet-34

Run the evaluation scripts directly after verifying the dataset paths in their respective config files.  
Outputs are `.csv` files per dataset, suitable for further analysis.

> **Note:** Clip-based evaluation (cuts audio and skips aggregation) is present in the codebase but should not be used — it has poor performance and may be broken.

### Calibration dataset

`generateThresholdEval.py` creates a calibration subset by moving files from the main datasets into `Datasets\eval_threshold\`. Edit the source directories inside the script before running. Note that this will NOT replicate the split from experiment. You should use the `replicate_eval_threshold.py` script instead for exact replication, which reads the manifest and copies/moves files accordingly.

---

## Results analysis and plotting

When all the evaluations are complete, you should group the resulting folders together and run the script: `Results&Analysis\Analysis\Analysis Scripts\AuxiliaryScripts\01_aapply_epoch_calibration_thresholds`
This script can be run first in --dry-run mode to preview the expected results. After making sure that the files affected are as expected you can run it in execution mode to apply the calibration thresholds to the csv files.
The script will read the calibration datasets csv results and calculate the optimal threholds for specific epoch for each model. Then it will apply these thresholds to the datasets for those models and epochs.
                
To create the fusion dataset run the 1_create_fusion_dataset.py from the Auxiliary scripts

### Model Ranking

The script `Results&Analysis\Analysis\Analysis Scripts\AuxiliaryScripts\02_rank_models.py` reads the calibrated CSV results and produces a summary ranking of all models across datasets. It also generates plots comparing model performance.

```bash

## Project Structure

```
### Graphs and plots

To generate visualizations use the 6_comprehensive_evaluator.py located in Analysis Scripts folder.

submission_123/
├── setup_1_env.bat            # Step 1: venv + auto-downloads
├── setup_2_copy.bat           # Step 3: copy raw datasets into Datasets/
├── setup.bat                  # Top-level entry point / help
├── prepare_h2.ps1             # H-2 XML-to-WAV conversion + filter
├── create_datasets_dirs.ps1   # Creates Datasets/ folder tree
├── copy_raw_datasets.ps1      # Copies raw data into Datasets/
├── xml_to_audio.py            # H-2: decode base64 XML -> WAV
├── replicate_h2.py            # H-2: apply original file-size filter
├── files_removed_h2.csv       # H-2: list of files removed in original study
├── build_Yi_dataset.py        # Yi et al.: copy exact subset from Yi\C
├── yi_et_al_manifest.csv      # Yi et al.: list of the 79,466 files used
├── generateThresholdEval.py   # Generate calibration subset (dynamic, with manifest diff)
├── Formatting_Fix/            # datasets library hotfix
├── datasets_raw/              # Raw downloaded datasets (git-ignored)
├── Datasets/                  # Processed datasets ready for training
│   ├── Al-Emadi/             # yes_drone / unknown
│   ├── TrainingDatasets/
│   │   └── Al-Emadi/        # train/ + validation/ splits for CNN-LSTM/ResNet
│   ├── Augmented_Datasets_Alemadi/
│   ├── DronePrint/
│   ├── AuthorsCompiledSounds/
│   ├── Svanstrom & Englund/
│   ├── EmoSoundscapes/
│   ├── ESC-50-master/
│   ├── UrbanSound8K/
│   ├── H-2/
│   ├── Yi et al/
│   └── eval_threshold/
├── Models/                    # Saved model checkpoints
├── CNN_LSTM/                  # CNN-LSTM architecture
├── RESNET34/                  # ResNet-34 architecture
├── TRANSFORMER/               # Transformer-based models
├── TRANSFORMER\utils\augment_audio_files.py  # Data augmentation script for replicating research data-augments.
├── auxiliary_scripts/replicate_eval_threshold.py     # Replicate eval_threshold exactly from eval_manifest.csv
└── Results&Analysis/          # Evaluation results and plots
```

---

## License

This project is licensed under a non-commercial license. See [LICENSE](LICENSE) for details.  
Commercial use is prohibited.
