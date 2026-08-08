# Reproducible M³-Platform Workflow

This example reproduces the software path shown at interface level in manuscript Fig. `\ref{fig:result}`: project organization, modality import, preprocessing, feature extraction, visualization, and export. The files are deliberately small enough for functional verification. The bundled EEG and fNIRS records come from separate public sources, so this example is not a synchronized multimodal experiment and is not evidence of physiological, clinical, or algorithmic performance. Eye-tracking participant data are not distributed in this example.

## Contents

- `sample_data/`: GUI-readable EEG EDF, fNIRS SNIRF, and questionnaire JSON inputs; provenance is in `sample_data/LICENSES.md`.
- `configuration/workflow.json`: the exact parameters used below.
- `expected_outputs/README.md`: files and visible results to check after completing the GUI steps.

## Before starting

Install and launch the full application as described in the repository-level `README.md`. Keep the application working directory at `gallery`, because project creation copies `resource/config.json` and `resource/Template.json` using relative paths.

## GUI walkthrough

Use the values in `configuration/workflow.json`; do not substitute values from the paper's matched-parameter reference-tool table without checking the configuration.

### 1. Create Project, Experiment, and Participant

1. From the project page, select **Create Project** and create `ReproducibleWorkflow`.
2. Add an experiment named `FunctionalDemo`.
3. Add participant `Participant01` (age 24 for the fNIRS age field).
4. In the participant import dialog select:
   - EEG: `reproducibility/gui_workflow/sample_data/eeg/S001R03.edf`
   - fNIRS: `reproducibility/gui_workflow/sample_data/fnirs/neuro_run01.snirf`

Expected: the participant appears below the experiment and the EEG, fNIRS, and Questionnaire pages become available. This corresponds to the project organization shown in Fig. `\ref{fig:result}`a.

### 2. Confirm import

Open each modality page and inspect its information card and waveform/table view.

Expected: EEG reports 64 channels at 160 Hz, and the fNIRS SNIRF record loads intensity channels and annotations. If a page reports **Data Not Loaded**, stop and re-check the selected path rather than continuing.

### 3. EEG preprocessing and features

In **EEG → Data Preprocessing** enable:

- Bandpass Filter: `1.0` to `40.0` Hz
- Line Noise Filter: `50 Hz`
- Re-referencing: `Average`

Select **Confirm**. In **Event Window Setting**, choose event `T1`, set `-1.0` to `2.0` s and baseline `None`. In **Feature Analysis**, choose event `T1` and extract Mean Amplitude, Amplitude Variance, and Total Energy.

Expected: the processed waveform updates (Fig. `\ref{fig:result}`c), a feature table is generated, and timestamped preprocessing/feature files are written to the participant EEG output directories.

### 4. fNIRS preprocessing and features

In **fNIRS → Data Preprocessing** enable:

- Detrend: order `1`
- Motion Correction: `TDDR`
- Bandpass Filter: `0.01` to `0.2` Hz

Select **Confirm**. In **Event Window Setting**, choose event `1`, set `-2.0` to `10.0` s and baseline `None`. In **Feature Analysis**, select Mean, Peak, Minimum, AUC, and Peak Latency.

Expected: the hemodynamic view updates and a feature table is exported.

### 5. Questionnaire-associated metadata

The project creates a participant questionnaire file from `gallery/resource/Template.json`. To reproduce this compact example, replace the experiment's generated `Template.json` with `sample_data/questionnaire/demo_questionnaire.json`, reopen the Questionnaire page, select **Option 1**, and submit.

Expected: an answer-record CSV and a variable CSV are created; `Demo score` equals `1`. Scoring formulas and item values are template-defined. There is no global reverse-scoring or missing-value default.

### 6. Export and check

Use the EEG and fNIRS export/save controls. Confirm the presence of preprocessed data, features, visualizations, and parameter files under the participant output folders. GUI-generated file names may include timestamps; compare the folders, file types, table headings, and visible interface states with `expected_outputs/README.md` rather than expecting fixed timestamped names.

Optional model inference is not part of the required walkthrough. If used, select a compatible TorchScript model in the EEG or fNIRS model card; the current inference implementation loads it on the CPU. A model trained for a different channel order, sampling rate, event window, or label definition is not a valid example input.
