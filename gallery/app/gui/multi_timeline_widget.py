from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRectF, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QWidget

from qfluentwidgets import isDarkTheme, themeColor, ToolTipFilter, ToolTipPosition

class SliderHandle(QWidget):
    """ Slider handle """

    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.setFixedSize(22, 22)
        self._radius = 5
        self.radiusAni = QPropertyAnimation(self, b'radius', self)
        self.radiusAni.setDuration(100)

    @pyqtProperty(float)
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, r):
        self._radius = r
        self.update()

    def enterEvent(self, e):
        self._startAni(6.5)

    def leaveEvent(self, e):
        self._startAni(5)

    def _startAni(self, radius):
        self.radiusAni.stop()
        self.radiusAni.setStartValue(self.radius)
        self.radiusAni.setEndValue(radius)
        self.radiusAni.start()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # draw outer circle
        isDark = isDarkTheme()
        painter.setPen(QColor(0, 0, 0, 90 if isDark else 25))
        painter.setBrush(QColor(69, 69, 69) if isDark else Qt.GlobalColor.white)
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))

        # draw inner circle
        painter.setBrush(themeColor())
        painter.drawEllipse(QPoint(11, 11), self.radius, self.radius)

class MultiTimelineWidget(QWidget):
    time_range_changed = pyqtSignal(float, float)

    def __init__(self, multi_data):
        super().__init__()
        self.multi_data = multi_data
        self.total_duration = multi_data.global_duration
        self.visible_start = multi_data.global_start_time
        self.visible_duration = min(30, self.total_duration)  # Initial 30 seconds or total duration
        self.min_visible_duration = 0.1  # Minimum visible duration in seconds
        self.setMinimumHeight(40)
        self.setMouseTracking(True)
        self.dragging = False
        self.drag_start_pos = None
        self.init_ui()

    def init_ui(self):
        self.start_handle = SliderHandle(self)
        self.end_handle = SliderHandle(self)
        self._adjust_handle_pos()
        self.installEventFilter(ToolTipFilter(self, 300, ToolTipPosition.TOP))

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        
        # Draw background groove
        bg_color = QColor(255, 255, 255, 115) if isDarkTheme() else QColor(0, 0, 0, 100)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(QRectF(11, 9, self.width() - 22, 4), 2, 2)

        # Draw active part of the groove
        painter.setBrush(themeColor())
        start_pos = self.time_to_pos(self.visible_start)
        end_pos = self.time_to_pos(self.visible_start + self.visible_duration)
        painter.drawRoundedRect(QRectF(start_pos, 9, end_pos - start_pos, 4), 2, 2)

    def time_to_pos(self, time):
        return 11 + ((time - self.multi_data.global_start_time) / self.total_duration) * (self.width() - 22)

    def pos_to_time(self, pos):
        return self.multi_data.global_start_time + max(0, min(((pos - 11) / (self.width() - 22)) * self.total_duration, self.total_duration))

    def _adjust_handle_pos(self):
        start_pos = int(self.time_to_pos(self.visible_start))
        end_pos = int(self.time_to_pos(self.visible_start + self.visible_duration))
        self.start_handle.move(start_pos - 11, 0)
        self.end_handle.move(end_pos - 11, 0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.x() - self.drag_start_pos.x()
            delta_time = self.pos_to_time(event.x()) - self.pos_to_time(self.drag_start_pos.x())
            
            new_start = max(self.multi_data.global_start_time, min(self.visible_start + delta_time, self.multi_data.global_end_time - self.visible_duration))
            self.visible_start = new_start
            
            self._adjust_handle_pos()
            self.update()
            self.time_range_changed.emit(self.visible_start, self.visible_start + self.visible_duration)
            
            self.drag_start_pos = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def wheelEvent(self, event):
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        
        new_duration = max(self.min_visible_duration, min(self.visible_duration / zoom_factor, self.total_duration))
        
        # If we've reached the minimum duration, don't zoom further
        if new_duration == self.min_visible_duration and self.visible_duration == self.min_visible_duration:
            return

        # Calculate new start time to keep the center of the visible range fixed
        center_time = self.visible_start + self.visible_duration / 2
        new_start = center_time - new_duration / 2
        
        # Ensure new start time is within bounds
        new_start = max(self.multi_data.global_start_time, min(new_start, self.multi_data.global_end_time - new_duration))
        
        self.visible_start = new_start
        self.visible_duration = new_duration
        
        self._adjust_handle_pos()
        self.update()
        self.time_range_changed.emit(self.visible_start, self.visible_start + self.visible_duration)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_handle_pos()

    def update_time_range_from_plot(self, start, end):
        self.visible_start = start
        self.visible_duration = max(self.min_visible_duration, end - start)
        self._adjust_handle_pos()
        self.update()