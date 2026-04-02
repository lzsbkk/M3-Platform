import copy
from PyQt5.QtGui import QColor
import re
import numpy as np
import pandas as pd
from mne.annotations import Annotations
import mne
from mne.preprocessing.nirs import optical_density, beer_lambert_law, temporal_derivative_distribution_repair
import matplotlib.pyplot as plt
from mne.preprocessing.nirs import temporal_derivative_distribution_repair, beer_lambert_law
from mne_nirs.experimental_design import make_first_level_design_matrix, create_boxcar
from mne_nirs.statistics import run_glm
import matplotlib.ticker as ticker
from nilearn.plotting import plot_design_matrix
import openpyxl
from scipy import integrate
import subprocess

import matplotlib
import random
import os
import time

import pickle

import logging
mne.set_log_level('WARNING')
logging.getLogger('mne').setLevel(logging.WARNING)


matplotlib.use('Agg')

class FNIRSData:
    def __init__(self, project_base_path = None, filename=None, age = 10, output_path = None, db_info=None):
        self.parent = None
        self.processed_data = None
        self.raw_od = None
        self.data_type = 'fnirs'
        self.raw_data = None
        self.raw_hameo = None

        self.age = age
        self.default_event_window = (-2.0, 10.0)
        self.event_windows = {}
        self.default_event_baseline = None
        self.event_baseline = {}

        self.filename = filename
        self.events = []
        self.start_time = 0

        self.db_info = db_info
        self.viewmode = 'processd'

        self.output_path = output_path
        self.project_base_path = project_base_path

        if filename:
            if filename.endswith('.pkl'):
                loaded_instance = self.load_from_pickle(filename)
                self.__dict__.update(loaded_instance.__dict__)
            else:
                self.initialize_fnirs_data(filename)
        
        self.output_path = output_path
    
    def update_database(self, field, value):
        
        if not self.db_info:
            raise ValueError("db_info is not provided")

        project = self.db_info['project']
        subject_id = self.db_info['subject_id']
        project.update_subject_data(subject_id, 'fnirs', field, value)
    
    def save_to_pickle(self):
        
        parent = self.parent
        self.parent = None
        base_name = os.path.splitext(self.filename)[0]
        pickle_filename = f"{base_name}_preprocessed.pkl"
        with open(pickle_filename, 'wb') as f:
            pickle.dump(self, f)
        print(f"Data Saved To {pickle_filename}")

        relative_path = os.path.relpath(pickle_filename, start=self.db_info['project'].base_path)
        self.update_database('preprocessed', relative_path)
        self.parent = parent

    @classmethod
    def load_from_pickle(cls, filename):
        
        with open(filename, 'rb') as f:
            return pickle.load(f)
    
    def initialize_fnirs_data(self, filename):
        if filename.endswith('.lufr'):
            filename = self.convert_lufr_to_snirf(filename)
        self.raw_data = mne.io.read_raw_snirf(filename, optode_frame='unknown', preload=True)
        self.raw_od = optical_density(self.raw_data)
        self.processed_data = beer_lambert_law(self.raw_od, ppf=self.calculate_dpf_duncan(self.age))

        hbo_data = self.processed_data.get_data(picks='hbo')
        hbr_data = self.processed_data.get_data(picks='hbr')
        hbt_data = hbo_data + hbr_data

        new_ch_names = []
        for ch_name in self.processed_data.ch_names:
            if 'hbo' in ch_name.lower():
                new_ch_names.append(ch_name.replace('hbo', 'HbO').replace('HBO', 'HbO'))
            elif 'hbr' in ch_name.lower():
                new_ch_names.append(ch_name.replace('hbr', 'HbR').replace('HBR', 'HbR'))
            else:
                new_ch_names.append(ch_name)

        self.processed_data.rename_channels(dict(zip(self.processed_data.ch_names, new_ch_names)))

        hbt_info = mne.create_info(
            ch_names=[ch.replace('HbO', 'HbT') for ch in self.processed_data.ch_names if 'HbO' in ch],
            sfreq=self.processed_data.info['sfreq'],
            ch_types='hbo'
        )

        raw_hbt = mne.io.RawArray(hbt_data, hbt_info)
        self.processed_data.add_channels([raw_hbt], force_update_info=True)
        self.processed_data = self.reorder_fnirs_data(self.processed_data)
        self.processed_data.apply_function(lambda x: x * 1e6, picks=['hbo','hbr'])
        
        self.raw_hameo = self.processed_data.copy()

        self.read_events()
        self.update_attributes()

    @staticmethod
    def reorder_fnirs_data(raw_data):
        sd_pairs = []
        for ch in raw_data.ch_names:
            sd = re.match(r'(S\d+_D\d+)', ch).group(1)
            if sd not in sd_pairs:
                sd_pairs.append(sd)

        new_order = []
        for hb_type in ['HbO', 'HbR', 'HbT']:
            for sd in sd_pairs:
                channel = f"{sd} {hb_type}"
                if channel in raw_data.ch_names:
                    new_order.append(channel)

        return raw_data.reorder_channels(new_order)

    def calculate_dpf_duncan(self, age):
        
        if age < 0:
            raise ValueError("Age Cna't Be Negative")

        dpf = 4.99 + 0.067 * (age ** 0.814)
        return dpf
    
    def update_attributes(self):
        if self.viewmode == 'processed':
            self.data = self.processed_data.get_data()
        else:
            self.data = self.raw_hameo.get_data()

        self.channel_names = self.processed_data.ch_names
        print("Channel List Updated")
        # print(self.channel_names)
        self.num_channels = len(self.channel_names)
        self.sample_rate = self.processed_data.info['sfreq']
        self.duration = self.processed_data.times[-1] - self.processed_data.times[0]
        self.time = self.processed_data.times
        self.num_samples = self.data.shape[1]
        self.data_time = self.processed_data.times[-1]

        lower_percentile = 1  
        upper_percentile = 99  
        
        data_min = np.percentile(self.data, lower_percentile)
        data_max = np.percentile(self.data, upper_percentile)
        
        range_extension = 0.1  
        data_range = data_max - data_min
        data_min -= data_range * range_extension
        data_max += data_range * range_extension

        self.y_scale = [data_min, data_max]
    
    def read_events(self):
        annotations = self.processed_data.annotations
        
        self.events = []
        event_colors = {}  

        for onset, duration, description in zip(annotations.onset, annotations.duration, annotations.description):
            if description not in event_colors:
                color = QColor(*[random.randint(0, 255) for _ in range(3)])
                event_colors[description] = color
            else:
                color = event_colors[description]

            event = (onset, onset + duration, (color.red(), color.green(), color.blue()), description)
            self.events.append(event)

        print(f"Read {len(self.events)} events from the file.")

    def get_data(self, start_time, end_time):
        start_index = int(start_time * self.sample_rate)
        end_index = int(end_time * self.sample_rate)
        return self.time[start_index:end_index], self.data[:, start_index:end_index]

    def get_channel_names(self):
        return self.channel_names

    def get_y_scale(self):
        return self.y_scale

    def get_processed_data(self):
        return self.processed_data

    def copy(self):
        return copy.deepcopy(self)

    def set_default_event_baseline(self, baseline):
        
        self.default_event_baseline = baseline
        print(f"Default event baseline time updated: {baseline} seconds")

    def set_event_baseline(self, event_name, baseline):
        
        self.event_baseline[event_name] = baseline
        print(f"Baseline time updated for event '{event_name}': {baseline} seconds")

    def get_event_baseline(self, event_name):
        
        if event_name in self.event_baseline:
            return self.event_baseline[event_name]
        else:
            print(f"Warning: Baseline time not found for event '{event_name}'. Using default value {self.default_event_baseline} seconds.")
            return self.default_event_baseline
        
    def set_default_event_window(self, tmin, tmax):
        
        self.default_event_window = (tmin, tmax)
        print(f"Event Time Window Template Already Reseted: [{tmin}, {tmax}]")

    def set_event_window(self, event_name, tmin, tmax):
        
        self.event_windows[event_name] = (tmin, tmax)
        print(f"Time window updated for event '{event_name}': [{tmin}, {tmax}]")

    def get_event_window(self, event_name):
        
        if event_name in self.event_windows:
            return self.event_windows[event_name]
        else:
            matching_events = [event for event in self.events if event[3] == event_name]
            
            if matching_events:
                durations = [event[1] - event[0] for event in matching_events]
                
                if len(set(durations)) == 1 and durations[0] > 0:
                    tmax = durations[0]
                    tmin = self.default_event_window[0]
                    print(f"Warning: Time window not found for event '{event_name}'. Using default tmin {tmin} and event duration {tmax} as tmax.")
                    return (tmin, tmax)
            
            print(f"警告：未找到事件 '{event_name}' 的时间窗口，或事件持续时间不一致，或持续时间为0。使用默认值 {self.default_event_window}。")

            return self.default_event_window
        
    @classmethod
    def from_existing(cls, existing_data):
        new_instance = cls()
        
        new_instance.processed_data = existing_data.processed_data.copy() if existing_data.processed_data is not None else None
        new_instance.raw_od = existing_data.raw_od.copy() if existing_data.raw_od is not None else None
        new_instance.raw_data = existing_data.raw_data.copy() if existing_data.raw_data is not None else None
        new_instance.data_type = existing_data.data_type
        new_instance.default_event_window = existing_data.default_event_window
        new_instance.default_event_baseline = existing_data.default_event_baseline
        new_instance.event_windows = existing_data.event_windows.copy()
        new_instance.event_baseline = existing_data.event_baseline.copy()
        new_instance.filename = existing_data.filename
        new_instance.events = [event for event in existing_data.events]
        new_instance.start_time = existing_data.start_time
        new_instance.output_path = existing_data.output_path
        new_instance.project_base_path = existing_data.project_base_path
        new_instance.db_info = existing_data.db_info.copy()
        new_instance.age = existing_data.age
        new_instance.raw_hameo = existing_data.raw_hameo.copy()
        new_instance.parent = existing_data.parent

        if hasattr(existing_data, 'data'):
            new_instance.data = np.array(existing_data.data)
        if hasattr(existing_data, 'channel_names'):
            new_instance.channel_names = list(existing_data.channel_names)
        if hasattr(existing_data, 'num_channels'):
            new_instance.num_channels = existing_data.num_channels
        if hasattr(existing_data, 'sample_rate'):
            new_instance.sample_rate = existing_data.sample_rate
        if hasattr(existing_data, 'num_samples'):
            new_instance.num_samples = existing_data.num_samples
        if hasattr(existing_data, 'data_time'):
            new_instance.data_time = existing_data.data_time
        if hasattr(existing_data, 'duration'):
            new_instance.duration = existing_data.duration
        if hasattr(existing_data, 'time'):
            new_instance.time = np.array(existing_data.time)
        if hasattr(existing_data, 'y_scale'):
            new_instance.y_scale = list(existing_data.y_scale)

        return new_instance
    
    def convert_lufr_to_snirf(self, lufr_path):
        
        try:
            converter_path = os.path.abspath(os.path.join(
                os.getcwd(),
                'resource',
                'lumo2snirf.exe'
            ))
            
            if not os.path.exists(converter_path):
                raise FileNotFoundError(f"LUFR converter tool not found: {converter_path}")
            
            snirf_path = os.path.splitext(lufr_path)[0] + '.snirf'
            
            if os.path.exists(snirf_path):
                os.remove(snirf_path)
            
            subprocess.run(
                [converter_path, "-i", lufr_path, "-o", snirf_path],
                creationflags=subprocess.CREATE_NO_WINDOW  
            )
            
            for _ in range(30):  
                if os.path.exists(snirf_path) and os.path.getsize(snirf_path) > 0:
                    time.sleep(0.5)  
                    return snirf_path
                time.sleep(0.5)
                
            raise FileNotFoundError("Conversion timeout: SNIRF file not generated")
                    
        except Exception as e:
            print(f"Error during conversion: {str(e)}")
            raise
    
    def add_event(self, event):
        start_time, end_time, color, description = event
        if isinstance(color, QColor):
            color = (color.red(), color.green(), color.blue())
        elif isinstance(color, str):
            color = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        self.events.append((start_time, end_time, color, description))
        
        duration = end_time - start_time
        start_time_raw = start_time
        start_time_processed = start_time - self.get_start_time()
        
        for data in [self.processed_data, self.raw_od]:
            if data.annotations is None or len(data.annotations) == 0:
                orig_time = data.info['meas_date']
                start = start_time_raw if data == self.raw_od else start_time_processed
                annotation = Annotations(onset=[start], duration=[duration], description=[description], orig_time=orig_time)
                data.set_annotations(annotation)
            else:
                start = start_time_raw if data == self.raw_od else start_time_processed
                data.annotations.append(onset=[start], duration=[duration], description=[description])
        self.save_to_pickle()
        self.export_to_csv(export_channels=False, export_events=True, export_preprocessing=False)

    def delete_event(self, event):
        if event in self.events:
            self.events.remove(event)
            
            start_time, end_time, _, description = event
            start_time_raw = start_time
            start_time_processed = start_time - self.get_start_time()
            
            for data in [self.processed_data, self.raw_od]:
                if data.annotations is not None:
                    annotations = data.annotations
                    start = start_time_raw if data == self.raw_od else start_time_processed
                    mask = (annotations.onset != start) | (annotations.description != description)
                    data.set_annotations(annotations[mask])
            self.save_to_pickle()
            self.export_to_csv(export_channels=False, export_events=True, export_preprocessing=False)
        else:
            print(f"Warning: Event {event} not found in the events list.")

    def clear_events(self):
        self.events.clear()
        
        self.processed_data.set_annotations(None)
        self.raw_od.set_annotations(None)
        self.save_to_pickle()
        self.export_to_csv(export_channels=False, export_events=True, export_preprocessing=False)

    def get_events(self):
        return self.events

    def is_valid_bad_segments(self, bad_segments):
        
        # if not isinstance(bad_segments, list):
        #     return False
        # for seg in bad_segments:
        #     if not (isinstance(seg, tuple) or isinstance(seg, list)) or len(seg) != 2:
        #         return False
        #     start, end = seg
        #     if not (isinstance(start, (int, float)) and isinstance(end, (int, float))):
        #         return False
        #     if start >= end:
        #         return False
        if not isinstance(bad_segments, list):
            print("Bad segments data must be in list format.")
            return False
        for seg in bad_segments:
            if not (isinstance(seg, tuple) or isinstance(seg, list)) or len(seg) != 2:
                print(f"Invalid bad segment format: {seg}. Should be (start_time, end_time).")
                return False
            start, end = seg
            if not (isinstance(start, (int, float)) and isinstance(end, (int, float))):
                print(f"Bad segment times must be numeric: {seg}.")
                return False
            if start >= end:
                print(f"Start time must be less than end time for bad segment: {seg}.")
                return False
        return True

    def _compute_channel_distances(self, raw):
        
        channel_distances = {}
        for ch in raw.info['chs']:
            ch_name = ch['ch_name']
            loc = ch['loc']
            source_pos = np.array(loc[:3])
            detector_pos = np.array(loc[3:6])
            distance_m = np.linalg.norm(detector_pos - source_pos)
            distance_cm = distance_m * 100  
            channel_distances[ch_name] = distance_cm
        return channel_distances

    def _filter_channels_by_distance(self, raw, channel_distances, min_distance, max_distance):
        
        filtered_channels = []
        # for ch_name, distance in channel_distances.items():
        #     if min_distance is not None and distance < min_distance:
        #         continue
        #     if max_distance is not None and distance > max_distance:
        #         continue
        #     filtered_channels.append(ch_name)
        for ch_name, distance in channel_distances.items():
            if min_distance is not None and distance < min_distance:
                print(f"Channel {ch_name} distance {distance:.2f} cm is less than minimum distance {min_distance:.2f} cm, excluded.")
                continue
            if max_distance is not None and distance > max_distance:
                print(f"Channel {ch_name} distance {distance:.2f} cm is greater than maximum distance {max_distance:.2f} cm, excluded.")
                continue
            filtered_channels.append(ch_name)
        print(f"Number of channels retained after filtering: {len(filtered_channels)}")
        return filtered_channels

    def _get_channels_by_base_name(self, base_name):
        
        matched_channels = [ch for ch in self.raw_hameo.ch_names if ch.startswith(base_name)]
        return matched_channels

    def fnirs_preprocessing_pipeline(self, crop=None, min_distance=None, max_distance=None, exclude_bads=None, 
                             bad_segments=None, filter_bands=None, resample=None, 
                             detrend=False, detrend_order=1, tddr=True):
        try:
            raw_od_copy = self.raw_od.copy()

            # if crop is not None:
            #     data_start = raw_od_copy.times[0]
            #     data_end = raw_od_copy.times[-1]
                
            #     if crop[0] < data_start or crop[1] > data_end:
                
            #     if crop[0] >= crop[1]:
                
            #     time_mask = (raw_od_copy.times >= crop[0]) & (raw_od_copy.times <= crop[1])
            #     if not np.any(time_mask):
                
            #     try:
            #         self.start_time = crop[0]
            #         raw_od_copy = raw_od_copy.crop(tmin=crop[0], tmax=crop[1])
            #     except Exception as e:
            # else:
            #     self.start_time = 0
            if crop is not None:
                data_start = raw_od_copy.times[0]
                data_end = raw_od_copy.times[-1]
                
                if crop[0] < data_start or crop[1] > data_end:
                    raise ValueError(f"Crop time range ({crop[0]}, {crop[1]}) exceeds actual data range ({data_start}, {data_end})")
                
                if crop[0] >= crop[1]:
                    raise ValueError(f"Crop start time ({crop[0]}) must be less than end time ({crop[1]})")
                
                time_mask = (raw_od_copy.times >= crop[0]) & (raw_od_copy.times <= crop[1])
                if not np.any(time_mask):
                    raise ValueError("No data points remain after cropping")
                
                try:
                    self.start_time = crop[0]
                    raw_od_copy = raw_od_copy.crop(tmin=crop[0], tmax=crop[1])
                    print(f"Data cropped to time range: {crop}")
                except Exception as e:
                    raise ValueError(f"Data cropping failed: {str(e)}")
            else:
                self.start_time = 0
                print("Data was not cropped.")

            if min_distance is not None or max_distance is not None:
                picks = mne.pick_types(raw_od_copy.info, meg=False, fnirs=True)
                dists = mne.preprocessing.nirs.source_detector_distances(raw_od_copy.info, picks=picks)
                
                channels_to_keep = []
                for ch_name, dist in zip(raw_od_copy.ch_names, dists):
                    dist_cm = dist * 100  
                    if (min_distance is None or dist_cm >= min_distance) and (max_distance is None or dist_cm <= max_distance):
                        channels_to_keep.append(ch_name)
                
                if not channels_to_keep:
                    raise ValueError("No channels remain after distance range filtering. Please adjust the distance range.")
                
                raw_od_copy.pick_channels(channels_to_keep)
                print(f"Channels filtered by distance, retained: {len(channels_to_keep)}")

            if exclude_bads is not None:
                all_matched_bads = []
                for base_name in exclude_bads:
                    matched_bads = [ch for ch in raw_od_copy.ch_names if base_name in ch]
                    if matched_bads:
                        all_matched_bads.extend(matched_bads)
                    # else:
                        print(f"Channels matched for base name '{base_name}': {matched_bads}")
                    else:
                        print(f"No channels found matching base name '{base_name}'.")
                
                all_matched_bads = list(set(all_matched_bads))
                existing_bads = [ch for ch in all_matched_bads if ch in raw_od_copy.ch_names]
                
                if existing_bads:
                    raw_od_copy.drop_channels(existing_bads)
                # else:
                    print(f"Bad channels removed: {existing_bads}")
                    print(f"Remaining channels: {len(raw_od_copy.ch_names)}")
                else:
                    print("No bad channels found to remove.")

            # if detrend:
            #     if detrend_order not in [0, 1]:
            #     raw_od_copy._data = mne.filter.detrend(raw_od_copy._data, order=detrend_order)
            # else:
            if detrend:
                if detrend_order not in [0, 1]:
                    raise ValueError("Detrend order must be 0 or 1")
                raw_od_copy._data = mne.filter.detrend(raw_od_copy._data, order=detrend_order)
                print(f"Detrending applied using {detrend_order} order polynomial fit.")
            else:
                print("Detrending skipped.")

            if tddr:
                raw_od_copy = temporal_derivative_distribution_repair(raw_od_copy)
            # else:
                print("Head motion correction (TDDR) applied.")
            else:
                print("Head motion correction skipped.")

            if bad_segments is not None:
                valid_segments = self.is_valid_bad_segments(bad_segments)
                if valid_segments:
                    self.bad_segments = bad_segments
                    bad_annot = Annotations(
                        onset=[seg[0] - self.start_time for seg in self.bad_segments],
                        duration=[seg[1] - seg[0] for seg in self.bad_segments],
                        description=['BAD'] * len(self.bad_segments),
                        orig_time=raw_od_copy.info['meas_date']
                    )
                    existing_annot = raw_od_copy.annotations
                    merged_annot = existing_annot + bad_annot
                    raw_od_copy.set_annotations(merged_annot)
                    print(f"Bad segments marked: {self.bad_segments}")
                else:
                    print("Invalid Bad Segments")
                    

            raw_haemo = beer_lambert_law(raw_od_copy, ppf=self.calculate_dpf_duncan(self.age))

            hbo_data = raw_haemo.get_data(picks='hbo')
            hbr_data = raw_haemo.get_data(picks='hbr')
            hbt_data = hbo_data + hbr_data

            new_ch_names = []
            for ch_name in raw_haemo.ch_names:
                if 'hbo' in ch_name.lower():
                    new_ch_names.append(ch_name.replace('hbo', 'HbO').replace('HBO', 'HbO'))
                elif 'hbr' in ch_name.lower():
                    new_ch_names.append(ch_name.replace('hbr', 'HbR').replace('HBR', 'HbR'))
                else:
                    new_ch_names.append(ch_name)

            raw_haemo.rename_channels(dict(zip(raw_haemo.ch_names, new_ch_names)))

            hbt_info = mne.create_info(
                ch_names=[ch.replace('HbO', 'HbT') for ch in raw_haemo.ch_names if 'HbO' in ch],
                sfreq=raw_haemo.info['sfreq'],
                ch_types='hbo'
            )

            raw_hbt = mne.io.RawArray(hbt_data, hbt_info)
            raw_haemo.add_channels([raw_hbt], force_update_info=True)

            raw_haemo = self.reorder_fnirs_data(raw_haemo)

            raw_haemo.apply_function(lambda x: x * 1e6, picks=['hbo', 'hbr'])

            if filter_bands is not None:
                from scipy.signal import butter, filtfilt as _filtfilt
                sfreq = raw_haemo.info['sfreq']
                b, a = butter(3, [filter_bands[0], filter_bands[1]], btype='bandpass', fs=sfreq)
                for idx in range(raw_haemo._data.shape[0]):
                    raw_haemo._data[idx] = _filtfilt(b, a, raw_haemo._data[idx])
                print(f"Bandpass Filter Already Applied: {filter_bands}")

            if resample is not None:
                raw_haemo = raw_haemo.resample(sfreq=resample)
                print(f"Already Resampled To {resample} Hz。")

            self.processed_data = raw_haemo

            self.update_attributes()

            if hasattr(self, 'parent') and self.parent is not None:
                self.parent.update_preprocess_data()
                
            self.save_to_pickle()
            print("Preprocessing Pipeline Done and Exported")
            self.export_to_csv(crop=crop, min_distance=min_distance, max_distance=max_distance,
                            exclude_bads=exclude_bads, bad_segments=bad_segments,
                            filter_bands=filter_bands, resample=resample,
                            detrend_order=detrend_order, tddr=tddr)

        except Exception as e:
            logging.error(f"Error in Preprocessing: {str(e)}", exc_info=True)
            print(f"Error in Preprocessing: {str(e)}")
            raise

    def export_to_csv(self, crop=None, min_distance=None, max_distance=None, exclude_bads=None, 
                  bad_segments=None, filter_bands=None, resample=None, detrend_order=None, tddr=None,
                  export_channels=True, export_events=True, export_preprocessing=True):
        
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            
            base_filename = self.output_path + "\\"
            output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSPreprocessing")
            os.makedirs(output_folder, exist_ok=True)

            if export_channels and hasattr(self, 'processed_data') and self.processed_data is not None:
                try:
                    processed_data = self.processed_data.get_data()
                    processed_times = self.processed_data.times
                    
                    data_dict = {'Time (s)': processed_times}
                    
                    for i, channel in enumerate(self.processed_data.ch_names):
                        data_dict[f"{channel} (μmol/L)"] = processed_data[i, :].tolist()

                    df_data = pd.DataFrame(data_dict)
                    
                    channel_data_path = os.path.join(output_folder, f"{timestamp}_preprocessed.csv")
                    df_data.to_csv(channel_data_path, index=False, encoding='utf-8-sig')
                    print(f"Channels Data Exported To {channel_data_path}")
                    
                except Exception as e:
                    print(f"Error in Exporting Channels Data: {str(e)}")
                    logging.error(f"Error in Exporting Channels Data: {str(e)}", exc_info=True)

            if export_events and hasattr(self, 'processed_data') and self.processed_data is not None:
                try:
                    annotations = self.processed_data.annotations
                    if annotations is not None and len(annotations) > 0:
                        # df_events = pd.DataFrame({
                        # })
                        df_events = pd.DataFrame({
                            'Description': annotations.description,
                            'Start Time (s)': annotations.onset,
                            'Furation (s)': annotations.duration
                        })
                        events_data_path = os.path.join(output_folder, f"{timestamp}_eventData.csv")
                        df_events.to_csv(events_data_path, index=False, encoding='utf-8-sig')
                        print(f"Event Data Exported To {events_data_path}")
                    else:
                        print("No Event")
                except Exception as e:
                    print(f"Error in Export Event Data: {str(e)}")
                    logging.error(f"Error in Exporting Event Data: {str(e)}", exc_info=True)

            if export_preprocessing:
                try:
                    # preprocessing_params = {
                    # }
                    preprocessing_params = {
                        'Time Cropping': str(crop),
                        'Minimum Distance (cm)': str(min_distance),
                        'Maximum Distance (cm)': str(max_distance),
                        'Exclude Bad Channels': str(exclude_bads),
                        'Remove Bad Segments': str(bad_segments),
                        'Detrend': str(detrend_order),
                        'Motion Correction (TDDR)': str(tddr),
                        'Bandpass Filter': str(filter_bands),
                        'Resample': str(resample)
                    }
                    df_params = pd.DataFrame(list(preprocessing_params.items()), columns=['Parameter', 'Value'])
                    params_data_path = os.path.join(output_folder, f"{timestamp}_prepocessingParameter.csv")
                    df_params.to_csv(params_data_path, index=False, encoding='utf-8-sig')
                    print(f"Preprocessing Parameter Exported To {params_data_path}")
                except Exception as e:
                    print(f"Error in Exporting Preprocessing Parameter: {str(e)}")
                    logging.error(f"Error in Exporting Preprocessing Parameter: {str(e)}", exc_info=True)

            print(f"All Choosed Data Exported To {output_folder}")

        except Exception as e:
            error_msg = f"Error in Exporting: {str(e)}"
            print(error_msg)
            logging.error(error_msg, exc_info=True)
            raise
        
    def run_glm_analysis(self, hrf_model='spm'):
        
        single_haemo = self.processed_data.copy()
        single_haemo.apply_function(lambda x: x / 1e6, picks=['hbo','hbr'])
        design_matrix = make_first_level_design_matrix(
            single_haemo, 
            hrf_model=hrf_model, 
            drift_model=None, 
            stim_dur=single_haemo.annotations.duration
        )

        fig, ax1 = plt.subplots(figsize=(10, 6), constrained_layout=True)
        plot_design_matrix(design_matrix, ax=ax1)
        ax1.set_title("Design Matrix")

        glm_est = run_glm(single_haemo, design_matrix)

        column = ['Channel'] + list(glm_est.design)
        column[-1] = 'Constant Term'  

        list_all_beta = []  
        indicators = ['hbo', 'hbr', 'hbt']

        for indicator in indicators:
            for channel in glm_est.ch_names:
                if indicator in channel.lower():
                    list_channel_beta = [channel]
                    for beta in glm_est.data[channel].theta:
                        list_channel_beta.append(float(beta))
                    list_all_beta.append(list_channel_beta)

        BetaFrame = pd.DataFrame(columns=column, data=list_all_beta)

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSFeature")
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_GLMAnalysis.csv")
        figure_file = os.path.join(output_folder, f"{timestamp}_GLMAnalysis.png")

        BetaFrame.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"GLM Saved To {output_file}")

        fig.savefig(figure_file, dpi=300, bbox_inches='tight')
        print(f"GLM Figure Saved To {figure_file}")

        return fig
    
    def get_predict_data(self, event_name):
        events, event_dict = mne.events_from_annotations(self.processed_data)

        if event_name not in event_dict:
            raise ValueError(f"Event '{event_name}' Can't Find in Data")
        
        tmin, tmax = self.get_event_window(event_name)
        baseline = self.get_event_baseline(event_name)
        epochs = mne.Epochs(self.processed_data, events, event_id=event_dict, tmin=tmin, tmax=tmax,
                            proj=True, baseline=(baseline, 0), preload=True, verbose=False)

        epochs_event = epochs[event_name]
        channel_names = epochs.ch_names
        for channel in channel_names:
            if channel not in epochs.ch_names:
                raise ValueError(f"Channel '{channel}' Can't Find in Data")
        event_data = epochs_event.get_data()
        return event_data

    def predict_to_csv(self, label, event):
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRS_predict")
        os.makedirs(output_folder, exist_ok=True)

        event_predict = pd.DataFrame({
            'Event': event,
            'Predict Label': label
        },index=[0])
        event_predict_data_path = os.path.join(output_folder, f"{event}_predict.csv")
        event_predict.to_csv(event_predict_data_path, index=False, encoding='utf-8-sig')
        print(f"Event Predict Data Exported To {event_predict_data_path}")

    def extract_features(self, event_name, channel_names=None, features=None, folder=''):
        
        feature_map = {
            'Mean': 'mean',
            'Peak': 'peak',
            'Minimum': 'min',
            'AUC': 'auc',
            'Peak Latency': 'latency'
        }
        feature_units = {
            'Mean': 'μmol/L',
            'Peak': 'μmol/L',
            'Minimum': 'μmol/L',
            'AUC': 'μmol·s/L',
            'Peak Latency': 's'
        }
        inverse_feature_map = {v: k for k, v in feature_map.items()}

        if features:
            features = [feature_map.get(f, f) for f in features]

        events, event_dict = mne.events_from_annotations(self.processed_data)

        if event_name not in event_dict:
            raise ValueError(f"Event '{event_name}' Can't Find in Data")
        
        tmin, tmax = self.get_event_window(event_name)
        baseline = self.get_event_baseline(event_name)
        epochs = mne.Epochs(self.processed_data, events, event_id=event_dict, tmin=tmin, tmax=tmax,
                            proj=True, baseline=(baseline, 0), preload=True, verbose=False)

        epochs_event = epochs[event_name]

        if channel_names is None:
            channel_names = epochs.ch_names

        available_channels = [ch for ch in channel_names if ch in epochs.ch_names]
        if len(available_channels) < len(channel_names):
            print(f"Warning: The following channels were not found in the data and will be skipped: {set(channel_names) - set(available_channels)}")

        if not available_channels:
            raise ValueError("No available channels for feature extraction.")

        event_average = epochs_event.average(picks=available_channels)

        event_data = event_average.get_data()

        def extract_metrics(data, times, baseline_end=0):
            baseline_idx = np.where(times <= baseline_end)[0][-1]
            metrics = {}
            
            if features is None or 'mean' in features:
                metrics['Mean'] = np.mean(data[:, baseline_idx:], axis=1)
            if features is None or 'peak' in features:
                metrics['Peak'] = np.max(data[:, baseline_idx:], axis=1)
            if features is None or 'min' in features:
                metrics['Minimum'] = np.min(data[:, baseline_idx:], axis=1)
            if features is None or 'auc' in features:
                metrics['AUC'] = np.array([integrate.simps(channel[baseline_idx:], times[baseline_idx:]) for channel in data])
            if features is None or 'latency' in features:
                metrics['Peak Latency'] = times[baseline_idx:][np.argmax(data[:, baseline_idx:], axis=1)]
            return metrics
            # if features is None or 'mean' in features:
            # if features is None or 'peak' in features:
            # if features is None or 'min' in features:
            # if features is None or 'auc' in features:
            # if features is None or 'latency' in features:
            # return metrics

        metrics = extract_metrics(event_data, event_average.times)

        results = []
        for i, channel in enumerate(available_channels):
            # result = {
            # }
            result = {
                'Event': event_name,
                'Channels': channel
            }
            for feature, values in metrics.items():
                result[f"{feature} ({feature_units[feature]})"] = values[i]
            results.append(result)

        df_results = pd.DataFrame(results)

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSFeature", folder)
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_features.csv")

        df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Results Saved To {output_file}")

        return df_results
    
    def plot_single_channel_response(self, channel_base, hemoglobin_types=None):
        
        single_haemo = self.processed_data.copy()
        single_haemo.apply_function(lambda x: x / 1e6, picks=['hbo','hbr'])

        if hemoglobin_types is None:
            hemoglobin_types = ['HbO', 'HbR', 'HbT']

        picks = []
        for hb in hemoglobin_types:
            pattern = re.compile(f"{channel_base} {hb}", re.IGNORECASE)
            picks.extend([i for i, ch in enumerate(single_haemo.ch_names) if pattern.search(ch)])

        if not picks:
            raise ValueError(f"No channels found matching '{channel_base}' for the specified hemoglobin types: {hemoglobin_types}")

        data = single_haemo.get_data(picks=picks)
        times = single_haemo.times

        colors = {'HbO': '#FF5733', 'HbR': '#3498DB', 'HbT': '#2ECC71'}
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for i, pick in enumerate(picks):
            channel_name = single_haemo.ch_names[pick]
            hb_type = next(hb for hb in hemoglobin_types if hb in channel_name)
            ax.plot(times, data[i], label=channel_name, color=colors[hb_type], linewidth=2)

        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel('Amplitude (μmol/L)', fontsize=12)
        ax.set_title(f"Response for channel: {channel_base}", fontsize=16)
        ax.legend(fontsize=10, loc='upper right')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        ax.yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=True))
        ax.yaxis.offsetText.set_visible(False)

        plt.tight_layout()

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSVisualization")
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_{channel_base}_{'_'.join(hemoglobin_types)}.png")

        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Single-channel response plot saved to {output_file}")

        return fig

    def plot_event_data(self, event_name, hb_types=['HbO', 'HbR', 'HbT']):
        
        single_haemo = self.processed_data.copy()
        single_haemo.apply_function(lambda x: x / 1e6, picks=['hbo','hbr'])

        events, event_dict = mne.events_from_annotations(single_haemo)

        if event_name not in event_dict:
            raise ValueError(f"Event '{event_name}' not found in the data.")

        tmin, tmax = self.get_event_window(event_name)
        baseline = self.get_event_baseline(event_name)

        sfreq = single_haemo.info['sfreq']
        if (tmax - tmin) * sfreq < 2:
            raise ValueError("Time window is too small. Increase the time range.")
        
        epochs = mne.Epochs(single_haemo, events, event_id=event_dict, tmin=tmin, tmax=tmax,
                            proj=True, baseline=(baseline, 0), preload=True, verbose=False)

        if len(epochs.times) < 2:
            raise ValueError("Not enough time points in the epoch. Increase the time range.")

        evoked_dict = {}
        color_dict = {}
        for hb_type in hb_types:
            if hb_type not in ['HbO', 'HbR', 'HbT']:
                raise ValueError(f"Invalid hb_type: {hb_type}. Choose from 'HbO', 'HbR', or 'HbT'.")
            picks = [ch for ch in epochs.ch_names if hb_type in ch]
            if picks:
                evoked = epochs[event_name].average(picks=picks)
                evoked.rename_channels(lambda x: x[:-4])  # Remove the hb_type suffix from channel names
                evoked_dict[f"{event_name}/{hb_type}"] = evoked
                color_dict[hb_type] = {"HbO": "r", "HbR": "b", "HbT": "g"}[hb_type]

        if not evoked_dict:
            raise ValueError("No data to plot. Check your hb_types selection.")

        styles_dict = {event_name: dict(linestyle="solid")}

        fig, ax = plt.subplots(figsize=(12, 6))
        mne.viz.plot_compare_evokeds(
            evoked_dict, combine="mean", ci=0.95, colors=color_dict, styles=styles_dict, axes=ax, show=False
        )

        ax.set_title(f"Event-Related Response: {event_name} ({', '.join(hb_types)})")
        fig.tight_layout()

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSVisualization")
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_{event_name}_{'_'.join(hb_types)}_Event-relatedResponse.png")

        fig.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Event-related response plot saved to {output_file}")

        return fig

    def plot_topography(self, event_name, hb_type='hbo',times=None):
        

        if times is None:
            times = 'peaks'
        single_haemo = self.processed_data.copy()
        single_haemo.apply_function(lambda x: x / 1e6, picks=['hbo','hbr'])
        events, event_dict = mne.events_from_annotations(single_haemo)

        if event_name not in event_dict:
            raise ValueError(f"Event '{event_name}' not found in the data.")

        tmin, tmax = self.get_event_window(event_name)

        baseline = self.get_event_baseline(event_name)
        epochs = mne.Epochs(single_haemo, events, event_id=event_dict, tmin=tmin, tmax=tmax,
                            proj=True, baseline=(baseline, 0), preload=True, verbose=False)

        if len(epochs.times) < 2:
            raise ValueError("Not enough time points in the epoch. Increase the time range.")

        topomap_args = dict(extrapolate="local")

        hbo_picks = [ch for ch in epochs.ch_names if 'HbO' in ch]
        hbr_picks = [ch for ch in epochs.ch_names if 'HbR' in ch]
        hbt_picks = [ch for ch in epochs.ch_names if 'HbT' in ch]

        if hb_type.lower() == 'hbo':
            fig = epochs[event_name].average(picks=hbo_picks).plot_joint(
                times=times, topomap_args=topomap_args, title="HbO Response")
        elif hb_type.lower() == 'hbr':
            fig = epochs[event_name].average(picks=hbr_picks).plot_joint(
                times=times, topomap_args=topomap_args, title="HbR Response")
        elif hb_type.lower() == 'hbt':
            hbt_data = epochs[event_name].average(picks=hbt_picks).data
            hbt_evoked = epochs[event_name].average(picks=hbo_picks).copy()  
            hbt_evoked.data = hbt_data
            hbt_evoked.comment = 'HbT'
            fig = hbt_evoked.plot_joint(
                times=times, topomap_args=topomap_args, title="HbT Response")
        else:
            raise ValueError("Invalid hb_type. Choose 'hbo', 'hbr', or 'hbt'.")

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSVisualization")
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_{event_name}_{hb_type.upper()}_topography.png")

        fig.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"{hb_type.upper()} topography plot saved to {output_file}")

        return fig

    def plot_topology_time_series(self, event_name, hb_type='hbo'):
        
        single_haemo = self.processed_data.copy()
        single_haemo.apply_function(lambda x: x / 1e6, picks=['hbo','hbr'])
        events, event_dict = mne.events_from_annotations(single_haemo)

        if event_name not in event_dict:
            raise ValueError(f"Event '{event_name}' not found in the data.")

        tmin, tmax = self.get_event_window(event_name)

        baseline = self.get_event_baseline(event_name)
        epochs = mne.Epochs(single_haemo, events, event_id=event_dict, tmin=tmin, tmax=tmax,
                            proj=True, baseline=(baseline, 0), preload=True, verbose=False)

        hb_type = hb_type.lower()
        if hb_type == 'hbo':
            picks = [ch for ch in epochs.ch_names if 'HbO' in ch]
            color = 'r'
            name = 'HbO'
        elif hb_type == 'hbr':
            picks = [ch for ch in epochs.ch_names if 'HbR' in ch]
            color = 'b'
            name = 'HbR'
        elif hb_type == 'hbt':
            picks = [ch for ch in epochs.ch_names if 'HbT' in ch]
            color = 'g'
            name = 'HbT'
        else:
            raise ValueError("Invalid hb_type. Choose 'hbo', 'hbr', or 'hbt'.")

        evoked = epochs[event_name].average(picks=picks)

        if hb_type == 'hbt':
            hbo_picks = [ch for ch in epochs.ch_names if 'HbO' in ch]
            hbt_evoked = epochs[event_name].average(picks=hbo_picks).copy()
            hbt_evoked.data = evoked.data
            hbt_evoked.comment = 'HbT'
            evoked = hbt_evoked

        fig, ax = plt.subplots(figsize=(12, 8))
        mne.viz.plot_evoked_topo(evoked, color=color, axes=ax, 
                                legend=False, show=False, 
                                title=f'{name} Response for {event_name}')
        plt.tight_layout()

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSVisualization")
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_{event_name}_{name}_topographicTimeCourse.png")

        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"{name} topographic time course plot saved to {output_file}")

        return fig

    def plot_event_heatmap(self, event_name, hb_type='hbo'):
        
        single_haemo = self.processed_data.copy()
        single_haemo.apply_function(lambda x: x / 1e6, picks=['hbo','hbr'])
        events, event_dict = mne.events_from_annotations(single_haemo)

        if event_name not in event_dict:
            raise ValueError(f"Event '{event_name}' not found in the data.")

        tmin, tmax = self.get_event_window(event_name)
        baseline = self.get_event_baseline(event_name)
        epochs = mne.Epochs(single_haemo, events, event_id=event_dict, tmin=tmin, tmax=tmax,
                            proj=True, baseline=(baseline, 0), preload=True, verbose=False)

        hb_type = hb_type.lower()
        if hb_type == 'hbo':
            picks = [ch for ch in epochs.ch_names if 'HbO' in ch]
            title = 'HbO Response'
        elif hb_type == 'hbr':
            picks = [ch for ch in epochs.ch_names if 'HbR' in ch]
            title = 'HbR Response'
        elif hb_type == 'hbt':
            picks = [ch for ch in epochs.ch_names if 'HbT' in ch]
            title = 'HbT Response'
        else:
            raise ValueError("Invalid hb_type. Choose 'hbo', 'hbr', or 'hbt'.")

        plt.figure()

        epochs[event_name].plot_image(picks=picks, combine='mean', vmin=-0.5, vmax=0.5, 
                                    title=f'{title} for {event_name}', show=False)
        
        fig = plt.gcf()
        
        fig.axes[-1].set_ylim(-0.5, 0.5)

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "fNIRSVisualization")
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_{event_name}_{hb_type.upper()}_heatmap.png")

        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"{hb_type.upper()} Heatmap Saved To {output_file}")

        return fig

    def get_start_time(self):
        
        return self.start_time