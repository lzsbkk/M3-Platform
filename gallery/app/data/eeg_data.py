import copy
from PyQt5.QtGui import QColor
import re
import numpy as np
import pandas as pd
from mne.annotations import Annotations
import mne
from mne.preprocessing.nirs import optical_density, beer_lambert_law, temporal_derivative_distribution_repair
import matplotlib.pyplot as plt
from mne.viz import plot_ica_components
from mne.preprocessing import ICA
from nilearn.plotting import plot_design_matrix
import openpyxl
from scipy import integrate, signal
import warnings
from scipy.spatial.distance import pdist, squareform
from ..common.monitor import PerformanceMonitor
import matplotlib
import random
import os
import time

import pickle

import logging
mne.set_log_level('WARNING')
logging.getLogger('mne').setLevel(logging.WARNING)

matplotlib.use('Agg')

class EEGData:
    def __init__(self, filename=None, custom_montage=None, output_path = None, db_info=None):
        self.processed_data = None
        self.raw_data = None
        self.data_type = 'eeg'

        self.processed_data_copy = None
        self.raw_data_copy = None
                
        self.default_event_window = (-1.0, 2.0)
        self.event_windows = {}
        self.default_event_baseline = None
        self.event_baseline = {}

        self.ica_components = 20
        self.ica_exclude = [1]

        self.bad_segments = []

        self.filename = filename
        self.events = []
        self.start_time = 0

        self.viewmode = 'processed'

        self.db_info = db_info
        self.has_eog = None

        self.output_path = output_path
        if filename:
            if filename.endswith('.pkl'):
                self.load_from_pickle(filename)
            else:
                self.initialize_eeg_data(filename, custom_montage)
        
        self.output_path = output_path

    def update_database(self, field, value):
        
        if not self.db_info:
            raise ValueError("db_info is not provided")

        project = self.db_info['project']
        subject_id = self.db_info['subject_id']
        project.update_subject_data(subject_id, 'eeg', field, value)

    def save_to_pickle(self):
        
        base_name = os.path.splitext(self.filename)[0]
        pickle_filename = f"{base_name}_preprocessed.pkl"
        with open(pickle_filename, 'wb') as f:
            pickle.dump(self, f)
        print(f"Data Already Saved To {pickle_filename}")

        relative_path = os.path.relpath(pickle_filename, start=self.db_info['project'].base_path)
        self.update_database('preprocessed', relative_path)

    def load_from_pickle(self, filename):
        
        with open(filename, 'rb') as f:
            loaded_data = pickle.load(f)
            self.__dict__.update(loaded_data.__dict__)
        print(f"Data Loaded from {filename}")

    def initialize_eeg_data(self, filename, custom_montage=None):
        
        try:
            if filename.endswith('.eeg') or filename.endswith('.set'):
                self.raw = mne.io.read_raw_eeglab(filename, preload=True)
            elif filename.endswith('.edf') or filename.endswith('.gdf'):
                self.raw = mne.io.read_raw_edf(filename, preload=True)
            elif filename.endswith('.vhdr'):
                self.raw = mne.io.read_raw_brainvision(filename, preload=True)
            elif filename.endswith('.cnt'):
                self.raw = mne.io.read_raw_cnt(filename, preload=True)
            elif filename.endswith('.raw'):
                self.raw = mne.io.read_raw_egi(filename, preload=True)
            elif filename.endswith('.data'):
                self.raw = mne.io.read_raw_nicolet(filename, preload=True)
            elif filename.endswith('.cdt'):
                self.raw = mne.io.read_raw_curry(filename, preload=True)
            elif filename.endswith('.sqd') or filename.endswith('.con'):
                self.raw = mne.io.read_raw_kit(filename, preload=True)
            elif filename.endswith('.ds'):
                self.raw = mne.io.read_raw_ctf(filename, preload=True)
            elif filename.endswith('.pxpl'):
                self.raw = mne.io.read_raw_persyst(filename, preload=True)
            else:
                raise ValueError('Unsupported file format: {}'.format(filename))
        
            if custom_montage:
                try:
                    montage = mne.channels.read_custom_montage(custom_montage)
                    new_chan_names = np.loadtxt(custom_montage, dtype=str, usecols=3)
                    old_chan_names = self.raw.info['ch_names']
                    
                    # if len(new_chan_names) != len(old_chan_names):
                    #     self._apply_standard_montage()
                    # else:
                    chan_names_dict = {old_chan_names[i]: new_chan_names[i] for i in range(len(old_chan_names))}
                    self.raw.rename_channels(chan_names_dict)
                    self.raw.set_montage(montage, on_missing='ignore')
                except Exception as e:
                    print(f"Error in Applying Montage File{str(e)}")
                    print("Please Use Standard 10-20 System")
                    self._apply_standard_montage()
            else:
                self._apply_standard_montage()

            self._check_and_set_eog_channels()

            self._initialize_processed_data()
        except Exception as e:
            print(f"Error in Initializing EEG Data: {str(e)}")
            raise

    def _check_and_set_eog_channels(self):
        
        eog_channels = [ch for ch in self.raw.ch_names if ch.upper().startswith('EOG') or ch in ['HEO', 'VEO']]
        if eog_channels:
            self.has_eog = True
            self.raw.set_channel_types({ch: 'eog' for ch in eog_channels})
            print(f"Find and Set EOG Channels: {', '.join(eog_channels)}")
        else:
            self.has_eog = False
            print("Can't Find EOG Channels in Data")

    def _handle_overlapping_electrodes(self, dig_ch_pos, threshold=1e-5, return_overlapping=False):
        
        positions = np.array(list(dig_ch_pos.values()))
        channels = list(dig_ch_pos.keys())

        distances = pdist(positions)
        distance_matrix = squareform(distances)

        overlapping_pairs = []
        for i in range(len(channels)):
            for j in range(i+1, len(channels)):
                if distance_matrix[i, j] < threshold:
                    overlapping_pairs.append((channels[i], channels[j]))

        for ch1, ch2 in overlapping_pairs:
            pos1, pos2 = np.array(dig_ch_pos[ch1]), np.array(dig_ch_pos[ch2])
            midpoint = (pos1 + pos2) / 2
            
            offset = np.random.rand(3) * 0.01 - 0.005  
            
            dig_ch_pos[ch1] = tuple(midpoint + offset)
            dig_ch_pos[ch2] = tuple(midpoint - offset)

        if return_overlapping:
            return dig_ch_pos, overlapping_pairs
        return dig_ch_pos

    def _apply_standard_montage(self):
        try:
            standard_montage = mne.channels.make_standard_montage("standard_1020")
            existing_channels = [ch for ch in self.raw.ch_names if ch in standard_montage.ch_names]
            
            if existing_channels:
                new_montage = mne.channels.make_standard_montage("standard_1020")
                new_montage_chs = [ch for ch in new_montage.ch_names if ch in existing_channels]
                
                new_dig_ch_pos = {ch: new_montage.get_positions()['ch_pos'][ch] for ch in new_montage_chs}
                
                new_dig_ch_pos, overlapping_pairs = self._handle_overlapping_electrodes(new_dig_ch_pos, return_overlapping=True)
                
                new_montage = mne.channels.make_dig_montage(ch_pos=new_dig_ch_pos, coord_frame='head')

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self.raw.set_montage(new_montage, match_case=False, on_missing='warn')
                
                print(f"Apply 10-20 System, Anf Find {len(existing_channels)} Channels.")
                
                overlapping = [pair for pair in overlapping_pairs if pair[0] in self.raw.ch_names and pair[1] in self.raw.ch_names]
        #         if overlapping:
        #             for pair in overlapping:
        #         else:
        #     else:
        # except Exception as e:
                if overlapping:
                    print("The following electrode pairs have been adjusted to avoid overlap:")
                    for pair in overlapping:
                        print(f"  - {pair[0]} and {pair[1]}")
                else:
                    print("No overlapping electrodes detected.")
            else:
                print("No channels matching the standard 10-20 system found. Skipping montage setup.")
        except Exception as e:
            print(f"Error applying standard 10-20 system: {str(e)}")
            print("Using original channel positions instead.")
    
    def _set_eog_channels(self):
        eog_channels = [ch for ch in self.raw.ch_names if ch.upper().startswith('EOG') or ch in ['HEO', 'VEO']]
        # if eog_channels:
        #     self.raw.set_channel_types({ch: 'eog' for ch in eog_channels})
        # else:
        if eog_channels:
            self.raw.set_channel_types({ch: 'eog' for ch in eog_channels})
            print(f"The following channels have been set to EOG type: {', '.join(eog_channels)}")
        else:
            print("No EOG channels found")

    def _initialize_processed_data(self):
        
        self.raw_data = self.raw.copy()
        self.processed_data = self.raw_data.copy()
        
        # try:
        #     if self.has_eog:
        #         self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg', 'eog'])
        #     else:
        #         self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg'])
        # except Exception as e:
        try:
            if self.has_eog:
                self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg', 'eog'])
                print("Initial amplification applied to EEG and EOG channels")
            else:
                self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg'])
                print("Initial amplification applied to EEG channels")
        except Exception as e:
            print(f"Error during initial data amplification: {str(e)}")
        
        self.processed_data_copy = self.processed_data.copy()
        self.raw_data_copy = self.processed_data.copy()

        self.read_events()
        self.update_attributes()

    def update_attributes(self):
        
        if self.viewmode == 'processed':
            self.data = self.processed_data.get_data()
        else:
            self.data = self.raw_data_copy.get_data()
            
        self.channel_names = self.processed_data.ch_names
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
            print(f"Warning: Baseline time not found for event '{event_name}'. Using default value of {self.default_event_baseline} seconds.")
            return self.default_event_baseline
        
    def set_default_event_window(self, tmin, tmax):
        
        self.default_event_window = (tmin, tmax)
        print(f"Default event time window updated: [{tmin}, {tmax}]")

    def set_event_window(self, event_name, tmin, tmax):
        
        self.event_windows[event_name] = (tmin, tmax)
        print(f"Time window updated for event '{event_name}': [{tmin}, {tmax}]")

    def get_event_window(self, event_name):
        
        if event_name in self.event_windows:
            return self.event_windows[event_name]
        else:
            matching_events = [event for event in self.events if event[3] == event_name]
            print(matching_events)
            if matching_events:
                durations = [event[1] - event[0] for event in matching_events]
                print(len(set(durations)))
                print(durations[0])
                if len(set(durations)) == 1 and durations[0] > 0:
                    tmax = durations[0]
                    tmin = self.default_event_window[0]
                    print(f"Warning: Time window not found for event '{event_name}'. Using default tmin of {tmin} and event duration of {tmax} as tmax.")
                    return (tmin, tmax)
            
            print(f"Warning: Time window not found for event '{event_name}', or inconsistent event duration, or duration is zero. Using default value {self.default_event_window}.")
            return self.default_event_window
    
    def set_ica_components(self, components):
        self.ica_components = components
        print(f"Number of ICA components updated: {components}")

    @classmethod
    def from_existing(cls, existing_data):
        new_instance = cls()
        
        new_instance.raw_data = existing_data.raw_data.copy() if existing_data.raw_data is not None else None
        new_instance.processed_data = existing_data.processed_data.copy() if existing_data.processed_data is not None else None
        new_instance.processed_data_copy = existing_data.processed_data_copy.copy() if existing_data.processed_data_copy is not None else None
        new_instance.data_type = existing_data.data_type
        new_instance.has_eog = existing_data.has_eog
        new_instance.default_event_window = existing_data.default_event_window
        new_instance.default_event_baseline = existing_data.default_event_baseline
        new_instance.event_windows = existing_data.event_windows.copy()
        new_instance.event_baseline = existing_data.event_baseline.copy()
        new_instance.filename = existing_data.filename
        new_instance.events = [event for event in existing_data.events]
        new_instance.start_time = existing_data.start_time
        new_instance.output_path = existing_data.output_path
        new_instance.db_info = existing_data.db_info.copy()
        new_instance.raw_data_copy = existing_data.raw_data_copy.copy()

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
        
        for data in [self.processed_data, self.raw_data]:
            if data.annotations is None or len(data.annotations) == 0:
                orig_time = data.info['meas_date']
                start = start_time_raw if data == self.raw_data else start_time_processed
                annotation = Annotations(onset=[start], duration=[duration], description=[description], orig_time=orig_time)
                data.set_annotations(annotation)
            else:
                start = start_time_raw if data == self.raw_data else start_time_processed
                data.annotations.append(onset=[start], duration=[duration], description=[description])
        self.save_to_pickle()
        self.export_to_csv(export_channels=False, export_events=True, export_preprocessing=False, export_ica=False)

    def delete_event(self, event):
        if event in self.events:
            self.events.remove(event)
            
            start_time, end_time, _, description = event
            start_time_raw = start_time
            start_time_processed = start_time - self.get_start_time()
            
            for data in [self.processed_data, self.raw_data]:
                if data.annotations is not None:
                    annotations = data.annotations
                    start = start_time_raw if data == self.raw_data else start_time_processed
                    mask = (annotations.onset != start) | (annotations.description != description)
                    data.set_annotations(annotations[mask])
            self.save_to_pickle()
            self.export_to_csv(export_channels=False, export_events=True, export_preprocessing=False, export_ica=False)
        else:
            print(f"Warning: Event {event} not found in the events list.")

    def clear_events(self):
        self.events.clear()
        
        self.processed_data.set_annotations(None)
        self.raw_data.set_annotations(None)
        self.save_to_pickle()
        self.export_to_csv(export_channels=False, export_events=True, export_preprocessing=False, export_ica=False)

    def get_events(self):
        return self.events
    
    def get_start_time(self):
        return self.start_time
    
    # @PerformanceMonitor()
    def eeg_preprocessing_pipeline(self, crop=None, bandpass=None, notch=None, 
                               bad_segments=None, interpolate_bads=None, 
                               reference=None, resample=None):
        
        try:
            self.processed_data = self.raw_data.copy()

            if crop is not None:
                self.start_time = crop[0]
                self.processed_data = self.processed_data.crop(tmin=crop[0], tmax=crop[1])
            else:
                self.start_time = 0

            if bandpass is not None:
                from scipy.signal import butter, filtfilt as _filtfilt
                sfreq = self.processed_data.info['sfreq']
                b, a = butter(3, [bandpass[0], bandpass[1]], btype='bandpass', fs=sfreq)
                self.processed_data.apply_function(lambda x: _filtfilt(b, a, x), picks='eeg')

            if notch is not None:
                from scipy.signal import iirnotch, filtfilt as _filtfilt
                sfreq = self.processed_data.info['sfreq']
                b_n, a_n = iirnotch(notch, Q=25, fs=sfreq)
                self.processed_data.apply_function(lambda x: _filtfilt(b_n, a_n, x), picks='eeg')

            if interpolate_bads is not None:
                self.processed_data.info['bads'] = interpolate_bads
                self.processed_data.interpolate_bads(reset_bads=True, origin='auto',verbose=False)

            if reference == "Mastoid":
                ch_names = self.processed_data.info['ch_names']
                if 'TP9' not in ch_names or 'TP10' not in ch_names:
                    return "No suitable mastoid electrodes found (TP9 and TP10)"
                self.processed_data.set_eeg_reference(ref_channels=['TP9', 'TP10'])
            elif reference == "Average":
                self.processed_data.set_eeg_reference(ref_channels='average')

            if resample is not None:
                self.processed_data.resample(resample)

            if bad_segments is not None:
                if self.is_valid_bad_segments(bad_segments):
                    self.bad_segments = bad_segments
                    
                    bad_annot = mne.Annotations(
                        onset=[seg[0] - self.start_time for seg in self.bad_segments],
                        duration=[seg[1] - seg[0] for seg in self.bad_segments],
                        description=['BAD_' for _ in self.bad_segments]
                    )
                    
                    existing_annot = self.processed_data.annotations
                    
                    merged_annot = existing_annot + bad_annot
                    
                    self.processed_data.set_annotations(merged_annot)
                else:
                    print("Invalid Bad Segments")
            else:
                self.bad_segments = []

            # try:
            #     if self.has_eog:
            #         self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg', 'eog'])
            #     else:
            #         self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg'])
            # except Exception as e:
            try:
                if self.has_eog:
                    self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg', 'eog'])
                    print("Amplification applied to EEG and EOG channels")
                else:
                    self.processed_data.apply_function(lambda x: x * 1e6, picks=['eeg'])
                    print("Amplification applied to EEG channels")
            except Exception as e:
                print(f"Error during data amplification: {str(e)}")

            self.processed_data_copy = self.processed_data.copy()

            self.update_attributes()

            self.export_to_csv(crop=crop, bandpass=bandpass, notch=notch, 
                            bad_segments=bad_segments, interpolate_bads=interpolate_bads, 
                            reference=reference, resample=reference,
                            export_channels=True, export_events=True, 
                            export_preprocessing=True, export_ica=False)
            self.save_to_pickle()

            return None  

        except Exception as e:
            self.bad_segments = []  
            return f"Error in Preprocessing: {str(e)}"
    
    def predict_to_csv(self, label, event):
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "EEG_predict")
        os.makedirs(output_folder, exist_ok=True)

        event_predict = pd.DataFrame({
            'Event': event,
            'Predict Label': label
        },index=[0])
        event_predict_data_path = os.path.join(output_folder, f"{event}_predict.csv")
        event_predict.to_csv(event_predict_data_path, index=False, encoding='utf-8-sig')
        print(f"Event Predict Data Exported To {event_predict_data_path}")

    def export_to_csv(self, crop=None, bandpass=None, notch=None, bad_segments=None, interpolate_bads=None, reference=None, resample=None,
                 export_channels=True, export_events=True, export_preprocessing=True, export_ica=True, ica=False):
        
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), "EEG_Preprocessing")
        os.makedirs(output_folder, exist_ok=True)

        if export_channels:
            data_dict = {'Time (s)': self.time}
            for channel in self.channel_names:
                channel_index = self.channel_names.index(channel)
                data_dict[f"{channel} (μV)"] = self.data[channel_index, :].tolist()
            
            df_data = pd.DataFrame(data_dict)
            if ica:
                channel_data_path = os.path.join(output_folder, f"{timestamp}_预处理数据_ICA.csv")
            else:
                channel_data_path = os.path.join(output_folder, f"{timestamp}_预处理数据.csv")
            df_data.to_csv(channel_data_path, index=False, encoding='utf-8-sig')
            print(f"Channel Data Already Exported To {channel_data_path}")

        if export_events:
            annotations = self.processed_data.annotations
            # df_events = pd.DataFrame({
            # })
            df_events = pd.DataFrame({
                'Description': annotations.description,
                'Start Time (s)': annotations.onset,
                'Duration (s)': annotations.duration
            })
            events_data_path = os.path.join(output_folder, f"EventData.csv")
            df_events.to_csv(events_data_path, index=False, encoding='utf-8-sig')
            print(f"Event Data Exported To {events_data_path}")

        if export_preprocessing:
            # preprocessing_params = {
            # }
            preprocessing_params = {
                'Time Crop': str(crop),
                'Bandpass Filter': str(bandpass),
                'Line Noise Filter': str(notch),
                'Bad Segments': str(bad_segments),
                'Interpolate Bad Channels': str(interpolate_bads),
                'Re-reference': str(reference),
                'Resample': str(resample)
            }
            df_params = pd.DataFrame(list(preprocessing_params.items()), columns=['Parameter', 'Value'])
            params_data_path = os.path.join(output_folder, f"PreprocessingParameters.csv")
            df_params.to_csv(params_data_path, index=False, encoding='utf-8-sig')
            print(f"Preprocessing Parameter Exported To {params_data_path}")

        if export_ica:
            # ica_params = {
            # }
            ica_params = {
                'ICA Exclusion Component': self.ica_exclude
            }
            df_ica = pd.DataFrame(ica_params)
            ica_data_path = os.path.join(output_folder, f"ICAParameter.csv")
            df_ica.to_csv(ica_data_path, index=False, encoding='utf-8-sig')
            print(f"ICA Parameter Exported To {ica_data_path}")

        print(f"All Choosed Parameters Exported To: {output_folder}")


    def eeg_ICA_pipeline(self, ica_components=None):
        
        try:
            data = self.processed_data_copy.copy()
            
            montage = data.get_montage()
            if montage:
                print("Adjusting")
                ch_pos = montage.get_positions()['ch_pos']
                
                new_ch_pos = self._adjust_overlapping_electrodes(ch_pos)
                
                new_montage = mne.channels.make_dig_montage(ch_pos=new_ch_pos, coord_frame='head')
                data.set_montage(new_montage)

            if ica_components is not None:
                ica = ICA(
                    n_components=self.ica_components, 
                    max_iter='auto',
                    random_state=97,
                    method='fastica',
                    fit_params=dict(tol=0.01)
                )
                
                ica.fit(data)
                
                self.ica_exclude = ica_components
                
                self.processed_data = ica.apply(self.processed_data_copy.copy())
                
                self.update_attributes()
                
                self.save_to_pickle()
                self.export_to_csv(
                    export_channels=True,
                    export_events=False,
                    export_preprocessing=False,
                    export_ica=True,
                    ica=True
                )

                return None

        except Exception as e:
            return f"Fail To ICA Analysis: {str(e)}"

    def _adjust_overlapping_electrodes(self, ch_pos, min_dist=0.01):
        
        new_ch_pos = ch_pos.copy()
        
        midline_electrodes = ['FPZ', 'FZ', 'FCZ', 'CZ', 'CPZ', 'PZ', 'POZ', 'OZ']
        
        left_electrodes = [ch for ch in ch_pos.keys() if ch.endswith('1') 
                        or ch.startswith('F') and ch.endswith('3')
                        or ch.startswith('F') and ch.endswith('5')
                        or ch.startswith('F') and ch.endswith('7')]
        
        right_electrodes = [ch for ch in ch_pos.keys() if ch.endswith('2') 
                        or ch.startswith('F') and ch.endswith('4')
                        or ch.startswith('F') and ch.endswith('6')
                        or ch.startswith('F') and ch.endswith('8')]

        for i, electrode in enumerate(midline_electrodes):
            if electrode in new_ch_pos:
                pos = list(new_ch_pos[electrode])
                pos[1] -= i * min_dist
                new_ch_pos[electrode] = tuple(pos)

        for i, electrode in enumerate(left_electrodes):
            if electrode in new_ch_pos:
                pos = list(new_ch_pos[electrode])
                pos[0] -= min_dist
                pos[0] += np.random.rand() * min_dist * 0.5
                pos[1] += np.random.rand() * min_dist * 0.5
                new_ch_pos[electrode] = tuple(pos)

        for i, electrode in enumerate(right_electrodes):
            if electrode in new_ch_pos:
                pos = list(new_ch_pos[electrode])
                pos[0] += min_dist
                pos[0] -= np.random.rand() * min_dist * 0.5
                pos[1] += np.random.rand() * min_dist * 0.5
                new_ch_pos[electrode] = tuple(pos)

        return new_ch_pos
        
    def is_valid_bad_segments(self, bad_segments):
        
        if not isinstance(bad_segments, list):
            return False
        
        for segment in bad_segments:
            if not isinstance(segment, tuple) or len(segment) != 2:
                return False
            start, end = segment
            if not (isinstance(start, (int, float)) and isinstance(end, (int, float))):
                return False
            if start >= end:
                return False
            if start < 0 or end > self.raw_data.times[-1]:
                return False
        
        return True

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

    def extract_features(self, event_name, channel_names=None, features=None, frequency_bands=None, folder = ''):
        

        if channel_names is None:
            channel_names = self.channel_names

        all_features = ['Total Amplitude', 'Mean Amplitude', 'Amplitude Variance', 'Max Positive Peak', 'Max Negative Peak', 
                        'Latency Of Max Positive Peak', 'Latency Of Max Negative Peak', 'Total Energy', 'Peak Energy', 'Power Spectral Density']
        if features is None:
            features = all_features

        if frequency_bands is None:
            frequency_bands = {
                'delta': (0.5, 4),
                'theta': (4, 8),
                'alpha': (8, 13),
                'beta': (13, 30),
                'gamma': (30, 100)
            }

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

        for channel in channel_names:
            if channel not in epochs.ch_names:
                raise ValueError(f"Channel '{channel}' Can't Find in Data")


        
        # feature_units = {
        # }
        feature_units = {'Total Amplitude': 'μV',
                         'Mean Amplitude': 'μV',
                         'Amplitude Variance': 'μV²',
                         'Max Positive Peak': 'μV',
                         'Max Negative Peak': 'μV', 
                        'Latency Of Max Positive Peak': 's',
                        'Latency Of Max Negative Peak': 's',
                        'Total Energy': 'dB',
                        'Peak Energy': 'dB',
                        'Power Spectral Density': 'dB/Hz'
        }

        event_average = epochs_event.average(picks=channel_names)

        event_data = event_average.get_data()
        times = event_average.times

        def extract_metrics(data, times):
            baseline_idx = np.where(times <= 0)[0][-1] if 0 in times else 0
            metrics = {}
            
            if 'Total Amplitude' in features:
                metrics['Total Amplitude'] = np.max(data[:, baseline_idx:], axis=1) - np.min(data[:, baseline_idx:], axis=1)

            if 'Mean Amplitude' in features:
                metrics['Mean Amplitude'] = np.mean(data[:, baseline_idx:], axis=1)
            
            if 'Amplitude Variance' in features:
                metrics['Amplitude Variance'] = np.var(data[:, baseline_idx:], axis=1)
            
            if 'Max Positive Peak' in features:
                metrics['Max Positive Peak'] = np.max(data[:, baseline_idx:], axis=1)
            
            if 'Max Negative Peak' in features:
                metrics['Max Negative Peak'] = np.min(data[:, baseline_idx:], axis=1)


            
            
            
            
            
            if 'Latency Of Max Positive Peak' in features:
                metrics['Latency Of Max Positive Peak'] = times[baseline_idx:][np.argmax(data[:, baseline_idx:], axis=1)]
            
            if 'Latency Of Max Negative Peak' in features:
                metrics['Latency Of Max Negative Peak'] = times[baseline_idx:][np.argmin(data[:, baseline_idx:], axis=1)]
            
            #     freqs, psd = signal.welch(data, fs=1/(times[1]-times[0]), nperseg=len(times)//2)

            #                         for band, (low, high) in frequency_bands.items()}
                
            #                         for band, (low, high) in frequency_bands.items()}

            #                             for band, (low, high) in frequency_bands.items()}

            if any(f in features for f in ['Peak Energy', 'Power Spectral Density', 'Total Energy']):
                freqs, psd = signal.welch(data, fs=1/(times[1]-times[0]), nperseg=len(times)//2)

                if 'Total Energy' in features:
                    metrics['Total Energy'] = {band: 10 * np.log10(np.sum(psd[:, (freqs >= low) & (freqs <= high)] * np.diff(freqs)[0], axis=1))
                                    for band, (low, high) in frequency_bands.items()}
                
                if 'Peak Energy' in features:
                    metrics['Peak Energy'] = {band: 10 * np.log10(np.max(psd[:, (freqs >= low) & (freqs <= high)], axis=1))
                                    for band, (low, high) in frequency_bands.items()}

                if 'Power Spectral Density' in features:
                    metrics['Power Spectral Density'] = {band: 10 * np.log10(np.mean(psd[:, (freqs >= low) & (freqs <= high)], axis=1))
                                        for band, (low, high) in frequency_bands.items()}

            return metrics

        metrics = extract_metrics(event_data, times)

        results = []
        for i, channel in enumerate(channel_names):
            # result = {
            # }
            result = {
                'Event': event_name,
                'Channel': channel
            }
            for feature, values in metrics.items():
                if isinstance(values, dict):  
                    for band, band_values in values.items():
                        result[f"{feature}_{band} ({feature_units[feature]})"] = band_values[i]
                else:
                    result[f"{feature} ({feature_units[feature]})"] = values[i] if isinstance(values, np.ndarray) else values
            results.append(result)

        df_results = pd.DataFrame(results)

        self._save_results(df_results, "EEGFeature", folder)

        return df_results

    def _save_results(self, df_results, folder_name, folder = ''):
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        base_filename = self.output_path+"\\"
        
        output_folder = os.path.join(os.path.dirname(base_filename), folder_name, folder)
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, f"{timestamp}_Feature.csv")

        df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Result Saved To {output_file}")
    
    def plot_power_spectral_density(self, data_type='processed'):
        
        if data_type == 'raw':
            data = self.raw_data
        elif data_type == 'processed':
            data = self.processed_data.copy()
            # try:
            #     data.apply_function(lambda x: x / 1e6, picks=['eeg', 'eog'])
            # except ValueError as e:
            #     if "Invalid value for the 'picks' parameter" in str(e):
            #         try:
            #             data.apply_function(lambda x: x / 1e6, picks=['eeg'])
            #         except Exception as inner_e:
            #     else:
            #         raise
            # except Exception as e:
            try:
                # First attempt to process both EEG and EOG channels
                data.apply_function(lambda x: x / 1e6, picks=['eeg', 'eog'])
                print("Amplification applied to EEG and EOG channels")
            except ValueError as e:
                # If error occurs (likely due to missing EOG channels), process only EEG channels
                if "Invalid value for the 'picks' parameter" in str(e):
                    try:
                        data.apply_function(lambda x: x / 1e6, picks=['eeg'])
                        print("No EOG channels found. Amplification applied to EEG channels only.")
                    except Exception as inner_e:
                        print(f"Error processing EEG channels: {str(inner_e)}")
                else:
                    # Raise other types of ValueError
                    raise
            except Exception as e:
                print(f"Error processing data: {str(e)}")
        else:
            raise ValueError("data_type must be either 'raw' or 'processed'")

        fig = data.plot_psd(average=True, show=False)

        self._save_figure(fig, "Power Spectral Density Plot")

        return fig

    def plot_ica_topography(self, components='all'):
        
        data = self.processed_data.copy()
        try:
            if self.has_eog:
                data.apply_function(lambda x: x / 1e6, picks=['eeg', 'eog'])
            else:
                data.apply_function(lambda x: x / 1e6, picks=['eeg'])
        except Exception as e:
            print(f"Error in Processing: {str(e)}")

        try:
            ica = ICA(n_components=self.ica_components, max_iter='auto', random_state=97)
            ica.fit(data)
        except ValueError as e:
            print(f"ICA fitting failed: {str(e)}")
            print("Attempting PCA dimensionality reduction...")
            n_components = min(self.ica_components, len(data.ch_names) - 1)
            ica = ICA(n_components=n_components, max_iter='auto', random_state=97, 
                    method='fastica', fit_params=dict(tol=0.01))
            ica.fit(data)

        montage = data.get_montage()
        if montage:
            ch_pos = montage.get_positions()['ch_pos']
            new_ch_pos, _ = self._handle_overlapping_electrodes(ch_pos, return_overlapping=True)
            new_montage = mne.channels.make_dig_montage(ch_pos=new_ch_pos, coord_frame='head')
            data.set_montage(new_montage)

        try:
            if components == 'all':
                fig = ica.plot_components(picks=range(ica.n_components_), inst=data, show=False)
                fig.set_size_inches(12, 8)
            elif isinstance(components, int):
                figs = ica.plot_properties(data, picks=[components], show=False)
                for i, fig in enumerate(figs):
                    plt.figure(fig.number)
            else:
                raise ValueError("components must be 'all' or an integer")
        except Exception as e:
            print(f"Fail To Draw: {str(e)}")
            return None

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        output_folder = os.path.join(os.path.dirname(self.output_path), "EEGVisualization")
        os.makedirs(output_folder, exist_ok=True)

        if components == 'all':
            output_file = os.path.join(output_folder, f"{timestamp}_ica_all.png")
            fig.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"ICA topography map saved to {output_file}")
            return fig
        else:
            for i, fig in enumerate(figs):
                output_file = os.path.join(output_folder, 
                                        f"{timestamp}_ica_component_{components}_properties_{i+1}.png")
                fig.savefig(output_file, dpi=300, bbox_inches='tight')
                print(f"ICA component {components} property map {i+1} saved to {output_file}")
            return figs
    
    def plot_ica_overlay(self):
        
        raw_data = self.processed_data_copy.copy()
        try:
            if self.has_eog:
                raw_data.apply_function(lambda x: x / 1e6, picks=['eeg', 'eog'])
            else:
                raw_data.apply_function(lambda x: x / 1e6, picks=['eeg'])
        except Exception as e:
            print(f"Error in Processing: {str(e)}")

        ica = ICA(max_iter='auto', random_state=97)
        ica.fit(raw_data)

        exclude = self.ica_exclude

        fig = ica.plot_overlay(raw_data, exclude=exclude, show=False)

        plt.suptitle(f"Signals before (red) and after (black) cleaning (Excluded components: {exclude})", 
                    fontsize=16)

        for ax in fig.axes[1:3]:  
            ax.yaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
            ax.ticklabel_format(style='sci', scilimits=(-2,3), axis='y')
            ax.yaxis.offsetText.set_visible(False)

        self._save_figure(fig, "ICA Before-After Difference Plot")
        return fig
    
    def plot_segmented_data(self, event_name=None, n_epochs=1):
        
        if event_name:
            epochs = self._get_epochs(event_name)
        else:
            epochs = self._get_epochs()

        scaling_factor = np.percentile(np.abs(epochs.get_data()), 95)
        if scaling_factor == 0:
            scaling_factor = 1  

        scaling_factor = scaling_factor * 0.5

        n_channels = len(epochs.ch_names)
        
        fig_height = max(8, n_channels * 0.3)
        fig_width = 12  
        
        fig = plt.figure(figsize=(fig_width, fig_height))
        ax = fig.add_subplot(111)
        
        data = epochs.get_data()
        times = epochs.times
        
        spacing = 2.5 * scaling_factor  
        
        for epoch in range(min(n_epochs, len(data))):
            for ch_idx, ch_name in enumerate(epochs.ch_names):
                offset = -ch_idx * spacing
                
                signal = data[epoch, ch_idx, :] + offset
                ax.plot(times, signal, linewidth=0.8, label=ch_name)
                
                ax.text(times[0] - 0.05, offset, ch_name,  
                    horizontalalignment='right', verticalalignment='center',
                    fontsize=8)
        
        ax.set_xlabel('Time (s)')
        
        ax.set_yticks([])
        ax.set_ylabel('')
        
        ax.grid(True, linestyle=':', alpha=0.5)
        
        plt.title(f"Epoch {epoch + 1}/{len(data)}", pad=10)  
        
        ax.set_xlim(times[0] - 0.1, times[-1] + 0.1)  
        ax.set_ylim(-n_channels * spacing - spacing/2, spacing)  
        
        scale_bar_length = spacing
        scale_bar_position = (times[-1] + 0.05, -n_channels * spacing / 2)  
        
        ax.plot([scale_bar_position[0], scale_bar_position[0]], 
                [scale_bar_position[1], scale_bar_position[1] + scale_bar_length], 
                'k-', linewidth=1.5)
        
        plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)  
        
        self._save_figure(fig, "Segmented Data Waveform Plot", event_name)

        return fig


    def plot_psd_topomap(self, event_name=None):
        
        if event_name:
            epochs = self._get_epochs(event_name)
        else:
            epochs = self._get_epochs()

        bands = [(0.5, 4,'Delta'), (4, 8, 'Theta'), (8, 12, 'Alpha'), (12, 30, 'Beta'),(30, 100,'gamma')]
        fig = epochs.plot_psd_topomap(bands=bands, vlim='joint', show=False)        
        self._save_figure(fig, "Power Spectrum Topography", event_name)

        return fig

    def plot_evoked_topomaps(self, event_name=None, times=None, average=None):
        
        epochs = self._get_epochs(event_name)
        evoked = epochs.average()

        if average is not None:
            fig = evoked.plot_topomap(times=times, average=average, colorbar=True, show=False)
            plt.suptitle(f"Averaged Evoked Topomap - {event_name if event_name else 'All Data'} (Average: {average}s)")
        else:
            if times is None:
                times = np.linspace(0, 2, 5)
            fig = evoked.plot_topomap(times=times, colorbar=True, show=False)
            plt.suptitle(f"Evoked Topomaps - {event_name if event_name else 'All Data'}")

        self._save_figure(fig, "Time Sequence Topography", event_name)
        return fig
    
    def plot_evoked_joint(self, event_name=None, times=None):
        
        epochs = self._get_epochs(event_name)
        evoked = epochs.average()

        if times is None:
            times = 'peaks'
        fig = evoked.plot_joint(times=times,show=False)
        plt.suptitle(f"Evoked Joint Plot - {event_name if event_name else 'All Data'}")

        return fig

    
    def plot_evoked_image(self, event_name=None):
        
        epochs = self._get_epochs(event_name)
        evoked = epochs.average()

        fig = evoked.plot_image(show=False)
        plt.suptitle(f"Evoked Image Plot - {event_name if event_name else 'All Data'}")

        self._save_figure(fig, "Channel-wise Heatmap", event_name)
        return fig

    def plot_evoked_topo(self, event_name=None):
        
        epochs = self._get_epochs(event_name)
        evoked = epochs.average()

        fig = evoked.plot_topo(show=False)
        plt.suptitle(f"Evoked Topo Plot - {event_name if event_name else 'All Data'}")

        return fig

    def plot_all_ica_components(self):
        
        data = self.raw_data

        ica = ICA(max_iter='auto', random_state=97)
        ica.fit(data)

        fig_list = []

        for i in range(self.ica_components):
            fig, ax = plt.subplots(figsize=(2, 2))  
            ica.plot_components(picks=[i], axes=ax, show=False, colorbar=False)
            
            ax.set_title('')
            ax.set_xlabel('')
            ax.set_ylabel('')
            ax.set_xticks([])
            ax.set_yticks([])
            
            ax.axis('off')
            
            fig.tight_layout(pad=0)
            
            fig_list.append(fig)

        return fig_list

    def _get_epochs(self, event_name=None):
        
        raw_data = self.processed_data.copy()
        # try:
        #     if self.has_eog:
        #         raw_data.apply_function(lambda x: x / 1e6, picks=['eeg', 'eog'])
        #     else:
        #         raw_data.apply_function(lambda x: x / 1e6, picks=['eeg'])
        # except Exception as e:
        try:
            if self.has_eog:
                raw_data.apply_function(lambda x: x / 1e6, picks=['eeg', 'eog'])
                print("Data processing applied to EEG and EOG channels")
            else:
                raw_data.apply_function(lambda x: x / 1e6, picks=['eeg'])
                print("Data processing applied to EEG channels")
        except Exception as e:
            print(f"Error during data processing: {str(e)}")

        if event_name:
            events, event_id = mne.events_from_annotations(raw_data)
            if event_name not in event_id:
                raise ValueError(f"Event '{event_name}' Can't Find in Data")
            tmin, tmax = self.get_event_window(event_name)
            baseline = self.get_event_baseline(event_name)
            epochs = mne.Epochs(raw_data, events, event_id=event_id[event_name],
                            tmin=tmin, tmax=tmax, baseline=(baseline, 0),
                            preload=True)
        else:
            epochs = mne.make_fixed_length_epochs(raw_data, duration=self.default_event_window[1], 
                                                preload=True)
        return epochs
    
    def _save_figure(self, fig, plot_type, event_name=None):
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        base_filename = self.output_path+"\\"
        output_folder = os.path.join(os.path.dirname(base_filename), "EEGVisualization")
        os.makedirs(output_folder, exist_ok=True)

        event_str = f"_{event_name}" if event_name else ""
        output_file = os.path.join(output_folder, f"{timestamp}{event_str}_{plot_type}.png")

        fig.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"{plot_type.replace('_', ' ').title()} Saved To {output_file}")