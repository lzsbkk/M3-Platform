import pandas as pd
import numpy as np
import json
import gzip
import os
import cv2
import subprocess
from mne.io import read_raw_eyelink
from mne.preprocessing.eyetracking import read_eyelink_calibration
from scipy.signal import medfilt
from PyQt5.QtGui import QColor
import json
from shapely.geometry import Polygon, Point
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from kneed import KneeLocator
from scipy.spatial.distance import pdist
import matplotlib.pyplot as plt
import time
import random
import pickle

class AOI:
    def __init__(self, name, coordinates, start_time, end_time=None):
        self.name = name
        self.coordinates = coordinates
        self.start_time = start_time
        self.end_time = end_time
        self.polygon = self._create_polygon()

    def _create_polygon(self):
        return Polygon(self.coordinates)

    def contains_point(self, x, y, timestamp):
        if self.start_time <= timestamp and (self.end_time is None or timestamp <= self.end_time):
            return self.polygon.contains(Point(x, y))
        return False
    

class ETData:
    def __init__(self, file_path, video_path=None, output_path = None, db_info=None):
        self.file_path = file_path
        self.video_path = video_path
        self.data_type = 'et'
        
        self.raw_data = None
        self.processed_data = None
        self.events = []
        self.fixations = None
        self.saccades = None
        self.blinks = None
        self.fps = 30
        self.resolution = [1920, 1080]  
        self.video_duration = None
        self.FOV = 106  # Field of View in degrees (diagonal)
        self.h_fov = None  # Horizontal FOV, None to auto-calculate from FOV and resolution
        self.v_fov = None  # Vertical FOV, None to auto-calculate from FOV and resolution
        self.sample_rate = None

        self.output_path = output_path+'\\'
        self.pre_output_dir = os.path.join(self.output_path, 'ETpreprocessing')
        self.analysis_output_dir = os.path.join(self.output_path, 'ETfeature')
        self.vis_output_dir = os.path.join(self.output_path, 'ETvisualization')

        self.aois = []
        
        # if self.file_path.endswith('.edf'):
        #     self.file_path = self.convert_edf_to_asc(self.file_path)

        os.makedirs(self.pre_output_dir, exist_ok=True)
        os.makedirs(self.analysis_output_dir, exist_ok=True)
        os.makedirs(self.vis_output_dir, exist_ok=True)

        self.db_info = db_info
        
        self.output_path = output_path

        if not self.video_path:
            self.find_video_file()
        self.get_video_resolution()
        if file_path.endswith('.pkl'):
            self.load_from_pickle(file_path)
        else:
            self.load_data()
            self.parse_user_events()
            self.apply_i_vt_filter(save=False)

        self.output_path = output_path

    def convert_edf_to_asc(self, edf_path):
        
        try:
            converter_path = os.path.abspath(os.path.join(
                os.getcwd(),  
                'resource',
                'EDF2ASC',
                'edf2asc.exe'
            ))
            
            if not os.path.exists(converter_path):
                raise FileNotFoundError(f"Can't find EDF converter: {converter_path}")
            
            asc_path = os.path.splitext(edf_path)[0] + '.asc'
            
            print(f"Starting conversion of EDF file: {edf_path}")
            print(f"Using conversion tool: {converter_path}")
            print(f"Output ASC file: {asc_path}")
            
            if os.path.exists(asc_path):
                os.remove(asc_path)
            
            try:
                result = subprocess.run(
                    [converter_path, edf_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False  
                )
                
                if result.stdout:
                    print("Converter output:")
                    print(result.stdout)
                
                if result.stderr:
                    print("Warning/Error:")
                    print(result.stderr)
                
                if os.path.exists(asc_path):
                    if "Converted successfully" in result.stdout:
                        print("Success To Convert EDF")
                        return asc_path
                    else:
                        print("Warning: Output file found but no success confirmation message")
                        return asc_path
                else:
                    raise FileNotFoundError("Converted ASC file was not generated")
                    
            except subprocess.CalledProcessError as e:
                if os.path.exists(asc_path) and "Converted successfully" in e.output:
                    print("Note: File appears to have converted successfully despite non-zero return code")
                    return asc_path
                else:
                    raise IOError(f"Conversion command failed: {str(e)}\nCommand output: {e.output}")
                
        except Exception as e:
            print(f"Error during conversion: {str(e)}")
            raise IOError(f"EDF file conversion failed: {str(e)}")

    def calculate_data_integrity(self):
        
        try:
            total_samples = len(self.processed_data)
            if total_samples == 0:
                return 0.0

            valid_data = (
                ~pd.isnull(self.processed_data['GazePointX']) & 
                ~pd.isnull(self.processed_data['GazePointY']) & 
                ~pd.isnull(self.processed_data['Pupil'])
            )

            integrity = (valid_data.sum() / total_samples) * 100

            return integrity

        except Exception as e:
            print(f"Error calculating data integrity: {str(e)}")
            return 0.0
    
    def get_start_time(self):
        return 0
    
    def update_database(self, field, value):
        
        if not self.db_info:
            raise ValueError("db_info is not provided")

        project = self.db_info['project']
        subject_id = self.db_info['subject_id']
        project.update_subject_data(subject_id, 'et', field, value)

    def save_to_pickle(self):
        
        base_name = os.path.splitext(self.file_path)[0]
        pickle_filename = f"{base_name}_preprocessing.pkl"
        with open(pickle_filename, 'wb') as f:
            pickle.dump(self, f)
        print(f"Data Svaed To {pickle_filename}")

        relative_path = os.path.relpath(pickle_filename, start=self.db_info['project'].base_path)
        self.update_database('preprocessed', relative_path)

    def load_from_pickle(self, filename):
        
        with open(filename, 'rb') as f:
            loaded_data = pickle.load(f)
            self.__dict__.update(loaded_data.__dict__)
        print(f"Data Loaded From {filename}")

    def parse_user_events(self):
        
        event_colors = {}  
        if self.file_path.endswith('.gz') or self.file_path.endswith('.csv'):
            meta_folder = os.path.join(os.path.dirname(self.file_path), 'meta')
            if os.path.exists(meta_folder):
                for filename in os.listdir(meta_folder):
                    if filename.startswith('user-event') and filename.endswith('.json'):
                        file_path = os.path.join(meta_folder, filename)
                        with open(file_path, 'r') as f:
                            event_data = json.load(f)
                            timestamp = event_data.get('timestamp')
                            label = event_data.get('label')
                            if timestamp is not None and label is not None:
                                if label not in event_colors:
                                    color = QColor(*[random.randint(0, 255) for _ in range(3)])
                                    event_colors[label] = color
                                else:
                                    color = event_colors[label]

                                self.events.append((timestamp, timestamp, (color.red(), color.green(), color.blue()), label))
        
        self.events.sort(key=lambda x: x[0])

        print(f"Parsed {len(self.events)} user events.")

    
    def get_event_color(self, event_type):
        
        if event_type not in self.event_colors:
            color = QColor(*[random.randint(0, 255) for _ in range(3)])
            self.event_colors[event_type] = color
        return self.event_colors[event_type]

    def add_aoi(self, name, coordinates, start_time, end_time=None):
        if not isinstance(coordinates, (list, tuple)):
            raise ValueError("Coordinates must be a list or tuple")

        if all(isinstance(x, (int, float)) for x in coordinates):
            coordinates = [(coordinates[i], coordinates[i+1]) for i in range(0, len(coordinates), 2)]

        new_aoi = AOI(name, coordinates, start_time, end_time)
        self.aois.append(new_aoi)
        print(f"Added New AOI: {name}")
        self.save_to_pickle()

    def delete_aoi(self, aoi):
        if aoi in self.aois:
            self.aois.remove(aoi)
        self.save_to_pickle()

    def clear_aois(self):
        self.aois.clear()
        self.save_to_pickle()

    def update_aoi(self, old_aoi, new_aoi):
        if old_aoi in self.aois:
            index = self.aois.index(old_aoi)
            self.aois[index] = new_aoi
        self.save_to_pickle()

    def get_aois(self):
        return self.aois

    def calculate_aoi_metrics(self):
        aoi_metrics = {aoi.name: {'fixation_count': 0, 'total_fixation_duration': 0} for aoi in self.aois}

        for fixation in self.fixations.to_dict('records'):
            for aoi in self.aois:
                if aoi.contains_point(fixation['x'], fixation['y'], fixation['start']):
                    aoi_metrics[aoi.name]['fixation_count'] += 1
                    aoi_metrics[aoi.name]['total_fixation_duration'] += fixation['duration']

        return aoi_metrics
    
    def process_data(self):
        def convert_gaze(x, max_val):
            try:
                if pd.isna(x):
                    return pd.NA
                return int(float(x) * max_val)
            except:
                return pd.NA

        def calculate_pupil(row):
            if pd.notna(row['PupilLeft']) and pd.notna(row['PupilRight']):
                return (row['PupilLeft'] + row['PupilRight']) / 2
            elif pd.notna(row['PupilLeft']):
                return row['PupilLeft']
            elif pd.notna(row['PupilRight']):
                return row['PupilRight']
            else:
                return None

        self.processed_data = self.raw_data.copy()
        self.processed_data['Pupil'] = self.processed_data.apply(calculate_pupil, axis=1)
        keep_cols = ['Timestamp', 'GazePointX', 'GazePointY', 'Pupil', 'PupilLeft', 'PupilRight']
        # Preserve 3D gaze direction columns if available
        for col in ['GazeDirX', 'GazeDirY', 'GazeDirZ']:
            if col in self.processed_data.columns:
                keep_cols.append(col)
        self.processed_data = self.processed_data[keep_cols]

        self.calculate_sampling_rate()

    def calculate_sampling_rate(self):
        time_diff = self.processed_data['Timestamp'].diff()
        
        time_diff = time_diff[1:].astype(float) * 1000
        
        avg_interval = time_diff.mean()
        
        self.sample_rate = 1000 / avg_interval
        
        print(f"Calculated sampling rate: {self.sample_rate:.2f} Hz")

    def find_video_file(self):
        directory = os.path.dirname(self.file_path)
        if not os.path.exists(directory):
            print(f"Directory Doesn't Exist: {directory}")
            return

        for file in os.listdir(directory):
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                self.video_path = os.path.join(directory, file)
                print(f"Find Video File: {self.video_path}")
                return
        
        print("Can't Find Video File in The Same Directory")

    def get_video_resolution(self):
        if self.video_path and os.path.exists(self.video_path):
            try:
                cap = cv2.VideoCapture(self.video_path)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                duration = frame_count / fps if fps > 0 else 0
                
                cap.release()
                
                self.fps = fps
                self.resolution = [width, height]
                self.video_duration = duration
                
                print(f"Video resolution: {width}x{height}")
                print(f"Video frame rate: {fps:.2f} fps")
                print(f"Video duration: {duration:.2f} seconds")
            except Exception as e:
                print(f"Failed to retrieve video information: {e}")
                print("Using default resolution: 1920x1080")    
                self.resolution = [1920, 1080]
                self.fps = 30
                self.video_duration = 0
        else:
            print("No video file found, using default resolution: 1920x1080")
            self.resolution = [1920, 1080]
            self.fps = 30
            self.video_duration = 0
    
    
    def load_asc_data(self):
        """
        Load and process EyeLink .asc file using MNE.
        Automatically detects and uses available channels.
        Converts pupil data from EyeLink units to millimeters (divide by 1000).
        """
        try:
            print(f"Loading ASC file: {self.file_path}")
            raw = read_raw_eyelink(self.file_path)
            
            available_channels = raw.ch_names
            print(f"Available channels: {available_channels}")
            
            channel_patterns = {
                'gaze_x': ['xpos', 'gaze_x'],
                'gaze_y': ['ypos', 'gaze_y'],
                'pupil': ['pupil', 'diameter']
            }
            
            channel_mapping = {}
            for data_type, patterns in channel_patterns.items():
                for ch in available_channels:
                    ch_lower = ch.lower()
                    if any(pattern in ch_lower for pattern in patterns):
                        if '_left' in ch_lower:
                            channel_mapping[ch] = f'{data_type}_left'
                        elif '_right' in ch_lower:
                            channel_mapping[ch] = f'{data_type}_right'
                        else:
                            channel_mapping[ch] = data_type

            print(f"Channel mapping: {channel_mapping}")
            
            self.sample_rate = raw.info['sfreq']
            print(f"Sampling rate: {self.sample_rate} Hz")
            
            timestamps = np.arange(raw.n_times) / self.sample_rate
            
            data_dict = {
                'Timestamp': timestamps,
                'GazePointX': np.nan * np.ones_like(timestamps),
                'GazePointY': np.nan * np.ones_like(timestamps),
                'PupilLeft': np.nan * np.ones_like(timestamps),
                'PupilRight': np.nan * np.ones_like(timestamps)
            }
            
            for ch_name, mapped_name in channel_mapping.items():
                data = raw.get_data(ch_name)[0]
                
                if 'gaze_x' in mapped_name:
                    data = np.clip(data / self.resolution[0], 0, 1)
                    if mapped_name == 'gaze_x_left' or mapped_name == 'gaze_x':
                        data_dict['GazePointX'] = data
                    elif mapped_name == 'gaze_x_right' and np.all(np.isnan(data_dict['GazePointX'])):
                        data_dict['GazePointX'] = data
                        
                elif 'gaze_y' in mapped_name:
                    data = np.clip(data / self.resolution[1], 0, 1)
                    if mapped_name == 'gaze_y_left' or mapped_name == 'gaze_y':
                        data_dict['GazePointY'] = data
                    elif mapped_name == 'gaze_y_right' and np.all(np.isnan(data_dict['GazePointY'])):
                        data_dict['GazePointY'] = data
                        
                elif 'pupil' in mapped_name:
                    data = data / 1000.0  
                    if mapped_name == 'pupil_left':
                        data_dict['PupilLeft'] = data
                    elif mapped_name == 'pupil_right':
                        data_dict['PupilRight'] = data
                    elif mapped_name == 'pupil' and 'PupilLeft' not in data_dict:
                        data_dict['PupilLeft'] = data
                        data_dict['PupilRight'] = data
            
            self.raw_data = pd.DataFrame(data_dict)
            
            self.process_data()
            
            self.integrity = self.calculate_data_integrity()
            
            print(f"Successfully loaded ASC file")
            print(f"Data shape: {self.raw_data.shape}")
            print(f"Data integrity: {self.integrity:.2f}%")
            
        except Exception as e:
            print(f"Error details: {str(e)}")
            raise IOError(f"Error reading ASC file {self.file_path}: {str(e)}")

    def calculate_pupil(self, row):
        
        left_valid = pd.notna(row.get('PupilLeft', np.nan))
        right_valid = pd.notna(row.get('PupilRight', np.nan))
        
        if left_valid and right_valid:
            return (row['PupilLeft'] + row['PupilRight']) / 2
        elif left_valid:
            return row['PupilLeft']
        elif right_valid:
            return row['PupilRight']
        return np.nan
    
    def load_data(self):
        
        if self.file_path.endswith('.gz'):
            data = []
            try:
                with gzip.open(self.file_path, 'rb') as f:
                    for line in f:
                        try:
                            line = line.decode('utf-8').strip()
                            if line:
                                json_data = json.loads(line)
                                timestamp = json_data['timestamp']

                                if json_data['type'] == 'gaze' and 'data' in json_data:
                                    gaze_data = json_data['data']
                                    gaze2d = gaze_data.get('gaze2d', [None, None])
                                    pupil_left = gaze_data.get('eyeleft', {}).get('pupildiameter', None)
                                    pupil_right = gaze_data.get('eyeright', {}).get('pupildiameter', None)
                                    # Extract 3D gaze direction for precise angular velocity calculation
                                    dir_left = gaze_data.get('eyeleft', {}).get('gazedirection', None)
                                    dir_right = gaze_data.get('eyeright', {}).get('gazedirection', None)
                                else:
                                    gaze2d = [None, None]
                                    pupil_left = None
                                    pupil_right = None
                                    dir_left = None
                                    dir_right = None

                                # Average gaze direction (mean of both eyes)
                                gaze_dir = [None, None, None]
                                if dir_left and dir_right:
                                    gaze_dir = [(dir_left[j] + dir_right[j]) / 2 for j in range(3)]
                                elif dir_left:
                                    gaze_dir = dir_left
                                elif dir_right:
                                    gaze_dir = dir_right

                                data.append({
                                    'Timestamp': timestamp,
                                    'GazePointX': gaze2d[0],
                                    'GazePointY': gaze2d[1],
                                    'PupilLeft': pupil_left,
                                    'PupilRight': pupil_right,
                                    'GazeDirX': gaze_dir[0],
                                    'GazeDirY': gaze_dir[1],
                                    'GazeDirZ': gaze_dir[2],
                                })
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"Error in Processing: {e}")
                            continue
                
                if not data:
                    raise ValueError(f"Can't Find Valid Data in {self.file_path}")
                
                self.raw_data = pd.DataFrame(data)
                self.process_data()
                self.integrity = self.calculate_data_integrity()
                
                print(f"Successfully loaded {len(data)} data points from {self.file_path}")
                print(f"Data integrity: {self.integrity:.2f}%")
                
            except Exception as e:
                raise IOError(f"Error in Reading {self.file_path}: {str(e)}")
                
        elif self.file_path.endswith('.csv'):
            data = []
            try:
                with open(self.file_path, 'rb') as f:
                    for line in f:
                        try:
                            line = line.decode('utf-8').strip()
                            if line:
                                json_data = json.loads(line)
                                timestamp = json_data['timestamp']
                                
                                if json_data['type'] == 'gaze' and 'data' in json_data:
                                    gaze_data = json_data['data']
                                    gaze2d = gaze_data.get('gaze2d', [None, None])
                                    pupil_left = gaze_data.get('eyeleft', {}).get('pupildiameter', None)
                                    pupil_right = gaze_data.get('eyeright', {}).get('pupildiameter', None)
                                else:
                                    gaze2d = [None, None]
                                    pupil_left = None
                                    pupil_right = None
                                
                                data.append({
                                    'Timestamp': timestamp,
                                    'GazePointX': gaze2d[0],
                                    'GazePointY': gaze2d[1],
                                    'PupilLeft': pupil_left,
                                    'PupilRight': pupil_right
                                })
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"Error in Processing: {e}")
                            continue
                
                if not data:
                    raise ValueError(f"Can't Find Valid Data in {self.file_path}")
                
                self.raw_data = pd.DataFrame(data)
                self.process_data()
                self.integrity = self.calculate_data_integrity()
                
                print(f"Successfully loaded {len(data)} data points from {self.file_path}")
                print(f"Data integrity: {self.integrity:.2f}%")
                
            except Exception as e:
                raise IOError(f"Error in Reading {self.file_path}: {str(e)}")
                
        elif self.file_path.endswith('.asc'):
            self.load_asc_data()
            
        elif self.file_path.endswith('.edf'):
            print("EDF file detected, starting conversion...")
            try:
                asc_path = self.convert_edf_to_asc(self.file_path)
                original_path = self.file_path
                self.file_path = asc_path
                self.load_asc_data()
                self.file_path = original_path
            except Exception as e:
                raise IOError(f"Error in Processing EDF File: {str(e)}")
                
        else:
            raise ValueError("Unsupported file format. Supported formats: .gz, .csv, .asc, .edf")
        
    def calculate_gaze_angles(self):

        x = self.processed_data['GazePointX'].values
        y = self.processed_data['GazePointY'].values

        # Calculate actual horizontal/vertical FOV
        if self.h_fov is not None and self.v_fov is not None:
            hfov = self.h_fov
            vfov = self.v_fov
        else:
            # Derive from diagonal FOV and resolution
            w, h = self.resolution[0], self.resolution[1]
            diag = np.sqrt(w**2 + h**2)
            hfov = self.FOV * w / diag
            vfov = self.FOV * h / diag

        angle_x = x * hfov
        angle_y = y * vfov

        self.processed_data['GazeAngleX'] = angle_x
        self.processed_data['GazeAngleY'] = angle_y

    def get_video_path(self):
        
        return self.video_path

    def has_video(self):
        
        return self.video_path is not None
    
    def add_event(self, event):
        start_time, end_time, color, description = event
        if isinstance(color, QColor):
            color = (color.red(), color.green(), color.blue())
        elif isinstance(color, str):
            color = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        self.events.append((start_time, end_time, color, description))
        self.save_to_pickle()
        self.save_to_csv(export_gaze=False,
                export_events=True,
                export_preprocessing=False)

    def delete_event(self, event):
        if event in self.events:
            self.events.remove(event)
        self.save_to_pickle()
        self.save_to_csv(export_gaze=False,
                export_events=True,
                export_preprocessing=False)

    def edit_event(self, old_event, new_event):
        if old_event in self.events:
            index = self.events.index(old_event)
            self.events[index] = new_event
        else:
            raise ValueError("Old event not found")
        self.save_to_pickle()
        self.save_to_csv(export_gaze=False,
                export_events=True,
                export_preprocessing=False)

    def clear_events(self):
        self.events.clear()
        self.save_to_pickle()
        self.save_to_csv(export_gaze=False,
                export_events=True,
                export_preprocessing=False)


    def get_events(self):
        return self.events
    
    def apply_i_vt_filter(self, velocity_threshold=30, blink_threshold=75, blink_max_threshold=None,
                    interpolate=False, max_gap_length=75, denoise=False, 
                    denoise_method='median', window_size=3, 
                    use_time_window=False, velocity_window_length=20, 
                    merge_fixations=False, max_time_between_fixations=75, 
                    max_angle_between_fixations=0.5, 
                    discard_short_fixations=False, min_fixation_duration=60,
                    pupil_interpolate=False, pupil_max_gap=75,
                    pupil_filter=False, pupil_filter_method='median', pupil_window_size=3,
                    save=True):
        
        print("\nStarting I-VT filter application...")
        print(f"Initial data shape: {self.raw_data.shape}")
        
        self.process_data()

        print("\nStep 1: Calculating gaze angles from 2D data...")
        self.calculate_gaze_angles()

        if interpolate or pupil_interpolate:
            print("\nStep 2: Interpolating gaps...")
            if interpolate:
                print("Processing gaze data gaps...")
                self.interpolate_gaps(max_gap_length)
                # Recalculate gaze angles after interpolation
                self.calculate_gaze_angles()
            if pupil_interpolate:
                print("Processing pupil data gaps...")
                self.interpolate_pupil_data(pupil_max_gap)
        else:
            print("\nStep 2: Interpolation skipped.")

        if denoise or pupil_filter:
            print(f"\nStep 3: Applying noise reduction...")
            if denoise:
                print(f"Denoising gaze data using {denoise_method} method...")
                self.denoise_data(method=denoise_method, window_size=window_size)
                # Recalculate gaze angles after denoising
                self.calculate_gaze_angles()
            if pupil_filter:
                print(f"Filtering pupil data using {pupil_filter_method} method...")
                self.filter_pupil_data(method=pupil_filter_method, window_size=pupil_window_size)
        else:
            print("\nStep 3: Denoising skipped.")

        print(f"\nStep 4: Calculating velocities (window length: {velocity_window_length} ms)...")
        velocities = self.calculate_velocities(window_length=velocity_window_length)
        self.processed_data['Velocity'] = velocities

        print(f"\nStep 5: Classifying fixations and saccades (velocity threshold: {velocity_threshold} degrees/sec)...")
        fixations, saccades = self.classify_fixations_and_saccades(velocities, velocity_threshold)
        self._last_saccades = saccades  # Save saccade list for merge checking

        if merge_fixations:
            print(f"\nStep 6: Merging adjacent fixations...")
            fixations = self.merge_adjacent_fixations(fixations, max_time_between_fixations, max_angle_between_fixations)
        else:
            print("\nStep 6: Merging fixations skipped.")

        if discard_short_fixations:
            print(f"\nStep 7: Discarding short fixations (min duration: {min_fixation_duration} ms)...")
            fixations = self.discard_short_fixations(fixations, min_fixation_duration)
        else:
            print("\nStep 7: Discarding short fixations skipped.")

        if blink_threshold is not None:
            print(f"\nStep 8: Detecting blinks (min_threshold: {blink_threshold} ms, max_threshold: {blink_max_threshold} ms)...")
            blinks = self.detect_blinks(blink_threshold, blink_max_threshold)
        else:
            print("\nStep 8: Blink detection skipped.")
            blinks = []

        self.fixations = pd.DataFrame(fixations)
        self.saccades = pd.DataFrame(saccades)
        self.blinks = pd.DataFrame(blinks)

        
        if save:
            self.save_to_csv(
                export_gaze=True,
                export_events=True,
                export_preprocessing=True,
                pupil_interpolate=pupil_interpolate,
                pupil_max_gap=pupil_max_gap,
                pupil_filter=pupil_filter,
                pupil_filter_method=pupil_filter_method,
                pupil_window_size=pupil_window_size,
                velocity_threshold=velocity_threshold,
                blink_threshold=blink_threshold,
                blink_max_threshold=blink_max_threshold,
                interpolate=interpolate,
                max_gap_length=max_gap_length,
                denoise=denoise,
                denoise_method=denoise_method,
                window_size=window_size,
                velocity_window_length=velocity_window_length,
                merge_fixations=merge_fixations,
                max_time_between_fixations=max_time_between_fixations,
                max_angle_between_fixations=max_angle_between_fixations,
                discard_short_fixations=discard_short_fixations,
                min_fixation_duration=min_fixation_duration
            )
            self.save_to_pickle()

        print("\nI-VT filter application completed.")

    def interpolate_pupil_data(self, max_gap_length, min_gap_size=3):
        
        print(f"Starting pupil data interpolation. Max gap length: {max_gap_length} ms, Min gap size: {min_gap_size} samples")
        
        timestamps = self.processed_data['Timestamp'].values
        pupil_data = self.processed_data['Pupil'].values

        gaps = pd.isnull(pupil_data)
        
        if gaps[0]:
            print("Warning: Pupil data starts with a gap")
        if gaps[-1]:
            print("Warning: Pupil data ends with a gap")

        all_gaps = []
        current_gap_start = None
        for i, is_gap in enumerate(gaps):
            if is_gap and current_gap_start is None:
                current_gap_start = i
            elif not is_gap and current_gap_start is not None:
                gap_size = i - current_gap_start
                if gap_size >= min_gap_size:
                    all_gaps.append((current_gap_start, i))
                current_gap_start = None
        
        if current_gap_start is not None:
            gap_size = len(gaps) - current_gap_start
            if gap_size >= min_gap_size:
                all_gaps.append((current_gap_start, len(gaps)))

        print(f"Total number of pupil data gaps found: {len(all_gaps)}")

        interpolated_gaps = 0
        total_interpolated_points = 0

        for start, end in all_gaps:
            gap_duration = (timestamps[end-1] - timestamps[start]) * 1000  
            if gap_duration <= max_gap_length:
                if start > 0 and end < len(timestamps):
                    t_interp = timestamps[start:end]
                    pupil_interp = np.interp(t_interp, 
                                        [timestamps[start-1], timestamps[end]], 
                                        [pupil_data[start-1], pupil_data[end]])
                    
                    pupil_data[start:end] = pupil_interp
                    
                    interpolated_gaps += 1
                    total_interpolated_points += end - start
                    print(f"Interpolated pupil gap {interpolated_gaps}: Start: {start}, End: {end}, "
                        f"Duration: {gap_duration:.2f} ms, Points: {end-start}")
                else:
                    print(f"Skipped pupil gap interpolation due to invalid start/end indices. "
                        f"Start: {start}, End: {end}")
            else:
                print(f"Skipped pupil gap interpolation. Duration ({gap_duration:.2f} ms) "
                    f"exceeds max_gap_length")

        self.processed_data['Pupil'] = pupil_data

        print(f"Pupil interpolation complete. Interpolated {interpolated_gaps} gaps, "
            f"total {total_interpolated_points} points")

    def denoise_data(self, method='median', window_size=3):
        
        def apply_filter_with_nans(data, window_size, filter_func):
            
            result = np.copy(data)
            nan_mask = np.isnan(data)  
            
            valid_data = ~nan_mask
            if np.sum(valid_data) < window_size:
                return result  
                
            for i in range(len(data)):
                if nan_mask[i]:
                    continue  
                    
                start_idx = max(0, i - window_size // 2)
                end_idx = min(len(data), i + window_size // 2 + 1)
                window = data[start_idx:end_idx]
                
                valid_window = window[~np.isnan(window)]
                if len(valid_window) >= window_size // 2 + 1:
                    result[i] = filter_func(valid_window)
                
            return result

        try:
            x = self.processed_data['GazePointX'].values
            y = self.processed_data['GazePointY'].values

            if method == 'Moving Average':
                filter_func = np.mean
            elif method == 'Moving Median':
                filter_func = np.median
            else:
                raise ValueError("Invalid Filter, Please Use Moving Average or Moving Median")

            filtered_x = apply_filter_with_nans(x, window_size, filter_func)
            filtered_y = apply_filter_with_nans(y, window_size, filter_func)

            self.processed_data['GazePointX'] = filtered_x
            self.processed_data['GazePointY'] = filtered_y
            
            print(f"Completed {method} filtering:")
            print(f"  Window size: {window_size}")
            print(f"  Number of NaN values in X coordinates: {np.sum(np.isnan(filtered_x))}")
            print(f"  Number of NaN values in Y coordinates: {np.sum(np.isnan(filtered_y))}")

        except Exception as e:
            print(f"Error in Filtering: {str(e)}")
            raise

    def filter_pupil_data(self, method='median', window_size=3):
        
        def apply_filter_with_nans(data, window_size, filter_func):
            
            result = np.copy(data)
            nan_mask = np.isnan(data)  
            zero_mask = (data == 0)    
            invalid_mask = nan_mask | zero_mask  
            
            valid_data = ~invalid_mask
            if np.sum(valid_data) < window_size:
                return result
                
            for i in range(len(data)):
                if invalid_mask[i]:
                    continue
                    
                start_idx = max(0, i - window_size // 2)
                end_idx = min(len(data), i + window_size // 2 + 1)
                window = data[start_idx:end_idx]
                
                valid_window = window[~(np.isnan(window) | (window == 0))]
                if len(valid_window) >= window_size // 2 + 1:
                    result[i] = filter_func(valid_window)
                    
                    if result[i] < 2 or result[i] > 8:  
                        result[i] = data[i]  
                
            return result

        try:
            if 'Pupil' not in self.processed_data.columns:
                raise ValueError("No pupil data columns found in processed data")

            pupil_data = self.processed_data['Pupil'].values

            if method == 'Moving Average':
                filter_func = np.mean
            elif method == 'Moving Median':
                filter_func = np.median
            else:
                raise ValueError("Invalid Filter, Please Use Moving Average or Moving Median")

            filtered_pupil = apply_filter_with_nans(pupil_data, window_size, filter_func)

            self.processed_data['Pupil'] = filtered_pupil
            
            invalid_count = np.sum(np.isnan(filtered_pupil) | (filtered_pupil == 0))
            valid_data = filtered_pupil[~(np.isnan(filtered_pupil) | (filtered_pupil == 0))]
            
            # if len(valid_data) > 0:
            print(f"Completed pupil data {method} filtering:")
            print(f"  Window size: {window_size}")
            print(f"  Number of invalid data points: {invalid_count}")
            if len(valid_data) > 0:
                print(f"  Valid data range: {valid_data.min():.2f}mm - {valid_data.max():.2f}mm")
                print(f"  Average pupil size: {valid_data.mean():.2f}mm")

        except Exception as e:
            print(f"Error in Pupil Data Filtering: {str(e)}")
            raise

    def save_to_csv(self, export_gaze=True, export_events=True, export_preprocessing=True, **preprocessing_params):
        
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
        output_folder = os.path.join(self.pre_output_dir)
        os.makedirs(output_folder, exist_ok=True)

        if export_gaze:
            # gaze_data = {
            # }
            # gaze_df = pd.DataFrame(gaze_data)
            # gaze_df.to_csv(gaze_path, index=False, encoding='utf-8-sig', na_rep='NA')
            gaze_data = {
                'Timestamp (s)': self.processed_data['Timestamp'],
                'Gaze Point X': self.processed_data['GazePointX'],
                'Gaze Point Y': self.processed_data['GazePointY'],
                'Left Pupil Size (mm)': self.processed_data['PupilLeft'],
                'Right Pupil Size (mm)': self.processed_data['PupilRight'],
                'Average Pupil Size (mm)': self.processed_data['Pupil'],
                'Velocity (deg/s)': self.processed_data.get('Velocity', None),
                'Gaze Angle X (deg)': self.processed_data.get('GazeAngleX', None),
                'Gaze Angle Y (deg)': self.processed_data.get('GazeAngleY', None)
            }
            
            # Create DataFrame and export to CSV
            gaze_df = pd.DataFrame(gaze_data)
            gaze_path = os.path.join(output_folder, f"{timestamp}_gazeData.csv")
            gaze_df.to_csv(gaze_path, index=False, encoding='utf-8-sig', na_rep='NA')
            
            print(f"Complete gaze data has been exported to {gaze_path}")

        if export_events:
            if self.events:
                events_data = []
                for start, end, color, description in self.events:
                    # events_data.append({
                    # })
                    events_data.append({
                        'Description': description,
                        'Start Time (s)': start,
                        'End Time (s)': end,
                        'Duration (s)': end - start,
                        'Color': f"rgb{color}"
                    })
                events_df = pd.DataFrame(events_data)
                events_path = os.path.join(output_folder, f"{timestamp}_event.csv")
                events_df.to_csv(events_path, index=False, encoding='utf-8-sig')
                print(f"Event Data Exported To {events_path}")

            if hasattr(self, 'fixations') and self.fixations is not None:
                fixations_df = self.fixations.copy()
                # fixations_df.to_csv(fixations_path, index=False, encoding='utf-8-sig')
                fixations_df.columns = ['Start Time (s)', 'End Time (s)', 'Duration (s)', 
                                        'X Coordinate', 'Y Coordinate']
                fixations_path = os.path.join(output_folder, f"{timestamp}_fixationEvent.csv")
                fixations_df.to_csv(fixations_path, index=False, encoding='utf-8-sig')
                print(f"Fixation event data has been exported to {fixations_path}")

            if hasattr(self, 'saccades') and self.saccades is not None:
                saccades_df = self.saccades.copy()
                # saccades_df.to_csv(saccades_path, index=False, encoding='utf-8-sig')
                saccades_df.columns = ['Start Time (s)', 'End Time (s)', 'Duration (s)', 
                                    'Start X Coordinate', 'Start Y Coordinate', 
                                    'End X Coordinate', 'End Y Coordinate', 'Amplitude (°)']
                saccades_path = os.path.join(output_folder, f"{timestamp}_saccadeEvents.csv")
                saccades_df.to_csv(saccades_path, index=False, encoding='utf-8-sig')
                print(f"Saccade event data has been exported to {saccades_path}")

            if hasattr(self, 'blinks') and self.blinks is not None:
                blinks_df = self.blinks.copy()
                blinks_df.columns = ['Start Time (s)', 'End Time (s)', 'Duration (ms)']
                blinks_path = os.path.join(output_folder, f"{timestamp}_blinkEvent.csv")
                blinks_df.to_csv(blinks_path, index=False, encoding='utf-8-sig')
                print(f"Blinke Data Exported To {blinks_path}")

        if export_preprocessing and preprocessing_params:
            # preprocessing_info = [
            #     ]),
            #     ]),
            #     ]),
            #     ])
            # ]
            preprocessing_info = [
                ('Pupil Data Preprocessing', [
                    ('Pupil Interpolation', preprocessing_params.get('pupil_interpolate', False)),
                    ('Pupil Interpolation Threshold (ms)', preprocessing_params.get('pupil_max_gap', 'NA')),
                    ('Pupil Filter', preprocessing_params.get('pupil_filter', False)),
                    ('Pupil Filter Method', preprocessing_params.get('pupil_filter_method', 'NA')),
                    ('Pupil Filter Window', preprocessing_params.get('pupil_window_size', 'NA'))
                ]),
                ('Fixation Detection', [
                    ('Angular Velocity Threshold (°/s)', preprocessing_params.get('velocity_threshold', 'NA')),
                    ('Blink Detection Min Threshold (ms)', preprocessing_params.get('blink_threshold', 'NA')),
                    ('Blink Detection Max Threshold (ms)', preprocessing_params.get('blink_max_threshold', 'NA'))
                ]),
                ('Data Preprocessing', [
                    ('Gaze Interpolation', preprocessing_params.get('interpolate', False)),
                    ('Gaze Interpolation Threshold (ms)', preprocessing_params.get('max_gap_length', 'NA')),
                    ('Gaze Filter', preprocessing_params.get('denoise', False)),
                    ('Gaze Filter Method', preprocessing_params.get('denoise_method', 'NA')),
                    ('Gaze Filter Window', preprocessing_params.get('window_size', 'NA')),
                    ('Velocity Calculation Time Window (ms)', preprocessing_params.get('velocity_window_length', 'NA'))
                ]),
                ('Fixation Preprocessing', [
                    ('Fixation Merge', preprocessing_params.get('merge_fixations', False)),
                    ('Max Merge Time (ms)', preprocessing_params.get('max_time_between_fixations', 'NA')),
                    ('Max Merge Angle (度)', preprocessing_params.get('max_angle_between_fixations', 'NA')),
                    ('Min Fixation Duration', preprocessing_params.get('discard_short_fixations', False)),
                    ('Min Fixation Time (ms)', preprocessing_params.get('min_fixation_duration', 'NA'))
                ])
            ]

            params_data = []
            for category, params in preprocessing_info:
                for param_name, param_value in params:
                    # params_data.append({
                    # })
                    params_data.append({
                        'Parameter Category': category,
                        'Parameter': param_name,
                        'Value': str(param_value)
                    })

            params_df = pd.DataFrame(params_data)
            params_path = os.path.join(output_folder, f"{timestamp}_preprocessingParameter.csv")
            params_df.to_csv(params_path, index=False, encoding='utf-8-sig')
            print(f"Preprocessing Parameters Exported To {params_path}")

        print(f"All Data Exported To Folder: {output_folder}")

    def interpolate_gaps(self, max_gap_length, min_gap_size=3):
        print(f"Starting gap interpolation. Max gap length: {max_gap_length} ms, Min gap size: {min_gap_size} samples")
        
        timestamps = self.processed_data['Timestamp'].values
        x = self.processed_data['GazePointX'].values
        y = self.processed_data['GazePointY'].values

        gaps = pd.isnull(x) | pd.isnull(y)
        
        if gaps[0]:
            print("Warning: Data starts with a gap")
        if gaps[-1]:
            print("Warning: Data ends with a gap")

        all_gaps = []
        current_gap_start = None
        for i, is_gap in enumerate(gaps):
            if is_gap and current_gap_start is None:
                current_gap_start = i
            elif not is_gap and current_gap_start is not None:
                gap_size = i - current_gap_start
                if gap_size >= min_gap_size:
                    all_gaps.append((current_gap_start, i))
                current_gap_start = None
        
        if current_gap_start is not None:
            gap_size = len(gaps) - current_gap_start
            if gap_size >= min_gap_size:
                all_gaps.append((current_gap_start, len(gaps)))

        print(f"Total number of gaps found: {len(all_gaps)}")
        print(f"First few gaps: {all_gaps[:5]}")
        print(f"Last few gaps: {all_gaps[-5:]}")

        interpolated_gaps = 0
        total_interpolated_points = 0

        for start, end in all_gaps:
            gap_duration = (timestamps[end-1] - timestamps[start]) * 1000  
            if gap_duration <= max_gap_length:
                if start > 0 and end < len(timestamps):
                    t_interp = timestamps[start:end]
                    x_interp = np.interp(t_interp, [timestamps[start-1], timestamps[end]], [x[start-1], x[end]])
                    y_interp = np.interp(t_interp, [timestamps[start-1], timestamps[end]], [y[start-1], y[end]])

                    x[start:end] = x_interp
                    y[start:end] = y_interp
                    
                    interpolated_gaps += 1
                    total_interpolated_points += end - start
                    print(f"Interpolated gap {interpolated_gaps}: Start: {start}, End: {end}, Duration: {gap_duration:.2f} ms, Points: {end-start}")
                else:
                    print(f"Skipped gap interpolation due to invalid start/end indices. Start: {start}, End: {end}")
            else:
                print(f"Skipped gap interpolation. Duration ({gap_duration:.2f} ms) exceeds max_gap_length")

        self.processed_data['GazePointX'] = x
        self.processed_data['GazePointY'] = y

        print(f"Interpolation complete. Interpolated {interpolated_gaps} gaps, total {total_interpolated_points} points")

        remaining_gaps = pd.isnull(self.processed_data['GazePointX']) | pd.isnull(self.processed_data['GazePointY'])
        print(f"Remaining gaps after interpolation: {remaining_gaps.sum()}")

    # def denoise_data(self, method='median', window_size=3):
    #     x = self.processed_data['GazePointX'].values
    #     y = self.processed_data['GazePointY'].values

    #         x = pd.Series(x).rolling(window=window_size, center=True, min_periods=1).mean().values
    #         y = pd.Series(y).rolling(window=window_size, center=True, min_periods=1).mean().values
    #         x = pd.Series(x).rolling(window=window_size, center=True, min_periods=1).median().values
    #         y = pd.Series(y).rolling(window=window_size, center=True, min_periods=1).median().values
    #     else:
    #         raise ValueError("Unsupported denoise method")

    #     self.processed_data['GazePointX'] = x
    #     self.processed_data['GazePointY'] = y

    def calculate_velocities(self, window_length=20, min_valid_samples=2, velocity_threshold=30):

        print(f"Starting velocity calculation. Time window length: {window_length} ms, Minimum valid samples: {min_valid_samples}")

        timestamps = self.processed_data['Timestamp'].values

        # Use 2D gaze + FOV to estimate angular velocity (consistent with Tobii Pro Lab I-VT)
        use_3d = False
        if 'GazeAngleX' not in self.processed_data.columns:
            raise ValueError("GazeAngleX not found in processed_data.")

        if len(timestamps) < 2:
            raise ValueError("Insufficient data points to calculate velocity.")

        avg_sample_interval = np.mean(np.diff(timestamps[:min(100, len(timestamps)-1)])) * 1000
        samples_in_window = max(min_valid_samples, int(window_length / avg_sample_interval) + 1)

        velocities = np.full(len(timestamps), np.nan)

        for i in range(len(timestamps)):
            start = max(0, i - samples_in_window // 2)
            end = min(len(timestamps), i + samples_in_window // 2 + 1)
            window_time = timestamps[start:end]

            if use_3d:
                # 3D mode: use gaze direction vector angle
                wx = dx_arr[start:end]
                wy = dy_arr[start:end]
                wz = dz_arr[start:end]
                valid_mask = ~np.isnan(wx) & ~np.isnan(wy) & ~np.isnan(wz)
            else:
                # 2D mode: use GazeAngle
                x = self.processed_data['GazeAngleX'].values
                y = self.processed_data['GazeAngleY'].values
                wx = x[start:end]
                wy = y[start:end]
                valid_mask = ~np.isnan(wx) & ~np.isnan(wy)

            if valid_mask.sum() < min_valid_samples:
                continue

            valid_time = window_time[valid_mask]
            if len(valid_time) < 2:
                continue

            dt = valid_time[-1] - valid_time[0]
            if dt <= 0:
                continue

            if use_3d:
                # 3D: angle between first and last gaze direction vectors
                v1 = np.array([wx[valid_mask][0], wy[valid_mask][0], wz[valid_mask][0]])
                v2 = np.array([wx[valid_mask][-1], wy[valid_mask][-1], wz[valid_mask][-1]])
                n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                if n1 > 0 and n2 > 0:
                    cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
                    angle_change = np.degrees(np.arccos(cos_angle))
                else:
                    continue
            else:
                # 2D: angle difference between first and last
                vx = wx[valid_mask]
                vy = wy[valid_mask]
                angle_change = np.sqrt((vx[-1] - vx[0])**2 + (vy[-1] - vy[0])**2)

            velocities[i] = angle_change / dt

            if velocities[i] > 1000:
                velocities[i] = np.nan

        valid_velocities = velocities[~np.isnan(velocities)]
        # if len(valid_velocities) > 0:
        # else:
        if len(valid_velocities) > 0:
            print(f"Number of valid velocities calculated: {len(valid_velocities)}")
            print(f"Velocity statistics: Min = {np.min(valid_velocities):.2f}, "
                f"Max = {np.max(valid_velocities):.2f}, "
                f"Mean = {np.mean(valid_velocities):.2f}, "
                f"Median = {np.median(valid_velocities):.2f}")
        else:
            print("Warning: No valid velocity values were calculated")

        return velocities
    
    def create_event(self, start_idx, end_idx, event_type):
        
        start_time = self.processed_data['Timestamp'].iloc[start_idx]
        end_time = self.processed_data['Timestamp'].iloc[end_idx]
        duration = end_time - start_time
        # Use angle coordinates (GazeAngleX/Y) so merge threshold (0.5 deg) works in correct space
        if 'GazeAngleX' in self.processed_data.columns:
            x_values = self.processed_data['GazeAngleX'].iloc[start_idx:end_idx+1].dropna()
            y_values = self.processed_data['GazeAngleY'].iloc[start_idx:end_idx+1].dropna()
        else:
            x_values = self.processed_data['GazePointX'].iloc[start_idx:end_idx+1].dropna()
            y_values = self.processed_data['GazePointY'].iloc[start_idx:end_idx+1].dropna()

        if x_values.empty or y_values.empty:
            return None

        if event_type == 'fixation':
            x = x_values.mean()
            y = y_values.mean()
            return {
                'start': start_time,
                'end': end_time,
                'duration': duration,
                'x': x,
                'y': y
            }
        elif event_type == 'saccade':
            x_start = x_values.iloc[0]
            y_start = y_values.iloc[0]
            x_end = x_values.iloc[-1]
            y_end = y_values.iloc[-1]
            amplitude = np.sqrt((x_end - x_start)**2 + (y_end - y_start)**2)

            return {
                'start': start_time,
                'end': end_time,
                'duration': duration,
                'x_start': x_start,
                'y_start': y_start,
                'x_end': x_end,
                'y_end': y_end,
                'amplitude': amplitude
            }

    def classify_fixations_and_saccades(self, velocities, velocity_threshold):
        
        fixations = []
        saccades = []
        saccade_velocities = []  
        event_start = None
        current_event = None
        min_duration = 0.02  
        max_gap_duration = 0.075  

        timestamps = self.processed_data['Timestamp'].values
        gaze_x = self.processed_data['GazePointX'].values
        gaze_y = self.processed_data['GazePointY'].values

        def is_valid_data(start_idx, end_idx):
            
            if start_idx >= end_idx:
                return False
                
            x_data = gaze_x[start_idx:end_idx]
            y_data = gaze_y[start_idx:end_idx]
            vel_data = velocities[start_idx:end_idx]
            
            missing_ratio = (np.isnan(x_data).sum() + np.isnan(y_data).sum()) / (2 * len(x_data))
            max_gap = 0
            current_gap = 0
            
            for i in range(len(x_data)):
                if np.isnan(x_data[i]) or np.isnan(y_data[i]):
                    current_gap += 1
                    max_gap = max(max_gap, current_gap)
                else:
                    current_gap = 0
                    
            return (max_gap / self.sample_rate < max_gap_duration)

        for i in range(len(velocities)):
            if np.isnan(velocities[i]):
                # If in a fixation, check if this NaN gap is short enough to bridge over
                if event_start is not None and current_event == 'fixation':
                    nan_end = i
                    while nan_end < len(velocities) and np.isnan(velocities[nan_end]):
                        nan_end += 1
                    gap_dur = timestamps[min(nan_end, len(timestamps)-1)] - timestamps[i]
                    if gap_dur <= max_gap_duration:
                        continue  # Short gap, skip, keep current fixation uninterrupted

                # Long gap or non-fixation event: terminate current event
                if event_start is not None:
                    duration = timestamps[i-1] - timestamps[event_start]
                    if duration >= min_duration and is_valid_data(event_start, i):
                        event = self.create_event(event_start, i-1, current_event)
                        if event:
                            if current_event == 'fixation':
                                fixations.append(event)
                            else:
                                saccades.append(event)
                                event_velocities = velocities[event_start:i-1]
                                event_velocities = event_velocities[~np.isnan(event_velocities)]
                                if len(event_velocities) > 0:
                                    saccade_velocities.append({
                                        'peak_velocity': np.max(event_velocities),
                                        'mean_velocity': np.mean(event_velocities),
                                        'start_time': event['start']
                                    })
                    event_start = None
                    current_event = None
                continue

            event_type = 'fixation' if velocities[i] < velocity_threshold else 'saccade'

            if event_start is None:
                event_start = i
                current_event = event_type
            elif event_type != current_event:
                duration = timestamps[i-1] - timestamps[event_start]
                if duration >= min_duration and is_valid_data(event_start, i):
                    event = self.create_event(event_start, i-1, current_event)
                    if event:
                        if current_event == 'fixation':
                            fixations.append(event)
                        else:
                            saccades.append(event)
                            event_velocities = velocities[event_start:i-1]
                            event_velocities = event_velocities[~np.isnan(event_velocities)]
                            if len(event_velocities) > 0:
                                saccade_velocities.append({
                                    'peak_velocity': np.max(event_velocities),
                                    'mean_velocity': np.mean(event_velocities),
                                    'start_time': event['start']  
                                })
                event_start = i
                current_event = event_type

        if event_start is not None:
            duration = timestamps[-1] - timestamps[event_start]
            if duration >= min_duration and is_valid_data(event_start, len(velocities)):
                event = self.create_event(event_start, len(velocities)-1, current_event)
                if event:
                    if current_event == 'fixation':
                        fixations.append(event)
                    else:
                        saccades.append(event)
                        event_velocities = velocities[event_start:]
                        event_velocities = event_velocities[~np.isnan(event_velocities)]
                        if len(event_velocities) > 0:
                            saccade_velocities.append({
                                'peak_velocity': np.max(event_velocities),
                                'mean_velocity': np.mean(event_velocities),
                                'start_time': event['start']
                            })

        self.fixations = pd.DataFrame(fixations)
        self.saccades = pd.DataFrame(saccades)
        self.saccade_velocities = pd.DataFrame(saccade_velocities)  

        print(f"\nIdentified event statistics:")
        print(f"Number of fixation events: {len(fixations)}")
        print(f"Number of saccade events: {len(saccades)}")
        
        if saccade_velocities:
            # peak_velocities = [v['peak_velocity'] for v in saccade_velocities]
            # mean_velocities = [v['mean_velocity'] for v in saccade_velocities]
            print("\nSaccade velocity statistics (degrees/second):")
            peak_velocities = [v['peak_velocity'] for v in saccade_velocities]
            mean_velocities = [v['mean_velocity'] for v in saccade_velocities]
            print(f"Peak velocity - Mean: {np.mean(peak_velocities):.1f}, "
                f"Max: {np.max(peak_velocities):.1f}, "
                f"Min: {np.min(peak_velocities):.1f}")
            print(f"Mean velocity - Mean: {np.mean(mean_velocities):.1f}, "
                f"Max: {np.max(mean_velocities):.1f}, "
                f"Min: {np.min(mean_velocities):.1f}")

        return fixations, saccades
        
    def detect_blinks(self, blink_threshold, blink_max_threshold=None):
        
        blinks = []
        blink_start = None
        in_blink = False
        
        gaze_data = self.processed_data[['GazePointX', 'GazePointY']]
        timestamps = self.processed_data['Timestamp']
        
        gaze_missing = pd.isnull(gaze_data['GazePointX']) | pd.isnull(gaze_data['GazePointY'])
        
        sample_interval = 1000 / self.sample_rate if self.sample_rate else 1  
        min_samples = max(2, int(blink_threshold / sample_interval))  
        
        for i in range(len(gaze_missing)):
            if gaze_missing.iloc[i]:  
                if not in_blink:  
                    blink_start = timestamps.iloc[i]
                    in_blink = True
            else:  
                if in_blink:  
                    blink_end = timestamps.iloc[i]
                    blink_duration = (blink_end - blink_start) * 1000  
                    
                    if blink_duration >= blink_threshold:
                        if blink_max_threshold is None or blink_duration <= blink_max_threshold:
                            start_idx = timestamps[timestamps == blink_start].index[0]
                            end_idx = timestamps[timestamps == blink_end].index[0]
                            missing_samples = gaze_missing.iloc[start_idx:end_idx].sum()
                            
                            if missing_samples >= min_samples:
                                blinks.append({
                                    'start': blink_start,
                                    'end': blink_end,
                                    'duration': blink_duration
                                })
                    in_blink = False
        
        if in_blink:
            blink_end = timestamps.iloc[-1]
            blink_duration = (blink_end - blink_start) * 1000
            if blink_duration >= blink_threshold:
                if blink_max_threshold is None or blink_duration <= blink_max_threshold:
                    start_idx = timestamps[timestamps == blink_start].index[0]
                    missing_samples = gaze_missing.iloc[start_idx:].sum()
                    if missing_samples >= min_samples:
                        blinks.append({
                            'start': blink_start,
                            'end': blink_end,
                            'duration': blink_duration
                        })
        
        # if blinks:
        #     durations = [b['duration'] for b in blinks]
        print(f"Detected {len(blinks)} blink events")
        if blinks:
            durations = [b['duration'] for b in blinks]
            print("Blink duration statistics:")
            print(f"  Minimum: {min(durations):.2f} ms")
            print(f"  Maximum: {max(durations):.2f} ms")
            print(f"  Average: {sum(durations)/len(durations):.2f} ms")
        
        return blinks


    def merge_adjacent_fixations(self, fixations, max_time_between_fixations, max_angle_between_fixations):
        if not fixations:
            return fixations

        merged_fixations = [fixations[0]]
        
        for current in fixations[1:]:
            previous = merged_fixations[-1]
            time_between = current['start'] - previous['end']
            angle_between = np.sqrt((current['x'] - previous['x'])**2 + (current['y'] - previous['y'])**2)
            
            if time_between <= max_time_between_fixations/1000 and angle_between <= max_angle_between_fixations:
                # Merge fixations
                merged_fixations[-1]['end'] = current['end']
                merged_fixations[-1]['duration'] += current['duration'] + time_between
                merged_fixations[-1]['x'] = (previous['x'] * previous['duration'] + current['x'] * current['duration']) / (previous['duration'] + current['duration'])
                merged_fixations[-1]['y'] = (previous['y'] * previous['duration'] + current['y'] * current['duration']) / (previous['duration'] + current['duration'])
            else:
                merged_fixations.append(current)
        
        # print(f"Fixations after merging: {len(merged_fixations)}")
        # print("Merged fixation durations:")
        # durations = [f['duration'] for f in merged_fixations]
        # print(pd.Series(durations).describe())
        
        return merged_fixations

    def discard_short_fixations(self, fixations, min_fixation_duration):
        long_fixations = [f for f in fixations if f['duration'] >= min_fixation_duration / 1000]
        
        # print(f"Fixations after discarding short ones: {len(long_fixations)}")
        # if long_fixations:
        #     print("Long fixation durations:")
        #     durations = [f['duration'] for f in long_fixations]
        #     print(pd.Series(durations).describe())
        # else:
        #     print("No fixations remaining after discarding short ones.")
        
        return long_fixations
    
    def analyze_data(self, metrics_list=None):
        
        if metrics_list is None:
            # metrics_list = [
            # ]
            metrics_list = [
                "First Fixation Duration", "First Fixation Time", "Fixation Count", "Total Fixation Duration",
                "Average Fixation Duration", "Fixation Rate", "Saccade Ratio", "Fixation-Saccade Ratio",
                "Saccade Count", "Average Saccade Amplitude", "First Saccade Latency", "Saccade Direction",
                "Saccade Peak Velocity", "Average Saccade Duration", "Saccade Rate",
                "Mean Pupil Diameter", "Minimum Pupil Diameter", "Maximum Pupil Diameter",
                "Pupil Diameter Variance", "Pupil Area Growth Rate",
                "Blink Count", "Total Blink Duration", "Average Blink Duration"
            ]

        results = []

        all_data_result = self.analyze_single_toi("All", 
                                                0, 
                                                self.processed_data['Timestamp'].max(), 
                                                metrics_list)
        results.append(all_data_result)

        for event in self.events:
            start_time, end_time, _, toi_name = event
            toi_result = self.analyze_single_toi(toi_name, start_time, end_time, metrics_list)
            results.append(toi_result)

        df = pd.DataFrame(results)

        # column_units = {
        # }
        column_units = {
            "First Fixation Time": "(s)",
            "First Fixation Duration": "(s)",
            "Total Fixation Duration": "(s)",
            "Average Fixation Duration": "(s)",
            "Total Visit Duration": "(s)",
            "Average Visit Duration": "(s)",
            "Average Fixation Ratio": "(%)",
            "Fixation Rate": "(/s)",
            "Fixation-Saccade Ratio": "(%)",
            "Average Saccade Amplitude": "(°)",
            "First Saccade Latency": "(s)",
            "Saccade Peak Velocity": "(°/s)",
            "Average Saccade Duration": "(s)",
            "Saccade Rate": "(/s)",
            "Mean Pupil Diameter": "(mm)",
            "Minimum Pupil Diameter": "(mm)",
            "Maximum Pupil Diameter": "(mm)",
            "Pupil Diameter Variance": "(mm²)",
            "Pupil Area Growth Rate": "(mm²/s)",
            "Total Blink Duration": "(s)",
            "Average Blink Duration": "(s)"
        }

        df.rename(columns={col: f"{col} {column_units.get(col, '')}" for col in df.columns}, 
                inplace=True)

        for col in df.columns:
            if col not in ['TOI', 'Start Time', 'End Time', 'Saccade Direction']:
                df[col] = df[col].apply(lambda x: f"{x:.4f}" if isinstance(x, (int, float)) else x)

        self.save_analysis_results(df, 'feature.csv')
        return df

    def analyze_single_toi(self, toi_name, start_time, end_time, metrics_list):
        
        print(f"\nStart Analyzing TOI: {toi_name}")
        toi_data = self.get_toi_data(start_time, end_time)
        toi_fixations = self.get_toi_events(self.fixations, start_time, end_time)
        toi_saccades = self.get_toi_events(self.saccades, start_time, end_time)
        toi_blinks = self.get_toi_events(self.blinks, start_time, end_time)

        result = {'TOI': toi_name, 'Start Time': start_time, 'End Time': end_time}
        
        # if len(toi_data) == 0:
        # if len(toi_fixations) == 0:
        # if len(toi_saccades) == 0:
        # if len(toi_blinks) == 0:
        if len(toi_data) == 0:
            print(f"Warning: No valid eye tracking data found for TOI '{toi_name}'")
        if len(toi_fixations) == 0:
            print(f"Warning: No valid fixation data found for TOI '{toi_name}'")
        if len(toi_saccades) == 0:
            print(f"Warning: No valid saccade data found for TOI '{toi_name}'")
        if len(toi_blinks) == 0:
            print(f"Warning: No valid blink data found for TOI '{toi_name}'")
                    
        for metric in metrics_list:
            print(f"Compute Metric: {metric}")
            value = self.calculate_metric_with_check(metric, toi_data, toi_fixations, toi_saccades, toi_blinks, start_time)
            result[metric] = value

        return result

    def calculate_metric_with_check(self, metric, toi_data, toi_fixations, toi_saccades, toi_blinks, start_time):
        
        try:
            value = self.calculate_metric(metric, toi_data, toi_fixations, toi_saccades, toi_blinks, start_time)
            
            if pd.isna(value):
                reason = self.get_nan_reason(metric, toi_data, toi_fixations, toi_saccades, toi_blinks)
                print(f"Warning: Metric '{metric}' computed as NaN - {reason}")
                return 0
                
            return value
            
        except Exception as e:
            print(f"Error: An error occurred while computing metric '{metric}' - {str(e)}")
            return 0
        
    def get_nan_reason(self, metric, toi_data, toi_fixations, toi_saccades, toi_blinks):
        
        #     if len(toi_fixations) == 0:
                
        #     if len(toi_fixations) == 0:
                
        #     if len(toi_fixations) == 0:
                
        #     if len(toi_data) == 0:
                
        #     if len(toi_saccades) == 0:
                
        #     if len(toi_saccades) == 0:
                
        #     if len(toi_blinks) == 0:
                
        #     valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
        #     if len(valid_pupil) == 0:
                
        #     valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
        #     if len(valid_pupil) < 2:
                
        if metric in ['First Fixation Time', 'First Fixation Duration']:
            if len(toi_fixations) == 0:
                return "No valid fixations detected"
                
        elif metric in ['Fixation Count', 'Total Fixation Duration', 'Average Fixation Duration']:
            if len(toi_fixations) == 0:
                return "No fixation data available in time period"
                
        elif metric in ['Visit Count', 'Total Visit Duration', 'Average Visit Duration']:
            if len(toi_fixations) == 0:
                return "No visit records found"
                
        elif metric in ['Average Fixation Ratio', 'Fixation Rate']:
            if len(toi_data) == 0:
                return "No valid raw data available for ratio calculation"
                
        elif metric == 'Fixation-Saccade Ratio':
            if len(toi_saccades) == 0:
                return "No saccade data detected"
                
        elif metric in ['Saccade Count', 'Average Saccade Amplitude', 'First Saccade Latency', 'Saccade Peak Velocity']:
            if len(toi_saccades) == 0:
                return "No valid saccade data available"
                
        elif metric in ['Total Blink Duration', 'Average Blink Duration']:
            if len(toi_blinks) == 0:
                return "No blink events detected"
                
        elif metric in ['Minimum Pupil Diameter', 'Maximum Pupil Diameter', 'Mean Pupil Diameter', 'Pupil Diameter Variance']:
            valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
            if len(valid_pupil) == 0:
                return "No valid pupil data available (after excluding 0s and NaNs)"
                
        elif metric == 'Pupil Area Growth Rate':
            valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
            if len(valid_pupil) < 2:
                return "Insufficient valid pupil data to calculate growth rate (at least 2 valid values required)"
                
        return "NaN result due to unknown reason"

    def get_toi_data(self, start_time, end_time):
        
        return self.processed_data[(self.processed_data['Timestamp'] >= start_time) & 
                                (self.processed_data['Timestamp'] <= end_time)]

    def get_toi_events(self, events_df, start_time, end_time):
        
        if events_df is None or len(events_df) == 0:
            return pd.DataFrame()
        return events_df[(events_df['start'] >= start_time) & (events_df['end'] <= end_time)]


    def calculate_metric(self, metric, toi_data, toi_fixations, toi_saccades, toi_blinks, start_time):
        
        # try:
        #         if len(toi_fixations) == 0:
        #             return 0
        #         return max(0, toi_fixations['start'].iloc[0] - start_time)
                
        #         if len(toi_fixations) == 0:
        #             return 0
        #         return max(0, toi_fixations['duration'].iloc[0])
                
        #         return len(toi_fixations)
                
        #         return max(0, toi_fixations['duration'].sum())
                
        #         if len(toi_fixations) == 0:
        #             return 0
        #         return max(0, toi_fixations['duration'].mean())
                
        #         return len(toi_fixations)
                
        #         return max(0, toi_fixations['duration'].sum())
                
        #         if len(toi_fixations) == 0:
        #             return 0
        #         return max(0, toi_fixations['duration'].mean())
                
        #         total_time = toi_data['Timestamp'].max() - toi_data['Timestamp'].min()
        #         if total_time <= 0 or len(toi_fixations) == 0:
        #             return 0
        #         return max(0, self.calculate_total_fixation_time(toi_fixations) / total_time)
                
        #         if len(toi_fixations) <= 1:
        #             return 0
        #         total_time = toi_fixations['end'].max() - toi_fixations['start'].min()
        #         if total_time <= 0:
        #             return 0
        #         return max(0, (len(toi_fixations) - 1) / total_time)
                
        #         fixation_time = self.calculate_total_fixation_time(toi_fixations)
        #         saccade_time = toi_saccades['duration'].sum() if len(toi_saccades) > 0 else 0
        #         if saccade_time <= 0:
        #             return 0
        #         return max(0, fixation_time / saccade_time)
                
        #         return len(toi_saccades)
                
        #         if len(toi_saccades) == 0:
        #             return 0
        #         return max(0, toi_saccades['amplitude'].mean())
                
        #         if len(toi_saccades) == 0:
        #             return 0
        #         return max(0, toi_saccades['start'].iloc[0] - start_time)
                
        #         if len(toi_saccades) == 0:
        #             return "[0.0000, 0.0000]"
        #         mean_horizontal = np.mean(toi_saccades['x_end'] - toi_saccades['x_start'])
        #         mean_vertical = np.mean(toi_saccades['y_end'] - toi_saccades['y_start'])
        #         return f"[{mean_horizontal:.4f}, {mean_vertical:.4f}]"
                
        #         if len(toi_saccades) == 0:
        #             return 0
        #         return max(0, toi_saccades['amplitude'].max())
                
        #         if len(toi_saccades) == 0:
        #             return 0
        #         return max(0, toi_saccades['duration'].mean())
                
        #         total_time = toi_data['Timestamp'].max() - toi_data['Timestamp'].min()
        #         if total_time <= 0:
        #             return 0
        #         return max(0, len(toi_saccades) / total_time)
                
        #         if len(toi_blinks) == 0:
        #             return 0
                
        #         if len(toi_blinks) == 0:
        #             return 0
                
        #         valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
        #         if len(valid_pupil) == 0:
        #             return 0
        #         min_pupil = valid_pupil.min()
        #         if min_pupil < 2:
        #         return min_pupil
                
        #         valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
        #         if len(valid_pupil) == 0:
        #             return 0
        #         max_pupil = valid_pupil.max()
        #         if max_pupil > 8:
        #         return max_pupil
                
        #         valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
        #         if len(valid_pupil) == 0:
        #             return 0
        #         mean_pupil = valid_pupil.mean()
        #         if not 2 <= mean_pupil <= 8:
        #         return mean_pupil
                
        #         valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
        #         if len(valid_pupil) == 0:
        #             return 0
        #         return valid_pupil.var()
                
        #         valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
        #         if len(valid_pupil) < 2:
        #             return 0
        #         pupil_areas = np.pi * (valid_pupil / 2) ** 2
        #         timestamps = toi_data.loc[valid_pupil.index, 'Timestamp']
        #         growth_rates = []
        #         for i in range(1, len(pupil_areas)):
        #             area_change = pupil_areas.iloc[i] - pupil_areas.iloc[i-1]
        #             time_change = timestamps.iloc[i] - timestamps.iloc[i-1]
        #             if time_change > 0:
        #                 growth_rates.append(area_change / time_change)
        #         return np.mean(growth_rates) if growth_rates else 0

        #         return len(toi_blinks)
                
        #     else:
        #         return 0
                
        # except Exception as e:
        #     return 0
        try:
            if metric == 'First Fixation Time':
                if len(toi_fixations) == 0:
                    return 0
                return max(0, toi_fixations['start'].iloc[0] - start_time)
                
            elif metric == 'First Fixation Duration':
                if len(toi_fixations) == 0:
                    return 0
                return max(0, toi_fixations['duration'].iloc[0])
                
            elif metric == 'Fixation Count':
                return len(toi_fixations)
                
            elif metric == 'Total Fixation Duration':
                return max(0, toi_fixations['duration'].sum())
                
            elif metric == 'Average Fixation Duration':
                if len(toi_fixations) == 0:
                    return 0
                return max(0, toi_fixations['duration'].mean())
                
            elif metric == 'Visit Count':
                return len(toi_fixations)
                
            elif metric == 'Total Visit Duration':
                return max(0, toi_fixations['duration'].sum())
                
            elif metric == 'Average Visit Duration':
                if len(toi_fixations) == 0:
                    return 0
                return max(0, toi_fixations['duration'].mean())
                
            elif metric == 'Average Fixation Ratio':
                total_time = toi_data['Timestamp'].max() - toi_data['Timestamp'].min()
                if total_time <= 0 or len(toi_fixations) == 0:
                    return 0
                return max(0, self.calculate_total_fixation_time(toi_fixations) / total_time)
                
            elif metric == 'Fixation Rate':
                if len(toi_fixations) <= 1:
                    return 0
                total_time = toi_fixations['end'].max() - toi_fixations['start'].min()
                if total_time <= 0:
                    return 0
                return max(0, (len(toi_fixations) - 1) / total_time)
                
            elif metric == 'Fixation-Saccade Ratio':
                fixation_time = self.calculate_total_fixation_time(toi_fixations)
                saccade_time = toi_saccades['duration'].sum() if len(toi_saccades) > 0 else 0
                if saccade_time <= 0:
                    return 0
                return max(0, fixation_time / saccade_time)
                
            elif metric == 'Saccade Count':
                return len(toi_saccades)
                
            elif metric == 'Average Saccade Amplitude':
                if len(toi_saccades) == 0:
                    return 0
                return max(0, toi_saccades['amplitude'].mean())
                
            elif metric == 'First Saccade Latency':
                if len(toi_saccades) == 0:
                    return 0
                return max(0, toi_saccades['start'].iloc[0] - start_time)
                
            elif metric == 'Saccade Direction':
                if len(toi_saccades) == 0:
                    return "[0.0000, 0.0000]"
                mean_horizontal = np.mean(toi_saccades['x_end'] - toi_saccades['x_start'])
                mean_vertical = np.mean(toi_saccades['y_end'] - toi_saccades['y_start'])
                return f"[{mean_horizontal:.4f}, {mean_vertical:.4f}]"
                
            elif metric == 'Saccade Peak Velocity':
                if len(toi_saccades) == 0:
                    return 0
                return max(0, toi_saccades['amplitude'].max())
                
            elif metric == 'Average Saccade Duration':
                if len(toi_saccades) == 0:
                    return 0
                return max(0, toi_saccades['duration'].mean())
                
            elif metric == 'Saccade Rate':
                total_time = toi_data['Timestamp'].max() - toi_data['Timestamp'].min()
                if total_time <= 0:
                    return 0
                return max(0, len(toi_saccades) / total_time)
                
            elif metric == 'Total Blink Duration':
                if len(toi_blinks) == 0:
                    return 0
                return max(0, toi_blinks['duration'].sum() / 1000)  # Convert to seconds
                
            elif metric == 'Average Blink Duration':
                if len(toi_blinks) == 0:
                    return 0
                return max(0, toi_blinks['duration'].mean() / 1000)  # Convert to seconds
                
            elif metric == 'Minimum Pupil Diameter':
                # Exclude 0 and NaN values
                valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
                if len(valid_pupil) == 0:
                    print(f"Warning: No valid pupil data found (after excluding 0s and NaNs)")
                    return 0
                min_pupil = valid_pupil.min()
                if min_pupil < 2:
                    print(f"Warning: Abnormally small pupil diameter detected: {min_pupil}mm")
                return min_pupil
                
            elif metric == 'Maximum Pupil Diameter':
                # Exclude 0 and NaN values
                valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
                if len(valid_pupil) == 0:
                    print(f"Warning: No valid pupil data found (after excluding 0s and NaNs)")
                    return 0
                max_pupil = valid_pupil.max()
                if max_pupil > 8:
                    print(f"Warning: Abnormally large pupil diameter detected: {max_pupil}mm")
                return max_pupil
                
            elif metric == 'Mean Pupil Diameter':
                # Exclude 0 and NaN values
                valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
                if len(valid_pupil) == 0:
                    print(f"Warning: No valid pupil data found (after excluding 0s and NaNs)")
                    return 0
                mean_pupil = valid_pupil.mean()
                if not 2 <= mean_pupil <= 8:
                    print(f"Warning: Abnormal mean pupil diameter detected: {mean_pupil}mm")
                return mean_pupil
                
            elif metric == 'Pupil Diameter Variance':
                # Exclude 0 and NaN values
                valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
                if len(valid_pupil) == 0:
                    print(f"Warning: No valid pupil data found (after excluding 0s and NaNs)")
                    return 0
                return valid_pupil.var()
                
            elif metric == 'Pupil Area Growth Rate':
                # Exclude 0 and NaN values
                valid_pupil = toi_data['Pupil'].replace(0, np.nan).dropna()
                if len(valid_pupil) < 2:
                    print(f"Warning: Insufficient valid pupil data to calculate growth rate")
                    return 0
                pupil_areas = np.pi * (valid_pupil / 2) ** 2
                timestamps = toi_data.loc[valid_pupil.index, 'Timestamp']
                growth_rates = []
                for i in range(1, len(pupil_areas)):
                    area_change = pupil_areas.iloc[i] - pupil_areas.iloc[i-1]
                    time_change = timestamps.iloc[i] - timestamps.iloc[i-1]
                    if time_change > 0:
                        growth_rates.append(area_change / time_change)
                return np.mean(growth_rates) if growth_rates else 0

            elif metric == 'Blink Count':
                return len(toi_blinks)
                
            else:
                print(f"Warning: Unknown metric type '{metric}'")
                return 0
    
        except Exception as e:
            print(f"Error: An error occurred while computing metric '{metric}' - {str(e)}")
            return 0

    def calculate_first_fixation_time(self, fixations, start_time):
        if not fixations.empty:
            return fixations['start'].iloc[0] - start_time
        return np.nan

    def calculate_first_fixation_duration(self, fixations):
        if not fixations.empty:
            return fixations['duration'].iloc[0]
        return np.nan

    def calculate_total_fixation_time(self, fixations):
        
        return fixations['duration'].sum() if not fixations.empty else 0

    def calculate_average_fixation_time(self, fixations):
        if not fixations.empty:
            return fixations['duration'].mean()
        return np.nan

    def calculate_visit_count(self, fixations):
        return len(fixations)

    def calculate_total_visit_time(self, fixations):
        return fixations['duration'].sum()

    def calculate_average_visit_time(self, fixations):
        if not fixations.empty:
            return fixations['duration'].mean()
        return np.nan

    def calculate_average_fixation_rate(self, fixations, toi_data):
        total_time = toi_data['Timestamp'].max() - toi_data['Timestamp'].min()
        if total_time > 0:
            return self.calculate_total_fixation_time(fixations) / total_time
        return np.nan

    def calculate_fixation_transition_rate(self, fixations):
        if len(fixations) > 1:
            total_time = fixations['end'].max() - fixations['start'].min()
            return (len(fixations) - 1) / total_time if total_time > 0 else np.nan
        return np.nan

    def calculate_fixation_saccade_ratio(self, fixations, saccades):
        fixation_time = self.calculate_total_fixation_time(fixations)
        saccade_time = saccades['duration'].sum()
        if saccade_time > 0:
            return fixation_time / saccade_time
        return np.nan

    def calculate_average_saccade_amplitude(self, saccades):
        return saccades['amplitude'].mean() if 'amplitude' in saccades.columns else np.nan

    def calculate_first_saccade_start(self, saccades, start_time):
        if not saccades.empty:
            return saccades['start'].iloc[0] - start_time
        return np.nan

    def calculate_saccade_direction(self, saccades):
        if 'x_start' in saccades.columns and 'x_end' in saccades.columns and 'y_start' in saccades.columns and 'y_end' in saccades.columns:
            horizontal_directions = saccades['x_end'] - saccades['x_start']
            vertical_directions = saccades['y_end'] - saccades['y_start']
            
            mean_horizontal = np.mean(horizontal_directions)
            mean_vertical = np.mean(vertical_directions)
            
            return f"[{mean_horizontal:.4f}, {mean_vertical:.4f}]"
        return "[nan, nan]"

    def calculate_saccade_peak(self, saccades):
        return saccades['amplitude'].max() if 'amplitude' in saccades.columns else np.nan

    def calculate_average_saccade_time(self, saccades):
        return saccades['duration'].mean()

    def calculate_average_saccade_rate(self, saccades, toi_data):
        total_time = toi_data['Timestamp'].max() - toi_data['Timestamp'].min()
        if total_time > 0:
            return len(saccades) / total_time
        return np.nan

    def calculate_average_pupil_diameter(self, toi_data):
        return toi_data['Pupil'].mean()

    def calculate_min_pupil_diameter(self, toi_data):
        return toi_data['Pupil'].min()

    def calculate_max_pupil_diameter(self, toi_data):
        return toi_data['Pupil'].max()

    def calculate_pupil_diameter_variance(self, toi_data):
        return toi_data['Pupil'].var()

    def calculate_pupil_area_growth_rate(self, toi_data):
        pupil_areas = np.pi * (toi_data['Pupil'] / 2) ** 2
        timestamps = toi_data['Timestamp']
        
        if len(pupil_areas) < 2:
            return np.nan
        
        growth_rates = []
        for i in range(1, len(pupil_areas)):
            area_change = pupil_areas.iloc[i] - pupil_areas.iloc[i-1]
            time_change = timestamps.iloc[i] - timestamps.iloc[i-1]
            if time_change > 0:
                growth_rate = area_change / time_change
                growth_rates.append(growth_rate)
        
        return np.mean(growth_rates) if growth_rates else np.nan

    def analyze_aois(self, metrics_list=None):
        

        if metrics_list is None:
            # metrics_list = [
            # ]
            metrics_list = [
                'Fixation Visit Count', 'Total Fixation Visit Duration', 'Average Fixation Visit Duration', 
                'First Fixation Visit Time', 'Revisit Count', 'Fixation Point Count', 
                'Average Fixation Duration', 'Total Fixation Duration', 'Fixation Time Ratio',
                'First Fixation Latency', 'Mean Pupil Size'
            ]

        results = []

        for aoi in self.aois:
            aoi_data = self.get_aoi_data(aoi)
            result = {'AOI': aoi.name}
            
            # for metric in metrics_list:
            #         result[metric] = self.calculate_visit_count(aoi_data)
            #         result[metric] = self.calculate_total_visit_time(aoi_data)
            #         result[metric] = self.calculate_average_visit_time(aoi_data)
            #         result[metric] = self.calculate_first_visit_time(aoi_data)
            #         result[metric] = self.calculate_revisit_count(aoi_data)
            #         result[metric] = len(aoi_data)
            #         result[metric] = self.calculate_average_fixation_duration(aoi_data)
            #         result[metric] = self.calculate_total_fixation_duration(aoi_data)
            #         result[metric] = self.calculate_dwell_time_percentage(aoi_data, aoi)
            #         result[metric] = self.calculate_time_to_first_fixation(aoi_data, aoi)
            #         result[metric] = self.calculate_average_pupil_size(aoi_data)
            for metric in metrics_list:
                if metric == 'Fixation Visit Count':
                    result[metric] = self.calculate_visit_count(aoi_data)
                elif metric == 'Total Fixation Visit Duration':
                    result[metric] = self.calculate_total_visit_time(aoi_data)
                elif metric == 'Average Fixation Visit Duration':
                    result[metric] = self.calculate_average_visit_time(aoi_data)
                elif metric == 'First Fixation Visit Time':
                    result[metric] = self.calculate_first_visit_time(aoi_data)
                elif metric == 'Revisit Count':
                    result[metric] = self.calculate_revisit_count(aoi_data)
                elif metric == 'Fixation Point Count':
                    result[metric] = len(aoi_data)
                elif metric == 'Average Fixation Duration':
                    result[metric] = self.calculate_average_fixation_duration(aoi_data)
                elif metric == 'Total Fixation Duration':
                    result[metric] = self.calculate_total_fixation_duration(aoi_data)
                elif metric == 'Fixation Time Ratio':
                    result[metric] = self.calculate_dwell_time_percentage(aoi_data, aoi)
                elif metric == 'First Fixation Latency':
                    result[metric] = self.calculate_time_to_first_fixation(aoi_data, aoi)
                elif metric == 'Mean Pupil Size':
                    result[metric] = self.calculate_average_pupil_size(aoi_data)
            results.append(result)

        df = pd.DataFrame(results)

        # column_units = {
        # }
        column_units = {
            'Fixation Visit Count': '(count)',
            'Total Fixation Visit Duration': '(s)',
            'Average Fixation Visit Duration': '(s)',
            'First Fixation Visit Time': '(s)',
            'Revisit Count': '(count)',
            'Fixation Point Count': '(count)',
            'Average Fixation Duration': '(s)',
            'Total Fixation Duration': '(s)',
            'Fixation Time Ratio': '(%)',
            'First Fixation Latency': '(s)',
            'Mean Pupil Size': '(mm)'
        }

        df.rename(columns={col: f"{col} {column_units.get(col, '')}" for col in df.columns}, inplace=True)

        for col in df.columns:
            if col != 'AOI':
                df[col] = df[col].apply(lambda x: f"{x:.4f}" if isinstance(x, (int, float)) else x)

        self.save_analysis_results(df, 'AOIAnalysis.csv')
        return df

    def get_aoi_data(self, aoi):
        
        aoi_fixations = self.fixations[
            (self.fixations['start'] >= aoi.start_time) &
            (self.fixations['end'] <= (aoi.end_time if aoi.end_time else float('inf'))) &
            self.fixations.apply(lambda row: aoi.contains_point(row['x'], row['y'], row['start']), axis=1)
        ]
        
        pupil_sizes = []
        for _, fixation in aoi_fixations.iterrows():
            fixation_data = self.processed_data[
                (self.processed_data['Timestamp'] >= fixation['start']) &
                (self.processed_data['Timestamp'] <= fixation['end'])
            ]
            avg_pupil_size = fixation_data['Pupil'].mean()
            pupil_sizes.append(avg_pupil_size)
        
        aoi_fixations['Pupil'] = pupil_sizes
        
        return aoi_fixations

    def calculate_visit_count(self, aoi_data):
        
        return len(aoi_data.groupby((aoi_data['start'] - aoi_data['start'].shift() > 0.5).cumsum()))

    def calculate_total_visit_time(self, aoi_data):
        
        return aoi_data['duration'].sum()

    def calculate_average_visit_time(self, aoi_data):
        
        visits = aoi_data.groupby((aoi_data['start'] - aoi_data['start'].shift() > 0.5).cumsum())
        return visits['duration'].sum().mean() if len(visits) > 0 else 0

    def calculate_first_visit_time(self, aoi_data):
        
        return aoi_data['start'].min() if not aoi_data.empty else np.nan

    def calculate_revisit_count(self, aoi_data):
        
        return max(0, self.calculate_visit_count(aoi_data) - 1)

    def calculate_average_fixation_duration(self, aoi_data):
        
        return aoi_data['duration'].mean() if not aoi_data.empty else 0

    def calculate_total_fixation_duration(self, aoi_data):
        
        return aoi_data['duration'].sum()

    def calculate_dwell_time_percentage(self, aoi_data, aoi):
        
        total_time = aoi.end_time - aoi.start_time if aoi.end_time else self.fixations['end'].max() - aoi.start_time
        return (self.calculate_total_fixation_duration(aoi_data) / total_time) * 100 if total_time > 0 else 0

    def calculate_time_to_first_fixation(self, aoi_data, aoi):
        
        if not aoi_data.empty:
            return aoi_data['start'].min() - aoi.start_time
        return np.nan

    def calculate_average_pupil_size(self, aoi_data):
        
        return aoi_data['Pupil'].mean() if 'Pupil' in aoi_data.columns else np.nan
    
    def get_valid_pupil_data(self, pupil_data):
        
        valid_pupil = pupil_data.replace(0, np.nan).dropna()
        if len(valid_pupil) == 0:
            print("Warning: No Valid Pupil Data")
        return valid_pupil

    def check_pupil_validity(self, pupil_value, context=""):
        
        # if pupil_value < 2:
        # elif pupil_value > 8:
        if pupil_value < 2:
            print(f"Warning: Abnormally small pupil diameter detected in {context}: {pupil_value}mm")
        elif pupil_value > 8:
            print(f"Warning: Abnormally large pupil diameter detected in {context}: {pupil_value}mm")
        return 2 <= pupil_value <= 8

    def save_analysis_results(self, df, filename):
        
        output_path = os.path.join(self.analysis_output_dir, filename)
        df.to_csv(output_path, index=False, encoding='utf-8-sig', float_format='%.4f')
        print(f"Analysis Saved To: {output_path}")

    def print_analysis_summary(self, df):
        
        print("\n=== Analysis Results Summary ===")
        print(f"Number of TOIs analyzed: {len(df)}")
        print("\nStatistical information for each metric:")
        
        for column in df.columns:
            #     values = pd.to_numeric(df[column], errors='coerce')
            #     print(f"\n{column}:")
            if column not in ['TOI Name', 'Start Time', 'End Time', 'Saccade Direction']:
                values = pd.to_numeric(df[column], errors='coerce')
                print(f"\n{column}:")
                print(f"  Mean: {values.mean():.4f}")
                print(f"  Minimum: {values.min():.4f}")
                print(f"  Maximum: {values.max():.4f}")
                print(f"  Standard Deviation: {values.std():.4f}")

    def calculate_cosine_similarity(self, vectors):
        
        n = len(vectors)
        if n < 2:
            return 1.0  
            
        similarities = []
        for i in range(n):
            for j in range(i + 1, n):
                dot_product = np.dot(vectors[i], vectors[j])
                norm_i = np.linalg.norm(vectors[i])
                norm_j = np.linalg.norm(vectors[j])
                
                if norm_i > 0 and norm_j > 0:
                    similarity = dot_product / (norm_i * norm_j)
                    similarities.append(similarity)
        
        return np.mean(similarities) if similarities else 0.0

    def cluster_analysis(self, data_type='fixations', algorithm='kmeans', toi_name=None):
        
        if data_type == 'fixations':
            data = self.get_fixations(toi_name)
            if len(data) < 2:
                raise ValueError(f"Selected fixation data contains less than 2 samples for TOI: {toi_name}")
            X = data[['x', 'y']].values
        elif data_type == 'saccades':
            data = self.get_saccades(toi_name)
            if len(data) < 2:
                raise ValueError(f"Selected saccade data contains less than 2 samples for TOI: {toi_name}")
            data['direction'] = np.arctan2(data['y_end'] - data['y_start'], 
                                        data['x_end'] - data['x_start'])
            data['direction_deg'] = np.degrees(data['direction'])
            X = data[['direction_deg', 'amplitude']].values
        else:
            raise ValueError("data_type must be 'fixations' or 'saccades'")

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        if algorithm == 'kmeans':
            n_clusters = max(2, self.determine_optimal_k(X_scaled))
            clusterer = KMeans(n_clusters=n_clusters, random_state=42)
        elif algorithm == 'dbscan':
            eps, min_samples = self.determine_dbscan_params(X_scaled)
            clusterer = DBSCAN(eps=eps, min_samples=min_samples)
            labels = clusterer.fit_predict(X_scaled)
            if len(np.unique(labels[labels != -1])) < 2:
                print("DBSCAN produced less than 2 clusters, switching to K-means with k=2")
                clusterer = KMeans(n_clusters=2, random_state=42)
        else:
            raise ValueError("algorithm must be 'kmeans' or 'dbscan'")

        labels = clusterer.fit_predict(X_scaled)
        data['cluster'] = labels

        if data_type == 'fixations':
            pupil_data = []
            for idx, row in data.iterrows():
                mask = ((self.processed_data['Timestamp'] >= row['start']) & 
                    (self.processed_data['Timestamp'] <= row['end']))
                mean_pupil = self.processed_data.loc[mask, 'Pupil'].mean()
                pupil_data.append(mean_pupil)
            data['mean_pupil'] = pupil_data

        cluster_stats = []
        for cluster in np.unique(labels):
            if cluster == -1 and algorithm == 'dbscan':  
                continue
                
            cluster_data = data[data['cluster'] == cluster]
            
            # stats = {
            # }
            stats = {
                'Cluster': cluster,
                'Sample Count': len(cluster_data),
                'Average Duration': cluster_data['duration'].mean(),
                'Total Duration': cluster_data['duration'].sum()
            }
            
            if data_type == 'fixations':
                # stats.update({
                # })
                stats.update({
                    'Mean X Coordinate': cluster_data['x'].mean(),
                    'Mean Y Coordinate': cluster_data['y'].mean(),
                    'X Coordinate Standard Deviation': cluster_data['x'].std(),
                    'Y Coordinate Standard Deviation': cluster_data['y'].std(),
                    'Mean Pupil Size': cluster_data['mean_pupil'].mean()
                })
            elif data_type == 'saccades':
                vectors = np.column_stack([
                    cluster_data['x_end'] - cluster_data['x_start'],
                    cluster_data['y_end'] - cluster_data['y_start']
                ])
                
                # stats.update({
                # })
                stats.update({
                    'Mean Direction (°)': cluster_data['direction_deg'].mean(),
                    'Direction Standard Deviation': cluster_data['direction_deg'].std(),
                    'Mean Amplitude (°)': cluster_data['amplitude'].mean(),
                    'Amplitude Standard Deviation': cluster_data['amplitude'].std(),
                    'Mean Velocity (°/s)': cluster_data['amplitude'].mean() / cluster_data['duration'].mean(),
                    'Mean Cosine Similarity': self.calculate_cosine_similarity(vectors)
                })

            cluster_stats.append(stats)

        results_df = pd.DataFrame(cluster_stats)

        toi_suffix = f"_{toi_name}" if toi_name else ""
        output_filename = f"{data_type}_{algorithm}{toi_suffix}_cluster_analysis.csv"
        output_path = os.path.join(self.analysis_output_dir, output_filename)
        results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"Cluster analysis results have been saved to: {output_path}")

        aspect_ratio = self.resolution[0] / self.resolution[1]
        fig_width = 10
        fig_height = fig_width / aspect_ratio
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        
        if data_type == 'fixations':
            scatter = ax.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', alpha=0.7)
            ax.set_xlabel('X coordinate')
            ax.set_ylabel('Y coordinate')
            ax.set_xlim(0, 1)
            ax.set_ylim(1, 0)
        elif data_type == 'saccades':
            scatter = ax.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', alpha=0.7)
            ax.set_xlabel('Direction (degrees)')
            ax.set_ylabel('Amplitude')

        title_map = {'fixations': 'Fixation', 'saccades': 'Saccade'}
        algo_map = {'kmeans': 'K-means', 'dbscan': 'DBSCAN'}
        title = f'{title_map[data_type]} {algo_map[algorithm]} Clustering'
        if toi_name:
            title += f'\nTOI: {toi_name}'
        ax.set_title(title)
        plt.colorbar(scatter, label='Cluster')

        plt.tight_layout()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        fig_filename = f"{data_type}_{algorithm}{toi_suffix}_cluster_visualization.png"
        fig_path = os.path.join(self.vis_output_dir, fig_filename)
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"Cluster Visualization Saved To: {fig_path}")

        return results_df, fig

    def determine_optimal_k(self, X):
        
        max_k = min(10, len(X) - 1)  
        distortions = []
        for k in range(1, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42)
            kmeans.fit(X)
            distortions.append(kmeans.inertia_)
        
        diffs = np.diff(distortions)
        elbow_point = np.argmin(diffs) + 1
        return elbow_point + 1  

    def determine_dbscan_params(self, X):
        
        distances = pdist(X)
        eps = np.percentile(distances, 10)  

        min_samples = max(3, int(np.log(len(X))))

        return eps, min_samples
    
    def draw_fixations(self, toi_name=None, durationsize=True, durationcolour=True, alpha=0.5, use_background=False):
        fixations = self.get_fixations(toi_name)
        
        aspect_ratio = self.resolution[0] / self.resolution[1]
        fig_width = 10  
        fig_height = fig_width / aspect_ratio
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        
        if use_background and self.video_path:
            background = self.get_video_frame(toi_name)
            if background is not None:
                ax.imshow(background, extent=[0, 1, 1, 0], aspect='auto')
        
        x = np.clip(fixations['x'], 0, 1)
        y = np.clip(fixations['y'], 0, 1)

        ax.xaxis.set_ticks_position('top')  
        ax.xaxis.set_label_position('top')  
        
        if durationsize:
            siz = fixations['duration'] * 50  
            siz = np.clip(siz, 20, 500)  
        else:
            siz = 100  
        
        if durationcolour:
            col = fixations['duration']
            norm = plt.Normalize(col.min(), col.max())
        else:
            col = 'r'
            norm = None
        
        scatter = ax.scatter(x, y, s=siz, c=col, marker='o', cmap='jet', alpha=alpha, edgecolors='none', norm=norm)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)  
        
        if durationcolour:
            cbar = plt.colorbar(scatter)
            cbar.set_label('Fixation duration (seconds)')
        
        ax.set_title("Focus on scatter plot")
        
        plt.tight_layout()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
        return fig

    def get_video_frame(self, toi_name=None):
        if not self.video_path:
            return None
        
        cap = cv2.VideoCapture(self.video_path)
        
        if toi_name:
            toi = next((event for event in self.events if event[3] == toi_name), None)
            if toi:
                start_time = toi[0]
                cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)  
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame
        else:
            return None

    def draw_heatmap(self, toi_name=None, durationweight=True, alpha=0.5, use_background=False):
        fixations = self.get_fixations(toi_name)
        
        aspect_ratio = self.resolution[0] / self.resolution[1]
        fig_width = 10  
        fig_height = fig_width / aspect_ratio
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        if use_background and self.video_path:
            background = self.get_video_frame(toi_name)
            if background is not None:
                ax.imshow(background, extent=[0, 1, 1, 0], aspect='auto')

        heatmap = self.create_heatmap(fixations, durationweight)
        im = ax.imshow(heatmap, cmap='jet', alpha=alpha, extent=[0, 1, 1, 0], aspect='auto')

        ax.xaxis.set_ticks_position('top')  
        ax.xaxis.set_label_position('top')  

        cbar = plt.colorbar(im)
        cbar.set_label('Fixations intensity')

        ax.set_title("Heatmap")

        plt.tight_layout()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        return fig
    
    def plot_statistics(self, toi_name=None):
        
        if toi_name:
            toi = next((event for event in self.events if event[3] == toi_name), None)
            if toi:
                start_time, end_time = toi[0], toi[1]
                saccade_velocities = self.saccade_velocities[
                    (self.saccade_velocities['start_time'] >= start_time) & 
                    (self.saccade_velocities['start_time'] <= end_time)
                ]
                fixations = self.fixations[
                    (self.fixations['start'] >= start_time) & 
                    (self.fixations['end'] <= end_time)
                ]
            else:
                raise ValueError(f"Can't Find TOI Named {toi_name}")
        else:
            saccade_velocities = self.saccade_velocities
            fixations = self.fixations

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        fig.subplots_adjust(hspace=0.4)

        velocities = saccade_velocities['mean_velocity'].values
        if len(velocities) > 0:
            v_min, v_max = np.floor(velocities.min()), np.ceil(velocities.max())
            bin_width = 20  
            n_bins = min(int((v_max - v_min) / bin_width) + 1, 20)
            velocity_bins = np.linspace(v_min, v_max, n_bins + 1)
            
            counts1, bins1, patches1 = ax1.hist(velocities, bins=velocity_bins,
                                            color='skyblue', edgecolor='black')
            
            ax1.set_xticks(velocity_bins)
            ax1.set_xticklabels([f'{int(b)}' for b in velocity_bins], rotation=45)
            
            v_stats = (f'Mean: {np.mean(velocities):.1f}°/s\n'
                    f'Std: {np.std(velocities):.1f}°/s\n'
                    f'N: {len(velocities)}')
            ax1.text(0.95, 0.95, v_stats,
                    transform=ax1.transAxes,
                    verticalalignment='top',
                    horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax1.set_xlabel('Saccade Velocity [deg/s]')
        ax1.set_ylabel('Cases')
        ax1.set_title('Saccades: Velocity Distribution')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        durations = fixations['duration'].values * 1000  
        if len(durations) > 0:
            d_min, d_max = np.floor(durations.min()), np.ceil(durations.max())
            bin_width = 50  
            n_bins = min(int((d_max - d_min) / bin_width) + 1, 20)
            duration_bins = np.linspace(d_min, d_max, n_bins + 1)
            
            counts2, bins2, patches2 = ax2.hist(durations, bins=duration_bins,
                                            color='lightgreen', edgecolor='black')
            
            ax2.set_xticks(duration_bins)
            ax2.set_xticklabels([f'{int(b)}' for b in duration_bins], rotation=45)
            
            d_stats = (f'Mean: {np.mean(durations):.1f}ms\n'
                    f'Std: {np.std(durations):.1f}ms\n'
                    f'N: {len(durations)}')
            ax2.text(0.95, 0.95, d_stats,
                    transform=ax2.transAxes,
                    verticalalignment='top',
                    horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax2.set_xlabel('Fixation Duration [ms]')
        ax2.set_ylabel('Cases')
        ax2.set_title('Fixations: Duration Distribution')
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        if toi_name:
            fig.suptitle(f'Statistics for TOI: {toi_name}')

        plt.tight_layout()

        toi_suffix = f"_{toi_name}" if toi_name else ""
        fig_filename = f"statistics{toi_suffix}.png"
        fig_path = os.path.join(self.vis_output_dir, fig_filename)
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"Statistic Figure Saved To: {fig_path}")

        return fig
    
    def create_heatmap(self, fixations, durationweight=True):
        heatmap_resolution = (300, 300)  
        heatmap = np.zeros(heatmap_resolution)
        
        for x, y, duration in zip(fixations['x'], fixations['y'], fixations['duration']):
            heatmap_x = int(x * (heatmap_resolution[1] - 1))
            heatmap_y = int((1 - y) * (heatmap_resolution[0] - 1))
            
            if 0 <= heatmap_x < heatmap_resolution[1] and 0 <= heatmap_y < heatmap_resolution[0]:
                if durationweight:
                    heatmap[heatmap_y, heatmap_x] += duration
                else:
                    heatmap[heatmap_y, heatmap_x] += 1

        heatmap = self.gaussian_filter(heatmap, sigma=2)
        
        heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min() + 1e-8)

        return heatmap

    def gaussian_filter(self, heatmap, sigma=30):
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(heatmap, sigma=sigma)
    

    def draw_scanpath(self, toi_name=None, alpha=0.8, use_background=False):
        
        import matplotlib.patheffects as path_effects

        saccades = self.get_saccades(toi_name)
        if len(saccades) == 0:
            print("No saccades found for visualization")
            return None

        aspect_ratio = self.resolution[0] / self.resolution[1]
        fig_width = 10
        fig_height = fig_width / aspect_ratio
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        if use_background and self.video_path:
            background = self.get_video_frame(toi_name)
            if background is not None:
                ax.imshow(background, extent=[0, 1, 1, 0], aspect='auto')

        n_saccades = len(saccades)
        cmap = plt.cm.viridis  
        colors = [cmap(i / max(1, n_saccades - 1)) for i in range(n_saccades)]

        marker_size = 100  

        all_points_x = []
        all_points_y = []
        all_colors = []
        all_sizes = []

        for i, saccade in enumerate(saccades.itertuples()):
            color = colors[i]
            start_x, start_y = saccade.x_start, saccade.y_start
            end_x, end_y = saccade.x_end, saccade.y_end
            
            all_points_x.extend([start_x, end_x])
            all_points_y.extend([start_y, end_y])
            all_colors.extend([color, color])
            all_sizes.extend([marker_size, marker_size])

        scatter = ax.scatter(all_points_x, all_points_y,
                            s=all_sizes,
                            c=all_colors,
                            marker='o',
                            alpha=alpha,
                            edgecolor='white',
                            linewidth=1,
                            zorder=2)

        arrow_style = dict(
            head_width=0.02,
            head_length=0.03,
            width=0.005,
            alpha=alpha,
            length_includes_head=True,
            zorder=3  
        )

        for i, saccade in enumerate(saccades.itertuples()):
            color = colors[i]
            start_x, start_y = saccade.x_start, saccade.y_start
            end_x, end_y = saccade.x_end, saccade.y_end
            
            dx = end_x - start_x
            dy = end_y - start_y
            arrow_length = np.sqrt(dx**2 + dy**2)

            local_style = arrow_style.copy()
            local_style['head_width'] = max(0.01, arrow_length * 0.15)
            local_style['head_length'] = max(0.015, arrow_length * 0.2)
            
            ax.arrow(start_x, start_y, dx, dy,
                    color='white',
                    width=local_style['width'] * 2,
                    head_width=local_style['head_width'] * 1.2,
                    head_length=local_style['head_length'] * 1.2,
                    alpha=alpha * 0.8,
                    length_includes_head=True,
                    zorder=2)
            
            ax.arrow(start_x, start_y, dx, dy,
                    color=color,
                    **local_style)

        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)

        ax.xaxis.set_ticks_position('top')  
        ax.xaxis.set_label_position('top')  
        title = "Scanpath Analysis"
        if toi_name:
            title += f" - TOI: {toi_name}"
        if len(saccades) > 0:
            title += f"\nTotal {len(saccades)} saccades"
        ax.set_title(title)

        ax.set_xticks([])
        ax.set_yticks([])

        norm = plt.Normalize(0, n_saccades - 1)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm)
        cbar.set_ticks([0, n_saccades - 1])
        cbar.set_ticklabels(['Start', 'End'])
        cbar.set_label('Saccade Sequence')

        plt.tight_layout()

        toi_suffix = f"_{toi_name}" if toi_name else ""
        background_suffix = "_with_background" if use_background else ""
        fig_filename = f"scanpath{toi_suffix}{background_suffix}.png"
        fig_path = os.path.join(self.vis_output_dir, fig_filename)
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"Scanpath Saved To: {fig_path}")

        return fig
    
    def plot_numbered_scanpath(self, toi_name=None, use_background=False):
        
        fixations = self.get_fixations(toi_name)
        
        aspect_ratio = self.resolution[0] / self.resolution[1]
        fig_width = 10
        fig_height = fig_width / aspect_ratio
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        if use_background and self.video_path:
            background = self.get_video_frame(toi_name)
            if background is not None:
                ax.imshow(background, extent=[0, 1, 1, 0], aspect='auto')

        x = fixations['x'].values
        y = fixations['y'].values
        durations = fixations['duration'].values

        sizes = np.clip(durations * 1000, 200, 2000)  
        
        for i in range(len(x)-1):
            ax.plot([x[i], x[i+1]], [y[i], y[i+1]], 
                    color='yellow', alpha=0.5, linewidth=1,
                    zorder=1)  

        scatter = ax.scatter(x, y, s=sizes, 
                            color='white',      
                            edgecolor='black',  
                            alpha=0.7,
                            zorder=2)           

        for i in range(len(x)):
            ax.text(x[i], y[i], str(i+1),
                    horizontalalignment='center',
                    verticalalignment='center',
                    color='black',
                    fontweight='bold',
                    fontsize=8,
                    zorder=3)  

        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)  

        ax.xaxis.set_ticks_position('top')  
        ax.xaxis.set_label_position('top')  

        if toi_name:
            ax.set_title(f"Gaze Scanpath - TOI: {toi_name}")
        else:
            ax.set_title("Gaze Scanpath - All Data")

        ax.set_xticks([])
        ax.set_yticks([])

        legend_elements = [
            plt.scatter([], [], s=300, c='white', edgecolor='black', alpha=0.7,
                    label='Fixation'),
            plt.Line2D([0], [0], color='yellow', alpha=0.5, label='Saccade')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()

        toi_suffix = f"_{toi_name}" if toi_name else ""
        background_suffix = "_with_background" if use_background else ""
        fig_filename = f"numbered_scanpath{toi_suffix}{background_suffix}.png"
        fig_path = os.path.join(self.vis_output_dir, fig_filename)
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"Numbered Scanpath Saved To: {fig_path}")

        return fig

    def plot_temporal_series(self, toi_name=None):
        
        if toi_name:
            toi = next((event for event in self.events if event[3] == toi_name), None)
            if toi:
                start_time = toi[0]
                end_time = toi[1]
                mask = (self.processed_data['Timestamp'] >= start_time) & \
                    (self.processed_data['Timestamp'] <= end_time)
                data = self.processed_data[mask].copy()
            else:
                raise ValueError(f"TOI {toi_name} not found")
        else:
            data = self.processed_data.copy()
            start_time = data['Timestamp'].iloc[0]
            end_time = data['Timestamp'].iloc[-1]

        fig = plt.figure(figsize=(12, 9))
        
        gs = fig.add_gridspec(4, 1, top=0.85)  
        gs.update(hspace=0.3)

        time_series = data['Timestamp'] - start_time

        # 1. Gaze X position
        ax1 = fig.add_subplot(gs[0])
        ax1.plot(time_series, data['GazePointX'], 'b-', linewidth=1)
        ax1.set_ylabel('Gaze X\n(screen ratio)')
        ax1.set_ylim(-0.1, 1.1)
        ax1.grid(True, alpha=0.3)

        # 2. Gaze Y position
        ax2 = fig.add_subplot(gs[1])
        ax2.plot(time_series, data['GazePointY'], 'g-', linewidth=1)
        ax2.set_ylabel('Gaze Y\n(screen ratio)')
        ax2.set_ylim(-0.1, 1.1)
        ax2.grid(True, alpha=0.3)

        # 3. Gaze velocity
        ax3 = fig.add_subplot(gs[2])
        ax3.plot(time_series, data['Velocity'], 'r-', linewidth=1)
        ax3.set_ylabel('Velocity\n(deg/s)')
        ax3.grid(True, alpha=0.3)

        # 4. Pupil size
        ax4 = fig.add_subplot(gs[3])
        ax4.plot(time_series, data['Pupil'], 'k-', linewidth=1)
        ax4.set_ylabel('Pupil Size\n(mm)')
        ax4.set_xlabel('Time (s)')
        ax4.grid(True, alpha=0.3)

        axes = [ax1, ax2, ax3, ax4]
        
        legend_patches = []
        
        if hasattr(self, 'fixations') and len(self.fixations) > 0:
            fixations = self.get_fixations(toi_name)
            for _, fix in fixations.iterrows():
                for ax in axes:
                    ax.axvspan(fix['start'] - start_time, fix['end'] - start_time, 
                            color='green', alpha=0.2)
            legend_patches.append(plt.Rectangle((0, 0), 1, 1, facecolor='green', alpha=0.2, label='Fixation'))

        if hasattr(self, 'saccades') and len(self.saccades) > 0:
            saccades = self.get_saccades(toi_name)
            for _, sac in saccades.iterrows():
                for ax in axes:
                    ax.axvspan(sac['start'] - start_time, sac['end'] - start_time, 
                            color='red', alpha=0.2)
            legend_patches.append(plt.Rectangle((0, 0), 1, 1, facecolor='red', alpha=0.2, label='Saccade'))

        if hasattr(self, 'blinks') and len(self.blinks) > 0:
            blinks = self.get_toi_events(self.blinks, start_time, end_time)
            for _, blink in blinks.iterrows():
                for ax in axes:
                    ax.axvspan(blink['start'] - start_time, blink['end'] - start_time, 
                            color='blue', alpha=0.2)
            legend_patches.append(plt.Rectangle((0, 0), 1, 1, facecolor='blue', alpha=0.2, label='Blink'))

        if legend_patches:
            fig.legend(handles=legend_patches, 
                    loc='upper center',   
                    ncol=3,              
                    bbox_to_anchor=(0.5, 0.98),  
                    frameon=True,        
                    fancybox=True,       
                    shadow=True)         

        for ax in axes[:-1]:
            ax.set_xticklabels([])

        if toi_name:
            fig.suptitle(f'Temporal Series - TOI: {toi_name}', y=1.02)
        else:
            fig.suptitle('Temporal Series - All Data', y=1.02)

        plt.tight_layout()

        toi_suffix = f"_{toi_name}" if toi_name else ""
        fig_filename = f"temporal_series{toi_suffix}.png"
        fig_path = os.path.join(self.vis_output_dir, fig_filename)
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"Temporal Series: {fig_path}")

        return fig

    def get_fixations(self, toi_name=None):
        if toi_name:
            toi = next((event for event in self.events if event[3] == toi_name), None)
            if not toi:
                raise ValueError(f"Can't Find TOI Named {toi_name}")
            start_time, end_time = toi[0], toi[1]
            fixations = self.fixations[(self.fixations['start'] >= start_time) & (self.fixations['end'] <= end_time)]
        else:
            fixations = self.fixations
        return fixations

    def get_saccades(self, toi_name=None):
        if toi_name:
            toi = next((event for event in self.events if event[3] == toi_name), None)
            if not toi:
                raise ValueError(f"Can't Find TOI Named {toi_name}")
            start_time, end_time = toi[0], toi[1]
            saccades = self.saccades[(self.saccades['start'] >= start_time) & (self.saccades['end'] <= end_time)]
        else:
            saccades = self.saccades
        return saccades

    def draw_gaze_scatter(self, toi_name=None, alpha=0.5, use_background=False):
        gaze_data = self.get_gaze_data(toi_name)
        
        aspect_ratio = self.resolution[0] / self.resolution[1]
        fig_width = 10  
        fig_height = fig_width / aspect_ratio
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        if use_background and self.video_path:
            background = self.get_video_frame(toi_name)
            if background is not None:
                ax.imshow(background, extent=[0, 1, 1, 0], aspect='auto')

        scatter = ax.scatter(gaze_data['GazePointX'], gaze_data['GazePointY'], 
                             s=1,  
                             c=gaze_data['Timestamp'],  
                             cmap='viridis', 
                             alpha=alpha)

        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)  

        ax.xaxis.set_ticks_position('top')  
        ax.xaxis.set_label_position('top')  

        cbar = plt.colorbar(scatter)
        cbar.set_label('Time (seconds)')

        ax.set_title("Gaze scatter plot")

        plt.tight_layout()
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        return fig
    
    def get_gaze_data(self, toi_name=None):
        if toi_name:
            toi = next((event for event in self.events if event[3] == toi_name), None)
            if toi:
                start_time, end_time = toi[0], toi[1]
                return self.processed_data[(self.processed_data['Timestamp'] >= start_time) & 
                                      (self.processed_data['Timestamp'] <= end_time)]
        return self.processed_data
    
