# gui/eeg_plot_widget.py

from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtGui import QPainter, QColor, QFont, QPen
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer, QLineF
from qfluentwidgets import ThemeColor, CaptionLabel
import numpy as np
import math
from .eeg_plot_utils import GridCalculator, CoordinateTransformer, WaveformDrawer, FontSizeCalculator
from scipy import signal

import math

def calculate_time_interval(time_range):
    time_span = time_range[1] - time_range[0]
    
    target_intervals = 7.5  
    
    initial_interval = time_span / target_intervals
    
    magnitude = 10 ** math.floor(math.log10(initial_interval))
    normalized = initial_interval / magnitude
    
    if normalized < 1.5:
        nice_interval = magnitude
    elif normalized < 3:
        nice_interval = 2 * magnitude
    elif normalized < 7:
        nice_interval = 5 * magnitude
    else:
        nice_interval = 10 * magnitude
    
    return nice_interval
        
class MultiPlotWidget(QWidget):
    time_range_changed = pyqtSignal(float, float)
    mouse_moved = pyqtSignal(float, float, int)  # time, value, channel_index

    def __init__(self, eeg_data, channel, data_index, global_channel_index, signal_type=None, parent=None):
        super().__init__(parent)
        self.eeg_data = eeg_data
        self.channel = channel
        self.data_index = data_index
        self.global_channel_index = global_channel_index
        self.signal_type = signal_type
        self.channel_name = eeg_data.get_channel_names()[channel]
        self.data_start_time = self.eeg_data.get_start_time()
        self.data_end_time = self.data_start_time + self.eeg_data.duration
        max_display_duration = 30
        
        if self.eeg_data.duration <= max_display_duration:
            self.time_range = [self.data_start_time, self.data_end_time]
        else:
            self.time_range = [self.data_start_time, self.data_start_time + max_display_duration]
        self.setMinimumHeight(100)
        self.y_range = list(eeg_data.get_y_scale())
        self.left_margin = 60
        self.right_margin = 20
        self.top_margin = 20  # Slightly reduced top margin
        self.bottom_margin = 30  # Slightly reduced bottom margin
        self.events = []
        self.transformer = CoordinateTransformer(self)
        self.waveform_drawer = WaveformDrawer(self, self.transformer)
        self.dragging = False
        self.last_pos = None
        self.crosshair_pos = None
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_tooltip)
        self.tooltip_data = None

        self.unit_label = self.get_unit_label()
        self.init_ui()

    def init_ui(self):
        self.y_label = CaptionLabel(self)
        self.y_label.move(5, 5)
        
        self.setStyleSheet("""
            EEGPlotWidget {
                background-color: blue;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        
        self.setMouseTracking(True)

    def get_unit_label(self):
        if self.eeg_data.data_type == 'eeg':
            return 'μV'
        elif self.eeg_data.data_type == 'fnirs':
            return 'μmol/L'
        else:
            return ''  
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.draw_background(painter)
        self.draw_axes(painter)
        self.draw_grid(painter)
        # self.draw_events(painter)
        self.draw_bad(painter)
        self.draw_waveform(painter)
        self.draw_time_axis(painter)
        self.draw_y_axis(painter)
        self.draw_crosshair(painter)
    
    def draw_bad(self, painter):
        if not hasattr(self.eeg_data, 'bad_segments') or not self.eeg_data.bad_segments:
            return

        painter.setClipRect(self.left_margin, self.top_margin, 
                            self.width() - self.left_margin - self.right_margin, 
                            self.height() - self.top_margin - self.bottom_margin)

        bad_color = QColor(255, 0, 0, 50)  
        painter.setBrush(bad_color)
        painter.setPen(Qt.NoPen)

        for start, end in self.eeg_data.bad_segments:
            x_start = self.transformer.time_to_x(start)
            x_end = self.transformer.time_to_x(end)

            if x_end < self.left_margin or x_start > self.width() - self.right_margin:
                continue  

            rect = QRectF(max(x_start, self.left_margin), self.top_margin,
                          min(x_end, self.width() - self.right_margin) - max(x_start, self.left_margin),
                          self.height() - self.top_margin - self.bottom_margin)
            painter.drawRect(rect)

        painter.setClipping(False)

    def draw_background(self, painter):
        # painter.fillRect(self.rect(), QColor(38, 53, 68))
        # painter.fillRect(self.rect(), QColor(245, 240, 255))
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        # painter.fillRect(self.rect(), QColor(50, 50, 50))

        plot_rect = QRectF(self.left_margin, self.top_margin, 
                           self.width() - self.left_margin - self.right_margin, 
                           self.height() - self.top_margin - self.bottom_margin)
        # painter.fillRect(plot_rect, QColor(50, 50, 50))

    def draw_axes(self, painter):
        painter.setPen(QPen(ThemeColor.DARK_1.color(), 2))
        painter.drawLine(self.left_margin, self.top_margin, self.left_margin, self.height() - self.bottom_margin)  # Y-axis
        painter.drawLine(self.left_margin, self.height() - self.bottom_margin, self.width() - self.right_margin, self.height() - self.bottom_margin)  # X-axis

    def draw_grid(self, painter):
        painter.setPen(QPen(ThemeColor.DARK_2.color(), 1, Qt.DotLine))
        
        clip_rect = QRectF(self.left_margin, self.top_margin, 
                        self.width() - self.left_margin - self.right_margin, 
                        self.height() - self.top_margin - self.bottom_margin)
        painter.setClipRect(clip_rect)
        
        time_interval = calculate_time_interval(self.time_range)
        start_time = math.floor(self.time_range[0] / time_interval) * time_interval
        end_time = math.ceil(self.time_range[1] / time_interval) * time_interval
        
        for t in np.arange(start_time, end_time + time_interval, time_interval):
            x = self.transformer.time_to_x(t)
            painter.drawLine(x, self.top_margin, x, self.height() - self.bottom_margin)

        y_interval = (self.y_range[1] - self.y_range[0]) / 4
        for y in np.arange(self.y_range[0], self.y_range[1] + y_interval, y_interval):
            y_pos = self.transformer.value_to_y(y)
            painter.drawLine(self.left_margin, y_pos, self.width() - self.right_margin, y_pos)

        painter.setClipping(False)

    def draw_events(self, painter):
        visible_start = self.transformer.x_to_time(self.left_margin)
        visible_end = self.transformer.x_to_time(self.width() - self.right_margin)

        # Draw event areas
        painter.setClipRect(self.left_margin, self.top_margin, 
                            self.width() - self.left_margin - self.right_margin, 
                            self.height() - self.top_margin - self.bottom_margin)
        
        visible_events = []
        use_dots = False
        min_label_distance = 50
        last_x_center = float('-inf')

        for event in self.events:
            start, end, color, name = event
            x_start = self.transformer.time_to_x(start)
            x_end = self.transformer.time_to_x(end)
            
            if x_start == x_end:  # Single event
                if visible_start <= start <= visible_end:
                    painter.setPen(QPen(self.get_qcolor(color), 2))
                    painter.drawLine(x_start, self.top_margin, x_start, self.height() - self.bottom_margin)
            else:  # Event interval
                if not (end < visible_start or start > visible_end):
                    rect = QRectF(x_start, self.top_margin, x_end - x_start, 
                                self.height() - self.top_margin - self.bottom_margin)
                    painter.fillRect(rect, self.get_qcolor(color, alpha=128))
            
            if (visible_start <= start <= visible_end) or (visible_start <= end <= visible_end) or (start <= visible_start and end >= visible_end):
                x_center = (x_start + x_end) / 2
                if x_center - last_x_center < min_label_distance:
                    use_dots = True
                visible_events.append((x_center, color, name))
                last_x_center = x_center

        painter.setClipping(False)

        # Draw event labels or dots
        for x_center, color, name in visible_events:
            painter.setPen(QPen(self.get_qcolor(color)))
            
            if use_dots:
                font = painter.font()
                font.setPointSize(4)  
                painter.setFont(font)
                
                fm = painter.fontMetrics()
                dot_width = fm.width('●')
                dot_height = fm.height()
                
                painter.drawText(QPointF(x_center - dot_width/2, self.top_margin - 10 + dot_height/2), '●')
            else:
                font = FontSizeCalculator.calculate_font_size(painter, [name], self.width() - self.left_margin - self.right_margin, is_horizontal=True, start_size=8, bold=True)
                painter.setFont(font)

                text_width = painter.fontMetrics().width(name)
                text_left = max(self.left_margin, min(x_center - text_width / 2, self.width() - self.right_margin - text_width))

                text_rect = QRectF(text_left, self.top_margin - 20, text_width, 20)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, name)

    def get_qcolor(self, color, alpha=255):
        if isinstance(color, QColor):
            return color
        elif isinstance(color, (tuple, list)) and len(color) in [3, 4]:
            if len(color) == 3:
                return QColor(*color, alpha)
            else:
                return QColor(*color)
        elif isinstance(color, str):
            return QColor(color)
        else:
            return QColor(255, 0, 0, alpha)  

    def simple_downsample(self, data, time, target_points):
        
        if len(data) <= target_points:
            return data, time

        step = len(data) // target_points

        downsampled_data = data[::step]
        downsampled_time = time[::step]

        if len(downsampled_data) < target_points:
            downsampled_data = np.append(downsampled_data, data[-1])
            downsampled_time = np.append(downsampled_time, time[-1])

        return downsampled_data, downsampled_time

    def draw_waveform(self, painter):
        data_start_time = self.eeg_data.get_start_time()
        data_end_time = self.eeg_data.time[-1] + data_start_time

        extra_time = 0.1  
        start_index = int((max(self.time_range[0], data_start_time) - data_start_time) * self.eeg_data.sample_rate)
        end_index = int((min(self.time_range[1] + extra_time, data_end_time) - data_start_time) * self.eeg_data.sample_rate)
        
        start_index = max(0, start_index)
        end_index = min(end_index, self.eeg_data.data.shape[1])
        
        data = self.eeg_data.data[self.channel, start_index:end_index]
        time = self.eeg_data.time[start_index:end_index] + data_start_time
        

        time_range = self.time_range[1] - self.time_range[0]
        pixels_per_second = (self.width() - self.left_margin - self.right_margin) / time_range

        target_points = int((self.width() - self.left_margin - self.right_margin)/4)
        data_downsampled, time_downsampled = self.simple_downsample(data, time, target_points)

        self.waveform_drawer.draw(painter, data_downsampled, time_downsampled, self.eeg_data.sample_rate, pixels_per_second)

        clip_rect = QRectF(self.left_margin, self.top_margin, 
                        self.width() - self.left_margin - self.right_margin, 
                        self.height() - self.top_margin - self.bottom_margin)
        painter.setClipRect(clip_rect)

        if self.time_range[0] < data_start_time:
            x_start = max(self.transformer.time_to_x(self.time_range[0]), self.left_margin)
            x_end = min(self.transformer.time_to_x(data_start_time), self.width() - self.right_margin)
            rect = QRectF(x_start, self.top_margin, x_end - x_start, 
                        self.height() - self.top_margin - self.bottom_margin)
            painter.fillRect(rect, QColor(128, 128, 128, 128))  

        if self.time_range[1] > data_end_time:
            x_start = max(self.transformer.time_to_x(data_end_time), self.left_margin)
            x_end = min(self.transformer.time_to_x(self.time_range[1]), self.width() - self.right_margin)
            rect = QRectF(x_start, self.top_margin, x_end - x_start, 
                        self.height() - self.top_margin - self.bottom_margin)
            painter.fillRect(rect, QColor(128, 128, 128, 128))  

        painter.setClipping(False)
        # self.draw_unit_label(painter)

    # def draw_unit_label(self, painter):
    #     painter.setPen(QPen(ThemeColor.DARK_1.color(), 1))
    #     font = painter.font()
    #     font.setPointSize(8)
    #     painter.setFont(font)
        
    #     label_text = f"{self.unit_label}"
    #     text_width = painter.fontMetrics().width(label_text)
    #     text_height = painter.fontMetrics().height()
        
    #     painter.drawText(
    #         self.left_margin - 5,
    #         self.height() - self.bottom_margin - text_height - 10,
    #         label_text
    #     )

    def draw_time_axis(self, painter):
        painter.setPen(QPen(ThemeColor.DARK_1.color(), 1))
        
        time_interval = calculate_time_interval(self.time_range)
        start_time = math.floor(self.time_range[0] / time_interval) * time_interval
        end_time = math.ceil(self.time_range[1] / time_interval) * time_interval
        
        labels = []
        for t in np.arange(start_time, end_time + time_interval, time_interval):
            if time_interval >= 1:
                labels.append(f"{int(t)}s")
            else:
                labels.append(f"{t:.1f}s")
        
        font = FontSizeCalculator.calculate_font_size(painter, labels, self.width() - self.left_margin - self.right_margin, is_horizontal=True, start_size=6)
        painter.setFont(font)
        
        for t in np.arange(start_time, end_time + time_interval, time_interval):
            x = self.transformer.time_to_x(t)
            if self.left_margin <= x <= self.width() - self.right_margin:
                painter.drawLine(x, self.height() - self.bottom_margin, x, self.height() - self.bottom_margin + 5)
                
                if time_interval >= 1:
                    label = f"{int(t)}s"
                else:
                    label = f"{t:.1f}s"
                text_width = painter.fontMetrics().width(label)
                text_x = max(self.left_margin, min(x - text_width / 2, self.width() - self.right_margin - text_width))
                painter.drawText(int(text_x), self.height() - 5, label)

    def draw_y_axis(self, painter):
        painter.setPen(QPen(ThemeColor.DARK_1.color(), 1))
        
        y_interval = (self.y_range[1] - self.y_range[0]) / 4
        labels = [f"{y:.2f}" for y in np.arange(self.y_range[0], self.y_range[1] + y_interval, y_interval)]
        
        font = FontSizeCalculator.calculate_font_size(painter, labels, self.left_margin - 5, is_horizontal=False, start_size=6)
        painter.setFont(font)
        
        for y in np.arange(self.y_range[0], self.y_range[1] + y_interval, y_interval):
            y_pos = self.transformer.value_to_y(y)
            painter.drawLine(self.left_margin - 5, y_pos, self.left_margin, y_pos)
            painter.drawText(5, y_pos + 4, f"{y:.2f}"+" "+self.unit_label)

    def set_y_range(self, y_min, y_max):
        self.y_range = [y_min, y_max]
        self.update()

    
    def draw_crosshair(self, painter):
        if self.crosshair_pos is not None:
            x, y = self.crosshair_pos
            if self.left_margin <= x <= self.width() - self.right_margin:
                painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
                painter.drawLine(x, self.top_margin, x, self.height() - self.bottom_margin)
                
                # Draw intersection point
                painter.setPen(QPen(Qt.red, 4))
                painter.drawPoint(x, y)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        x = event.x()
        if self.left_margin <= x <= self.width() - self.right_margin:
            time = self.transformer.x_to_time(x)
            value = self.get_value_at_time(time)
            if value is not None:
                y = self.transformer.value_to_y(value)
                self.crosshair_pos = (x, y)
                self.update()
                self.mouse_moved.emit(time, value, self.channel)
                
                # Store tooltip data and start timer
                self.tooltip_data = (event.globalPos(), time, value)
                self.tooltip_timer.start(500)  # 500 ms delay
            else:
                self.crosshair_pos = None
                self.tooltip_timer.stop()
                self.tooltip_data = None
                QToolTip.hideText()
        else:
            self.crosshair_pos = None
            self.tooltip_timer.stop()
            self.tooltip_data = None
            QToolTip.hideText()
        
        self.update()

        if self.dragging:
            dx = event.x() - self.last_pos.x()
            self.last_pos = event.pos()

            # Update time range
            time_delta = dx / (self.width() - self.left_margin - self.right_margin) * (self.time_range[1] - self.time_range[0])
            new_start = self.time_range[0] - time_delta
            new_end = self.time_range[1] - time_delta

            # Check if new range is within bounds
            if new_start >= 0 and new_end <= self.eeg_data.duration:
                self.time_range = [new_start, new_end]
                self.time_range_changed.emit(*self.time_range)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)

    # def wheelEvent(self, event):
    #     # Wheel event is disabled
    #     event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()  # Ensure the widget is redrawn when resized

    def get_value_at_time(self, time):
        try:
            data_start_time = self.eeg_data.get_start_time()
            index = int((time - data_start_time) * self.eeg_data.sample_rate)
            if 0 <= index < self.eeg_data.data.shape[1]:
                return self.eeg_data.data[self.channel, index]
            else:
                return None
        except Exception as e:
            return None
        
    def update_crosshair(self, time, value):
        if value is not None:
            x = self.transformer.time_to_x(time)
            y = self.transformer.value_to_y(value)
            self.crosshair_pos = (x, y)
            self.update()
        else:
            self.crosshair_pos = None
            self.update()

    def show_tooltip(self):
        if self.tooltip_data:
            global_pos, time, value = self.tooltip_data
            tooltip_text = f"时间: {time:.3f}s\n值: {value:.3f}"
            
            # Adjust tooltip position to be near the intersection point
            adjusted_pos = self.mapToGlobal(QPointF(self.crosshair_pos[0] + 10, self.crosshair_pos[1] - 10).toPoint())
            QToolTip.showText(adjusted_pos, tooltip_text, self)

    def set_time_range(self, start, end):
        self.time_range = [start, end]
        self.update()

    def reset_view(self):
        data_start_time = self.eeg_data.get_start_time()
        self.time_range = [data_start_time, data_start_time + 10]
        self.y_range = list(self.eeg_data.get_y_scale())
        self.update()

    def add_event(self, event):
        self.events.append(event)
        self.update()
    
    def delete_event(self, event):
        if event in self.events:
            self.events.remove(event)
            self.update()
        else:
            print("Event not found.")  

    def clear_events(self):
        self.events.clear()
        self.update()

    def leaveEvent(self, event):
        self.crosshair_pos = None
        self.tooltip_timer.stop()
        self.tooltip_data = None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)