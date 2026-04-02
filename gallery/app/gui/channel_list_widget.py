from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import pyqtSignal, Qt
from qfluentwidgets import ScrollArea, CardWidget, BodyLabel, IconWidget, FluentIcon
from .eeg_plot_widget import EEGPlotWidget

class ChannelListWidget(ScrollArea):
    time_range_changed = pyqtSignal(float, float)

    def __init__(self, eeg_data, wave_color, parent=None):
        super().__init__(parent)
        self.eeg_data = eeg_data
        self.channel_plots = []
        self.show_hbo = True
        self.show_hbr = True
        self.show_hbt = True
        self.wave_color = wave_color
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.enableTransparentBackground()
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setSpacing(1)
        self.layout.setContentsMargins(1, 1, 1, 1)

        self.create_channel_cards()

        self.layout.addStretch()
        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.container.setObjectName('view')

    def create_warning_card(self):
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        warning_label = BodyLabel("通道数量过多(>1000)，暂不支持可视化显示")
        card_layout.addWidget(warning_label)
        return card

    def create_channel_cards(self):
        visible_channels = self.get_visible_channels_count()
        
        if visible_channels > 1000:
            self.layout.addWidget(self.create_warning_card())
            return
            
        for channel in range(self.eeg_data.num_channels):
            channel_name = self.eeg_data.get_channel_names()[channel]
            if self.should_show_channel(channel_name):
                channel_card = self.create_channel_card(channel)
                self.layout.addWidget(channel_card)

    def should_show_channel(self, channel_name):
        channel_name = channel_name.lower()
        if self.eeg_data.data_type == 'fnirs':
            if 'hbo' in channel_name and not self.show_hbo:
                return False
            if 'hbr' in channel_name and not self.show_hbr:
                return False
            if 'hbt' in channel_name and not self.show_hbt:
                return False
        return True

    def get_visible_channels_count(self):
        if self.eeg_data.data_type != 'fnirs':
            return self.eeg_data.num_channels
            
        count = 0
        for channel_name in self.eeg_data.get_channel_names():
            if self.should_show_channel(channel_name):
                count += 1
        return count

    def create_channel_card(self, channel):
        card = CardWidget()
        card.setObjectName(f"channel_card_{channel}")
        card_layout = QVBoxLayout(card)
        
        # Channel name with icon
        channel_name = self.eeg_data.get_channel_names()[channel]
        name_layout = QHBoxLayout()
        
        icon = IconWidget(FluentIcon.IOT)
        icon.setFixedSize(16, 16)
        name_layout.addWidget(icon)
        
        name_label = BodyLabel(channel_name)
        name_layout.addWidget(name_label)
        name_layout.addStretch()
        
        # EEG Plot
        plot_widget = EEGPlotWidget(self.eeg_data, channel, self.wave_color)
        plot_widget.channel_name = channel_name
        
        self.channel_plots.append(plot_widget)
        
        # Add widgets to card layout
        card_layout.addLayout(name_layout)
        card_layout.addWidget(plot_widget)
        
        # Connect signals
        plot_widget.time_range_changed.connect(self.update_all_time_ranges)
        plot_widget.mouse_moved.connect(self.update_all_crosshairs)
        
        return card

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
        self.time_range_changed.emit(0, 10)

    def set_y_range(self, y_min, y_max):
        for plot in self.channel_plots:
            plot.set_y_range(y_min, y_max)
    
    def get_y_range(self):
        if self.channel_plots:
            return self.channel_plots[0].get_y_range()
        return None, None

    def update_all_crosshairs(self, time, value, source_channel):
        for i, plot in enumerate(self.channel_plots):
            if i != source_channel:
                plot_value = plot.get_value_at_time(time)
                plot.update_crosshair(time, plot_value)
                
    def add_event(self, event):
        for plot in self.channel_plots:
            plot.add_event(event)

    def delete_event(self, event):
        for plot in self.channel_plots:
            plot.delete_event(event)

    def clear_events(self):
        for plot in self.channel_plots:
            plot.clear_events()

    def set_fnirs_display(self, show_hbo, show_hbr, show_hbt):
        self.show_hbo = show_hbo
        self.show_hbr = show_hbr
        self.show_hbt = show_hbt
        self.update_channel_visibility()

    def update_channel_visibility(self):
        if self.eeg_data.data_type == 'fnirs':
            visible_channels = self.get_visible_channels_count()
            if visible_channels > 1000:
                self.update_data()
                return
                
            for i, plot in enumerate(self.channel_plots):
                channel_name = plot.channel_name.lower()
                card = self.findChild(CardWidget, f"channel_card_{i}")
                if card:
                    if 'hbo' in channel_name:
                        card.setVisible(self.show_hbo)
                    elif 'hbr' in channel_name:
                        card.setVisible(self.show_hbr)
                    elif 'hbt' in channel_name:
                        card.setVisible(self.show_hbt)
            self.update()

    def update_data(self):
        # Clear current layout
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        # Clear channel_plots list
        self.channel_plots.clear()

        # Recreate channel cards
        self.create_channel_cards()

        # Update the widget
        self.container.updateGeometry()
        self.updateGeometry()