# Reference-tool output comparison

This directory provides the metric-calculation code used for the matched-parameter preprocessing-output comparison reported in Table 3 of the manuscript.

## Scope

The preprocessing outputs were generated separately in M3-Platform and the corresponding reference tools under the settings recorded in `parameters.json`. Those operations included graphical-interface configuration and, for Tobii Pro Lab, proprietary software operation. The supplied Python scripts do not automate either application's graphical interface. They begin with the exported preprocessing outputs, align comparable channels or timestamps, and calculate the reported agreement metrics.

The private EEG, fNIRS, and eye-tracking validation recordings, their sample-level preprocessing outputs, and the resulting comparison files are not distributed. The scripts document and reproduce the metric calculations when users supply their own authorized paired exports.

## Included scripts

- `scripts/compare_eeg.py`: channel matching, Pearson correlation, RMSE, NRMSE, and maximum absolute error for EEG CSV exports.
- `scripts/compare_fnirs.py`: channel matching and the same continuous-signal metrics for pre-bandpass and post-bandpass HbO/HbR CSV exports.
- `scripts/compare_eyetracking.py`: timestamp matching, gaze/pupil signal metrics, fixation-event summaries, point-wise agreement, Cohen's kappa, and fixation F1-score.

The scripts require packages already pinned in the repository-level `requirements.txt`: NumPy, pandas, SciPy, and scikit-learn.

## Expected exported columns

EEG and fNIRS CSV files must contain `Time_s` followed by channel columns. Corresponding M3-Platform and reference-tool exports must use matching channel names; matching is case-insensitive for EEG and whitespace/case-normalized for fNIRS.

The M3-Platform eye-tracking gaze CSV must contain:

```text
Timestamp_s,GazeX_px,GazeY_px,Pupil_mm,Velocity_deg_s
```

The M3-Platform fixation CSV must contain `Duration_s`. The reference input is a Tobii Pro Lab tab-separated export containing the standard columns used by the script, including `Sensor`, `Recording timestamp`, gaze-point coordinates, filtered pupil diameter, and eye-movement classification fields.

## Commands

Run commands from this directory and replace the placeholders with authorized local exports.

```bash
python scripts/compare_eeg.py \
  /path/to/m3_eeg.csv \
  /path/to/eeglab_eeg.csv \
  --output-dir results/eeg
```

```bash
python scripts/compare_fnirs.py \
  --m3-pre /path/to/m3_fnirs_pre_bandpass.csv \
  --reference-pre /path/to/homer3_fnirs_pre_bandpass.csv \
  --m3-post /path/to/m3_fnirs_post_bandpass.csv \
  --reference-post /path/to/homer3_fnirs_post_bandpass.csv \
  --output-dir results/fnirs
```

```bash
python scripts/compare_eyetracking.py \
  --m3-gaze /path/to/m3_et_gaze.csv \
  --m3-fixations /path/to/m3_et_fixations.csv \
  --tobii-tsv /path/to/tobii_export.tsv \
  --output-dir results/eyetracking
```

The eye-tracking comparison uses nearest-timestamp matching with a 15 ms tolerance and a 30-degree/s threshold for the point-wise fixation classification, as recorded in `parameters.json`.

## Interpretation boundary

These scripts reproduce the comparison calculations when supplied with the corresponding exported outputs. They do not reproduce the private recordings, automate GUI operation, or establish general performance superiority over the reference tools.
