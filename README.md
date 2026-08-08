# M³-Platform

M³-Platform is an offline desktop application for organizing, preprocessing, analyzing, visualizing, and exporting EEG, fNIRS, eye-tracking (ET), and questionnaire-associated data.

## Installation and Launch

### Tested configuration

The application and the paper's sequential software benchmark were run on the following recorded configuration. This is a tested configuration, not a minimum hardware requirement.

- Microsoft Windows 10, build 26200 (`Windows-10-10.0.26200-SP0`)
- Python 3.9.12
- Intel Core i9-12900H-compatible workstation record (14 physical/20 logical cores)
- 16 GB nominal RAM (15.80 GiB reported by the operating system)
- CPU execution for the GUI preprocessing workflow and TorchScript inference

The current evidence does not establish a minimum CPU or RAM requirement, and macOS/Linux GUI compatibility has not been validated. A GPU is not required to launch the application, run the included reproducible workflow, or use the current TorchScript inference paths: those paths explicitly load models on the CPU. The public-dataset training scripts select CUDA when available and otherwise fall back to CPU; the archived paper runs record `cuda`, but the GPU model was not captured in the experiment metadata.

### Create the environment

From an Anaconda Prompt or PowerShell in the repository root:

```powershell
conda env create -f environment.yml
conda activate m3-platform-py39
```

`environment.yml` fixes Python 3.9.12 and installs the pinned packages in `requirements.txt`. Major versions include PyQt5 5.15.11, MNE-Python 1.6.1, MNE-NIRS 0.6.0, NumPy 1.24.4, SciPy 1.10.1, pandas 2.0.3, scikit-learn 1.3.2, and PyTorch 2.4.0. The Git-based PyQt-SiliconUI dependency is pinned to an exact commit.

### Launch

The application uses relative paths for `resource/config.json`, `resource/Template.json`, fonts, and the bundled EyeLink EDF converter. Launch from the `gallery` directory:

```powershell
cd gallery
python demo.py
```

On successful startup, the M³-Platform main window opens. As a minimal verification, select **Create Project**, create one project and one experiment, and confirm that the project appears in the left navigation tree. EyeLink EDF-to-ASC conversion additionally depends on the bundled Windows executable under `gallery/resource/EDF2ASC/`; the other sample inputs do not use that converter.

## Reproducible Example Workflow

The repository-based example is in [`reproducibility/gui_workflow/`](reproducibility/gui_workflow/README.md). It provides legally redistributable EEG and fNIRS sample files, deterministic questionnaire metadata, a fixed JSON parameter record, step-by-step GUI instructions, and an expected-output checklist for manual verification. Eye-tracking participant data are not distributed with the example.

The example demonstrates software operation only. Its modality files are independent public records and must not be used to infer synchronized physiology, clinical validity, or classifier performance.

## Repository layout relevant to reproducibility

- `environment.yml`: Python version and environment entry point.
- `requirements.txt`: pinned full-application Python dependencies.
- `gallery/demo.py`: application entry point.
- `gallery/resource/`: required configuration, questionnaire template, fonts, montage resources, and Windows EyeLink converter.
- `reproducibility/gui_workflow/`: small GUI sample workflow, fixed parameters, and a manual output checklist.
- `reproducibility/gui_performance/`: optional GUI-operation performance recorder documentation, input-configuration record, and local-result verification utility.
- `reproducibility/reference_tool_comparison/`: parameter record and metric-calculation scripts for the Table 3 preprocessing-output comparison.

## License

The original M3-Platform source code is distributed under the GNU General Public License v3.0; see [`LICENSE`](LICENSE). GPL-3.0 permits research and commercial use subject to its license conditions, including source-code and same-license obligations when covered derivative works are distributed. Third-party dependencies, sample data, fonts, and vendor utilities remain subject to their respective terms; sample-data provenance and licenses are recorded in [`reproducibility/gui_workflow/sample_data/LICENSES.md`](reproducibility/gui_workflow/sample_data/LICENSES.md).
