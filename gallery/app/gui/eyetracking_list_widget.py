from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import pyqtSignal, Qt
from qfluentwidgets import SmoothScrollArea, CardWidget, BodyLabel, IconWidget, FluentIcon
from .eyetracking_plot_widget import EyeTrackingPlotWidget

class EyeTrackingChannelListWidget(SmoothScrollArea):
    time_range_changed = pyqtSignal(float, float)

    def __init__(self, et_data, parent=None):
        super().__init__(parent)
        self.et_data = et_data
        self.channel_plots = []
        self.custom_events = []  
        self.parent = parent
        self.enableTransparentBackground()
        self.init_ui()

    def init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        # plot_types = [
        # ]
        plot_types = [
            ("Fixation", "Fixation Event"),
            ("Saccade", "Saccade Event"),
            ("Blink", "Blink Event"),
            ("GazePointX", "Gaze Point X"),
            ("GazePointY", "Gaze Point Y"),
            ("Velocity", "Velocity (°/s)"),
            ("Pupil", "Pupil Size (mm)")
        ]

        for data_type, display_name in plot_types:
            channel_card = self.create_channel_card(data_type, display_name)
            layout.addWidget(channel_card)

        layout.addStretch()
        self.setWidget(container)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container.setObjectName('view')

    def create_channel_card(self, data_type, display_name):
        card = CardWidget()
        card.setObjectName(f"channel_card_{data_type}")
        card_layout = QVBoxLayout(card)
        
        # Channel name with icon
        name_layout = QHBoxLayout()
        
        icon = IconWidget(FluentIcon.IOT)
        icon.setFixedSize(16, 16)
        name_layout.addWidget(icon)
        
        name_label = BodyLabel(display_name)
        name_layout.addWidget(name_label)
        name_layout.addStretch()
        
        # Eye Tracking Plot
        plot_widget = EyeTrackingPlotWidget(self.et_data, data_type)
        plot_widget.channel_name = data_type
        
        self.channel_plots.append(plot_widget)
        
        # Add widgets to card layout
        card_layout.addLayout(name_layout)
        card_layout.addWidget(plot_widget)
        
        # Connect signals
        plot_widget.time_range_changed.connect(self.update_all_time_ranges)
        plot_widget.mouse_moved.connect(self.update_all_crosshairs)
        
        return card

    def set_current_time(self, time):
        for plot in self.channel_plots:
            plot.set_current_time(time)
        self.update()

    def update_all_time_ranges(self, start, end):
        for plot in self.channel_plots:
            plot.set_time_range(start, end)
        self.time_range_changed.emit(start, end)

    def update_time_range(self, start, end):
        for plot in self.channel_plots:
            plot.set_time_range(start, end)

    def reset_all_views(self):
        for plot in self.channel_plots:
            plot.reset_view()
        self.time_range_changed.emit(0, self.et_data.processed_data['Timestamp'].max())

    def update_all_crosshairs(self, time, value, source_channel):
        for i, plot in enumerate(self.channel_plots):
            if i != source_channel:
                plot_value = plot.get_value_at_time(time)
                plot.update_crosshair(time, plot_value)

    def load_events(self):
        for plot in self.channel_plots:
            if plot.channel_name == "Fixation":
                plot.add_events(self.et_data.fixations)
            elif plot.channel_name == "Saccade":
                plot.add_events(self.et_data.saccades)
            elif plot.channel_name == "Blink":
                plot.add_events(self.et_data.blinks)
        self.add_custom_events()

    def update_data(self, new_et_data):
        self.et_data = new_et_data
        self.channel_plots.clear()
        self.init_ui()
        self.load_events()

    def add_custom_event(self, event):
        self.custom_events.append(event)
        for plot in self.channel_plots:
            plot.add_custom_event(event)

    def delete_custom_event(self, event):
        if event in self.custom_events:
            self.custom_events.remove(event)
        for plot in self.channel_plots:
            plot.delete_custom_event(event)

    def clear_custom_events(self):
        self.custom_events.clear()
        for plot in self.channel_plots:
            plot.clear_custom_events()

    def add_custom_events(self):
        for plot in self.channel_plots:
            for event in self.custom_events:
                plot.add_custom_event(event)

    def get_custom_events(self):
        return self.custom_events