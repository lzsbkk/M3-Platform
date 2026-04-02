from PyQt5.QtCore import Qt, pyqtSignal,QSize,QTimer
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor,QPixmap, QResizeEvent,QImage,QPainter
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget, QFrame, QTableWidgetItem, QDialog,QDesktopWidget,
                             QMainWindow, QSizePolicy, QStackedWidget, QLabel, QColorDialog,QFileDialog,QTreeWidgetItem)
from qfluentwidgets import (CheckBox,InfoBar, InfoBarPosition, StrongBodyLabel, SmoothScrollArea, Pivot, TreeWidget,
                            CardWidget, LineEdit, BodyLabel, ExpandLayout, InfoBarIcon, 
                            ColorDialog, Theme, setTheme, PushButton, ComboBox, SpinBox, 
                            TableWidget, IconWidget, FluentIcon, ToolTipFilter, ToolTipPosition, PillToolButton)

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QProgressBar
from qfluentwidgets import (
    CardWidget, StrongBodyLabel, PrimaryPushButton, InfoBar, 
    InfoBarPosition, ProgressRing
)

from .gallery_interface import GalleryInterface
from ..common.translator import Translator
from ..common.style_sheet import StyleSheet
from ..gui.eyetracking_viewer_widget import EyeTrackingViewerWidget
from ..gui.et_player import ETPlayer
from ..data.et_data import ETData
from ..common.monitor import PerformanceMonitor

import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import os
import io
import sys

class ImageViewerDialog(QDialog):
    
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        self.setup_ui()
        # setTheme(Theme.DARK)
        QTimer.singleShot(0, self.update_image)

    def setup_ui(self):
        self.setWindowTitle("Image Viewer")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_widget = QWidget(self)
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(10, 10, 10, 10)

        save_button = PrimaryPushButton("Save Image", self)
        save_button.clicked.connect(self.save_image)
        top_layout.addWidget(save_button, alignment=Qt.AlignLeft)
        top_layout.addStretch()

        main_layout.addWidget(top_widget)

        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.enableTransparentBackground()
        main_layout.addWidget(self.scroll_area)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)

        self.set_initial_size()

    def set_initial_size(self):
        screen = QDesktopWidget().availableGeometry()
        max_width = int(screen.width() * 0.8)
        max_height = int(screen.height() * 0.8)
        self.resize(max_width, max_height)
        self.center_window()

    def center_window(self):
        frame = self.frameGeometry()
        center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

    def update_image(self):
        if isinstance(self.image, plt.Figure):
            buf = io.BytesIO()
            self.image.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
        elif isinstance(self.image, QPixmap):
            pixmap = self.image
        else:
            raise ValueError("Unsupported image type")

        scroll_size = self.scroll_area.viewport().size()
        scaled_pixmap = pixmap.scaled(scroll_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def save_image(self):
        # file_path, selected_filter = QFileDialog.getSaveFileName(
        #     "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;SVG Files (*.svg);;All Files (*)"
        # )
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Image", "", 
            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;SVG Files (*.svg);;All Files (*)"
        )
        
        if file_path:
            try:
                if isinstance(self.image, plt.Figure):
                    if selected_filter == "PNG Files (*.png)":
                        format = 'png'
                    elif selected_filter == "JPEG Files (*.jpg *.jpeg)":
                        format = 'jpg'
                    elif selected_filter == "SVG Files (*.svg)":
                        format = 'svg'
                    else:
                        format = 'png'
                    
                    if not file_path.lower().endswith(f'.{format}'):
                        file_path += f'.{format}'
                    
                    self.image.savefig(file_path, format=format, dpi=300, bbox_inches='tight')
                else:
                    if selected_filter == "SVG Files (*.svg)":
                        raise ValueError("Error Solution: QPixmap SVG Export Limitation")
                    format = 'PNG' if selected_filter == "PNG Files (*.png)" else 'JPEG'
                    self.image.save(file_path, format)

                # InfoBar.success(
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.success(
                    title='Success',
                    content="Image Successfully Saved",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            except Exception as e:
                # InfoBar.error(
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.error(
                    title='Error',
                    content=f"Faile To Save: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.update_image)

class CombinedETWidget(QWidget):
    
    def __init__(self, et_data, viewer, player):
        super().__init__()
        self.et_data = et_data
        self.layout = QVBoxLayout(self)
        self.viewer = viewer
        self.player = player
        
        self.layout.addWidget(self.player, 2)
        self.layout.addWidget(self.viewer, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

class ETInterface(GalleryInterface):
    
    def __init__(self, parent=None, data_file_path=None, et_data=None, db_info=None):
        t = Translator()
        super().__init__(
            title='',
            subtitle='',
            parent=parent
        )
        self.setObjectName('ETInterface')

        self.data_file_path = data_file_path
        self.db_info = db_info

        subject_data = self.get_subject_data()

        self.experiment = subject_data['experiment_name']
        self.name = subject_data['name']
        self.age = subject_data['age']
        self.output_path = subject_data['full_output_path']

        if et_data is None:
            self.et_data = ETData(file_path=self.data_file_path, output_path=self.output_path, db_info=self.db_info)
        else:
            self.et_data = et_data
        
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        left_column = QWidget()
        right_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        right_layout = QVBoxLayout(right_column)

        left_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.et_viewer=EyeTrackingViewerWidget(self.et_data)
        self.et_player=ETPlayer(self.et_data,self.et_viewer)
        
        self.combined_et_widget = CombinedETWidget(self.et_data,self.et_viewer,self.et_player)
        
        # left_layout.addWidget(self.createExampleCard(title='  ET Data', widget=self.combined_et_widget))
        right_layout.addWidget(self.createExampleCard(title='  ET Data', widget=self.combined_et_widget))

        self.pivot_interface = PivotInterface(self, et_data=self.et_data,et_viewer=self.et_viewer,et_player=self.et_player)
        # right_layout.addWidget(self.pivot_interface, 1)
        left_layout.addWidget(self.pivot_interface, 1)

        main_layout.addWidget(left_column, 1)  
        main_layout.addWidget(right_column, 2)  

        self.update_data_info()

    def get_subject_data(self):
        
        if not self.db_info:
            raise ValueError("db_info is not provided")

        project = self.db_info['project']
        subject_id = self.db_info['subject_id']
        subject_data = project.get_subject_data(subject_id)
        
        if subject_data:
            experiment = project.get_experiment_by_id(subject_data['experiment_id'])
            if experiment:
                subject_data['experiment_name'] = experiment['name']
            else:
                subject_data['experiment_name'] = "Unknown Experiment"
            
            subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['et_output_path'])
            
            if subject_data.get('et_data_path'):
                subject_data['et_data_path'] = os.path.join(project.base_path, subject_data['et_data_path'])
            else:
                subject_data['et_data_path'] = None

            if self.data_file_path:
                self.data_file_path = os.path.join(project.base_path, self.data_file_path)
        else:
            raise ValueError("Unable to retrieve subject data from database")
        
        return subject_data
    
    def update_data_info(self):
        
        if hasattr(self.pivot_interface, 'infoDataInterface'):
            self.pivot_interface.infoDataInterface.update_data_info(self.et_data)


    def createExampleCard(self, title, widget):
        
        card = QFrame()
        card.setObjectName("ExampleCard")
        layout = QVBoxLayout(card)
        
        title_label = StrongBodyLabel(self)
        title_label.setText(title)
        layout.addWidget(title_label)
        
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(widget)
        
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        return card

class PivotInterface(QWidget):
    
    def __init__(self, parent=None, et_data=None, et_viewer=None, et_player=None):
        super().__init__(parent=parent)
        self.et_data = et_data
        self.et_viewer = et_viewer
        self.et_player = et_player
        
        self.Eparent = parent

        self.setObjectName('PivotInterface')
        self.vBoxLayout = QVBoxLayout(self)

        self.pivot = Pivot(self)
        self.contentArea = QWidget(self)
        self.contentLayout = QVBoxLayout(self.contentArea)

        self.stackedWidget = QStackedWidget(self.contentArea)
        self.contentLayout.addWidget(self.stackedWidget, 1)

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.contentArea, 1)

        self.infoDataInterface = DataInfoInterface(self)
        self.preprocessingInterface = PreprocessingInterface(self, et_data=self.et_data, et_viewer=self.et_viewer,et_player=self.et_player)
        self.featureExtractionInterface = FeatureExtractionInterface(self,et_data=self.et_data)
        self.visualizationInterface = VisualizationInterface(self,et_data=self.et_data)

        self.addSubInterface(self.infoDataInterface, 'Data Info', 'Data Info')
        self.addSubInterface(self.preprocessingInterface, 'Process', 'Process')
        self.addSubInterface(self.featureExtractionInterface, 'Feature Analysis', 'Feature Analysis')
        self.addSubInterface(self.visualizationInterface, 'Visualization', 'Visualization')

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stackedWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.infoDataInterface)
        self.pivot.setCurrentItem(self.infoDataInterface.objectName())

    def addSubInterface(self, widget: QWidget, objectName, text):
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget)
        )

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.pivot.setCurrentItem(widget.objectName())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustContentArea()

    def adjustContentArea(self):
        pivot_height = self.pivot.sizeHint().height()
        self.contentArea.setFixedHeight(self.height() - pivot_height)
    
    def update_data_info(self, et_data):
        self.infoDataInterface.update_data_info(et_data)

    def update_processed_data_info(self, et_data):
        self.infoDataInterface.update_processed_data_info(et_data)

class DataInfoInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('dataInfoInterface')

        self.Eparent = parent

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setSpacing(10)
        # self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

        self.info_cards = {}
        self.setup_ui()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_ui(self):
        self.create_info_card("Experiment", self.Eparent.Eparent.experiment)
        self.create_info_card("Participant", self.Eparent.Eparent.name)
        self.create_info_card("Video Frame Rate", "")
        self.create_info_card("Video Duration", "") 
        self.create_info_card("Video Resolution", "")
        self.create_info_card("Data Sampling Rate", "")
        self.create_info_card("Data Completeness", "")
        self.vBoxLayout.addStretch(1)

    def create_info_card(self, title, value):
        info_card = CustomInfoCard(title, value, self)
        self.info_cards[title] = info_card
        self.vBoxLayout.addWidget(info_card)

    def update_data_info(self, et_data):
        self.info_cards["Video Frame Rate"].content = f"{et_data.fps:.2f} Hz"
        
        # Convert seconds to HH:MM:SS format
        hours, remainder = divmod(int(et_data.video_duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        self.info_cards["Video Duration"].content = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        self.info_cards["Video Resolution"].content = f"{str(et_data.resolution)}"
        self.info_cards["Data Sampling Rate"].content = f"{et_data.sample_rate:.2f} Hz"
        self.info_cards["Data Completeness"].content = f"{et_data.integrity:.2f} %"

        for card in self.info_cards.values():
            card.update_content()
    
    def update_processed_data_info(self, et_data):

        for card in self.info_cards.values():
            card.update_content()

class CustomInfoCard(CardWidget):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.title = title
        self.content = content
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        self.title_label = BodyLabel(self.title, self)
        self.content_container = LineEdit(self)
        self.content_container.setText(self.content)
        self.content_container.setReadOnly(True)
        # self.content_container.setStyleSheet("""
        #     QLineEdit {
        #         color: white;
        #         background-color: transparent;
        #         border: none;
        #         padding: 0px;
        #     }
        # """)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.content_container, alignment=Qt.AlignRight)
        layout.setContentsMargins(20, 10, 20, 10)

    def update_content(self):
        self.content_container.setText(self.content)

class PreprocessingCard(CardWidget):
    def __init__(self, parent=None, et_data=None):
        super().__init__(parent)
        self.et_data = et_data
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # layout.addWidget(title_label)

        pupil_group_label = BodyLabel("Pupil Data Preprocessing", self)
        pupil_group_label.setStyleSheet("font-weight: bold;color:black;")
        layout.addWidget(pupil_group_label)

        pupil_interpolate_layout = QHBoxLayout()
        self.pupil_interpolate_check = self.create_checkbox("Pupil Data Interpolation Threshold")
        pupil_interpolate_layout.addWidget(self.pupil_interpolate_check)
        self.pupil_gap_length = LineEdit(self)
        self.pupil_gap_length.setPlaceholderText("75")
        pupil_interpolate_layout.addWidget(self.pupil_gap_length)
        pupil_interpolate_layout.addWidget(BodyLabel("ms", self))
        layout.addLayout(pupil_interpolate_layout)

        pupil_filter_layout = QHBoxLayout()
        self.pupil_filter_check = self.create_checkbox("Pupil Data Filter")
        pupil_filter_layout.addWidget(self.pupil_filter_check)
        self.pupil_filter_method = self.create_combo_box(["Moving Average", "Moving Median"])
        pupil_filter_layout.addWidget(self.pupil_filter_method)
        self.pupil_window_size = ComboBox(self)
        self.pupil_window_size.addItems(["3", "5", "7", "9"])
        self.pupil_window_size.setCurrentIndex(0)  
        self.pupil_window_size.setFixedWidth(110)
        pupil_filter_layout.addWidget(self.pupil_window_size)
        pupil_filter_layout.addWidget(BodyLabel("Samples", self))
        layout.addLayout(pupil_filter_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        gaze_group_label = BodyLabel("Gaze Data Preprocessing", self)
        gaze_group_label.setStyleSheet("font-weight: bold;color:black;")
        layout.addWidget(gaze_group_label)

        fixation_layout = QHBoxLayout()
        fixation_layout.addWidget(BodyLabel("Fixation Detection Threshold (Angular Velocity)", self))
        self.velocity_threshold = LineEdit(self)
        self.velocity_threshold.setPlaceholderText("30")
        fixation_layout.addWidget(self.velocity_threshold)
        fixation_layout.addWidget(BodyLabel("°/s", self))
        layout.addLayout(fixation_layout)

        blink_min_layout = QHBoxLayout()
        blink_min_layout.addWidget(BodyLabel("Blink Detection Threshold", self))
        self.blink_threshold_min = LineEdit(self)
        self.blink_threshold_min.setPlaceholderText("100")
        blink_min_layout.addWidget(self.blink_threshold_min)
        blink_min_layout.addWidget(BodyLabel("-", self))
        self.blink_threshold_max = LineEdit(self)
        self.blink_threshold_max.setPlaceholderText("300")
        blink_min_layout.addWidget(self.blink_threshold_max)
        blink_min_layout.addWidget(BodyLabel("ms", self))
        layout.addLayout(blink_min_layout)

        gaze_interpolate_layout = QHBoxLayout()
        self.interpolate_check = self.create_checkbox("Gaze Data Interpolation Threshold")
        gaze_interpolate_layout.addWidget(self.interpolate_check)
        self.max_gap_length = LineEdit(self)
        self.max_gap_length.setPlaceholderText("75")
        gaze_interpolate_layout.addWidget(self.max_gap_length)
        gaze_interpolate_layout.addWidget(BodyLabel("ms", self))
        layout.addLayout(gaze_interpolate_layout)

        gaze_filter_layout = QHBoxLayout()
        self.denoise_check = self.create_checkbox("Gaze Data Filter")
        gaze_filter_layout.addWidget(self.denoise_check)
        self.denoise_method = self.create_combo_box(["Moving Average", "Moving Median"])
        gaze_filter_layout.addWidget(self.denoise_method)
        self.window_size = ComboBox(self)
        self.window_size.addItems(["3", "5", "7", "9"])
        self.window_size.setCurrentIndex(0)  
        self.window_size.setFixedWidth(110)
        gaze_filter_layout.addWidget(self.window_size)
        gaze_filter_layout.addWidget(BodyLabel("Samples", self))
        layout.addLayout(gaze_filter_layout)

        velocity_window_layout = QHBoxLayout()
        self.use_time_window_check = self.create_checkbox("Velocity Calculation Time Window")
        velocity_window_layout.addWidget(self.use_time_window_check)
        self.velocity_window_length = LineEdit(self)
        self.velocity_window_length.setPlaceholderText("20")
        velocity_window_layout.addWidget(self.velocity_window_length)
        velocity_window_layout.addWidget(BodyLabel("ms", self))
        layout.addLayout(velocity_window_layout)

        merge_fixations_layout = QHBoxLayout()
        self.merge_fixations_check = self.create_checkbox("Fixation Merge Threshold")
        merge_fixations_layout.addWidget(self.merge_fixations_check)

        merge_fixations_layout.addWidget(BodyLabel("Time", self))
        self.max_time_between_fixations = LineEdit(self)
        self.max_time_between_fixations.setFixedWidth(70)
        self.max_time_between_fixations.setPlaceholderText("75")
        merge_fixations_layout.addWidget(self.max_time_between_fixations)
        merge_fixations_layout.addWidget(BodyLabel("ms", self))

        merge_fixations_layout.addWidget(BodyLabel("Angle", self))
        self.max_angle_between_fixations = LineEdit(self)
        self.max_angle_between_fixations.setFixedWidth(70)
        self.max_angle_between_fixations.setPlaceholderText("0.5")
        merge_fixations_layout.addWidget(self.max_angle_between_fixations)
        merge_fixations_layout.addWidget(BodyLabel("°", self))
        layout.addLayout(merge_fixations_layout)

        discard_short_fixations_layout = QHBoxLayout()
        self.discard_short_fixations_check = self.create_checkbox("Min Fixation Duration Threshold")
        discard_short_fixations_layout.addWidget(self.discard_short_fixations_check)
        self.min_fixation_duration = LineEdit(self)
        self.min_fixation_duration.setPlaceholderText("60")
        discard_short_fixations_layout.addWidget(self.min_fixation_duration)
        discard_short_fixations_layout.addWidget(BodyLabel("ms", self))
        layout.addLayout(discard_short_fixations_layout)

        self.confirm_button = PrimaryPushButton("Confirm", self)
        self.confirm_button.clicked.connect(self.on_confirm)
        layout.addWidget(self.confirm_button)

    def create_combo_box(self, items):
        combo_box = ComboBox(self)
        combo_box.addItems(items)
        combo_box.setFixedWidth(110)
        return combo_box

    def create_checkbox(self, label):
        checkbox = CheckBox(self)
        checkbox.setText(label)
        return checkbox
    
    # @PerformanceMonitor()
    def on_confirm(self):
        if self.et_data is None:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Data Not Loaded",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            velocity_threshold = float(self.velocity_threshold.text() or "30")
            blink_threshold_min = float(self.blink_threshold_min.text() or "100")
            blink_threshold_max = float(self.blink_threshold_max.text() or "300")
            
            interpolate = self.interpolate_check.isChecked()
            max_gap_length = float(self.max_gap_length.text() or "75") if interpolate else None
            denoise = self.denoise_check.isChecked()
            denoise_method = self.denoise_method.currentText() if denoise else None
            window_size = int(self.window_size.currentText()) if denoise else None
            
            pupil_interpolate = self.pupil_interpolate_check.isChecked()
            pupil_max_gap = float(self.pupil_gap_length.text() or "75") if pupil_interpolate else None
            pupil_filter = self.pupil_filter_check.isChecked()
            pupil_filter_method = self.pupil_filter_method.currentText() if pupil_filter else None
            pupil_window_size = int(self.pupil_window_size.currentText()) if pupil_filter else None
            
            use_time_window = self.use_time_window_check.isChecked()
            velocity_window_length = int(self.velocity_window_length.text() or "20") 
            merge_fixations = self.merge_fixations_check.isChecked()
            max_time_between_fixations = float(self.max_time_between_fixations.text() or "75") if merge_fixations else None
            max_angle_between_fixations = float(self.max_angle_between_fixations.text() or "0.5") if merge_fixations else None
            discard_short_fixations = self.discard_short_fixations_check.isChecked()
            min_fixation_duration = float(self.min_fixation_duration.text() or "60") if discard_short_fixations else None

            self.et_data.apply_i_vt_filter(
                velocity_threshold=velocity_threshold,
                blink_threshold=blink_threshold_min,
                blink_max_threshold=blink_threshold_max,
                interpolate=interpolate,
                max_gap_length=max_gap_length,
                denoise=denoise,
                denoise_method=denoise_method,
                window_size=window_size,
                velocity_window_length=velocity_window_length,
                merge_fixations=merge_fixations,
                max_time_between_fixations=max_time_between_fixations,
                max_angle_between_fixations=max_angle_between_fixations,
                discard_short_fixations=discard_short_fixations,
                min_fixation_duration=min_fixation_duration,
                pupil_interpolate=pupil_interpolate,
                pupil_max_gap=pupil_max_gap,
                pupil_filter=pupil_filter,
                pupil_filter_method=pupil_filter_method,
                pupil_window_size=pupil_window_size
            )

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Data Preprocessing Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Data Preprocessing Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )


class PreprocessingInterface(SmoothScrollArea):
    def __init__(self, parent=None, et_data=None, et_viewer=None, et_player=None):
        super().__init__(parent)
        self.et_data = et_data
        self.et_viewer = et_viewer
        self.et_player = et_player
        self.parent = parent
        self.enableTransparentBackground()
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        self.vBoxLayout.setSpacing(10)
        # self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        
        self.setup_ui()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollWidget.setObjectName('view')

    def setup_ui(self):        
        self.preprocessing_card = PreprocessingCard(self, self.et_data)
        self.vBoxLayout.addWidget(self.preprocessing_card)
    
        self.event_annotation = EventAnnotationCard(self, self.et_data, self.et_viewer)
        self.vBoxLayout.addWidget(self.event_annotation)

        # Add AOI Settings Card
        self.aoi_settings = AOISettingsCard("AOI Setting", self.et_data, self.et_player)
        self.vBoxLayout.addWidget(self.aoi_settings)

    def update_processed_data_info(self, et_data):
        if hasattr(self.parent, 'update_processed_data_info'):
            self.parent.update_processed_data_info(et_data)


class EventAnnotationCard(CardWidget):
    def __init__(self, parent=None, et_data=None, et_viewer=None):
        super().__init__(parent)
        self.title = "TOI Setting"
        self.et_data = et_data
        self.et_viewer = et_viewer
        self.setup_ui()
        self.load_events()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        description_layout = QHBoxLayout()
        description_layout.addWidget(BodyLabel("TOI Description", self))
        self.event_description = LineEdit(self)
        self.event_description.setPlaceholderText("TOI Description Information")
        description_layout.addWidget(self.event_description)
        layout.addLayout(description_layout)

        time_layout = QHBoxLayout()
        
        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(BodyLabel("Start Time", self))
        self.start_time = LineEdit(self)
        self.start_time.setPlaceholderText("Start Time (s)")
        start_time_layout.addWidget(self.start_time)
        self.start_time_button = PushButton("+", self)
        self.start_time_button.clicked.connect(lambda: self.set_current_time(self.start_time))
        start_time_layout.addWidget(self.start_time_button)
        time_layout.addLayout(start_time_layout)

        end_time_layout = QHBoxLayout()
        end_time_layout.addWidget(BodyLabel("End Time", self))
        self.end_time = LineEdit(self)
        self.end_time.setPlaceholderText("End Time (s)")
        end_time_layout.addWidget(self.end_time)
        self.end_time_button = PushButton("+", self)
        self.end_time_button.clicked.connect(lambda: self.set_current_time(self.end_time))
        end_time_layout.addWidget(self.end_time_button)
        time_layout.addLayout(end_time_layout)

        layout.addLayout(time_layout)

        self.add_event_button = PrimaryPushButton("Add Event", self)
        self.add_event_button.setIcon(FluentIcon.ADD)
        self.add_event_button.clicked.connect(self.add_event)
        layout.addWidget(self.add_event_button)

        self.event_table = TableWidget(self)
        self.event_table.setColumnCount(5)
        self.event_table.setHorizontalHeaderLabels(["Color", "Start Time", "End Time", "TOI Description", "Delete"])
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.setColumnWidth(4, 60)
        
        self.event_table.setEditTriggers(TableWidget.DoubleClicked | TableWidget.EditKeyPressed)
        self.event_table.itemChanged.connect(self.on_item_changed)
        
        self.event_table.setMinimumHeight(200)
        self.event_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout.addWidget(self.event_table)

        self.setMinimumHeight(420)

    def set_current_time(self, time_input):
        if self.et_viewer:
            current_time = self.et_viewer.current_time
            time_input.setText(f"{current_time:.2f}")

    def validate_input(self):
        try:
            start_time = float(self.start_time.text())
            end_time = float(self.end_time.text())
            
            if start_time < 0 or end_time < 0:
                raise ValueError("Time Cannot Be Negative")
            
            if end_time <= start_time:
                raise ValueError("End Time Must Be Greater Than Start Time")

            return start_time, end_time
        except ValueError as e:
            # InfoBar.error(
            #     content=str(e),
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return None, None

    def add_event(self):
        if self.et_data is None:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Data Not Loaded",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        if not self.start_time.text() or not self.end_time.text() or not self.event_description.text():
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warnig',
                content="Please Fill All The Fields",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        start_time, end_time = self.validate_input()
        if start_time is None or end_time is None:
            return

        description = self.event_description.text()

        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        event = (start_time, end_time, color, description)
        
        try:
            self.et_data.add_event(event)
            self.et_viewer.add_toi(event)
            self.add_event_to_table(start_time, end_time, color, description)
            
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Event Added",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

            self.event_description.clear()
            self.start_time.clear()
            self.end_time.clear()
        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Fail To Add Event: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def add_event_to_table(self, start_time, end_time, color, description):
        row = self.event_table.rowCount()
        self.event_table.insertRow(row)
        
        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_label = QLabel()
        color_label.setFixedSize(16, 16)
        qcolor = QColor(*color)
        color_label.setStyleSheet(f"background-color: {qcolor.name()}; border: 1px solid {'#c0c0c0'}; border-radius: 2px;")
        color_layout.addWidget(color_label, alignment=Qt.AlignCenter)
        self.event_table.setCellWidget(row, 0, color_widget)

        self.event_table.setItem(row, 1, QTableWidgetItem(f"{start_time:.2f}"))
        self.event_table.setItem(row, 2, QTableWidgetItem(f"{end_time:.2f}"))
        self.event_table.setItem(row, 3, QTableWidgetItem(description))

        delete_button = PillToolButton(FluentIcon.DELETE)
        delete_button.clicked.connect(lambda: self.delete_event(row))
        self.event_table.setCellWidget(row, 4, delete_button)

    def load_events(self):
        if self.et_data:
            for event in self.et_data.get_events():
                start_time, end_time, color, description = event
                self.add_event_to_table(start_time, end_time, color, description)

    def delete_event(self, row):
        if self.et_data is None or row >= len(self.et_data.get_events()):
            print(f"Warning: Cannot delete event at row {row}.")
            return

        event = self.et_data.get_events()[row]
        self.et_data.delete_event(event)
        if self.et_viewer:
            self.et_viewer.delete_toi(event)
        self.event_table.removeRow(row)

        # InfoBar.success(
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=2000,
        #     parent=self
        # )
        InfoBar.success(
            title='Success',
            content=f"Event Is Already Deleted: {event[3]}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def on_item_changed(self, item):
        row = item.row()
        column = item.column()
        new_value = item.text()

        if self.et_data is None or row >= len(self.et_data.get_events()):
            return

        old_event = self.et_data.get_events()[row]
        new_event = list(old_event)

        try:
            if column == 1:  
                new_start_time = float(new_value)
                if new_start_time < 0 or (self.et_data.video_duration and new_start_time > self.et_data.video_duration):
                    raise ValueError(f"Start Time Must Be Between 0 And {self.et_data.video_duration}s")
                new_event[0] = new_start_time
            elif column == 2:  
                new_end_time = float(new_value)
                if new_end_time < 0 or (self.et_data.video_duration and new_end_time > self.et_data.video_duration):
                    raise ValueError(f"End Time Must Be Between 0 And {self.et_data.video_duration}s")
                new_event[1] = new_end_time
            elif column == 3:  
                new_event[3] = new_value

            if new_event[1] <= new_event[0]:
                
                raise ValueError("End Time Must Be Greater Than Start Time")

            new_event = tuple(new_event)
            self.et_data.edit_event(old_event, new_event)
            # if self.et_viewer:
            #     self.et_viewer.update_toi(old_event, new_event)

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
        except ValueError as e:
            # InfoBar.error(
            #     content=str(e),
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            self.event_table.blockSignals(True)
            if column == 1 or column == 2:  
                item.setText(f"{old_event[column-1]:.2f}")
            elif column == 3:  
                item.setText(old_event[column])
        
            self.event_table.blockSignals(False)

class AOISettingsCard(CardWidget):
    aoi_added = pyqtSignal(object)  # Signal to notify when an AOI is added

    def __init__(self, title, et_data, et_player, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        self.et_player = et_player
        self.is_collecting = False
        self.is_previewing = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # AOI Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(BodyLabel("AOI Name:", self))
        self.name_input = LineEdit(self)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Time range input
        time_layout = QHBoxLayout()
        
        # Start time
        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(BodyLabel("Start Time", self))
        self.start_time = LineEdit(self)
        self.start_time.setPlaceholderText("Start Time (s)")
        self.start_time.textChanged.connect(self.update_et_player_time_range)
        start_time_layout.addWidget(self.start_time)
        self.start_time_button = PushButton("+", self)
        self.start_time_button.clicked.connect(lambda: self.set_current_time(self.start_time))
        start_time_layout.addWidget(self.start_time_button)
        time_layout.addLayout(start_time_layout)

        # End time
        end_time_layout = QHBoxLayout()
        end_time_layout.addWidget(BodyLabel("End Time", self))
        self.end_time = LineEdit(self)
        self.end_time.setPlaceholderText("End Time (s)")
        self.end_time.textChanged.connect(self.update_et_player_time_range)
        end_time_layout.addWidget(self.end_time)
        self.end_time_button = PushButton("+", self)
        self.end_time_button.clicked.connect(lambda: self.set_current_time(self.end_time))
        end_time_layout.addWidget(self.end_time_button)
        time_layout.addLayout(end_time_layout)

        layout.addLayout(time_layout)

        # AOI Coordinates input
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(BodyLabel("AOI Coordinates", self))
        self.coord_input = LineEdit(self)
        self.coord_input.setPlaceholderText("x1,y1,x2,y2,...")
        coord_layout.addWidget(self.coord_input)
        self.collect_button = PushButton("Start Collection", self)
        self.collect_button.clicked.connect(self.toggle_collection)
        coord_layout.addWidget(self.collect_button)
        layout.addLayout(coord_layout)

        # Preview and Add buttons
        button_layout = QHBoxLayout()
        self.preview_button = PushButton("Preview", self)
        self.preview_button.clicked.connect(self.toggle_preview)
        button_layout.addWidget(self.preview_button)
        self.add_button = PrimaryPushButton("Add AOI", self)
        self.add_button.clicked.connect(self.add_aoi)
        button_layout.addWidget(self.add_button)
        layout.addLayout(button_layout)

        # AOI Table
        self.aoi_table = TableWidget(self)
        self.aoi_table.setColumnCount(5)
        self.aoi_table.setHorizontalHeaderLabels(["Name", "Start Time", "End Time", "Preview", "Delete"])
        self.aoi_table.horizontalHeader().setStretchLastSection(True)
        self.aoi_table.setColumnWidth(4, 40)
        self.aoi_table.setMinimumHeight(200)
        layout.addWidget(self.aoi_table)

    def set_current_time(self, time_input):
        if self.et_player:
            current_time = self.et_player.current_frame / self.et_player.fps
            time_input.setText(f"{current_time:.2f}")

    def update_et_player_time_range(self):
        try:
            start_time = float(self.start_time.text()) if self.start_time.text() else None
            end_time = float(self.end_time.text()) if self.end_time.text() else None
            self.et_player.set_aoi_time_range(start_time, end_time)
        except ValueError:
            pass

    def toggle_collection(self):
        if not self.is_collecting:
            self.is_collecting = True
            self.collect_button.setText("Collection Done")
            self.et_player.start_aoi_collection(self.collection_finished)
        else:
            self.is_collecting = False
            self.collect_button.setText("Start Collection")
            self.et_player.stop_aoi_collection()

    def collection_finished(self, coordinates):
        self.coord_input.setText(','.join(map(lambda x: f"{x:.4f}", coordinates)))
        self.is_collecting = False
        self.collect_button.setText("Start Collection")

    def validate_input(self):
        try:
            name = self.name_input.text()
            if not name:
                raise ValueError("AOI Name Cannot Be Empty")

            coordinates = [float(x) for x in self.coord_input.text().split(',')]
            if len(coordinates) < 6 or len(coordinates) % 2 != 0:
                raise ValueError("Invalid Coordinate Format. Please Enter x,y Coordinates For At Least 3 Points")

            start_time = float(self.start_time.text()) if self.start_time.text() else None
            end_time = float(self.end_time.text()) if self.end_time.text() else None
            
            if start_time is not None and end_time is not None:
                if start_time < 0 or end_time < 0:
                    raise ValueError("Time Cannot Be Negative")
                
                if end_time <= start_time:
                    raise ValueError("End Time Must Be Greater Than Start Time")

            return name, coordinates, start_time, end_time
        except ValueError as e:
            # InfoBar.error(
            #     content=str(e),
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return None

    def toggle_preview(self):
        if not self.is_previewing:
            self.preview_aoi()
        else:
            self.cancel_preview()

    def preview_aoi(self):
        input_data = self.validate_input()
        if not input_data:
            return

        name, coordinates, start_time, end_time = input_data

        try:
            if self.et_player:
                self.et_player.start_aoi_preview(coordinates, start_time, end_time)
                self.is_previewing = True
                self.preview_button.setText("Cancel Preview")
            else:
                raise Exception("ET Player not initialized")

        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"AOI Preview Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def cancel_preview(self):
        if self.et_player:
            self.et_player.stop_aoi_preview()
        self.is_previewing = False
        self.preview_button.setText("Preview")

    def add_aoi(self):
        input_data = self.validate_input()
        if not input_data:
            return

        name, coordinates, start_time, end_time = input_data

        try:
            if not isinstance(coordinates, list):
                raise ValueError("Coordinates Must Be A List")

            coord_tuples = [(coordinates[i], coordinates[i+1]) for i in range(0, len(coordinates), 2)]

            self.et_data.add_aoi(name, coord_tuples, start_time, end_time)

            aoi = {
                'name': name,
                'coordinates': coord_tuples,
                'start_time': start_time,
                'end_time': end_time
            }

            self.add_aoi_to_table(aoi)
            self.aoi_added.emit(aoi)

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="AOI Is Already Added",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

            # Clear inputs and cancel preview
            self.name_input.clear()
            self.coord_input.clear()
            self.start_time.clear()
            self.end_time.clear()
            self.cancel_preview()

        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"AOI Addition Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def add_aoi_to_table(self, aoi):
        row = self.aoi_table.rowCount()
        self.aoi_table.insertRow(row)
        self.aoi_table.setItem(row, 0, QTableWidgetItem(aoi['name']))
        self.aoi_table.setItem(row, 1, QTableWidgetItem(str(aoi['start_time'])))
        self.aoi_table.setItem(row, 2, QTableWidgetItem(str(aoi['end_time'])))

        preview_button = PushButton("Preview")
        preview_button.clicked.connect(lambda: self.toggle_aoi_preview(row))
        self.aoi_table.setCellWidget(row, 3, preview_button)

        delete_button = PushButton("Delete")
        delete_button.clicked.connect(lambda: self.delete_aoi(row))
        self.aoi_table.setCellWidget(row, 4, delete_button)

    def toggle_aoi_preview(self, row):
        preview_button = self.aoi_table.cellWidget(row, 3)
        if preview_button.text() == "Preview":
            self.preview_table_aoi(row)
            preview_button.setText("Cancel")
        else:
            self.cancel_preview()
            preview_button.setText("Preview")

    def preview_table_aoi(self, row):
        name = self.aoi_table.item(row, 0).text()
        aoi = next((a for a in self.et_data.get_aois() if a.name == name), None)
        if aoi:
            coordinates = [coord for point in aoi.coordinates for coord in point]
            self.et_player.start_aoi_preview(coordinates, aoi.start_time, aoi.end_time)
            self.is_previewing = True

    def delete_aoi(self, row):
        aoi_name = self.aoi_table.item(row, 0).text()
        aoi = next((a for a in self.et_data.get_aois() if a.name == aoi_name), None)
        if aoi:
            self.et_data.delete_aoi(aoi)
            self.aoi_table.removeRow(row)

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Succedd',
                content=f"Already Deleted AOI: {aoi_name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def load_aois(self):
        if self.et_data:
            for aoi in self.et_data.get_aois():
                self.add_aoi_to_table({
                    'name': aoi.name,
                    'coordinates': aoi.coordinates,
                    'start_time': aoi.start_time,
                    'end_time': aoi.end_time
                })

class FeatureExtractionInterface(SmoothScrollArea):
    def __init__(self, parent=None, et_data=None):
        super().__init__(parent)
        self.et_data = et_data
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        self.parent = parent
        self.enableTransparentBackground()
        self.vBoxLayout.setSpacing(10)
        # self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        
        self.setup_ui()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollWidget.setObjectName('view')

    def setup_ui(self):
        self.feature_extraction_card = FeatureExtractionCard("Feature Extraction", self.et_data)
        self.aoi_analysis_card = AOIAnalysisCard("AOI Analysis", self.et_data)
        self.cluster_analysis_card = SimpleClusterAnalysisCard("ET Pattern Mining", self.et_data)

        self.vBoxLayout.addWidget(self.feature_extraction_card)
        self.vBoxLayout.addWidget(self.aoi_analysis_card)
        self.vBoxLayout.addWidget(self.cluster_analysis_card)
        self.vBoxLayout.addStretch(1)


from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFileDialog, QListWidgetItem
from PyQt5.QtCore import Qt
from qfluentwidgets import (CardWidget, ComboBox, LineEdit, PushButton, 
                            BodyLabel, SubtitleLabel, InfoBar, InfoBarPosition,
                            ListWidget, PrimaryPushButton, CheckBox, FlowLayout, 
                            Theme, PillPushButton, FluentIcon)

class FeatureExtractionCard(CardWidget):
    def __init__(self, title, et_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        # self.all_features = {
        #     ],
        #     ],
        #     ],
        #     ]
        # }
        self.all_features = {
            "Fixation Metrics": [
                "First Fixation Time", "First Fixation Duration", "Fixation Count", "Total Fixation Duration",
                "Average Fixation Duration", "Fixation Rate", "Saccade Ratio", "Fixation-Saccade Ratio"
            ],
            "Saccade Metrics": [
                "Saccade Count", "Average Saccade Amplitude", "First Saccade Latency", "Saccade Direction",
                "Saccade Peak Velocity", "Average Saccade Duration", "Saccade Rate"
            ],
            "Pupil Metrics": [
                "Mean Pupil Diameter", "Minimum Pupil Diameter", "Maximum Pupil Diameter",
                "Pupil Diameter Variance", "Pupil Area Growth Rate"
            ],
            "Blink Metrics": [
                "Blink Count", "Total Blink Duration", "Average Blink Duration"
            ]
        }
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Feature selection using TreeWidget
        self.feature_tree = TreeWidget(self)
        self.feature_tree.setHeaderHidden(True)
        self.populate_feature_tree()
        layout.addWidget(self.feature_tree)

        # Extract features button
        self.extract_button = PrimaryPushButton("Extract Features", self)
        self.extract_button.clicked.connect(self.extract_features)
        layout.addWidget(self.extract_button)

        self.setMinimumHeight(550)

    def populate_feature_tree(self):
        self.feature_tree.clear()
        root = QTreeWidgetItem(self.feature_tree, ["All Features"])
        root.setCheckState(0, Qt.Unchecked)

        for category, features in self.all_features.items():
            category_item = QTreeWidgetItem(root, [category])
            category_item.setCheckState(0, Qt.Unchecked)
            for feature in features:
                feature_item = QTreeWidgetItem(category_item, [feature])
                feature_item.setCheckState(0, Qt.Unchecked)

        self.feature_tree.expandAll()
        self.feature_tree.itemChanged.connect(self.update_tree_state)

    def update_tree_state(self, item, column):
        self.feature_tree.blockSignals(True)

        if item.text(0) == "All Features":
            self.set_all_checked(item, item.checkState(0))
        elif item.parent().text(0) == "All Features":
            self.set_category_checked(item, item.checkState(0))
        else:
            self.update_parent_state(item.parent())

        self.feature_tree.blockSignals(False)

    def set_all_checked(self, root_item, state):
        for i in range(root_item.childCount()):
            category_item = root_item.child(i)
            category_item.setCheckState(0, state)
            for j in range(category_item.childCount()):
                feature_item = category_item.child(j)
                feature_item.setCheckState(0, state)

    def set_category_checked(self, category_item, state):
        for i in range(category_item.childCount()):
            feature_item = category_item.child(i)
            feature_item.setCheckState(0, state)
        self.update_parent_state(category_item.parent())

    def update_parent_state(self, parent_item):
        child_count = parent_item.childCount()
        checked_count = sum(parent_item.child(i).checkState(0) == Qt.Checked for i in range(child_count))

        if checked_count == 0:
            parent_item.setCheckState(0, Qt.Unchecked)
        elif checked_count == child_count:
            parent_item.setCheckState(0, Qt.Checked)
        else:
            parent_item.setCheckState(0, Qt.PartiallyChecked)

        if parent_item.parent():
            self.update_parent_state(parent_item.parent())

    def get_selected_features(self):
        root = self.feature_tree.invisibleRootItem().child(0)  
        if root.checkState(0) == Qt.Checked:
            return [feature for category in self.all_features.values() for feature in category]
        
        selected_features = []
        for i in range(root.childCount()):
            category_item = root.child(i)
            if category_item.checkState(0) == Qt.Checked:
                selected_features.extend(self.all_features[category_item.text(0)])
            else:
                for j in range(category_item.childCount()):
                    feature_item = category_item.child(j)
                    if feature_item.checkState(0) == Qt.Checked:
                        selected_features.append(feature_item.text(0))
        return selected_features
    
    # @PerformanceMonitor()
    def extract_features(self):
        selected_features = self.get_selected_features()

        if not selected_features:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Choose At Least One Feature",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            df = self.et_data.analyze_data(metrics_list=selected_features)

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=3000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Features Extraction Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

            # self.show_results_dialog(df)

        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=3000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Features Extraction Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

class AOIAnalysisCard(CardWidget):
    def __init__(self, title, et_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        # self.all_metrics = {
        #     ],
        #     ],
        #     ]
        # }
        self.all_metrics = {
            "Visit Metrics": [
                "Fixation Visit Count", "Total Fixation Visit Duration", "Mean Fixation Visit Duration",
                "First Fixation Visit Time", "Revisit Count"
            ],
            "Fixation Metrics": [
                "Fixation Point Count", "Mean Fixation Duration", "Total Fixation Duration", 
                "Fixation Time Proportion"
            ],
            "Other Metrics": [
                "First Fixation Latency", "Mean Pupil Size"
            ]
        }
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Metrics selection using TreeWidget
        self.metrics_tree = TreeWidget(self)
        self.metrics_tree.setHeaderHidden(True)
        self.populate_metrics_tree()
        layout.addWidget(self.metrics_tree)

        # Analyze button
        self.analyze_button = PrimaryPushButton("Analyze AOI Data", self)
        self.analyze_button.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_button)

        self.setMinimumHeight(500)

    def populate_metrics_tree(self):
        self.metrics_tree.clear()
        root = QTreeWidgetItem(self.metrics_tree, ["All Metrics"])
        root.setCheckState(0, Qt.Unchecked)

        for category, metrics in self.all_metrics.items():
            category_item = QTreeWidgetItem(root, [category])
            category_item.setCheckState(0, Qt.Unchecked)
            for metric in metrics:
                metric_item = QTreeWidgetItem(category_item, [metric])
                metric_item.setCheckState(0, Qt.Unchecked)

        self.metrics_tree.expandAll()
        self.metrics_tree.itemChanged.connect(self.update_tree_state)

    def update_tree_state(self, item, column):
        self.metrics_tree.blockSignals(True)

        if item.text(0) == "All Metrics":
            self.set_all_checked(item, item.checkState(0))
        elif item.parent().text(0) == "All Metrics":
            self.set_category_checked(item, item.checkState(0))
        else:
            self.update_parent_state(item.parent())

        self.metrics_tree.blockSignals(False)

    def set_all_checked(self, root_item, state):
        for i in range(root_item.childCount()):
            category_item = root_item.child(i)
            category_item.setCheckState(0, state)
            for j in range(category_item.childCount()):
                metric_item = category_item.child(j)
                metric_item.setCheckState(0, state)

    def set_category_checked(self, category_item, state):
        for i in range(category_item.childCount()):
            metric_item = category_item.child(i)
            metric_item.setCheckState(0, state)
        self.update_parent_state(category_item.parent())

    def update_parent_state(self, parent_item):
        child_count = parent_item.childCount()
        checked_count = sum(parent_item.child(i).checkState(0) == Qt.Checked for i in range(child_count))

        if checked_count == 0:
            parent_item.setCheckState(0, Qt.Unchecked)
        elif checked_count == child_count:
            parent_item.setCheckState(0, Qt.Checked)
        else:
            parent_item.setCheckState(0, Qt.PartiallyChecked)

        if parent_item.parent():
            self.update_parent_state(parent_item.parent())

    def get_selected_metrics(self):
        root = self.metrics_tree.invisibleRootItem().child(0)  
        if root.checkState(0) == Qt.Checked:
            return [metric for category in self.all_metrics.values() for metric in category]
        
        selected_metrics = []
        for i in range(root.childCount()):
            category_item = root.child(i)
            if category_item.checkState(0) == Qt.Checked:
                selected_metrics.extend(self.all_metrics[category_item.text(0)])
            else:
                for j in range(category_item.childCount()):
                    metric_item = category_item.child(j)
                    if metric_item.checkState(0) == Qt.Checked:
                        selected_metrics.append(metric_item.text(0))
        return selected_metrics

    def start_analysis(self):
        selected_metrics = self.get_selected_metrics()

        if not selected_metrics:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Choose At Least One Metric",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            df = self.et_data.analyze_aois(metrics_list=selected_metrics)

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=3000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="AOI Analysis Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

            # self.show_results_dialog(df)

        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=3000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"AOI Analysis Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

class SimpleClusterAnalysisCard(CardWidget):
    def __init__(self, title, et_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        self.current_figure = None  
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        algo_layout = QHBoxLayout()
        algo_layout.addWidget(BodyLabel("Algorithm Choice:", self))
        self.algo_dropdown = ComboBox(self)
        self.algo_dropdown.addItems(['kmeans', 'DBSCAN'])
        algo_layout.addWidget(self.algo_dropdown)
        layout.addLayout(algo_layout)

        data_type_layout = QHBoxLayout()
        data_type_layout.addWidget(BodyLabel("Data Type:", self))
        self.data_type_dropdown = ComboBox(self)
        self.data_type_dropdown.addItems(['Fixations', 'Saccades'])
        data_type_layout.addWidget(self.data_type_dropdown)
        layout.addLayout(data_type_layout)

        toi_layout = QHBoxLayout()
        toi_layout.addWidget(BodyLabel("Choose TOI:", self))
        self.toi_dropdown = ComboBox(self)
        self.toi_dropdown.clicked.connect(self.update_toi_list)
        toi_layout.addWidget(self.toi_dropdown)
        layout.addLayout(toi_layout)

        self.update_toi_list()

        self.analyze_button = PrimaryPushButton("Start Analysis", self)
        self.analyze_button.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_button)


    def update_toi_list(self):
        
        current_text = self.toi_dropdown.currentText()
        self.toi_dropdown.clear()
        self.toi_dropdown.addItem("All Data")
        
        if self.et_data:
            toi_list = [event[3] for event in self.et_data.get_events()]
            self.toi_dropdown.addItems(toi_list)

        index = self.toi_dropdown.findText(current_text)
        if index >= 0:
            self.toi_dropdown.setCurrentIndex(index)
        else:
            self.toi_dropdown.setCurrentIndex(0)

    def start_analysis(self):
        algorithm = self.algo_dropdown.currentText()
        data_type = 'fixations' if self.data_type_dropdown.currentText() == 'Fixations' else 'saccades'
        toi_name = self.toi_dropdown.currentText()
        
        toi_name = None if toi_name == "All Data" else toi_name

        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("Analyzing...")

        try:
            _, self.current_figure = self.et_data.cluster_analysis(
                data_type=data_type, 
                algorithm=algorithm.lower(),
                toi_name=toi_name
            )
            
            if self.current_figure:
                dialog = ImageViewerDialog(self.current_figure, self)
                dialog.exec_()

            analysis_scope = "All Data" if toi_name is None else f"TOI: {toi_name}"
            InfoBar.success(
                title='Success',
                content=f"Cluster Analysis Done Using {algorithm} Algorithm For {self.data_type_dropdown.currentText()} In {analysis_scope}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='Error',
                content=f"Analysis Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        finally:
            self.analyze_button.setEnabled(True)
            self.analyze_button.setText("Start Analysis")


class VisualizationInterface(SmoothScrollArea):
    def __init__(self, parent=None, et_data=None):
        super().__init__(parent)
        self.et_data = et_data
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)

        self.parent = parent
        self.enableTransparentBackground()
        self.setup_ui()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.scrollWidget.setObjectName('view')

    def setup_ui(self):
        self.temporal_card = TemporalSeriesCard("ET Time Series", self.et_data)
        self.fixation_scatter_card = FixationScatterCard("Fixation Scatter Plot", self.et_data)
        self.heatmap_card = HeatmapCard("Heatmap", self.et_data)
        self.scanpath_card = ScanpathCard("Scanpath", self.et_data)
        self.gazescatter_card = GazeScatterCard("Gaze Scatter Plot", self.et_data)
        self.statistics_card = StatisticsCard("ET Statistics", self.et_data)
        self.numbered_scanpath_card = NumberedScanpathCard("Numbered Scanpath", self.et_data)

        self.vBoxLayout.addWidget(self.temporal_card)
        self.vBoxLayout.addWidget(self.statistics_card)
        self.vBoxLayout.addWidget(self.gazescatter_card)
        self.vBoxLayout.addWidget(self.fixation_scatter_card)
        self.vBoxLayout.addWidget(self.numbered_scanpath_card)
        self.vBoxLayout.addWidget(self.scanpath_card)
        self.vBoxLayout.addWidget(self.heatmap_card)
        self.vBoxLayout.addStretch(1)

class BaseVisualizationCard(CardWidget):
    def __init__(self, title, et_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        self.current_figure = None  
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        toi_layout = QHBoxLayout()
        toi_layout.addWidget(BodyLabel("Choose TOI:", self))

        self.toi_dropdown = ComboBox(self)
        self.toi_dropdown.addItem("All Data")
        self.update_toi_list()  
        self.toi_dropdown.clicked.connect(self.update_toi_list)  

        toi_layout.addWidget(self.toi_dropdown)
        layout.addLayout(toi_layout)

        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_data)
        layout.addWidget(self.plot_button)


    def plot_data(self):
        pass

    def update_toi_list(self):
        
        self.toi_dropdown.clear()
        self.toi_dropdown.addItem("All Data")

        toi_list = [event[3] for event in self.et_data.get_events()]
        self.toi_dropdown.addItems(toi_list)

    def show_dialog(self, fig):
        
        self.current_figure = fig
        dialog = ImageViewerDialog(fig, self)
        dialog.exec_()

    def show_error(self, message):
        # InfoBar.error(
        #     content=message,
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=4000,
        #     parent=self
        # )
        InfoBar.error(
            title='Error',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self
        )

class NumberedScanpathCard(CardWidget):
    def __init__(self, title, et_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # TOI selection
        toi_layout = QHBoxLayout()
        toi_layout.addWidget(BodyLabel("Choose TOI:", self))
        self.toi_dropdown = ComboBox(self)
        self.toi_dropdown.clicked.connect(self.update_toi_list)
        toi_layout.addWidget(self.toi_dropdown)
        layout.addLayout(toi_layout)

        # Background option
        self.use_background = CheckBox("Use First Video Frame As Background", self)
        layout.addWidget(self.use_background)

        self.update_toi_list()

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_scanpath)
        layout.addWidget(self.plot_button)

        # # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def update_toi_list(self):
        current_text = self.toi_dropdown.currentText()
        self.toi_dropdown.clear()
        self.toi_dropdown.addItem("All Data")
        
        if self.et_data:
            toi_list = [event[3] for event in self.et_data.get_events()]
            self.toi_dropdown.addItems(toi_list)

        index = self.toi_dropdown.findText(current_text)
        if index >= 0:
            self.toi_dropdown.setCurrentIndex(index)
        else:
            self.toi_dropdown.setCurrentIndex(0)

    def plot_scanpath(self):
        toi_name = self.toi_dropdown.currentText()
        if toi_name == "All Data":
            toi_name = None

        use_background = self.use_background.isChecked()

        self.plot_button.setEnabled(False)
        self.plot_button.setText("Drawing...")

        try:
            self.current_figure = self.et_data.plot_numbered_scanpath(
                toi_name=toi_name,
                use_background=use_background
            )
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            # self.show_image_preview()

            analysis_scope = "All Data" if toi_name is None else f"TOI: {toi_name}"
            background_info = "(With Background)" if use_background else ""
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content=f"Numbered Scanpath Visualization Done For {analysis_scope}{background_info}", 
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Fail To Draw: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        finally:
            self.plot_button.setEnabled(True)
            self.plot_button.setText("Draw Image")

    # def show_image_preview(self):
    #     if self.current_figure:
    #         buf = io.BytesIO()
    #         self.current_figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    #         buf.seek(0)
    #         image = QImage.fromData(buf.getvalue())
    #         pixmap = QPixmap.fromImage(image)
    #         scaled_pixmap = pixmap.scaled(450, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

class TemporalSeriesCard(CardWidget):
    def __init__(self, title, et_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # TOI selection
        toi_layout = QHBoxLayout()
        toi_layout.addWidget(BodyLabel("Choose TOI:", self))
        self.toi_dropdown = ComboBox(self)
        self.toi_dropdown.clicked.connect(self.update_toi_list)
        toi_layout.addWidget(self.toi_dropdown)
        layout.addLayout(toi_layout)

        self.update_toi_list()

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_temporal_series)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def update_toi_list(self):
        current_text = self.toi_dropdown.currentText()
        self.toi_dropdown.clear()
        self.toi_dropdown.addItem("All Data")
        
        if self.et_data:
            toi_list = [event[3] for event in self.et_data.get_events()]
            self.toi_dropdown.addItems(toi_list)

        index = self.toi_dropdown.findText(current_text)
        if index >= 0:
            self.toi_dropdown.setCurrentIndex(index)
        else:
            self.toi_dropdown.setCurrentIndex(0)

    def plot_temporal_series(self):
        toi_name = self.toi_dropdown.currentText()
        if toi_name == "All Data":
            toi_name = None

        self.plot_button.setEnabled(False)
        self.plot_button.setText("Drawing...")

        try:
            self.current_figure = self.et_data.plot_temporal_series(toi_name)
            # self.show_image_preview()
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            analysis_scope = "All Data" if toi_name is None else f"TOI: {toi_name}"
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content=f"ET Time Series Of {analysis_scope} Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Fail To Draw: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        finally:
            self.plot_button.setEnabled(True)
            self.plot_button.setText("Draw Image")

    # def show_image_preview(self):
    #     if self.current_figure:
    #         buf = io.BytesIO()
    #         self.current_figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    #         buf.seek(0)
    #         image = QImage.fromData(buf.getvalue())
    #         pixmap = QPixmap.fromImage(image)
    #         scaled_pixmap = pixmap.scaled(450, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

class StatisticsCard(CardWidget):
    def __init__(self, title, et_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.et_data = et_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # TOI selection
        toi_layout = QHBoxLayout()
        toi_layout.addWidget(BodyLabel("Choose TOI:", self))
        self.toi_dropdown = ComboBox(self)
        self.toi_dropdown.clicked.connect(self.update_toi_list)  
        toi_layout.addWidget(self.toi_dropdown)
        layout.addLayout(toi_layout)

        self.update_toi_list()

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_statistics)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()  # Initially hide the preview
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def update_toi_list(self):
        
        current_text = self.toi_dropdown.currentText()
        self.toi_dropdown.clear()
        
        self.toi_dropdown.addItem("All Data")
        
        if self.et_data:
            toi_list = [event[3] for event in self.et_data.get_events()]
            self.toi_dropdown.addItems(toi_list)

        index = self.toi_dropdown.findText(current_text)
        if index >= 0:
            self.toi_dropdown.setCurrentIndex(index)
        else:
            self.toi_dropdown.setCurrentIndex(0)

    def plot_statistics(self):
        toi_name = self.toi_dropdown.currentText()
        if toi_name == "All Data":
            toi_name = None

        self.plot_button.setEnabled(False)
        self.plot_button.setText("Drawing...")

        try:
            self.current_figure = self.et_data.plot_statistics(toi_name)
            # self.show_image_preview()
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            analysis_scope = "All Data" if toi_name is None else f"TOI: {toi_name}"
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content=f"ET Statistics Of {analysis_scope} Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Fail To Draw: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        finally:
            self.plot_button.setEnabled(True)
            self.plot_button.setText("Draw Image")

    # def show_image_preview(self):
    #     if self.current_figure:
    #         buf = io.BytesIO()
    #         self.current_figure.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    #         buf.seek(0)
    #         image = QImage.fromData(buf.getvalue())
    #         pixmap = QPixmap.fromImage(image)
    #         scaled_pixmap = pixmap.scaled(450, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

class FixationScatterCard(BaseVisualizationCard):
    def __init__(self, title, et_data, parent=None):
        super().__init__(title, et_data, parent)

    def setup_ui(self):
        super().setup_ui()
        self.duration_size = CheckBox("Use Duration For Scatter Point Size", self)
        self.duration_size.setChecked(True)  # Default checked
        self.duration_color = CheckBox("Use Duration For Scatter Point Color", self)
        self.duration_color.setChecked(True)  # Default checked
        self.use_background = CheckBox("Use First Video Frame As Background", self)
        self.layout().insertWidget(self.layout().count() - 2, self.duration_size)
        self.layout().insertWidget(self.layout().count() - 2, self.duration_color)
        self.layout().insertWidget(self.layout().count() - 2, self.use_background)

    def plot_data(self):
        toi_name = self.toi_dropdown.currentText()
        duration_size = self.duration_size.isChecked()
        duration_color = self.duration_color.isChecked()
        use_background = self.use_background.isChecked()
        if toi_name == "All Data":
            toi_name = None
        try:
            self.current_figure = self.et_data.draw_fixations(
                toi_name, 
                durationsize=duration_size, 
                durationcolour=duration_color,
                use_background=use_background
            )
            self.show_dialog(self.current_figure)
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Fixation Scatter Plot Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.show_error(f"Fail To Draw: {str(e)}")

class HeatmapCard(BaseVisualizationCard):
    def __init__(self, title, et_data, parent=None):
        super().__init__(title, et_data, parent)

    def setup_ui(self):
        super().setup_ui()
        self.duration_weight = CheckBox("Duration Weighted", self)
        self.use_background = CheckBox("Use First Video Frame As Background", self)
        self.layout().insertWidget(self.layout().count() - 2, self.duration_weight)
        self.layout().insertWidget(self.layout().count() - 2, self.use_background)

    def plot_data(self):
        toi_name = self.toi_dropdown.currentText()
        duration_weight = self.duration_weight.isChecked()
        use_background = self.use_background.isChecked()
        if toi_name == "All Data":
            toi_name = None
        try:
            self.current_figure = self.et_data.draw_heatmap(
                toi_name, 
                durationweight=duration_weight,
                use_background=use_background
            )
            self.show_dialog(self.current_figure)
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Heatmap Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.show_error(f"Fail; To Draw: {str(e)}")

class ScanpathCard(BaseVisualizationCard):
    def __init__(self, title, et_data, parent=None):
        super().__init__(title, et_data, parent)

    def setup_ui(self):
        super().setup_ui()
        self.use_background = CheckBox("Use First Video Frame As Background", self)
        self.layout().insertWidget(self.layout().count() - 2, self.use_background)

    def plot_data(self):
        toi_name = self.toi_dropdown.currentText()
        use_background = self.use_background.isChecked()
        if toi_name == "All Data":
            toi_name = None
        try:
            self.current_figure = self.et_data.draw_scanpath(
                toi_name, 
                use_background=use_background
            )
            self.show_dialog(self.current_figure)
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Scanpath Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.show_error(f"Fail To Draw: {str(e)}")
            
class GazeScatterCard(BaseVisualizationCard):
    def __init__(self, title, et_data, parent=None):
        super().__init__(title, et_data, parent)

    def setup_ui(self):
        super().setup_ui()
        self.use_background = CheckBox("Use First Video Frame As Background", self)
        self.layout().insertWidget(self.layout().count() - 2, self.use_background)

    def plot_data(self):
        toi_name = self.toi_dropdown.currentText()
        use_background = self.use_background.isChecked()
        if toi_name == "All Data":
            toi_name = None
        try:
            self.current_figure = self.et_data.draw_gaze_scatter(
                toi_name, 
                use_background=use_background
            )
            self.show_dialog(self.current_figure)
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Gaze Scatter Plot Done",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.show_error(f"Fail To Draw: {str(e)}")