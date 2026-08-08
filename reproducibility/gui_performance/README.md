# GUI-operation performance measurements

This directory documents the optional recorder used to characterize six operations initiated through the normal M3-Platform graphical interface: preprocessing and feature extraction for EEG, fNIRS, and eye tracking.

The recorder is implemented in `gallery/app/common/monitor.py` and is attached to the corresponding GUI slot functions. It is disabled unless `M3_GUI_PERFORMANCE_DIR` is set. One button click executes the original operation once and produces one measurement record; the recorder does not run a headless benchmark or repeat an operation automatically.

## Recorded protocol

- Configure and load one fixed input through the GUI.
- Keep the input and parameters unchanged for that operation.
- Execute one warm-up click, followed by 20 measured clicks.
- Execute only one operation at a time in the same application session.
- Measure from entry into the processing function invoked by the GUI to its return, including automatic result saving.
- Sample application-process-tree RSS every 2 ms after a 0.5 s pre-operation baseline.

The fixed input characteristics and settings are recorded in `performance_inputs.json`. The private ET recording and its scene video are not distributed.

## Enabling the recorder

From PowerShell, set the output directory before starting the application:

```powershell
$env:M3_GUI_PERFORMANCE_DIR = "C:\M3_GUI_performance_results"
$env:M3_GUI_PERFORMANCE_SESSION = "formal_gui_run"
$env:M3_GUI_PERFORMANCE_SAMPLE_MS = "2"
$env:M3_GUI_PERFORMANCE_BASELINE_SECONDS = "0.5"
$env:M3_GUI_PERFORMANCE_WARMUPS = "1"
$env:M3_GUI_PERFORMANCE_RUNS = "20"
cd gallery
python demo.py
```

Close that PowerShell session or remove `M3_GUI_PERFORMANCE_DIR` to disable recording.

## Output and verification

The recorder writes `gui_environment.json`, `gui_raw_results.csv`, and `gui_summary_results.csv` to the user-selected local output directory. The measurements used for the manuscript revision are not distributed in this repository.

To check a new run:

```powershell
python reproducibility\gui_performance\verify_gui_results.py --results C:\M3_GUI_performance_results --session formal_gui_run
```

The ET measurement configuration describes the private fixed recording used in the study. Neither that recording nor the resulting measurement files are distributed. The measurements do not establish performance superiority over other software.
