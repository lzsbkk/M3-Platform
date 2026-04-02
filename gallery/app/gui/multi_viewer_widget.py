# multi_viewer_widget.py

from PyQt5.QtWidgets import QWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QSplitter, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from qfluentwidgets import (SmoothScrollArea, PrimaryToolButton, FluentIcon, 
                            ToolTipFilter, ToolTipPosition, CardWidget, LineEdit,
                            StrongBodyLabel, BodyLabel, CheckBox, TreeWidget)
from .multi_channel_list_widget import MultiChannelListWidget
from .timeline_widget import TimelineWidget
from .multi_eyetracking_list_widget import MultiETChannelListWidget
import random
import hashlib
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ChannelTreeWidget(TreeWidget):
    visibility_changed = pyqtSignal(int, int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.itemChanged.connect(self.on_item_changed)

    def build_tree(self, channel_tree):
        self.clear()
        for data_item in channel_tree:
            data_tree_item = QTreeWidgetItem(self)
            data_tree_item.setText(0, data_item['name'])
            data_tree_item.setData(0, Qt.UserRole, data_item)
            for channel_item in data_item['children']:
                channel_tree_item = QTreeWidgetItem(data_tree_item)
                channel_tree_item.setText(0, channel_item['name'])
                channel_tree_item.setData(0, Qt.UserRole, channel_item)
                channel_tree_item.setCheckState(0, Qt.Checked if channel_item['visible'] else Qt.Unchecked)

    def on_item_changed(self, item, column):
        if column == 0:
            item_data = item.data(0, Qt.UserRole)
            if item_data and item_data['type'] == 'channel':
                data_index, channel_index = item_data['id']
                visible = item.checkState(0) == Qt.Checked
                self.visibility_changed.emit(data_index, channel_index, visible)

class MultiViewerWidget(QWidget):
    def __init__(self, multi_data, experiment, subject_name, parent=None):
        super().__init__(parent)
        self.multi_data = multi_data
        self.experiment = experiment
        self.subject_name = subject_name
        self.channel_list = None
        self.channel_tree = None
        self.timeline = None
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Create scroll area for channel list
        scroll_area = SmoothScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.enableTransparentBackground()
        
        # Create channel list widget based on data type
        self.channel_list = MultiChannelListWidget(self.multi_data)
        scroll_area.setWidget(self.channel_list)
        
        # Create timeline widget
        self.timeline = TimelineWidget(self.multi_data)

        # Left column
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        
        # Add experiment info
        self.setup_experiment_info(left_layout)
        
        # Create channel tree widget
        self.channel_tree = ChannelTreeWidget()
        self.channel_tree.visibility_changed.connect(self.on_channel_visibility_changed)
        self.channel_tree.build_tree(self.multi_data.get_channel_tree())
        left_layout.addWidget(self.channel_tree)
        
        # Right column
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        
        right_layout.addWidget(scroll_area)
        right_layout.addWidget(self.timeline)
        
        # Create a splitter to allow resizing
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_column)
        splitter.addWidget(right_column)
        splitter.setSizes([self.width() // 5, self.width() * 4 // 5])  # Set initial sizes
        
        main_layout.addWidget(splitter)
        
        # Connect signals
        if self.timeline and self.channel_list:
            self.timeline.time_range_changed.connect(self.channel_list.update_time_range)
            self.channel_list.time_range_changed.connect(self.timeline.update_time_range_from_plot)

    def setup_experiment_info(self, layout):
        info_card = CardWidget(self)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(15, 15, 15, 15)

        experiment_label = BodyLabel(f"Experiment Name: {self.experiment}", self)
        name_label = BodyLabel(f"Participant Name: {self.subject_name}", self)

        info_layout.addWidget(experiment_label)
        info_layout.addWidget(name_label)

        layout.addWidget(info_card)

    def on_channel_visibility_changed(self, data_index, channel_index, visible):
        try:
            self.multi_data.set_channel_visibility(data_index, channel_index, visible)
            if self.channel_list:
                self.channel_list.update_channel_visibility(data_index, channel_index, visible)
            else:
                logger.warning("channel_list is not initialized")
        except Exception as e:
            logger.error(f"Error in on_channel_visibility_changed: {str(e)}")

    def set_random_seed(self):
        try:
            seed_string = "_".join([f"{data.num_channels}_{data.sample_rate}" for data in self.multi_data.data_list if data is not None])
            seed = int(hashlib.sha256(seed_string.encode()).hexdigest(), 16) % (2**32)
            random.seed(seed)
        except Exception as e:
            logger.error(f"Error in set_random_seed: {str(e)}")

    def generate_random_color(self):
        while True:
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if 100 < brightness < 200:
                return QColor(r, g, b)

    def delete_event(self, event):
        try:
            self.channel_list.delete_event(event)
            self.timeline.delete_event(event)
        except Exception as e:
            logger.error(f"Error in delete_event: {str(e)}")

    def clear_events(self):
        try:
            self.channel_list.clear_events()
            self.timeline.clear_events()
        except Exception as e:
            logger.error(f"Error in clear_events: {str(e)}")

    def load_events_from_data(self):
        try:
            self.set_random_seed()
            events = self.multi_data.get_events()
            for event in events:
                self.add_event(event)
        except Exception as e:
            logger.error(f"Error in load_events_from_data: {str(e)}")

    def update_data(self, new_multi_data):
        try:
            self.multi_data = new_multi_data
            self.channel_tree.build_tree(self.multi_data.get_channel_tree())
            self.channel_list.update_data(new_multi_data)
            self.timeline.update_data(new_multi_data)
            self.clear_events()
            self.load_events_from_data()
        except Exception as e:
            logger.error(f"Error in update_data: {str(e)}")