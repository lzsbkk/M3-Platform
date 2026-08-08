# Eye-tracking regression checks

Run the focused regression tests with the project dependencies installed:

```sh
python -m unittest discover -s tests -p 'test_et_intervals.py'
```

Run the project processing functions against a Pro Lab wearable export:

```sh
python tests/validate_et_export.py EXPORT_TSV OUTPUT_DIRECTORY
```

The export must contain millisecond timestamps and the columns requested by
the script. The validation uses the published 20-record building facade data
(DOI: 10.5281/zenodo.7125956) and the `M3_30dps_Mean3` Pro Lab export. It keeps
the existing 2D/FOV velocity calculation and the 30 degrees/s, 20 ms velocity,
75 ms interpolation, 3-sample moving average, 75 ms/0.5 degree merging, and
60 ms minimum fixation settings.

## Event interval contract

New fixation and saccade events use `[start, end)` intervals. The exclusive end
is the next sample timestamp; the last sample uses the recording's estimated
sample period. Consumers selecting samples must use `timestamp < end`.
Previously saved events are not migrated or rewritten. Reprocess recordings
before comparing event durations or sample membership across software versions.

Short gaze gaps now include one- and two-sample gaps. Short classified fragments
remain available for merging, and the minimum fixation duration is applied
after merging. Merge centers use event durations captured before the interval
is updated. Duration comparisons allow 1e-10 seconds of numerical roundoff.

## Verification results

Six focused tests passed. On the 20-record Mean3 export, the project pipeline
produced a record-mean Cohen's kappa of 0.900204 (SD 0.023609, range
0.859099-0.955867), mean fixation F1 of 0.952522, and mean agreement of 0.953534.
Nine records exceeded kappa 0.9. The input export SHA-256 is
`f9136e49a18a915b34e940d46da3076bc4102e5085c71417284fae86e2f4542b`.

These checks exercise the actual ET processing methods through a TSV input
adapter. They do not exercise the native recording importer or the GUI. The
script emits record-level metrics, summary statistics, logs and source/input
hashes for auditing. Do not interpret processed-versus-raw gaze correlations
as agreement between two filtered gaze outputs.
