import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QTableWidgetItem
)
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, QPen, QPolygon
from PyQt5.QtCore import (
    QTimer, QThreadPool, QRunnable, pyqtSignal, QObject, Qt, QPoint, QRect, QSize
)
from qfluentwidgets import (
    ToolButton, Slider, FluentIcon, StrongBodyLabel, BodyLabel, LineEdit,
    PushButton, PrimaryPushButton, TableWidget, CardWidget, InfoBar,
    InfoBarPosition
)


class WorkerSignals(QObject):
    finished = pyqtSignal(np.ndarray, dict)
    error = pyqtSignal(str)


class FrameProcessor(QRunnable):
    def __init__(self, video_path, frame_number, et_data, fps):
        super().__init__()
        self.video_path = video_path
        self.frame_number = frame_number
        self.et_data = et_data
        self.fps = fps
        self.signals = WorkerSignals()

    def run(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise IOError("Cannot Open Video File")

            cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_number)
            ret, frame = cap.read()
            cap.release()

            if not ret:
                raise IOError(f"Cannot Read Frame {self.frame_number}")

            current_time = self.frame_number / self.fps
            gaze_data = self.get_gaze_data_at_time(current_time)
            self.signals.finished.emit(frame, gaze_data)
        except Exception as e:
            self.signals.error.emit(str(e))

    def get_gaze_data_at_time(self, time):
        if self.et_data.raw_data is None or self.et_data.raw_data.empty:
            return {}

        closest_data = self.et_data.raw_data.iloc[
            (self.et_data.raw_data['Timestamp'] - time).abs().argsort()[:1]
        ]
        return closest_data.iloc[0].to_dict() if not closest_data.empty else {}


class ClickableSlider(Slider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            position = event.pos()
            slider_length = self.width() - self.handle.width()
            value = int(
                (position.x() / slider_length) *
                (self.maximum() - self.minimum()) +
                self.minimum()
            )
            self.setValue(value)
            self.sliderReleased.emit()
            # print(f"Slider clicked. New value set to: {value}")  # Debug
        super().mousePressEvent(event)


class OverlayWidget(QWidget):
    aoi_updated = pyqtSignal(list)  # Emit list of QPoint

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Enable mouse events
        self.setStyleSheet("background-color: transparent;")
        self.aoi_collection_mode = False
        self.aoi_points = []
        self.aoi_polygon = None
        self.gaze_history = []
        self.dragging = False
        self.dragging_point_index = -1
        self.point_radius = 10  # Radius for detecting point clicks

        # Variables for preview AOI
        self.current_time = 0
        self.preview_aoi = None
        self.preview_start_time = None
        self.preview_end_time = None

    def set_current_time(self, current_time):
        self.current_time = current_time
        # print(f"OverlayWidget: Current time set to {self.current_time}")  # Debug
        self.update()

    def set_preview_aoi(self, coordinates, start_time, end_time):
        self.preview_aoi = coordinates  # Expecting list of tuples [(x1, y1), (x2, y2), ...]
        self.preview_start_time = start_time
        self.preview_end_time = end_time
        # print(f"OverlayWidget: Preview AOI set with coordinates={coordinates}, "
        #       f"start_time={start_time}, end_time={end_time}")  # Debug
        self.update()

    def clear_preview_aoi(self):
        self.preview_aoi = None
        self.preview_start_time = None
        self.preview_end_time = None
        # print("OverlayWidget: Preview AOI cleared")  # Debug
        self.update()

    def set_aoi_collection_mode(self, mode):
        self.aoi_collection_mode = mode
        if mode:
            self.clear_aoi()
        # print(f"OverlayWidget: AOI collection mode set to {self.aoi_collection_mode}")  # Debug
        self.update()

    def set_aoi_points(self, points):
        self.aoi_points = points
        self.calculate_polygon()
        self.aoi_updated.emit(self.aoi_points)
        # print(f"OverlayWidget: AOI points set to {self.aoi_points}")  # Debug 
        self.update()

    def set_aoi_polygon(self, polygon):
        self.aoi_polygon = polygon
        # print(f"OverlayWidget: AOI polygon set to {self.aoi_polygon}")  # Debug
        self.update()

    def set_gaze_history(self, gaze_history):
        self.gaze_history = gaze_history.copy()
        # print(f"OverlayWidget: Gaze history updated with {len(gaze_history)} points")  # Debug
        self.update()

    def clear_aoi(self):
        self.aoi_points = []
        self.aoi_polygon = None
        self.aoi_updated.emit(self.aoi_points)
        # print("OverlayWidget: AOI points and polygon cleared")  # Debug
        self.update()

    def calculate_polygon(self):
        if len(self.aoi_points) >= 3:
            # Convert QPoint to list of [x, y]
            points = np.array([[p.x(), p.y()] for p in self.aoi_points], dtype=np.int32)
            hull = cv2.convexHull(points)
            hull_points = [QPoint(x, y) for x, y in hull.squeeze()]
            self.aoi_polygon = hull_points
            # print(f"OverlayWidget: Convex hull calculated with {len(hull_points)} points")  # Debug
        else:
            self.aoi_polygon = None
            # print("OverlayWidget: Not enough points to calculate convex hull")  # Debug

    def find_point_at_pos(self, pos, scale_x, scale_y):
        for index, point in enumerate(self.aoi_points):
            # Convert frame coordinates to widget coordinates
            scaled_x = point.x() * scale_x
            scaled_y = point.y() * scale_y
            dist = np.hypot(pos.x() - scaled_x, pos.y() - scaled_y)
            if dist <= self.point_radius:
                # print(f"OverlayWidget: Point found at index {index}")  # Debug
                return index
        # print("OverlayWidget: No point found at the clicked position")  # Debug
        return -1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            parent = self.parent().parent()
            if hasattr(parent, 'original_frame_size') and hasattr(parent, 'video_display_rect'):
                scale_x = self.width() / parent.original_frame_size.width()
                scale_y = self.height() / parent.original_frame_size.height()
            else:
                scale_x = 1
                scale_y = 1

            point_index = self.find_point_at_pos(pos, scale_x, scale_y)
            if self.aoi_collection_mode:
                if point_index == -1:
                    # Add new point
                    pos_frame_x = pos.x() / scale_x
                    pos_frame_y = pos.y() / scale_y
                    new_point = QPoint(int(pos_frame_x), int(pos_frame_y))
                    self.aoi_points.append(new_point)
                    # print(f"OverlayWidget: New AOI point added at ({new_point.x()}, {new_point.y()})")  # Debug
                    self.calculate_polygon()
                    self.aoi_updated.emit(self.aoi_points)
                    self.update()
                else:
                    # Start dragging
                    self.dragging = True
                    self.dragging_point_index = point_index
                    # print(f"OverlayWidget: Started dragging point at index {point_index}")  # Debug
            else:
                if point_index != -1:
                    # Start dragging
                    self.dragging = True
                    self.dragging_point_index = point_index
                    # print(f"OverlayWidget: Started dragging point at index {point_index}")  # Debug
        elif event.button() == Qt.RightButton:
            pos = event.pos()
            parent = self.parent().parent()
            if hasattr(parent, 'original_frame_size') and hasattr(parent, 'video_display_rect'):
                scale_x = self.width() / parent.original_frame_size.width()
                scale_y = self.height() / parent.original_frame_size.height()
            else:
                scale_x = 1
                scale_y = 1

            point_index = self.find_point_at_pos(pos, scale_x, scale_y)
            if point_index != -1:
                # Remove the point
                removed_point = self.aoi_points.pop(point_index)
                # print(f"OverlayWidget: AOI point at index {point_index} removed")  # Debug
                self.calculate_polygon()
                self.aoi_updated.emit(self.aoi_points)
                self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and self.dragging_point_index != -1:
            pos = event.pos()
            parent = self.parent().parent()
            if hasattr(parent, 'original_frame_size') and hasattr(parent, 'video_display_rect'):
                scale_x = self.width() / parent.original_frame_size.width()
                scale_y = self.height() / parent.original_frame_size.height()
            else:
                scale_x = 1
                scale_y = 1

            # Convert widget coordinates to frame coordinates
            pos_frame_x = pos.x() / scale_x
            pos_frame_y = pos.y() / scale_y

            # Ensure the point stays within frame boundaries
            pos_frame_x = max(0, min(pos_frame_x, parent.original_frame_size.width()))
            pos_frame_y = max(0, min(pos_frame_y, parent.original_frame_size.height()))

            # Update point
            self.aoi_points[self.dragging_point_index] = QPoint(int(pos_frame_x), int(pos_frame_y))
            # print(f"OverlayWidget: AOI point at index {self.dragging_point_index} moved to ({int(pos_frame_x)}, {int(pos_frame_y)})")  # Debug
            self.calculate_polygon()
            self.aoi_updated.emit(self.aoi_points)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            # print(f"OverlayWidget: Stopped dragging point at index {self.dragging_point_index}")  # Debug
            self.dragging = False
            self.dragging_point_index = -1
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        parent = self.parent().parent()
        if not (self.aoi_collection_mode or self.aoi_polygon or self.gaze_history or self.preview_aoi):
            return

        video_width = parent.original_frame_size.width()
        video_height = parent.original_frame_size.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate scaling factors
        if hasattr(parent, 'original_frame_size') and hasattr(parent, 'video_display_rect'):
            scale_x = self.width() / parent.original_frame_size.width()
            scale_y = self.height() / parent.original_frame_size.height()

            # Draw AOI Polygon
            if self.aoi_polygon:
                scaled_polygon = QPolygon([
                    QPoint(int(p.x() * scale_x), int(p.y() * scale_y)) for p in self.aoi_polygon
                ])
                painter.setPen(QPen(QColor(255, 0, 0, 128), 2))
                painter.setBrush(QColor(255, 0, 0, 64))
                painter.drawPolygon(scaled_polygon)
                # print("OverlayWidget: AOI polygon drawn")  # Debug

            # Draw AOI Points
            if self.aoi_points:
                for point in self.aoi_points:
                    # Convert frame coordinates to widget coordinates
                    scaled_point = QPoint(int(point.x() * scale_x), int(point.y() * scale_y))
                    painter.setPen(QPen(Qt.red, 2))
                    painter.setBrush(QColor(255, 0, 0))
                    painter.drawEllipse(scaled_point, self.point_radius, self.point_radius)

            # Draw Preview AOI if within time range
            if self.preview_aoi and self.preview_start_time is not None and self.preview_end_time is not None:
                if self.preview_start_time <= self.current_time <= self.preview_end_time:
                    try:
                        scaled_polygon = QPolygon([
                            QPoint(int(x * scale_x * video_width), int(y * scale_y * video_height)) for x, y in self.preview_aoi
                        ])

                        painter.setPen(QPen(QColor(255, 0, 0, 128), 2))
                        painter.setBrush(QColor(255, 0, 0, 64))
                        painter.drawPolygon(scaled_polygon)
                    except Exception as e:
                        print(f"Draw Preview AOI Wrong: {str(e)}")

            # Draw Gaze History
            if self.gaze_history:
                # Fixed radius for gaze circles
                fixed_radius = 30  # Adjust as needed

                # Pen for connecting lines
                line_pen = QPen(QColor(255, 50, 50, 200), 2)
                painter.setPen(line_pen)

                # Draw lines between consecutive gaze points
                for i in range(1, len(self.gaze_history)):
                    prev_point = self.gaze_history[i - 1]
                    current_point = self.gaze_history[i]
                    scaled_prev = QPoint(int(prev_point[0] * scale_x), int(prev_point[1] * scale_y))
                    scaled_current = QPoint(int(current_point[0] * scale_x), int(current_point[1] * scale_y))
                    painter.drawLine(scaled_prev, scaled_current)
                # print(f"OverlayWidget: {len(self.gaze_history) - 1} gaze lines drawn")  # Debug

                # Reset pen for circles
                circle_pen = QPen(QColor(255, 50, 50, 150), 2)
                circle_brush = QColor(255, 50, 50, 50)
                painter.setPen(circle_pen)
                painter.setBrush(circle_brush)

                for point in self.gaze_history:
                    scaled_x = int(point[0] * scale_x)
                    scaled_y = int(point[1] * scale_y)
                    center = QPoint(scaled_x, scaled_y)

                    # Ensure the circle is within the video display boundaries
                    # Adjust position if necessary
                    if scaled_x - fixed_radius < 0:
                        center.setX(fixed_radius)
                    elif scaled_x + fixed_radius > self.width():
                        center.setX(self.width() - fixed_radius)

                    if scaled_y - fixed_radius < 0:
                        center.setY(fixed_radius)
                    elif scaled_y + fixed_radius > self.height():
                        center.setY(self.height() - fixed_radius)

                    painter.drawEllipse(center, fixed_radius, fixed_radius)
                # print(f"OverlayWidget: {len(self.gaze_history)} gaze circles drawn")  # Debug

            # # Draw Preview AOI if within time range
            # if self.preview_aoi and self.preview_start_time is not None and self.preview_end_time is not None:
            #     if self.preview_start_time <= self.current_time <= self.preview_end_time:
            #         try:
            #             scaled_polygon = QPolygon([
            #                 QPoint(int(x * scale_x), int(y * scale_y)) for x, y in self.preview_aoi
            #             ])

            #             painter.setPen(QPen(QColor(0, 255, 0, 128), 2))
            #             painter.setBrush(QColor(0, 255, 0, 64))
            #             painter.drawPolygon(scaled_polygon)
            #             # print("OverlayWidget: Preview AOI polygon drawn")  # Debug
            #         except Exception as e:
            
            # # Draw AOI Polygon
            # if self.aoi_polygon:
            #     scaled_polygon = QPolygon([
            #         QPoint(int(p.x() * scale_x), int(p.y() * scale_y)) for p in self.aoi_polygon
            #     ])
            #     painter.setPen(QPen(QColor(255, 0, 0, 128), 2))
            #     painter.setBrush(QColor(255, 0, 0, 64))
            #     painter.drawPolygon(scaled_polygon)
            #     print("OverlayWidget: AOI polygon drawn")  # Debug

        else:
            # If parent does not have original_frame_size or video_display_rect, do nothing
            pass


class ETPlayer(QWidget):
    def __init__(self, et_data, et_viewer):
        super().__init__()
        self.et_data = et_data
        self.et_viewer = et_viewer
        self.setWindowTitle("ET Player")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.layout = QVBoxLayout(self)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.video_label)

        self.controls_layout = QHBoxLayout()
        self.play_button = ToolButton()
        self.play_button.setIcon(FluentIcon.PLAY)
        self.play_button.clicked.connect(self.play_pause)
        self.controls_layout.addWidget(self.play_button)

        self.time_slider = ClickableSlider(Qt.Horizontal)
        self.time_slider.sliderPressed.connect(self.slider_pressed)
        self.time_slider.sliderReleased.connect(self.slider_released)
        self.controls_layout.addWidget(self.time_slider)

        self.progress_label = StrongBodyLabel()
        self.progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.progress_label.setFixedWidth(120)
        self.controls_layout.addWidget(self.progress_label)

        self.layout.addLayout(self.controls_layout)

        self.video_path = self.et_data.get_video_path()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30

        self.threadpool = QThreadPool()
        self.gaze_history = []
        self.max_history = 10
        self.last_valid_gaze = None
        self.color_accumulation = None
        self.is_slider_pressed = False

        self.preview_aoi = None
        self.aoi_start_time = None
        self.aoi_end_time = None

        self.aoi_collection_mode = False
        self.aoi_callback = None

        # Initialize OverlayWidget
        self.overlay = OverlayWidget(self.video_label)
        self.overlay.aoi_updated.connect(self.on_aoi_updated)
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Enable mouse events
        self.overlay.raise_()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_overlay)
        self.update_timer.start(50)  # Update every 50 milliseconds

        self.initialize_video()

    def initialize_video(self):
        if self.video_path and os.path.exists(self.video_path):
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                print("ETPlayer: Cannot Open Video File")
                return
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS) or 30

            ret, frame = cap.read()
            if ret:
                self.display_frame(frame, {})
                # print(f"ETPlayer: Initial frame displayed")  # Debug

                # Store original frame size
                height, width, _ = frame.shape
                self.original_frame_size = QSize(width, height)
                # print(f"ETPlayer: Original frame size set to {self.original_frame_size}")  # Debug

            cap.release()
            self.time_slider.setRange(0, self.total_frames - 1)
            print(f"ETPlayer: Video loaded successfully. Total frames: {self.total_frames}, FPS: {self.fps}")  # Debug
            self.update_progress_label()
        else:
            print("ETPlayer: Cannot Find Video File")

    def on_aoi_updated(self, aoi_points):
        if len(aoi_points) >= 3 and not self.aoi_collection_mode:
            relative_coords = self.pixel_to_relative_coords(aoi_points)
            print(f"ETPlayer: AOI updated with relative coordinates: {relative_coords}")  # Debug
            if self.aoi_callback:
                self.aoi_callback(relative_coords)
                print(f"ETPlayer: AOI callback executed with coordinates: {relative_coords}")  # Debug

    def update_overlay(self):
        self.overlay.update()

    def start_aoi_collection(self, callback):
        self.aoi_collection_mode = True
        self.aoi_callback = callback
        self.overlay.set_aoi_collection_mode(True)
        self.overlay.clear_aoi()
        print("ETPlayer: AOI collection mode started")  # Debug
        self.overlay.update()

    def stop_aoi_collection(self):
        self.aoi_collection_mode = False
        self.overlay.set_aoi_collection_mode(False)
        print("ETPlayer: AOI collection mode stopped")  # Debug
        if len(self.overlay.aoi_points) >= 3:
            relative_coords = self.pixel_to_relative_coords(self.overlay.aoi_points)
            print(f"ETPlayer: Collected AOI coordinates: {relative_coords}")  # Debug
            if self.aoi_callback:
                self.aoi_callback(relative_coords)
                print("ETPlayer: AOI callback executed after collection")  # Debug
        # Clear AOI drawing
        self.overlay.clear_aoi()
        self.aoi_callback = None
        self.overlay.update()

    def set_aoi_time_range(self, start_time, end_time):
        self.aoi_start_time = start_time
        self.aoi_end_time = end_time
        print(f"ETPlayer: AOI time range set to {self.aoi_start_time} - {self.aoi_end_time}")  # Debug
        self.overlay.update()

    def start_aoi_preview(self, coordinates, start_time, end_time):
        if not isinstance(coordinates, list):
            raise TypeError("Coordinates Must Be A List")
        if len(coordinates) % 2 != 0:
            raise ValueError("Num Of Coordinates Must Be Even, Indicating Points")
        relative_coords = [(coordinates[i], coordinates[i + 1]) for i in range(0, len(coordinates), 2)]
        print(f"ETPlayer: Starting AOI preview with coordinates={relative_coords}, start_time={start_time}, end_time={end_time}")  # Debug

        if start_time is None:
            start_time = 0.0
            print("ETPlayer: start_time is None, set to 0.0")  # Debug
        if end_time is None:
            end_time = self.total_frames / self.fps if self.fps > 0 else 30.0  
            print(f"ETPlayer: end_time is None, set to {end_time}")  # Debug

        self.overlay.set_preview_aoi(relative_coords, start_time, end_time)
        print(f"ETPlayer: AOI preview set in OverlayWidget")  # Debug

        self.refresh_current_frame()

    def stop_aoi_preview(self):
        self.overlay.clear_preview_aoi()
        print("ETPlayer: AOI preview stopped")  # Debug

        self.refresh_current_frame()

    def refresh_current_frame(self):
        if self.video_path is not None:
            print(f"ETPlayer: Refreshing current frame {self.current_frame}")  # Debug
            self.process_frame_at(self.current_frame)

    def play_pause(self):
        if self.video_path is None:
            print("ETPlayer: No video to play/pause")  # Debug
            return

        if self.playing:
            self.timer.stop()
            self.play_button.setIcon(FluentIcon.PLAY)
            print("ETPlayer: Playback paused")  # Debug
        else:
            self.timer.start(int(1000 / self.fps))
            self.play_button.setIcon(FluentIcon.PAUSE)
            print("ETPlayer: Playback started")  # Debug
        self.playing = not self.playing

    def update_progress_label(self):
        current_time = self.current_frame / self.fps
        total_time = self.total_frames / self.fps
        self.progress_label.setText(f"{self.format_time(current_time)} / {self.format_time(total_time)}")
        print(f"ETPlayer: Progress label updated to {current_time:.2f} / {total_time:.2f}")  # Debug

    def format_time(self, seconds):
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def display_frame(self, frame, gaze_data):
        try:
            frame = self.process_gaze_data(frame, gaze_data)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            label_size = self.video_label.size()
            scaled_pixmap = pixmap.scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)

            # Calculate the actual video display rect
            video_rect = QRect(
                max((label_size.width() - scaled_pixmap.width()) // 2, 0),
                max((label_size.height() - scaled_pixmap.height()) // 2, 0),
                scaled_pixmap.width(),
                scaled_pixmap.height()
            )
            self.video_display_rect = video_rect

            # Ensure no negative sizes are set
            if video_rect.height() < 0 or video_rect.width() < 0:
                print(f"ETPlayer: Warning - Negative video_rect dimensions encountered: {video_rect}")  # Debug
                video_rect = QRect(0, 0, max(scaled_pixmap.width(), 0), max(scaled_pixmap.height(), 0))
                self.video_display_rect = video_rect

            # Update overlay size and position
            self.overlay.setGeometry(video_rect)

            print(f"ETPlayer: Frame displayed. Original size: {w}x{h}, Display size: {scaled_pixmap.width()}x{scaled_pixmap.height()}")  # Debug

            # Update gaze history on overlay
            self.overlay.set_gaze_history(self.gaze_history)
        except Exception as e:
            print(f"ETPlayer: Error displaying frame: {str(e)}")  # Debug

    def process_gaze_data(self, frame, gaze_data):
        if not gaze_data:
            print("ETPlayer: No gaze data for this frame")  # Debug
            return frame

        frame_height, frame_width = frame.shape[:2]
        x_rel = gaze_data.get('GazePointX')
        y_rel = gaze_data.get('GazePointY')

        if x_rel is not None and y_rel is not None and not (np.isnan(x_rel) or np.isnan(y_rel)):
            x = int(x_rel * frame_width)
            y = int(y_rel * frame_height)
            self.last_valid_gaze = (x, y)
            print(f"ETPlayer: Valid gaze data - x: {x}, y: {y}")  # Debug

            self.gaze_history.append((x, y))
            if len(self.gaze_history) > self.max_history:
                self.gaze_history.pop(0)
        elif self.last_valid_gaze:
            x, y = self.last_valid_gaze
            self.gaze_history.append((x, y))
            if len(self.gaze_history) > self.max_history:
                self.gaze_history.pop(0)
            print(f"ETPlayer: Reusing last valid gaze data - x: {x}, y: {y}")  # Debug
        else:
            print("ETPlayer: No valid gaze data available")  # Debug
            return frame

        # No direct drawing on the frame; gaze is handled by the overlay
        return frame

    def slider_pressed(self):
        self.is_slider_pressed = True
        if self.playing:
            self.timer.stop()
            print("ETPlayer: Slider pressed, playback paused")  # Debug

    def slider_released(self):
        self.is_slider_pressed = False
        self.current_frame = self.time_slider.value()
        print(f"ETPlayer: Slider released, current frame set to {self.current_frame}")  # Debug
        self.color_accumulation = None
        self.gaze_history.clear()
        self.process_frame_at(self.current_frame)
        if self.playing:
            self.timer.start(int(1000 / self.fps))
            print("ETPlayer: Slider released, playback resumed")  # Debug

    def update_frame(self):
        if self.video_path is None or self.et_data is None:
            print("ETPlayer: Video path or ET data is not set")  # Debug
            return

        if not self.is_slider_pressed:
            if self.current_frame < self.total_frames:
                self.process_frame_at(self.current_frame)
                print(f"ETPlayer: Processing frame {self.current_frame}")  # Debug
                self.current_frame += 1
            else:
                self.current_frame = 0
                print("ETPlayer: Reached end of video, looping to frame 0")  # Debug
        print(f"ETPlayer: Frame updated to {self.current_frame}, preview_aoi: {self.preview_aoi}")  # Debug
        self.update()

    def process_frame_at(self, frame_number):
        print(f"ETPlayer: Starting FrameProcessor for frame {frame_number}")  # Debug
        worker = FrameProcessor(self.video_path, frame_number, self.et_data, self.fps)
        worker.signals.finished.connect(self.process_frame)
        worker.signals.error.connect(self.handle_error)
        self.threadpool.start(worker)

    def process_frame(self, frame, gaze_data):
        print(f"ETPlayer: FrameProcessor finished for frame {self.current_frame}")  # Debug
        self.display_frame(frame, gaze_data)
        self.time_slider.setValue(self.current_frame)
        self.update_progress_label()
        current_time = self.current_frame / self.fps
        self.overlay.set_current_time(current_time)
        self.et_viewer.set_current_time(current_time)

        # Update overlay
        self.overlay.update()

    def handle_error(self, error_message):
        print(f"ETPlayer: Error from FrameProcessor: {error_message}")  # Debug

    def closeEvent(self, event):
        self.timer.stop()
        print("ETPlayer: Application closed, timer stopped")  # Debug

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'video_label') and self.video_label.pixmap():
            print("ETPlayer: Window resized, refreshing current frame")  # Debug
            self.display_frame(self.get_current_frame(), {})  # Clear gaze data display

    def get_current_frame(self):
        cap = cv2.VideoCapture(self.video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = cap.read()
        cap.release()
        if ret:
            print(f"ETPlayer: Retrieved frame {self.current_frame} from video")  # Debug
        else:
            print(f"ETPlayer: Failed to retrieve frame {self.current_frame} from video")  # Debug
        return frame if ret else None

    def pixel_to_relative_coords(self, points):
        if hasattr(self, 'original_frame_size'):
            width = self.original_frame_size.width()
            height = self.original_frame_size.height()
            relative_coords = [coord for point in points for coord in (point.x() / width, point.y() / height)]
            print(f"ETPlayer: Converted pixel coordinates to relative coordinates: {relative_coords}")  # Debug
            return relative_coords
        print("ETPlayer: Original frame size not set, cannot convert to relative coordinates")  # Debug
        return []

    def draw_gaze_overlay(self):
        # This method can be expanded if additional gaze overlay features are needed
        pass

    def update_overlay(self):
        self.overlay.update()


def main():
    app = QApplication(sys.argv)
    # Mocked et_data and et_viewer for demonstration purposes
    class ETAOI:
        def __init__(self, name, coordinates, start_time, end_time):
            self.name = name
            self.coordinates = coordinates  # List of tuples [(x1, y1), (x2, y2), ...]
            self.start_time = start_time
            self.end_time = end_time

    class ETData:
        def __init__(self):
            # Replace with actual data loading logic
            # Example structure with Timestamp, GazePointX, GazePointY
            self.raw_data = None  # Replace with actual pandas DataFrame
            self.aois = []

        def get_video_path(self):
            return "path_to_your_video.mp4"  # Replace with actual video path

        def add_aoi(self, name, coordinates, start_time, end_time):
            new_aoi = ETAOI(name, coordinates, start_time, end_time)
            self.aois.append(new_aoi)
            print(f"ETData: AOI '{name}' added")  # Debug

        def get_aois(self):
            return self.aois

        def delete_aoi(self, aoi):
            if aoi in self.aois:
                self.aois.remove(aoi)
                print(f"ETData: AOI '{aoi.name}' deleted")  # Debug

    class ETViewer:
        def set_current_time(self, time):
            print(f"ETViewer: Current time set to {time}")  # Debug
            pass  # Implement as needed

    et_data = ETData()
    et_viewer = ETViewer()
    player = ETPlayer(et_data, et_viewer)
    player.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
