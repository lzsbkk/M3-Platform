# Manual expected-output checklist

Complete the steps in the parent `README.md` through the M³-Platform GUI. Because exported file names contain timestamps and project identifiers, verify the following content rather than an exact file name.

## Import

- The project tree contains `ReproducibleWorkflow` → `FunctionalDemo` → `Participant01`.
- EEG opens as a 64-channel, 160-Hz recording and event `T1` is available.
- The SNIRF record opens with intensity channels and event `1`.
- The questionnaire page displays `Workflow demo scale`.

## Processing and features

- EEG preprocessing records the 1–40 Hz bandpass, 50-Hz notch, and average reference; the feature table contains channel rows and the selected Mean Amplitude, Amplitude Variance, and Total Energy fields.
- fNIRS preprocessing records first-order detrending, TDDR, and the 0.01–0.2 Hz bandpass; the feature table contains the selected Mean, Peak, Minimum, AUC, and Peak Latency fields.
- Questionnaire export contains the selected answer and a `Demo score` value of `1`.

## Visualization and export

- The bundled EEG and fNIRS modalities can display their processed data in the corresponding GUI visualization cards.
- The participant output folders contain exported preprocessing data, processing-parameter records, and feature tables for the operations completed above.
- The tutorial does not require an inference result and does not provide an expected physiological or classification outcome.
