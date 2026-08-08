"""Run the project ET pipeline against a Pro Lab wearable TSV export."""
import argparse
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, f1_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('export', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / 'gallery/app/data/et_data.py'
    spec = importlib.util.spec_from_file_location('m3_et_validation', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    keep = ['Sensor', 'Recording name', 'Participant name', 'Recording timestamp [ms]',
            'Gaze point X [MCS px]', 'Gaze point Y [MCS px]',
            'Pupil diameter left [mm]', 'Pupil diameter right [mm]', 'Eye movement type']
    parts = []
    for chunk in pd.read_csv(args.export, sep='\t', usecols=keep, chunksize=150000, low_memory=False):
        parts.append(chunk.loc[chunk.Sensor.eq('Eye Tracker')])
    data = pd.concat(parts, ignore_index=True)
    results = []
    for recording, frame in data.groupby('Recording name', sort=True):
        frame = frame.sort_values('Recording timestamp [ms]').reset_index(drop=True)
        times = frame['Recording timestamp [ms]'].to_numpy(float) / 1000
        assert np.all(np.diff(times) > 0)
        x = frame['Gaze point X [MCS px]'].to_numpy(float)
        y = frame['Gaze point Y [MCS px]'].to_numpy(float)
        obj = module.ETData.__new__(module.ETData)
        obj.__dict__.update(file_path=str(args.export), video_path=None, data_type='et',
            events=[], fixations=None, saccades=None, blinks=None, fps=25,
            resolution=[1920, 1080], video_duration=None, FOV=106, h_fov=95,
            v_fov=63, sample_rate=None, output_path=None, db_info=None, aois=[])
        obj.raw_data = pd.DataFrame(dict(Timestamp=times, GazePointX=x / 1920,
            GazePointY=y / 1080, PupilLeft=frame['Pupil diameter left [mm]'].to_numpy(float),
            PupilRight=frame['Pupil diameter right [mm]'].to_numpy(float)))
        with (args.output / (recording.replace(' ', '_') + '.log')).open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
            obj.apply_i_vt_filter(velocity_threshold=30, blink_threshold=100,
                blink_max_threshold=300, interpolate=True, max_gap_length=75,
                denoise=True, denoise_method='Moving Average', window_size=3,
                use_time_window=True, velocity_window_length=20, merge_fixations=True,
                max_time_between_fixations=75, max_angle_between_fixations=.5,
                discard_short_fixations=True, min_fixation_duration=60,
                pupil_interpolate=True, pupil_max_gap=75, pupil_filter=True,
                pupil_filter_method='Moving Average', pupil_window_size=5, save=False)
        labels = frame['Eye movement type'].fillna('').str.strip().str.lower()
        mask = labels.ne('').to_numpy() & np.isfinite(x) & np.isfinite(y)
        reference = labels.eq('fixation').to_numpy()
        predicted = np.zeros(len(frame), dtype=bool)
        for event in obj.fixations.to_dict('records'):
            predicted |= (times >= event['start']) & (times < event['end'])
        row = dict(Recording=recording, Participant=frame['Participant name'].iloc[0],
            N=int(mask.sum()), Kappa=cohen_kappa_score(reference[mask], predicted[mask]),
            F1=f1_score(reference[mask], predicted[mask]),
            Agreement=float(np.mean(reference[mask] == predicted[mask])),
            Disagreements=int((reference[mask] != predicted[mask]).sum()))
        results.append(row)
        print(f'{recording}: kappa={row["Kappa"]:.6f}', flush=True)
    result = pd.DataFrame(results)
    result.to_csv(args.output / 'record_metrics.csv', index=False)
    summary = result[['Kappa', 'F1', 'Agreement']].agg(['mean', 'std', 'min', 'max'])
    summary.to_csv(args.output / 'summary.csv')
    with args.export.open('rb') as stream:
        export_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    audit = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        export_sha256=export_hash, recordings=len(result),
        above_09=int((result.Kappa > .9).sum()), disagreements=int(result.Disagreements.sum()),
        interval='[start, end)', coordinate_model='Existing 2D + FOV',
        scope='Project processing functions with TSV input adapter; native recording importer not exercised.')
    (args.output / 'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(summary.to_string())
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
