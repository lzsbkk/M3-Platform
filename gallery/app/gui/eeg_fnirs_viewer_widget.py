from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QSpacerItem, QSizePolicy, QGroupBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor, QCursor, QIcon, QImage, QPainterPath, QBrush, QMovie, QImageReader
from qfluentwidgets import (SwitchButton,SmoothScrollArea, PrimaryPushButton, LineEdit, 
                            FluentIcon, ToolTipFilter, ToolTipPosition, PrimaryToolButton,
                            setTheme, Theme, FlyoutView, Flyout, FlyoutAnimationType,
                            PushButton, SubtitleLabel, BodyLabel, CheckBox,CardWidget,StrongBodyLabel)
from .channel_list_widget import ChannelListWidget
from .timeline_widget import TimelineWidget
import random
import hashlib

class FlyoutViewBase(QWidget):
    """ Flyout view base class """

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def addWidget(self, widget: QWidget, stretch=0, align=Qt.AlignLeft):
        raise NotImplementedError

    def backgroundColor(self):
        return QColor(15, 26, 42)

    def borderColor(self):
        return QColor(38, 53, 68)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        painter.setBrush(self.backgroundColor())
        painter.setPen(self.borderColor())

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 8, 8)

class CustomFlyoutView(FlyoutViewBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.widgetLayout = QVBoxLayout()
        self.vBoxLayout.addLayout(self.widgetLayout)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.widgetLayout.setSpacing(12)
        self.widgetLayout.setContentsMargins(0, 0, 0, 0)

    def addWidget(self, widget):
        self.widgetLayout.addWidget(widget)

    def addLayout(self, layout):
        self.widgetLayout.addLayout(layout)


class EEGfNIRSViewerWidget(QWidget):
    def __init__(self, eeg_data, wave_color, parent=None):
        super().__init__(parent)
        self.eeg_data = eeg_data
        self.wave_color = wave_color
        self.init_ui()
        self.load_events_from_data()
        # self.wave_color = wave_color

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create scroll area
        scroll_area = SmoothScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.enableTransparentBackground()
        layout.addWidget(scroll_area, 1)

        # Create channel list window
        self.channel_list = ChannelListWidget(self.eeg_data, self.wave_color)
        
        scroll_area.setWidget(self.channel_list)

        # Add a spacer for the entire button and timeline layout
        # layout.addItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Create timeline and settings button layout
        timeline_layout = QHBoxLayout()

        # Settings button
        self.settings_button = PrimaryToolButton(FluentIcon.SETTING)
        self.settings_button.clicked.connect(self.show_settings_flyout)
        self.settings_button.setToolTip("Settings")
        self.settings_button.installEventFilter(ToolTipFilter(self.settings_button, 300, ToolTipPosition.TOP))
        timeline_layout.addWidget(self.settings_button, alignment=Qt.AlignTop)

        # Create a container for the timeline with a spacer
        timeline_container = QWidget()
        timeline_container_layout = QVBoxLayout(timeline_container)
        timeline_container_layout.setContentsMargins(0, 0, 0, 0)

        
        # Add spacer above timeline (for additional offset)
        timeline_container_layout.addItem(QSpacerItem(20, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))
        
        # Create timeline
        self.timeline = TimelineWidget(self.eeg_data)
        timeline_container_layout.addWidget(self.timeline)

        # Add timeline container to main layout
        timeline_layout.addWidget(timeline_container, 1)

        layout.addLayout(timeline_layout)

        # Connect signals
        self.timeline.time_range_changed.connect(self.channel_list.update_time_range)
        self.channel_list.time_range_changed.connect(self.timeline.update_time_range_from_plot)

        self.setLayout(layout)

    def set_random_seed(self):
        if hasattr(self.eeg_data, 'filename'):
            seed_string = self.eeg_data.filename
        else:
            seed_string = f"{self.eeg_data.num_channels}_{self.eeg_data.sample_rate}"
        
        seed = int(hashlib.sha256(seed_string.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)

    def load_events_from_data(self):
            self.set_random_seed()
            events = self.eeg_data.get_events()
            for event in events:
                self.add_event(event)

    def generate_random_color(self):
        
        while True:
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            if 100 < brightness < 200:
                return QColor(r, g, b)

    def add_event(self, event):
        
        self.channel_list.add_event(event)
        self.timeline.add_event(event)

    def delete_event(self, event):
        
        self.channel_list.delete_event(event)
        self.timeline.delete_event(event)

    def clear_events(self):
        
        self.channel_list.clear_events()
        self.timeline.clear_events()

    # def update_data(self, new_eeg_data):
    #     """
    #     """
    #     self.eeg_data = new_eeg_data
    #     self.channel_list.update_data(new_eeg_data)
    #     self.timeline.update_data(new_eeg_data)
    #     self.clear_events()
    #     self.load_events_from_data()

    def show_settings_flyout(self):
        # setTheme(Theme.LIGHT)
        view = CustomFlyoutView()
        view.setStyleSheet("color: #2b2b2b;")
        card_style = """
            CardWidget {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 12px;
            }
            StrongBodyLabel, BodyLabel {
                color: white;
            }
        """
        line_edit_style = """
            LineEdit {
                background-color: #252525;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """
        # Y-axis range input
        y_axis_card = CardWidget()
        y_axis_card.setStyleSheet(card_style)
        y_axis_layout = QVBoxLayout(y_axis_card)
        y_axis_label = StrongBodyLabel("Y-axis Range:")
        y_axis_layout.addWidget(y_axis_label)

        y_input_layout = QHBoxLayout()
        self.y_min_input = LineEdit()
        self.y_max_input = LineEdit()
        self.y_min_input.setPlaceholderText("Min value")
        self.y_max_input.setPlaceholderText("Max value")
        y_input_layout.addWidget(BodyLabel("Min:"))
        y_input_layout.addWidget(self.y_min_input)
        y_input_layout.addWidget(BodyLabel("Max:"))
        y_input_layout.addWidget(self.y_max_input)
        y_axis_layout.addLayout(y_input_layout)

        view.addWidget(y_axis_card)

        # X-axis range input
        x_axis_card = CardWidget()
        x_axis_card.setStyleSheet(card_style)
        x_axis_layout = QVBoxLayout(x_axis_card)
        x_axis_label = StrongBodyLabel("Time Range:")
        x_axis_layout.addWidget(x_axis_label)

        x_input_layout = QHBoxLayout()
        self.x_min_input = LineEdit()
        self.x_max_input = LineEdit()
        self.x_min_input.setPlaceholderText("Start time")
        self.x_max_input.setPlaceholderText("End time")
        x_input_layout.addWidget(BodyLabel("Start:"))
        x_input_layout.addWidget(self.x_min_input)
        x_input_layout.addWidget(BodyLabel("End:"))
        x_input_layout.addWidget(self.x_max_input)
        x_axis_layout.addLayout(x_input_layout)

        view.addWidget(x_axis_card)

        # fNIRS data display options
        if self.eeg_data.data_type == 'fnirs':
            fnirs_card = CardWidget()
            fnirs_card.setStyleSheet(card_style)
            fnirs_layout = QVBoxLayout(fnirs_card)
            fnirs_label = StrongBodyLabel("fNIRS View Setting")
            fnirs_layout.addWidget(fnirs_label)

            fnirs_checkbox_layout = QHBoxLayout()
            self.hbo_checkbox = CheckBox("HbO")
            self.hbr_checkbox = CheckBox("HbR")
            self.hbt_checkbox = CheckBox("HbT")

            # Set initial state based on current display
            self.hbo_checkbox.setChecked(self.channel_list.show_hbo)
            self.hbr_checkbox.setChecked(self.channel_list.show_hbr)
            self.hbt_checkbox.setChecked(self.channel_list.show_hbt)

            fnirs_checkbox_layout.addWidget(self.hbo_checkbox)
            fnirs_checkbox_layout.addWidget(self.hbr_checkbox)
            fnirs_checkbox_layout.addWidget(self.hbt_checkbox)

            fnirs_layout.addLayout(fnirs_checkbox_layout)

            view.addWidget(fnirs_card)
        for line_edit in [self.y_min_input, self.y_max_input, self.x_min_input, self.x_max_input]:
            line_edit.setStyleSheet(line_edit_style)
        # Set current values
        self.set_current_values()

        # Button layout
        button_layout = QHBoxLayout()

        # Reset button with sync icon
        reset_button = PrimaryToolButton(FluentIcon.SYNC)
        reset_button.clicked.connect(self.reset_axis_ranges)
        reset_button.setToolTip("Resetting")
        reset_button.installEventFilter(ToolTipFilter(reset_button, 300, ToolTipPosition.TOP))
        button_layout.addWidget(reset_button)
        button_layout.addStretch()

        # Apply button
        apply_button = PrimaryToolButton(FluentIcon.ACCEPT)
        apply_button.setToolTip("Apply")
        apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_button)
        button_style = """
            PrimaryToolButton {
                background-color: #005fb8;
                color: white;
            }
        """
        reset_button.setStyleSheet(button_style)
        apply_button.setStyleSheet(button_style)
        # Add button layout to view
        view.addLayout(button_layout)

        # Show flyout from the right side
        self.current_flyout = Flyout.make(view, self.settings_button, self.window(), FlyoutAnimationType.SLIDE_RIGHT)

    def apply_settings(self):
        try:
            self.set_axis_ranges()

            if self.eeg_data.data_type == 'fnirs':
                show_hbo = self.hbo_checkbox.isChecked()
                show_hbr = self.hbr_checkbox.isChecked()
                show_hbt = self.hbt_checkbox.isChecked()
                self.channel_list.set_fnirs_display(show_hbo, show_hbr, show_hbt)

            if self.current_flyout:
                self.current_flyout.close()

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Accidental Error: {str(e)}")

    def set_current_values(self):
        # Set current X-axis range
        x_min = self.timeline.visible_start
        x_max = x_min + self.timeline.visible_duration
        self.x_min_input.setText(f"{x_min:.2f}")
        self.x_max_input.setText(f"{x_max:.2f}")

        # Set current Y-axis range
        if self.channel_list.channel_plots:
            y_min, y_max = self.channel_list.channel_plots[0].y_range
            self.y_min_input.setText(f"{y_min:.2f}")
            self.y_max_input.setText(f"{y_max:.2f}")
        else:
            self.y_min_input.clear()
            self.y_max_input.clear()

    def reset_axis_ranges(self):
        self.channel_list.reset_all_views()
        self.set_current_values()

    def set_axis_ranges(self):
        try:
            y_min = float(self.y_min_input.text()) if self.y_min_input.text() else None
            y_max = float(self.y_max_input.text()) if self.y_max_input.text() else None
            x_min = float(self.x_min_input.text()) if self.x_min_input.text() else 0
            x_max = float(self.x_max_input.text()) if self.x_max_input.text() else self.eeg_data.duration

            if y_min is not None and y_max is not None:
                if y_min >= y_max:
                    raise ValueError("Y-axis: Min Value Must Be Less Than Max Value")
                for plot in self.channel_list.channel_plots:
                    plot.y_range = [y_min, y_max]
                    plot.update()
            
            if x_min >= x_max:
                raise ValueError("X-axis: Start Time Must Be Less Than End Time")
            
            duration = self.eeg_data.duration
            if not isinstance(duration, (int, float)) or duration <= 0:
                raise ValueError(f"Invalid EEG Data Duration: {duration}")
            
            if x_min < 0 or x_max > duration:
                raise ValueError(f"X-axis: Value Must Be Between 0 And {duration:.2f}")

            self.timeline.update_time_range_from_plot(x_min, x_max - x_min)

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Accidental Error: {str(e)}")