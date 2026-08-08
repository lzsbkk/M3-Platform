import copy
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

SOURCE = Path(__file__).resolve().parents[1] / 'gallery/app/data/et_data.py'
spec = importlib.util.spec_from_file_location('m3_et_intervals', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ETData = module.ETData


class EventIntervalTests(unittest.TestCase):
    def make_data(self, times, x=None):
        obj = ETData.__new__(ETData)
        obj.sample_rate = 100.0
        obj.processed_data = pd.DataFrame({
            'Timestamp': times,
            'GazePointX': np.zeros(len(times)) if x is None else x,
            'GazePointY': np.zeros(len(times)),
        })
        return obj

    def test_short_gaps_are_interpolated(self):
        for count in (1, 2):
            x = np.arange(count + 4, dtype=float)
            x[1:count + 1] = np.nan
            obj = self.make_data(np.arange(len(x)) / 100, x)
            obj.interpolate_gaps(75)
            np.testing.assert_allclose(obj.processed_data.GazePointX, np.arange(len(x)))

    def test_long_and_unbounded_gaps_remain_missing(self):
        x = np.arange(20, dtype=float)
        x[:2] = np.nan
        x[4:15] = np.nan
        x[-2:] = np.nan
        obj = self.make_data(np.arange(20) / 100, x)
        obj.interpolate_gaps(75)
        np.testing.assert_array_equal(np.isnan(obj.processed_data.GazePointX), np.isnan(x))

    def test_event_includes_last_sample_period(self):
        obj = self.make_data(np.arange(7) / 100)
        event = obj.create_event(0, 5, 'fixation')
        self.assertAlmostEqual(event['duration'], .060)
        self.assertEqual(obj.discard_short_fixations([event], 60), [event])
        tail = obj.create_event(6, 6, 'fixation')
        self.assertAlmostEqual(tail['duration'], .010)
        times = obj.processed_data.Timestamp.to_numpy()
        self.assertEqual(((times >= event['start']) & (times < event['end'])).sum(), 6)

    def test_fragments_survive_until_merge(self):
        obj = self.make_data(np.arange(9) / 100)
        fixations, _ = obj.classify_fixations_and_saccades(
            np.array([0., 0., 40., 0., 0., 40., 0., 0., 40.]), 30)
        self.assertEqual(len(fixations), 3)
        merged = obj.merge_adjacent_fixations(fixations, 75, .5)
        self.assertEqual(len(obj.discard_short_fixations(merged, 60)), 1)

    def test_merge_uses_original_weights_without_mutating_input(self):
        obj = self.make_data([0., .01])
        events = [dict(start=0., end=.1, duration=.1, x=0., y=0.),
                  dict(start=.12, end=.22, duration=.1, x=.4, y=.2)]
        original = copy.deepcopy(events)
        merged = obj.merge_adjacent_fixations(events, 75, .5)
        self.assertAlmostEqual(merged[0]['x'], .2)
        self.assertAlmostEqual(merged[0]['y'], .1)
        self.assertAlmostEqual(merged[0]['duration'], .22)
        self.assertEqual(events, original)

    def test_duration_roundoff_does_not_drop_threshold_event(self):
        obj = self.make_data([0., .01])
        events = [dict(duration=4.06 - 4.), dict(duration=.059)]
        self.assertEqual(obj.discard_short_fixations(events, 60), events[:1])


if __name__ == '__main__':
    unittest.main()
