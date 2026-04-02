from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import ScrollArea, CardWidget, BodyLabel, IconWidget, FluentIcon
from .multi_plot_widget import MultiPlotWidget
from .multi_eyetracking_plot_widget import MultiETPlotWidget
import logging

logger = logging.getLogger(__name__)

class MultiChannelListWidget(ScrollArea):
    time_range_changed = pyqtSignal(float, float)

    def __init__(self, multi_data, parent=None):
        super().__init__(parent)
        self.multi_data = multi_data
        self.channel_cards = {}  # Dictionary to store created cards
        self.channel_plots = []
        self.enableTransparentBackground()
        self.init_ui()

    def init_ui(self):
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setSpacing(1)
        self.layout.setContentsMargins(1, 1, 1, 1)

        if not self.multi_data.data_list or all(data is None for data in self.multi_data.data_list):
            no_data_label = QLabel("No data available")
            no_data_label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(no_data_label)
        
        self.layout.addStretch()
        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.container.setObjectName('view')

    def get_channel_key(self, data_index, channel_index):
        return f"{data_index}_{channel_index}"

    def create_channel_card(self, eeg_data, channel, data_index, global_channel_index):
        card = CardWidget()
        card.setObjectName(f"channel_card_{global_channel_index}")
        card_layout = QVBoxLayout(card)
        
        try:
            data_name = self.multi_data.get_data_name(data_index)
            channel_name = f"{data_name}-{eeg_data.get_channel_names()[channel]}"
        except Exception as e:
            logger.warning(f"Error getting channel name: {str(e)}")
            channel_name = f"Data {data_index+1}-Channel {channel}"
        
        name_layout = QHBoxLayout()
        icon = IconWidget(FluentIcon.IOT)
        icon.setFixedSize(16, 16)
        name_layout.addWidget(icon)
        name_label = BodyLabel(channel_name)
        name_layout.addWidget(name_label)
        name_layout.addStretch()
        
        try:
            plot_widget = MultiPlotWidget(eeg_data, channel, data_index, global_channel_index, parent=card)
            plot_widget.channel_name = channel_name
            self.channel_plots.append(plot_widget)
            
            card_layout.addLayout(name_layout)
            card_layout.addWidget(plot_widget)
            
            plot_widget.time_range_changed.connect(self.update_all_time_ranges)
            plot_widget.mouse_moved.connect(self.update_all_crosshairs)
        except Exception as e:
            logger.error(f"Error creating plot widget: {str(e)}")
            error_label = QLabel(f"Error loading plot: {str(e)}")
            card_layout.addWidget(error_label)
        
        return card

    def create_et_channel_card(self, et_data, channel_index, data_index, data_type, display_name):
        card = CardWidget()
        card.setObjectName(f"et_channel_card_{data_index}_{channel_index}")
        card_layout = QVBoxLayout(card)
        
        name_layout = QHBoxLayout()
        icon = IconWidget(FluentIcon.IOT)
        icon.setFixedSize(16, 16)
        name_layout.addWidget(icon)
        
        data_name = self.multi_data.get_data_name(data_index)
        channel_name = f"{data_name}-{display_name}"
        name_label = BodyLabel(channel_name)
        name_layout.addWidget(name_label)
        name_layout.addStretch()
        
        try:
            plot_widget = MultiETPlotWidget(self.multi_data, data_type, data_index, parent=card)
            plot_widget.channel_name = channel_name
            self.channel_plots.append(plot_widget)
            
            card_layout.addLayout(name_layout)
            card_layout.addWidget(plot_widget)
            
            plot_widget.time_range_changed.connect(self.update_all_time_ranges)
            plot_widget.mouse_moved.connect(self.update_all_crosshairs)
        except Exception as e:
            logger.error(f"Error creating ET plot widget: {str(e)}")
            error_label = QLabel(f"Error loading ET plot: {str(e)}")
            card_layout.addWidget(error_label)
        
        return card

    def ensure_channel_card_exists(self, data_index, channel_index):
        channel_key = self.get_channel_key(data_index, channel_index)
        
        if channel_key not in self.channel_cards:
            data = self.multi_data.data_list[data_index]
            if data is None:
                return None
                
            if data.data_type == 'et':
                # et_channels = [
                # ]
                et_channels = [
                    ("Fixation", "Fixation Event"),
                    ("Saccade", "Saccade Event"),
                    ("Blink", "Blink Event"),
                    ("GazePointX", "Gaze Point X"),
                    ("GazePointY", "Gaze Point Y"),
                    ("Velocity", "Velocity (°/s)"),
                    ("Pupil", "Pupil Size (mm)")
                ]
                if 0 <= channel_index < len(et_channels):
                    data_type, display_name = et_channels[channel_index]
                    card = self.create_et_channel_card(data, channel_index, data_index, data_type, display_name)
                    self.channel_cards[channel_key] = card
                    self.layout.insertWidget(self.layout.count() - 1, card)
            else:
                if hasattr(data, 'num_channels') and 0 <= channel_index < data.num_channels:
                    global_channel_index = sum(getattr(d, 'num_channels', 0) for d in self.multi_data.data_list[:data_index]) + channel_index
                    card = self.create_channel_card(data, channel_index, data_index, global_channel_index)
                    self.channel_cards[channel_key] = card
                    self.layout.insertWidget(self.layout.count() - 1, card)

        return self.channel_cards.get(channel_key)

    def update_channel_visibility(self, data_index, channel_index, visible):
        if visible:
            card = self.ensure_channel_card_exists(data_index, channel_index)
            if card:
                card.setVisible(visible)
        else:
            channel_key = self.get_channel_key(data_index, channel_index)
            if channel_key in self.channel_cards:
                self.channel_cards[channel_key].setVisible(visible)

    def update_data(self, new_multi_data):
        self.multi_data = new_multi_data
        self.channel_plots.clear()
        
        # Remove existing cards
        for card in self.channel_cards.values():
            card.setParent(None)
        self.channel_cards.clear()
        
        # Reinitialize UI
        self.init_ui()

        # Restore visibility states
        for data_index, visibility_dict in enumerate(self.multi_data.channel_visibility):
            for channel_index, visible in visibility_dict.items():
                if visible:
                    self.update_channel_visibility(data_index, channel_index, True)

    def update_all_time_ranges(self, start, end):
        for plot in self.channel_plots:
            plot.set_time_range(start, end)
        self.time_range_changed.emit(start, end)

    def update_time_range(self, start, end):
        for plot in self.channel_plots:
            if plot:
                try:
                    plot.set_time_range(start, end)
                except Exception as e:
                    logger.error(f"Error updating time range: {str(e)}")

    def reset_all_views(self):
        for plot in self.channel_plots:
            if plot:
                try:
                    plot.reset_view()
                except Exception as e:
                    logger.error(f"Error resetting view: {str(e)}")
        if self.channel_plots:
            first_plot = self.channel_plots[0]
            if first_plot:
                try:
                    self.time_range_changed.emit(first_plot.time_range[0], first_plot.time_range[1])
                except Exception as e:
                    logger.error(f"Error emitting time range changed signal: {str(e)}")

    def update_all_crosshairs(self, time, value, source_channel):
        for i, plot in enumerate(self.channel_plots):
            if plot and i != source_channel:
                try:
                    plot_value = plot.get_value_at_time(time)
                    plot.update_crosshair(time, plot_value)
                except Exception as e:
                    logger.error(f"Error updating crosshair: {str(e)}")

    def add_event(self, event):
        for plot in self.channel_plots:
            plot.add_event(event)

    def delete_event(self, event):
        for plot in self.channel_plots:
            plot.delete_event(event)

    def clear_events(self):
        for plot in self.channel_plots:
            plot.clear_events()