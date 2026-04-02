# multi_data.py

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class MultiData:
    def __init__(self, data_list, data_names):
        if len(data_list) != len(data_names):
            raise ValueError("The number of data names must match the number of data objects")
        self.data_list = data_list
        self.data_names = data_names
        self.update_global_properties()
        self.channel_visibility = self.initialize_channel_visibility()

    def update_global_properties(self):
        valid_data = [data for data in self.data_list if data is not None]
        if valid_data:
            try:
                self.global_start_time = min(self.get_start_time(data) for data in valid_data)
                self.global_end_time = max(self.get_end_time(data) for data in valid_data)
                self.global_duration = max(0, self.global_end_time - self.global_start_time)
                self.duration = self.global_duration
                self.num_channels = sum(self.get_data_channels(data) for data in self.data_list if data is not None)
            except Exception as e:
                logger.error(f"Error updating global properties: {str(e)}")
                self.reset_global_properties()
        else:
            self.reset_global_properties()

    def reset_global_properties(self):
        self.global_start_time = 0
        self.global_end_time = 0
        self.global_duration = 0
        self.duration = 0
        self.num_channels = 0

    def get_start_time(self, data):
        if data is None:
            return 0
        try:
            if hasattr(data, 'get_start_time'):
                return data.get_start_time()
            elif hasattr(data, 'processed_data') and 'Timestamp' in data.processed_data.columns:
                return data.processed_data['Timestamp'].min()
            else:
                return 0
        except Exception as e:
            logger.warning(f"Error getting start time: {str(e)}")
            return 0

    def get_end_time(self, data):
        if data is None:
            return 0
        try:
            if hasattr(data, 'get_start_time') and hasattr(data, 'duration'):
                return data.get_start_time() + data.duration
            elif hasattr(data, 'processed_data') and 'Timestamp' in data.processed_data.columns:
                return data.processed_data['Timestamp'].max()
            else:
                return 0
        except Exception as e:
            logger.warning(f"Error getting end time: {str(e)}")
            return 0

    def get_data_channels(self, data):
        if data is None:
            return 0
        try:
            if hasattr(data, 'data_type') and data.data_type == 'et':
                return 7  
            elif hasattr(data, 'num_channels'):
                return data.num_channels
            else:
                return 0
        except Exception as e:
            logger.warning(f"Error getting data channels: {str(e)}")
            return 0

    def initialize_channel_visibility(self):
        visibility = {}
        for i, data in enumerate(self.data_list):
            if data is not None:
                try:
                    if hasattr(data, 'data_type') and data.data_type == 'et':
                        visibility[i] = {j: False for j in range(7)}  
                    elif hasattr(data, 'num_channels'):
                        visibility[i] = {j: False for j in range(data.num_channels)}
                    else:
                        visibility[i] = {}
                except Exception as e:
                    logger.warning(f"Error initializing channel visibility for data {i}: {str(e)}")
                    visibility[i] = {}
            else:
                visibility[i] = {}
        return visibility

    def get_channel_tree(self):
        tree = []
        for i, (data, name) in enumerate(zip(self.data_list, self.data_names)):
            data_item = {
                'name': name,
                'type': 'data',
                'id': i,
                'children': []
            }
            if data is not None:
                try:
                    if hasattr(data, 'data_type') and data.data_type == 'et':
                        # et_data_types = [
                        # ]
                        et_data_types = [
                            ("Fixation", "Fixation Event"),
                            ("Saccade", "Saccade Event"),
                            ("Blink", "Blink Event"),
                            ("GazePointX", "Gaze Point X"),
                            ("GazePointY", "Gaze Point Y"),
                            ("Velocity", "Velocity (°/s)"),
                            ("Pupil", "Pupil Size (mm)")
                        ]
                        for j, (data_type, display_name) in enumerate(et_data_types):
                            channel_item = {
                                'name': display_name,
                                'type': 'channel',
                                'id': (i, j),
                                'visible': self.channel_visibility[i].get(j, False),
                                'data_type': data_type
                            }
                            data_item['children'].append(channel_item)
                    elif hasattr(data, 'get_channel_names') and hasattr(data, 'num_channels'):
                        for j in range(data.num_channels):
                            channel_item = {
                                'name': data.get_channel_names()[j],
                                'type': 'channel',
                                'id': (i, j),
                                'visible': self.channel_visibility[i].get(j, False)
                            }
                            data_item['children'].append(channel_item)
                except Exception as e:
                    logger.warning(f"Error creating channel tree for data {i}: {str(e)}")
            tree.append(data_item)
        return tree

    def set_channel_visibility(self, data_index, channel_index, visible):
        try:
            if data_index in self.channel_visibility and channel_index in self.channel_visibility[data_index]:
                self.channel_visibility[data_index][channel_index] = visible
        except Exception as e:
            logger.warning(f"Error setting channel visibility: {str(e)}")

    def get_data_name(self, data_index):
        try:
            return self.data_names[data_index]
        except IndexError:
            logger.warning(f"Data index {data_index} out of range")
            return f"Unknown Data {data_index}"

    def get_visible_channels(self):
        visible_channels = []
        for i, data in enumerate(self.data_list):
            if data is not None:
                try:
                    for j in range(self.get_data_channels(data)):
                        if self.channel_visibility[i].get(j, False):
                            visible_channels.append((i, j))
                except Exception as e:
                    logger.warning(f"Error getting visible channels for data {i}: {str(e)}")
        return visible_channels

    def get_data_at_time(self, time):
        data_points = []
        for i, data in enumerate(self.data_list):
            if data is None:
                continue
            try:
                if hasattr(data, 'data_type') and data.data_type == 'et':
                    et_data = data.processed_data
                    if self.get_start_time(data) <= time < self.get_end_time(data):
                        index = (et_data['Timestamp'] - time).abs().idxmin()
                        for j, col in enumerate(['Fixation', 'Saccade', 'Blink', 'GazePointX', 'GazePointY', 'Velocity', 'Pupil']):
                            if self.channel_visibility[i].get(j, False):
                                if col in ['Fixation', 'Saccade', 'Blink']:
                                    value = 1 if data.get_value_at_time(time, col) else 0
                                else:
                                    value = et_data.loc[index, col]
                                data_points.append((i, j, value))
                else:
                    if self.get_start_time(data) <= time < self.get_end_time(data):
                        index = int((time - self.get_start_time(data)) * data.sample_rate)
                        for j in range(data.num_channels):
                            if self.channel_visibility[i].get(j, False):
                                data_points.append((i, j, data.data[j, index]))
            except Exception as e:
                logger.warning(f"Error getting data at time {time} for data {i}: {str(e)}")
        return data_points

    def get_events(self):
        all_events = []
        for i, data in enumerate(self.data_list):
            if data is None:
                continue
            try:
                events = data.get_events()
                for event in events:
                    all_events.append((i,) + event)  # Add data index to each event
            except Exception as e:
                logger.warning(f"Error getting events for data {i}: {str(e)}")
        return all_events