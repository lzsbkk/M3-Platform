from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import SmoothScrollArea
from .eyetracking_list_widget import EyeTrackingChannelListWidget
from .et_timeline_widget import TimelineWidget

class EyeTrackingViewerWidget(QWidget):
    current_time_changed = pyqtSignal(float)  

    def __init__(self, et_data, parent=None):
        super().__init__(parent)
        self.et_data = et_data
        self.custom_events = []  
        self.current_time = 0  
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create scroll area
        scroll_area = SmoothScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.enableTransparentBackground()
        layout.addWidget(scroll_area, 1)

        # Create channel list window
        self.channel_list = EyeTrackingChannelListWidget(self.et_data)
        scroll_area.setWidget(self.channel_list)

        # Add a spacer
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Create timeline
        self.timeline = TimelineWidget(self.et_data)
        layout.addWidget(self.timeline)

        self.setLayout(layout)

        # Connect signals
        self.timeline.time_range_changed.connect(self.channel_list.update_time_range)
        self.channel_list.time_range_changed.connect(self.timeline.update_time_range_from_plot)

    def set_current_time(self, time):
        
        self.current_time = time
        self.channel_list.set_current_time(time)
        self.timeline.set_current_time(time)
        self.current_time_changed.emit(time)
        self.update()

    def set_time_range(self, start_time, end_time):
        
        self.timeline.set_time_range(start_time, end_time)
        self.channel_list.update_time_range(start_time, end_time - start_time)

    def update_data(self, new_et_data):
        
        self.et_data = new_et_data
        self.channel_list.update_data(new_et_data)
        self.timeline.update_data(new_et_data)

    def load_events(self):
        
        self.channel_list.load_events()
        self.timeline.load_events()

    def add_toi(self, toi):
        
        self.custom_events.append(toi)
        self.channel_list.add_custom_event(toi)
        self.timeline.add_event(toi)

    def delete_toi(self, toi):
        
        if toi in self.custom_events:
            self.custom_events.remove(toi)
        self.channel_list.delete_custom_event(toi)
        self.timeline.delete_event(toi)

    def clear_toi(self):
        
        self.custom_events.clear()
        self.channel_list.clear_custom_events()
        self.timeline.clear_events()

    def get_toi(self):
        
        return self.custom_events