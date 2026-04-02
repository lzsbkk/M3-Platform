from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QPainterPath
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer, QLineF
from qfluentwidgets import ThemeColor, CaptionLabel
import numpy as np
import math
from .et_plot_utils import GridCalculator, CoordinateTransformer, WaveformDrawer, FontSizeCalculator

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

class MultiETPlotWidget(QWidget):
    time_range_changed = pyqtSignal(float, float)
    mouse_moved = pyqtSignal(float, float, str)  # time, value, channel_name

    def __init__(self, multi_data, data_type, data_index, parent=None):
        super().__init__(parent)
        self.multi_data = multi_data
        self.data_type = data_type
        self.data_index = data_index
        self.channel_name = data_type
        self.channel = self.get_channel_index()
        self.time_range = [0, 30]
        self.setMinimumHeight(100)
        self.y_range = self.calculate_y_range()
        self.left_margin = 60
        self.right_margin = 20
        self.top_margin = 20
        self.bottom_margin = 30
        self.current_time = 0
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
        self.init_ui()

    def get_channel_index(self):
        et_channels = ["Fixation", "Saccade", "Blink", "GazePointX", "GazePointY", "Velocity", "Pupil"]
        return et_channels.index(self.data_type)
    
    def is_visible(self):
        return self.multi_data.channel_visibility[self.data_index].get(self.channel, False)
    
    def init_ui(self):
        self.y_label = CaptionLabel(self)
        self.y_label.move(5, 5)
        self.setStyleSheet("""
            MultiETPlotWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        self.setMouseTracking(True)

    def calculate_y_range(self):
        et_data = self.get_et_data()
        if et_data is None:
            return [0, 1]

        if self.data_type in ['GazePointX', 'GazePointY']:
            return [0, 1]
        elif self.data_type == 'Velocity':
            velocities = et_data.processed_data['Velocity'].dropna()
            if velocities.empty:
                return [0, 1]
            max_velocity = np.percentile(velocities, 99)
            return [0, max_velocity * 1.1]
        elif self.data_type == 'Pupil':
            pupils = et_data.processed_data['Pupil'].dropna()
            if pupils.empty:
                return [0, 1]
            min_pupil = np.percentile(pupils, 1)
            max_pupil = np.percentile(pupils, 99)
            range_pupil = max_pupil - min_pupil
            return [min_pupil - range_pupil * 0.1, max_pupil + range_pupil * 0.1]
        else:  # Fixation, Saccade, Blink
            return [0, 1]

    def get_et_data(self):
        return self.multi_data.data_list[self.data_index]

    def set_current_time(self, time):
        self.current_time = time
        self.update()

    def paintEvent(self, event):
        if not self.is_visible():
            return
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.draw_background(painter)
        self.draw_axes(painter)
        self.draw_grid(painter)
        self.draw_data(painter)
        self.draw_events(painter)
        self.draw_time_axis(painter)
        self.draw_y_axis(painter)
        self.draw_crosshair(painter)
        # self.draw_current_time(painter)

    def draw_current_time(self, painter):
        if self.time_range[0] <= self.current_time <= self.time_range[1]:
            x = self.transformer.time_to_x(self.current_time)
            painter.setPen(QPen(Qt.red, 2))
            painter.drawLine(x, self.top_margin, x, self.height() - self.bottom_margin)

    def draw_background(self, painter):
        painter.fillRect(self.rect(), QColor(245, 240, 255))
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

        if self.data_type in ['Fixation', 'Saccade', 'Blink']:
            return
        
        y_interval = (self.y_range[1] - self.y_range[0]) / 2
        for y in np.arange(self.y_range[0], self.y_range[1] + y_interval, y_interval):
            y_pos = self.transformer.value_to_y(y)
            painter.drawLine(self.left_margin, y_pos, self.width() - self.right_margin, y_pos)

        painter.setClipping(False)

    def draw_data(self, painter):
        if self.data_type in ['GazePointX', 'GazePointY', 'Pupil', 'Velocity']:
            self.draw_waveform(painter)
        elif self.data_type in ['Fixation', 'Saccade', 'Blink']:
            self.draw_events_data(painter)

    def draw_waveform(self, painter):
        et_data = self.get_et_data()
        if et_data is None:
            return

        data_start_time = et_data.get_start_time()
        data_end_time = et_data.processed_data['Timestamp'].max()

        extra_time = 0.1  
        start_index = int((max(self.time_range[0], data_start_time) - data_start_time) * et_data.sample_rate)
        end_index = int((min(self.time_range[1] + extra_time, data_end_time) - data_start_time) * et_data.sample_rate)
        
        start_index = max(0, start_index)
        end_index = min(end_index, len(et_data.processed_data))
        
        data = et_data.processed_data[self.data_type][start_index:end_index].values
        time = et_data.processed_data['Timestamp'][start_index:end_index].values

        time_range = self.time_range[1] - self.time_range[0]
        pixels_per_second = (self.width() - self.left_margin - self.right_margin) / time_range

        target_points = int((self.width() - self.left_margin - self.right_margin) / 2)
        data_downsampled, time_downsampled = self.simple_downsample(data, time, target_points)

        painter.setPen(QPen(ThemeColor.PRIMARY.color(), 1))
        path = QPainterPath()
        started = False

        for i in range(len(time_downsampled)):
            if np.isnan(data_downsampled[i]):
                if started:
                    painter.drawPath(path)
                    path = QPainterPath()
                    started = False
            else:
                screen_x = self.transformer.time_to_x(time_downsampled[i])
                screen_y = self.transformer.value_to_y(data_downsampled[i])
                
                if not started:
                    path.moveTo(screen_x, screen_y)
                    started = True
                else:
                    path.lineTo(screen_x, screen_y)

        if started:
            painter.drawPath(path)

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

    def draw_events_data(self, painter):
        et_data = self.get_et_data()
        if et_data is None:
            return

        events_data = getattr(et_data, self.data_type.lower() + 's', None)
        if events_data is not None and not events_data.empty:
            for _, event in events_data.iterrows():
                if self.time_range[0] <= event['start'] <= self.time_range[1] or \
                   self.time_range[0] <= event['end'] <= self.time_range[1] or \
                   (event['start'] <= self.time_range[0] and event['end'] >= self.time_range[1]):
                    x_start = max(self.transformer.time_to_x(event['start']), self.left_margin)
                    x_end = min(self.transformer.time_to_x(event['end']), self.width() - self.right_margin)
                    y_top = self.top_margin
                    y_bottom = self.height() - self.bottom_margin
                    
                    rect = QRectF(x_start, y_top, x_end - x_start, y_bottom - y_top)
                    
                    color = ThemeColor.PRIMARY.color()
                    color.setAlpha(128)  # Semi-transparent
                    
                    painter.fillRect(rect, color)

    def draw_events(self, painter):
        visible_start = self.time_range[0]
        visible_end = self.time_range[1]

        painter.setClipRect(self.left_margin, self.top_margin, 
                            self.width() - self.left_margin - self.right_margin, 
                            self.height() - self.top_margin - self.bottom_margin)
        
        for event in self.events:
            start, end, color, name = event
            if (visible_start <= start <= visible_end) or (visible_start <= end <= visible_end) or (start <= visible_start and end >= visible_end):
                x_start = self.transformer.time_to_x(start)
                x_end = self.transformer.time_to_x(end)
                
                rect = QRectF(x_start, self.top_margin, x_end - x_start, 
                            self.height() - self.top_margin - self.bottom_margin)
                painter.fillRect(rect, self.get_qcolor(color, alpha=128))
                
                # Draw event label
                painter.setPen(QPen(self.get_qcolor(color)))
                font = FontSizeCalculator.calculate_font_size(painter, [name], self.width() - self.left_margin - self.right_margin, is_horizontal=True, start_size=8, bold=True)
                painter.setFont(font)

                text_width = painter.fontMetrics().width(name)
                text_left = max(self.left_margin, min((x_start + x_end) / 2 - text_width / 2, self.width() - self.right_margin - text_width))

                text_rect = QRectF(text_left, self.top_margin, text_width, 20)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, name)

        painter.setClipping(False)

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
            return QColor(255, 0, 0, alpha)  # Default to red

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
        if self.data_type in ['Fixation', 'Saccade', 'Blink']:
            return
        painter.setPen(QPen(ThemeColor.DARK_1.color(), 1))
        
        y_interval = (self.y_range[1] - self.y_range[0]) / 2
        labels = [f"{y:.2f}" for y in np.arange(self.y_range[0], self.y_range[1] + y_interval, y_interval)]
        
        font = FontSizeCalculator.calculate_font_size(painter, labels, self.left_margin - 5, is_horizontal=False, start_size=6)
        painter.setFont(font)
        
        for y in np.arange(self.y_range[0], self.y_range[1] + y_interval, y_interval):
            y_pos = self.transformer.value_to_y(y)
            painter.drawLine(self.left_margin - 5, y_pos, self.left_margin, y_pos)
            painter.drawText(5, y_pos + 4, f"{y:.2f}")

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
                self.mouse_moved.emit(time, value, self.channel_name)
                
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

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def get_value_at_time(self, time):
        et_data = self.get_et_data()
        if et_data is None:
            return np.nan

        if self.data_type in ['GazePointX', 'GazePointY', 'Pupil', 'Velocity']:
            data = et_data.processed_data
            closest_index = (data['Timestamp'] - time).abs().idxmin()
            return data.loc[closest_index, self.data_type]
        elif self.data_type in ['Fixation', 'Saccade', 'Blink']:
            events_data = getattr(et_data, self.data_type.lower() + 's')
            if events_data is not None and not events_data.empty:
                # Find events that contain the given time
                relevant_events = events_data[(events_data['start'] <= time) & (events_data['end'] >= time)]
                if not relevant_events.empty:
                    return 1  # Event is occurring
            return 0  # No event at this time
        else:
            return np.nan

    def update_crosshair(self, time, value):
        x = self.transformer.time_to_x(time)
        y = self.transformer.value_to_y(value)
        self.crosshair_pos = (x, y)
        self.update()

    def show_tooltip(self):
        if self.tooltip_data:
            global_pos, time, value = self.tooltip_data
            if self.data_type in ['Fixation', 'Saccade', 'Blink']:
                tooltip_text = f"时间: {time:.3f}s\n状态: {'发生中' if value == 1 else '未发生'}"
            else:
                tooltip_text = f"时间: {time:.3f}s\n值: {value:.3f}"
            
            # Adjust tooltip position to be near the intersection point
            adjusted_pos = self.mapToGlobal(QPointF(self.crosshair_pos[0] + 10, self.crosshair_pos[1] - 10).toPoint())
            QToolTip.showText(adjusted_pos, tooltip_text, self)

    def set_time_range(self, start, end):
        self.time_range = [start, end]
        self.update()

    def reset_view(self):
        et_data = self.get_et_data()
        if et_data is not None:
            self.time_range = [0, et_data.processed_data['Timestamp'].max()]
            self.y_range = self.calculate_y_range()
            self.update()

    def add_custom_event(self, event):
        self.events.append(event)
        self.update()

    def delete_custom_event(self, event):
        if event in self.events:
            self.events.remove(event)
            self.update()

    def clear_custom_events(self):
        self.events.clear()
        self.update()

    def leaveEvent(self, event):
        self.crosshair_pos = None
        self.tooltip_timer.stop()
        self.tooltip_data = None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)