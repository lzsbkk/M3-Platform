from PyQt5.QtCore import Qt, QSize,QTimer
from PyQt5.QtGui import QColor,QPixmap, QResizeEvent,QImage
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget, QFrame, QTableWidgetItem, QDialog,QDesktopWidget,
                             QMainWindow, QSizePolicy, QStackedWidget, QLabel, QColorDialog,QFileDialog,QTreeWidgetItem,QFormLayout,QDialogButtonBox)
from qfluentwidgets import (CheckBox,InfoBar, InfoBarPosition, StrongBodyLabel, SmoothScrollArea, Pivot, 
                            CardWidget, LineEdit, BodyLabel, ExpandLayout, InfoBarIcon, 
                            ColorDialog, Theme, setTheme, PushButton, ComboBox, SpinBox, 
                            TableWidget, IconWidget, FluentIcon, ToolTipFilter, ToolTipPosition,TreeWidget)
from qfluentwidgets import ThemeColor

from .gallery_interface import GalleryInterface
from ..common.translator import Translator
from ..common.style_sheet import StyleSheet
from ..gui.eeg_fnirs_viewer_widget import EEGfNIRSViewerWidget
from ..data.fnirs_data import FNIRSData
from ..common.monitor import PerformanceMonitor
import torch
import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import os
import io
import sys
import re

class BadSegmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Add Bad Segment")
        self.setStyleSheet("""
        BadSegmentDialog {
            background-color: #323232;
        }
        BodyLabel, LineEdit, QDialogButtonBox {
            color: white; 
        }
        LineEdit {
            background-color: #333; 
            border: 1px solid #555;
            padding: 5px;
        }
        QDialogButtonBox QPushButton {
            background-color: #444;
            color: white;
            border: 1px solid #666;
            padding: 5px 10px;
        }
        """)
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.start_input = LineEdit(self)
        self.end_input = LineEdit(self)
        self.start_text = BodyLabel("Start Time (s):")
        self.end_text = BodyLabel("End Time (s):")
        form_layout.addRow(self.start_text, self.start_input)
        form_layout.addRow(self.end_text, self.end_input)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_segment(self):
        try:
            start = float(self.start_input.text())
            end = float(self.end_input.text())
            if start >= end:
                raise ValueError("Start Time Must Be Less Than End Time")
            return start, end
        except ValueError as e:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Invalid Input: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return None
    
class ImageViewerDialog(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        self.setup_ui()
        setTheme(Theme.LIGHT)
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
            

class FNIRSInterface(GalleryInterface):
    def __init__(self, parent=None, data_file_path=None, db_info=None, fnirs_data=None):
        t = Translator()
        super().__init__(
            title='',
            subtitle='',
            parent=parent
        )
        self.setObjectName('fNIRSInterface')
        
        self.data_file_path = data_file_path
        self.db_info = db_info

        subject_data = self.get_subject_data()

        self.experiment = subject_data['experiment_name']
        self.name = subject_data['name']
        self.age = subject_data['age']
        self.output_path = subject_data['full_output_path']

        if fnirs_data:
            self.fnirs_data_raw = fnirs_data
            self.fnirs_data_raw.parent = self
        elif self.age:
            self.fnirs_data_raw = FNIRSData(filename=self.data_file_path, age=self.age, output_path=self.output_path, db_info = self.db_info)
            self.fnirs_data_raw.parent = self
        else:
            self.fnirs_data_raw = FNIRSData(filename=self.data_file_path, output_path=self.output_path, db_info = self.db_info)
            self.fnirs_data_raw.parent = self

        self.fnirs_data_process = FNIRSData.from_existing(self.fnirs_data_raw)
        self.fnirs_data_raw.viewmode = 'raw'
        self.fnirs_data_raw.update_attributes()

        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        left_column = QWidget()
        # middle_column = QWidget()
        right_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        # self.middle_layout = QVBoxLayout(middle_column)
        # self.middle_layout.setObjectName("middle_layout")
        right_layout = QVBoxLayout(right_column)

        left_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # middle_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # self.eeg_viewer1 = EEGfNIRSViewerWidget(self.fnirs_data_raw, ThemeColor.LIGHT_2.color())
        self.eeg_viewer2 = EEGfNIRSViewerWidget(self.fnirs_data_process, ThemeColor.LIGHT_2.color())


        # data_list = [self.fnirs_data_raw, self.fnirs_data_process]  # Your list of data objects
        # multi_data = MultiData(data_list, data_names)
        # self.eeg_viewer2 = MultiViewerWidget(multi_data)
        
        right_layout.addWidget(self.createExampleCard(title='  fNIRS Data', widget=self.eeg_viewer2))
        # self.middle_layout.addWidget(self.createExampleCard(title='  Pre-processed Data', widget=self.eeg_viewer2))

        self.pivot_interface = PivotInterface(self, fnirs_data=self.fnirs_data_process, eeg_viewer=self.eeg_viewer2)
        left_layout.addWidget(self.pivot_interface, 1)

        main_layout.addWidget(left_column, 2)
        # main_layout.addWidget(middle_column, 1)
        main_layout.addWidget(right_column, 3)

        self.update_data_info()

    def update_preprocess_data(self):
        self.eeg_viewer2.channel_list.update_data()

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
            
            subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['fnirs_output_path'])
            
            if subject_data.get('fnirs_data_path'):
                subject_data['fnirs_data_path'] = os.path.join(project.base_path, subject_data['fnirs_data_path'])
            else:
                subject_data['fnirs_data_path'] = None

            if self.data_file_path:
                self.data_file_path = os.path.join(project.base_path, self.data_file_path)
        else:
            raise ValueError("Unable to retrieve subject data from database")
        
        return subject_data

    def update_data_info(self):
        if hasattr(self.pivot_interface, 'infoDataInterface'):
            self.pivot_interface.infoDataInterface.update_data_info(self.fnirs_data_raw, self.fnirs_data_process)

    def createExampleCard(self, title, widget):
        card = QFrame()
        card.setObjectName("ExampleCard")
        # card.setStyleSheet("""
        #     #ExampleCard {
        #         border: 1px solid #e0e0e0;
        #         border-radius: 5px;
        #         margin: 5px;
        #         padding: 5px;
        #     }
        # """)
        layout = QVBoxLayout(card)
        
        title_label = StrongBodyLabel(self)
        title_label.setText(title)
        layout.addWidget(title_label)
        
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(widget)
        
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        return card

class PivotInterface(QWidget):
    def __init__(self, parent=None, fnirs_data=None, eeg_viewer=None):
        super().__init__(parent=parent)
        self.fnirs_data = fnirs_data
        self.eeg_viewer = eeg_viewer

        self.Eparent = parent

        self.setObjectName('PivotInterface')
        self.vBoxLayout = QVBoxLayout(self)
        # self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        # self.vBoxLayout.setSpacing(0)

        self.pivot = Pivot(self)
        self.contentArea = QWidget(self)
        self.contentLayout = QVBoxLayout(self.contentArea)
        # self.contentLayout.setContentsMargins(0, 0, 0, 0)
        # self.contentLayout.setSpacing(0)

        self.stackedWidget = QStackedWidget(self.contentArea)
        self.contentLayout.addWidget(self.stackedWidget, 1)

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.contentArea, 1)

        self.infoDataInterface = DataInfoInterface(self)
        self.preprocessingInterface = PreprocessingInterface(self, fnirs_data=self.fnirs_data, eeg_viewer=self.eeg_viewer)
        self.featureExtractionInterface = FeatureExtractionInterface(self,fnirs_data=self.fnirs_data)
        self.visualizationInterface = VisualizationInterface(self,fnirs_data=self.fnirs_data)

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
    
    def update_data_info(self, fnirs_data_raw, fnirs_data_process):
        self.infoDataInterface.update_data_info(fnirs_data_raw, fnirs_data_process)

    def update_processed_data_info(self, fnirs_data_process):
        self.infoDataInterface.update_processed_data_info(fnirs_data_process)

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
        self.create_info_card("Channel Num", "")
        self.create_info_card("Raw Data Sampling Rate", "")
        self.create_info_card("Processed Data Sampling Rate", "")
        self.create_info_card("Sampling Points", "")
        self.create_info_card("Duration", "")
        self.vBoxLayout.addStretch(1)

    def create_info_card(self, title, value):
        info_card = CustomInfoCard(title, value, self)
        self.info_cards[title] = info_card
        self.vBoxLayout.addWidget(info_card)

    def update_data_info(self, fnirs_data_raw, fnirs_data_process):
        self.info_cards["Channel Num"].content = str(int(fnirs_data_raw.num_channels/3))
        self.info_cards["Raw Data Sampling Rate"].content = f"{fnirs_data_raw.sample_rate:.0f} Hz"
        self.info_cards["Processed Data Sampling Rate"].content = f"{fnirs_data_process.sample_rate:.0f} Hz"
        self.info_cards["Sampling Points"].content = f"{fnirs_data_process.num_samples}"
        self.info_cards["Duration"].content = f"{fnirs_data_process.data_time:.2f} s"

        for card in self.info_cards.values():
            card.update_content()
    
    def update_processed_data_info(self, fnirs_data_process):
        self.info_cards["Processed Data Sampling Rate"].content = f"{fnirs_data_process.sample_rate:.0f} Hz"
        self.info_cards["Sampling Points"].content = f"{fnirs_data_process.num_samples}"
        self.info_cards["Duration"].content = f"{fnirs_data_process.data_time:.2f} s"

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
    def __init__(self, parent=None, fnirs_data=None, eeg_viewer=None):
        super().__init__(parent)
        self.fnirs_data = fnirs_data
        self.eeg_viewer = eeg_viewer
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel("Data Preprocessing", self)
        layout.addWidget(title_label)

        distance_layout = QHBoxLayout()
        self.distance_filter_check = self.create_checkbox("Channel Filter")
        distance_layout.addWidget(self.distance_filter_check)
        self.min_distance = LineEdit(self)
        self.min_distance.setPlaceholderText("Minimum Distance (cm)")
        distance_layout.addWidget(self.min_distance)
        distance_layout.addWidget(BodyLabel("~", self))
        self.max_distance = LineEdit(self)
        self.max_distance.setPlaceholderText("Maximum Distance (cm)")
        distance_layout.addWidget(self.max_distance)
        layout.addLayout(distance_layout)

        crop_layout = QHBoxLayout()
        self.crop_check = self.create_checkbox("Time Cropping")
        crop_layout.addWidget(self.crop_check)
        self.crop_tmin = LineEdit(self)
        self.crop_tmin.setPlaceholderText("Start Time (s)")
        crop_layout.addWidget(self.crop_tmin)
        crop_layout.addWidget(BodyLabel("~", self))
        self.crop_tmax = LineEdit(self)
        self.crop_tmax.setPlaceholderText("End Time (s)")
        crop_layout.addWidget(self.crop_tmax)
        layout.addLayout(crop_layout)

        exclude_bads_layout = QHBoxLayout()
        self.exclude_bads_check = self.create_checkbox("Exclude Bad Channels")
        exclude_bads_layout.addWidget(self.exclude_bads_check)
        self.exclude_bads_input = LineEdit(self)
        self.exclude_bads_input.setPlaceholderText("Format: Channel1, Channel2,...")
        exclude_bads_layout.addWidget(self.exclude_bads_input)
        layout.addLayout(exclude_bads_layout)

        bad_segments_layout = QHBoxLayout()
        self.bad_segments_check = self.create_checkbox("Remove Bad Segments")
        bad_segments_layout.addWidget(self.bad_segments_check)
        self.bad_segments_input = LineEdit(self)
        self.bad_segments_input.setPlaceholderText("Format: (start1,end1), (start2,end2),...")
        bad_segments_layout.addWidget(self.bad_segments_input)
        self.add_bad_segment_button = PrimaryPushButton("Add", self)
        self.add_bad_segment_button.clicked.connect(self.add_bad_segment)
        bad_segments_layout.addWidget(self.add_bad_segment_button)
        layout.addLayout(bad_segments_layout)

        detrend_layout = QHBoxLayout()
        self.detrend_check = self.create_checkbox("Detrend")
        detrend_layout.setSpacing(28)
        detrend_layout.addWidget(self.detrend_check)
        self.detrend_order = self.create_combo_box(['0', '1'])
        self.detrend_order.setCurrentText('1')
        self.detrend_order.setFixedWidth(154)
        detrend_layout.addWidget(self.detrend_order)
        detrend_layout.addStretch(1)
        layout.addLayout(detrend_layout)

        tddr_layout = QHBoxLayout()
        self.tddr_check = self.create_checkbox("Motion Correction")
        tddr_layout.addWidget(self.tddr_check)
        self.tddr_type = self.create_combo_box(['TDDR', 'None'])
        self.tddr_type.setCurrentText('TDDR')
        self.tddr_type.setFixedWidth(154)
        tddr_layout.addWidget(self.tddr_type)
        tddr_layout.addStretch(1)
        layout.addLayout(tddr_layout)

        bandpass_layout = QHBoxLayout()
        self.bandpass_check = self.create_checkbox("Bandpass Filter")
        bandpass_layout.addWidget(self.bandpass_check)
        self.bandpass_low = LineEdit(self)
        self.bandpass_low.setPlaceholderText("Low-cut (Hz)")
        bandpass_layout.addWidget(self.bandpass_low)
        bandpass_layout.addWidget(BodyLabel("~", self))
        self.bandpass_high = LineEdit(self)
        self.bandpass_high.setPlaceholderText("High-cut (Hz)")
        bandpass_layout.addWidget(self.bandpass_high)
        layout.addLayout(bandpass_layout)

        resample_layout = QHBoxLayout()
        self.resample_check = self.create_checkbox("Resample")
        resample_layout.setSpacing(28)
        resample_layout.addWidget(self.resample_check)
        self.resample_freq = LineEdit(self)
        self.resample_freq.setPlaceholderText("New Sampling Rate (Hz)")
        self.resample_freq.setFixedWidth(154)
        resample_layout.addWidget(self.resample_freq)
        resample_layout.addStretch(1)
        layout.addLayout(resample_layout)

        self.confirm_button = PrimaryPushButton("Confirm", self)
        self.confirm_button.clicked.connect(self.on_confirm)
        layout.addWidget(self.confirm_button)

    def create_checkbox(self, label):
        checkbox = CheckBox(self)
        checkbox.setText(label)
        return checkbox

    def create_combo_box(self, items):
        combo_box = ComboBox(self)
        combo_box.addItems(items)
        combo_box.setFixedWidth(154)
        return combo_box

    def add_bad_segment(self):
        dialog = BadSegmentDialog(self)
        if dialog.exec_():
            segment = dialog.get_segment()
            if segment:
                start, end = segment
                current_text = self.bad_segments_input.text()
                if current_text:
                    new_text = f"{current_text},({start:.2f},{end:.2f})"
                else:
                    new_text = f"({start:.2f},{end:.2f})"
                self.bad_segments_input.setText(new_text)

    def validate_float(self, value, field_name):
        
        if not value:
            return None
        try:
            if not re.match(r'^\d+(\.\d+)?$', value):
                raise ValueError(f"{field_name} format is invalid. Please enter a valid number (e.g., 0.01 or 10).")
            return float(value)
        except ValueError as e:
            raise ValueError(f"{field_name} is invalid: {str(e)}")
    
    # @PerformanceMonitor()  
    def on_confirm(self):
        if self.fnirs_data is None:
            self.show_error("Data Not loaded")
            return

        try:
            min_distance = max_distance = None
            if self.distance_filter_check.isChecked():
                max_distance = self.validate_float(self.min_distance.text(), "Minimum Distance")
                max_distance = self.validate_float(self.max_distance.text(), "Maximum Distance")
                if min_distance is not None and max_distance is not None:
                    if min_distance < 0 or max_distance < 0:
                        raise ValueError("Distance Range Must Be Non-negative")
                    if min_distance > max_distance:
                        raise ValueError("Minimum Distance Cannot Be Greater Than Maximum Distance")

            crop = None
            if self.crop_check.isChecked():
                crop_tmin = self.validate_float(self.crop_tmin.text(), "Start Time")
                crop_tmax = self.validate_float(self.crop_tmax.text(), "End Time")
                if crop_tmin is not None and crop_tmax is not None:
                    if crop_tmin < 0 or crop_tmax < 0:
                        raise ValueError("Time Range Must Be Non-negative")
                    if crop_tmin > crop_tmax:
                        raise ValueError("Start Time Cannot Be Later Than End Time")
                    crop = (crop_tmin, crop_tmax)

            exclude_bads = None
            if self.exclude_bads_check.isChecked():
                exclude_bads_text = self.exclude_bads_input.text()
                if exclude_bads_text:
                    exclude_bads = [ch.strip() for ch in exclude_bads_text.split(',') if ch.strip()]
                else:
                    raise ValueError("Please Enter Bad Channel Names To Exclude")

            bad_segments = None
            if self.bad_segments_check.isChecked():
                bad_segments = self.parse_bad_segments(self.bad_segments_input.text())
                if bad_segments is None:
                    raise ValueError("Invalid Bad Segments Format")

            filter_bands = None
            if self.bandpass_check.isChecked():
                bandpass_low = self.validate_float(self.bandpass_low.text(), "Low Frequency")
                bandpass_high = self.validate_float(self.bandpass_high.text(), "High Frequency")
                if bandpass_low is not None and bandpass_high is not None:
                    if bandpass_low < 0 or bandpass_high < 0:
                        raise ValueError("Bandpass Filter Frequencies Must Be Non-negative")
                    if bandpass_low > bandpass_high:
                        raise ValueError("Low Frequency Cannot Be Greater Than high frequency")
                    filter_bands = (bandpass_low, bandpass_high)

            resample = None
            if self.resample_check.isChecked():
                resample = self.validate_float(self.resample_freq.text(), "Resampling Frequency")
                if resample is not None and resample <= 0:
                    raise ValueError("Resampling Frequency Must Be Greater Than 0")

            detrend = self.detrend_check.isChecked()
            detrend_order = int(self.detrend_order.currentText()) if detrend else None

            tddr = self.tddr_check.isChecked() and self.tddr_type.currentText() == 'TDDR'

            self.fnirs_data.fnirs_preprocessing_pipeline(
                crop=crop,
                min_distance=min_distance,
                max_distance=max_distance,
                exclude_bads=exclude_bads,
                bad_segments=bad_segments,
                filter_bands=filter_bands,
                resample=resample,
                detrend=detrend,
                detrend_order=detrend_order,
                tddr=tddr
            )


            if hasattr(self.parent, 'update_processed_data_info'):
                self.parent.update_processed_data_info(self.fnirs_data)

            self.show_success("Preprocessing Done")

        except ValueError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Preprocess Failed: {str(e)}")


    def show_error(self, message):
        # InfoBar.error(
        #     content=message,
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=5000,
        #     parent=self
        # )
        InfoBar.error(
            title='Error',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def show_success(self, message):
        # InfoBar.success(
        #     content=message,
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=2000,
        #     parent=self
        # )
        InfoBar.success(
            title='Success',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def parse_bad_segments(self, input_string):
        pattern = r'\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?)\)'
        matches = re.findall(pattern, input_string)

        if not matches:
            return None

        try:
            bad_segments = [(float(start), float(end)) for start, end in matches]
            return bad_segments
        except ValueError:
            return None

    def parse_bad_segments(self, input_string):
        pattern = r'\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?)\)'
        matches = re.findall(pattern, input_string)

        if not matches:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Invalid Bad Segments Format",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return None

        try:
            bad_segments = [(float(start), float(end)) for start, end in matches]
            return bad_segments
        except ValueError:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Invalid Bad Segments Data: Time Values Could Not Be Converted To Float",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return None

class PreprocessingInterface(SmoothScrollArea):
    def __init__(self, parent=None, fnirs_data=None, eeg_viewer=None):
        super().__init__(parent)
        self.fnirs_data = fnirs_data
        self.eeg_viewer = eeg_viewer
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
        self.preprocessing_card = PreprocessingCard(self, self.fnirs_data, self.eeg_viewer)
        self.vBoxLayout.addWidget(self.preprocessing_card)
        self.event_annotation = EventAnnotationCard("Event Annotation")
        if self.fnirs_data is not None and self.eeg_viewer is not None:
            self.event_annotation.set_data(self.fnirs_data, self.eeg_viewer)
        else:
            print("Warning: fnirs_data or eeg_viewer is None in PreprocessingInterface")
        self.vBoxLayout.addWidget(self.event_annotation)
        self.event_window_setting_card = EventWindowSettingCard("Event Extraction", self.fnirs_data)
        self.vBoxLayout.addWidget(self.event_window_setting_card)



    def update_processed_data_info(self, fnirs_data_process):
        if hasattr(self.parent, 'update_processed_data_info'):
            self.parent.update_processed_data_info(fnirs_data_process)

def predict_with_scripted_model(model, input_data):
    if not isinstance(input_data, torch.Tensor):
        input_tensor = torch.tensor(input_data, dtype=torch.float32)
    else:
        input_tensor = input_data.clone().detach()

    if input_tensor.dim() == 2:
        input_tensor = input_tensor.unsqueeze(0)
    
    # print(input_tensor.shape)
    with torch.no_grad():
        output = model(input_tensor)
        probabilities = torch.softmax(output, dim=1)
        fatigue_prob = probabilities[0, 1].item()
        pred_class = output.argmax(dim=1).item()
    
    return pred_class, fatigue_prob

def app_predict(real_eeg_data, model_path):
    device = torch.device("cpu")
    
    # if getattr(sys, 'frozen', False):
    #     application_path = sys._MEIPASS
    # else:
    #     application_path = os.path.dirname(os.path.abspath(__file__))
    
    # model_path = os.path.join(model_path, f"best_{condition}_model.pth")
    
    try:
        model = torch.jit.load(model_path, map_location=device)
        model.eval()
        
        print(f"Load Model {model_path} Successfully!")
        
        pred_class, prob = predict_with_scripted_model(model, real_eeg_data)
        
        class_label = "Yes" if pred_class == 1 else "No"
        
        return {
            "class_label": class_label,
            "probability": prob,
            "status": "success"
        }
    
    except Exception as e:
        return {
            "error": f"Fail To Predict: {str(e)}",
            "status": "error"
        }

class fNIRSModelAnalysisCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.current_figure = None
        self.last_directory = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        def create_label(text):
            label = BodyLabel(text)
            label.setFixedWidth(100)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return label
        # Algorithm selection
        # con_layout = QHBoxLayout()
        # con_layout.addWidget(BodyLabel("Condition Choice:", self))
        # self.con_dropdown = ComboBox(self)
        # self.con_dropdown.addItems(['Fatigue', 'Distraction', 'Vertigo'])
        # con_layout.addWidget(self.con_dropdown)
        # layout.addLayout(con_layout)

        layout.addWidget(BodyLabel("Model Path:"))
        self.model_path = LineEdit(self)
        self.model_path.setPlaceholderText('Model File Path')
        layout.addWidget(self.model_path)
        self.model_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.model_button.clicked.connect(lambda: self.browse_file(self.model_path, "Model Files (*.pth)"))
        layout.addWidget(self.model_button)

        event_layout = QHBoxLayout()
        event_layout.addWidget(BodyLabel("Event"))
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.clicked.connect(self.populate_event_dropdown)
        event_layout.addWidget(self.event_dropdown)
        layout.addLayout(event_layout)

        predict_result = QHBoxLayout()
        predict_result.addWidget(BodyLabel("Result"))
        self.predict_text = LineEdit(self)
        self.predict_text.setAlignment(Qt.AlignCenter)

        # self.predict_text.clicked.connect(self.populate_event_dropdown)
        predict_result.addWidget(self.predict_text)
        layout.addLayout(predict_result)

        # Analysis button
        self.analyze_button = PrimaryPushButton("Start Predict", self)
        self.analyze_button.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_button)

        


    def browse_file(self, edit, file_filter):
        initial_dir = self.last_directory if self.last_directory else None
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File", initial_dir, file_filter)
        if file_path:
            edit.setText(file_path)
            self.last_directory = os.path.dirname(file_path)

    def populate_event_dropdown(self):
        self.event_dropdown.clear()
        events = self.fnirs_data.get_events()
        unique_events = set(event[3] for event in events)  # Assuming event[3] is the description
        self.event_dropdown.addItems(sorted(unique_events))

    def start_analysis(self):
        # condition = self.con_dropdown.currentText()
        modelPath = self.model_path.text()
        selected_event = self.event_dropdown.currentText()
        

        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("Analyzing...")

        try:
            predic_data = self.fnirs_data.get_predict_data(selected_event)
            predic_data = predic_data[:,:,:-1]
            # predic_data.reshape((1,512,32))
            # print(predic_data.shape)
            predication = app_predict(predic_data, modelPath)
            print(f"Condition: {predication}!")
            self.predict_text.setText(predication['class_label'])
            self.fnirs_data.predict_to_csv(predication['class_label'], selected_event)
            InfoBar.success(
                title='Success',
                content=f"FNIRs Condition Predication Already Done!",
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
                content=f"Analysis Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        finally:
            self.analyze_button.setEnabled(True)
            self.analyze_button.setText("Start Predict")

class EventWindowSettingCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection dropdown
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(85)  
        event_layout.addWidget(event_label)
        self.event_dropdown = self.create_combo_box([])
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.event_dropdown.currentIndexChanged.connect(self.update_input_fields)
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)
        layout.addLayout(event_layout)

        # Event window input fields
        window_layout = QHBoxLayout()
        window_label = BodyLabel("Event Related Window", self)
        window_label.setFixedWidth(85)  
        window_layout.addWidget(window_label)
        self.tmin_input = LineEdit(self)
        self.tmin_input.setPlaceholderText("Start Time (s)")
        # self.tmin_input.setFixedWidth(100)
        self.tmin_input.textChanged.connect(self.update_event_window)
        window_layout.addWidget(self.tmin_input)
        window_layout.addWidget(BodyLabel("~", self))
        self.tmax_input = LineEdit(self)
        self.tmax_input.setPlaceholderText("End Time (s)")
        # self.tmax_input.setFixedWidth(100)
        self.tmax_input.textChanged.connect(self.update_event_window)
        window_layout.addWidget(self.tmax_input)
        # window_layout.addStretch(1)
        layout.addLayout(window_layout)

        # Baseline input field
        baseline_layout = QHBoxLayout()
        baseline_label = BodyLabel("Baseline Time", self)
        baseline_label.setFixedWidth(85)  
        baseline_layout.addWidget(baseline_label)
        self.baseline_input = LineEdit(self)
        self.baseline_input.setPlaceholderText("Baseline Time (s)")
        self.baseline_input.setFixedWidth(154)
        self.baseline_input.textChanged.connect(self.update_event_baseline)
        baseline_layout.addWidget(self.baseline_input)
        baseline_layout.addStretch(1)
        layout.addLayout(baseline_layout)

        self.populate_event_dropdown()

    def create_combo_box(self, items):
        combo_box = ComboBox(self)
        combo_box.addItems(items)
        combo_box.setFixedWidth(154)  
        return combo_box

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("Default Setting")
        events = self.fnirs_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "Default Setting":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def update_input_fields(self):
        selected_event = self.event_dropdown.currentText()
        if selected_event == "Default Setting":
            tmin, tmax = self.fnirs_data.default_event_window
            baseline = self.fnirs_data.default_event_baseline
        else:
            tmin, tmax = self.fnirs_data.get_event_window(selected_event)
            baseline = self.fnirs_data.get_event_baseline(selected_event)
        
        self.tmin_input.setText(str(tmin) if tmin is not None else "None")
        self.tmax_input.setText(str(tmax) if tmax is not None else "None")
        self.baseline_input.setText(str(baseline) if baseline is not None else "None")

    def update_event_window(self):
        selected_event = self.event_dropdown.currentText()
        tmin = self.tmin_input.text()
        tmax = self.tmax_input.text()

        try:
            tmin = float(tmin) if tmin and tmin.lower() != "none" else None
            tmax = float(tmax) if tmax and tmax.lower() != "none" else None

            if selected_event == "Default Setting":
                self.fnirs_data.set_default_event_window(tmin, tmax)
            else:
                self.fnirs_data.set_event_window(selected_event, tmin, tmax)
        except ValueError:
            pass
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )

    def update_event_baseline(self):
        selected_event = self.event_dropdown.currentText()
        baseline = self.baseline_input.text()

        try:
            if baseline == "" or baseline.lower() == "none" or baseline.lower() == "None":
                baseline = None
            else:
                baseline = float(baseline)
                if baseline >= 0:
                    # InfoBar.warning(
                    #     orient=Qt.Horizontal,
                    #     isClosable=True,
                    #     position=InfoBarPosition.TOP,
                    #     duration=2000,
                    #     parent=self
                    # )
                    InfoBar.warning(
                        title='Warning',
                        content="Baselin Time Must Be Less Than 0",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return  

            if selected_event == "Default Setting":
                self.fnirs_data.set_default_event_baseline(baseline)
            else:
                self.fnirs_data.set_event_baseline(selected_event, baseline)
        except ValueError:
            pass

class EventAnnotationCard(CardWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = None
        self.eeg_viewer = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        description_layout = QHBoxLayout()
        description_layout.addWidget(BodyLabel("Event Description", self))
        self.event_description = LineEdit(self)
        self.event_description.setPlaceholderText("Event Description Information")
        description_layout.addWidget(self.event_description)
        layout.addLayout(description_layout)

        time_layout = QHBoxLayout()
        time_layout.addWidget(BodyLabel("Start Time", self))
        self.start_time = LineEdit(self)
        self.start_time.setPlaceholderText("Start Time (s), Multiple Times Separated By Commas")
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(BodyLabel("Duration", self))
        self.duration = LineEdit(self)
        self.duration.setPlaceholderText("Duration (s)")
        time_layout.addWidget(self.duration)
        layout.addLayout(time_layout)

        self.add_event_button = PrimaryPushButton("Add Event", self)
        self.add_event_button.setIcon(FluentIcon.ADD)
        self.add_event_button.clicked.connect(self.add_events)
        layout.addWidget(self.add_event_button)

        self.event_table = TableWidget(self)
        self.event_table.setColumnCount(5)
        self.event_table.setHorizontalHeaderLabels(["Color", "Start Time", "Duration", "Description", "Delete"])
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.setColumnWidth(0, 40)
        self.event_table.setColumnWidth(4, 60)
        
        self.event_table.setMinimumHeight(200)  
        
        self.event_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout.addWidget(self.event_table)

        self.setMinimumHeight(420) 

    def set_data(self, fnirs_data, eeg_viewer):
        self.fnirs_data = fnirs_data
        self.eeg_viewer = eeg_viewer
        self.load_events()
        self.update_event_table()

    def load_events(self):
        if self.fnirs_data:
            for event in self.fnirs_data.get_events():
                start_time, end_time, color, description = event
                duration = end_time - start_time
                self.add_event_to_table(start_time, duration, color, description)

    def add_events(self):
        if self.fnirs_data is None:
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

        if not self.start_time.text() or not self.duration.text() or not self.event_description.text():
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Fill All The Fields",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            start_times = [float(t.strip()) for t in self.start_time.text().split(',')]
            duration = float(self.duration.text())
        except ValueError:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Time Must Be Valid Num",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        description = self.event_description.text()

        if duration < 0:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Duration Must Be Greater Than Or Equal To 0",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        existing_color = None
        for event in self.fnirs_data.get_events():
            if event[3] == description:
                existing_color = event[2]
                break

        if existing_color is None:
            existing_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        added_count = 0
        for start_time in start_times:
            end_time = start_time + duration
            event = (start_time, end_time, existing_color, description)
            
            try:
                self.fnirs_data.add_event(event)
                self.eeg_viewer.add_event(event)
                self.add_event_to_table(start_time, duration, existing_color, description)
                added_count += 1
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
                    content=f"Adding Event Failed: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

        if added_count > 0:
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content=f"Already Add {added_count} Events",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

            self.event_description.clear()
            self.start_time.clear()
            self.duration.clear()

    def add_event_to_table(self, start_time, duration, color, description):
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
        self.event_table.setItem(row, 2, QTableWidgetItem(f"{duration:.2f}"))
        self.event_table.setItem(row, 3, QTableWidgetItem(description))

        delete_button = PushButton(self)
        delete_button.setIcon(FluentIcon.CLOSE)
        delete_button.setToolTip("Delete Event")
        delete_button.setFixedSize(QSize(24, 24))
        delete_button.clicked.connect(lambda _, r=row: self.delete_event(r))
        
        delete_button.installEventFilter(ToolTipFilter(delete_button, 300, ToolTipPosition.TOP))
        
        delete_button_widget = QWidget()
        delete_button_layout = QHBoxLayout(delete_button_widget)
        delete_button_layout.setContentsMargins(0, 0, 0, 0)
        delete_button_layout.addWidget(delete_button, alignment=Qt.AlignCenter)
        self.event_table.setCellWidget(row, 4, delete_button_widget)

    def update_event_table(self):
        self.event_table.clearContents()
        self.event_table.setRowCount(0)
        if self.fnirs_data:
            for event in self.fnirs_data.get_events():
                start_time, end_time, color, description = event
                duration = end_time - start_time
                self.add_event_to_table(start_time, duration, color, description)

    def delete_event(self, row):
        if self.fnirs_data is None or row >= len(self.fnirs_data.get_events()):
            print(f"Warning: Cannot delete event at row {row}.")
            return

        event = self.fnirs_data.get_events()[row]
        self.fnirs_data.delete_event(event)
        if self.eeg_viewer:
            self.eeg_viewer.delete_event(event)
        self.update_event_table()

        # InfoBar.success(
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=2000,
        #     parent=self
        # )
        InfoBar.success(
            title='Success',
            content=f"Already Delete Event: {event[3]}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )


class FeatureExtractionInterface(SmoothScrollArea):
    def __init__(self, parent=None, fnirs_data=None):
        super().__init__(parent)
        self.fnirs_data = fnirs_data
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
        self.glm_analysis_card = GLMAnalysisCard("GLM Analysis", self.fnirs_data)
        self.feature_extraction_card = FeatureExtractionCard("Feature Extraction", self.fnirs_data)
        self.fnirs_model_predict_card = fNIRSModelAnalysisCard("fNIRs Condition Predict", self.fnirs_data)
        self.vBoxLayout.addWidget(self.glm_analysis_card)
        self.vBoxLayout.addWidget(self.feature_extraction_card)
        self.vBoxLayout.addWidget(self.fnirs_model_predict_card)
        self.vBoxLayout.addStretch(1)

class GLMAnalysisCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        hrf_layout = QHBoxLayout()
        hrf_layout.addWidget(BodyLabel("HRF Model", self))
        self.hrf_dropdown = ComboBox(self)
        self.hrf_dropdown.addItems(['glover','spm'])
        hrf_layout.addWidget(self.hrf_dropdown)
        layout.addLayout(hrf_layout)

        self.run_button = PrimaryPushButton("Run GLM Analysis", self)
        self.run_button.clicked.connect(self.run_glm_analysis)
        layout.addWidget(self.run_button)

        self.result_label = QLabel(self)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setVisible(False)
        self.result_label.mousePressEvent = self.on_image_click
        layout.addWidget(self.result_label)

    def run_glm_analysis(self):
        if self.fnirs_data is None:
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

        hrf_model = self.hrf_dropdown.currentText()

        try:
            self.current_figure = self.fnirs_data.run_glm_analysis(hrf_model=hrf_model)

            buf = io.BytesIO()
            self.current_figure.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            image = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(image)
            self.result_label.setPixmap(pixmap.scaled(450, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.result_label.setVisible(True)

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="GLM Analysis Done",
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
                content=f"GLM Analysis Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFileDialog, QListWidgetItem
from PyQt5.QtCore import Qt
from qfluentwidgets import (CardWidget, ComboBox, LineEdit, PushButton, 
                            BodyLabel, SubtitleLabel, InfoBar, InfoBarPosition,
                            ListWidget, PrimaryPushButton, CheckBox, FlowLayout, 
                            Theme, PillPushButton, FluentIcon)

class FeatureExtractionCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.all_features = ['Mean', 'Peak', 'Minimum', 'AUC', 'Peak Latency']
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Channel and Feature selection
        selection_layout = QHBoxLayout()

        # Channel selection
        channel_layout = QVBoxLayout()
        channel_layout.addWidget(BodyLabel("Channels"))
        
        self.channel_tree = TreeWidget(self)
        self.channel_tree.setHeaderHidden(True)
        self.populate_channel_tree()
        channel_layout.addWidget(self.channel_tree)

        selection_layout.addLayout(channel_layout)

        # Feature selection
        feature_layout = QVBoxLayout()
        feature_layout.addWidget(BodyLabel("Features"))
        
        self.feature_tree = TreeWidget(self)
        self.feature_tree.setHeaderHidden(True)
        self.populate_feature_tree()
        feature_layout.addWidget(self.feature_tree)

        selection_layout.addLayout(feature_layout)

        layout.addLayout(selection_layout)

        # Event selection
        event_layout = QHBoxLayout()
        event_layout.addWidget(BodyLabel("Event"))
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.clicked.connect(self.populate_event_dropdown)
        event_layout.addWidget(self.event_dropdown)
        layout.addLayout(event_layout)

        # Feature extraction type selection
        # extraction_type_layout = QHBoxLayout()
        # extraction_type_layout.addWidget(BodyLabel("Feature Classification"))
        # self.extraction_type_dropdown = ComboBox(self)
        # self.extraction_type_dropdown.addItems(["None", "Fatigue", "Distraction", "Vertigo"])
        # self.extraction_type_dropdown.setCurrentText("None")
        # extraction_type_layout.addWidget(self.extraction_type_dropdown)
        # layout.addLayout(extraction_type_layout)

        # Extract features button
        self.extract_button = PrimaryPushButton("Extract Features")
        self.extract_button.clicked.connect(self.extract_features)
        layout.addWidget(self.extract_button)

        # Initial population of event dropdown
        self.populate_event_dropdown()

        self.setMinimumHeight(550)

    def populate_channel_tree(self):
        self.channel_tree.clear()
        root = QTreeWidgetItem(self.channel_tree, ["All Channels"])
        root.setCheckState(0, Qt.Unchecked)
        
        hb_types = ['HbO', 'HbR', 'HbT']
        for hb_type in hb_types:
            hb_item = QTreeWidgetItem(root, [hb_type])
            hb_item.setCheckState(0, Qt.Unchecked)
            for channel in self.fnirs_data.channel_names:
                if channel.endswith(hb_type):
                    channel_item = QTreeWidgetItem(hb_item, [channel])
                    channel_item.setCheckState(0, Qt.Unchecked)
        
        self.channel_tree.expandAll()
        self.channel_tree.itemChanged.connect(lambda item, column: self.update_tree_state(self.channel_tree, item, column))

    def populate_feature_tree(self):
        self.feature_tree.clear()
        root = QTreeWidgetItem(self.feature_tree, ["All Features"])
        root.setCheckState(0, Qt.Unchecked)
        for feature in self.all_features:
            item = QTreeWidgetItem(root, [feature])
            item.setCheckState(0, Qt.Unchecked)
        self.feature_tree.expandAll()
        self.feature_tree.itemChanged.connect(lambda item, column: self.update_tree_state(self.feature_tree, item, column))

    def update_tree_state(self, tree_widget, item, column):
        tree_widget.blockSignals(True)  

        root = tree_widget.invisibleRootItem().child(0)
        if item == root:
            self.set_all_checked(root, item.checkState(0))
        elif item.parent() == root:
            self.set_group_checked(item, item.checkState(0))
        else:
            self.update_parent_state(item.parent())

        tree_widget.blockSignals(False)  

    def set_all_checked(self, root_item, state):
        for i in range(root_item.childCount()):
            child_item = root_item.child(i)
            child_item.setCheckState(0, state)
            if child_item.childCount() > 0:  
                for j in range(child_item.childCount()):
                    child_item.child(j).setCheckState(0, state)

    def set_group_checked(self, group_item, state):
        for i in range(group_item.childCount()):
            group_item.child(i).setCheckState(0, state)
        self.update_parent_state(group_item.parent())

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

    def populate_event_dropdown(self):
        self.event_dropdown.clear()
        events = self.fnirs_data.get_events()
        unique_events = set(event[3] for event in events)  # Assuming event[3] is the description
        self.event_dropdown.addItems(sorted(unique_events))
        
        # if self.event_dropdown.count() == 0:
        #     InfoBar.info(
        #         orient=Qt.Horizontal,
        #         isClosable=True,
        #         position=InfoBarPosition.TOP,
        #         duration=2000,
        #         parent=self
        #     )
    # @PerformanceMonitor()
    def extract_features(self):
        selected_channels = self.get_selected_items(self.channel_tree)
        selected_features = self.get_selected_items(self.feature_tree)
        selected_event = self.event_dropdown.currentText()
        # extraction_type = self.extraction_type_dropdown.currentText()

        if not selected_channels:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Choose At Least One Channel",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

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
                content="Please Choose At Least Feature",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        if not selected_event:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Choose At Least One Event",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            results = self.fnirs_data.extract_features(
                event_name=selected_event,
                channel_names=selected_channels,
                features=selected_features,
                # folder=extraction_type if extraction_type != "None" else ''
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
                content="Feature Extraction Done",
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
                content=f"Feature Extraction Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def get_selected_items(self, tree_widget):
        root = tree_widget.invisibleRootItem().child(0)  
        selected_items = []

        for i in range(root.childCount()):
            child_item = root.child(i)
            if child_item.checkState(0) in [Qt.Checked, Qt.PartiallyChecked]:
                if child_item.childCount() > 0:  
                    for j in range(child_item.childCount()):
                        channel_item = child_item.child(j)
                        if channel_item.checkState(0) == Qt.Checked:
                            selected_items.append(channel_item.text(0))
                else:  
                    selected_items.append(child_item.text(0))

        return selected_items

class VisualizationInterface(SmoothScrollArea):
    def __init__(self, parent=None, fnirs_data=None):
        super().__init__(parent)
        self.fnirs_data = fnirs_data
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
        self.single_channel_card = SingleChannelResponseCard("Single-Channel Event Response", self.fnirs_data)
        self.event_data_card = EventDataCard("Standard Event Response", self.fnirs_data)
        self.topography_card = TopographyCard("Joint Plot", self.fnirs_data)
        self.topology_time_series_card = TopologyTimeSeriesCard("Topological Time Series", self.fnirs_data)
        self.event_heatmap_card = EventHeatmapCard("Event Heatmap", self.fnirs_data)

        self.vBoxLayout.addWidget(self.single_channel_card)
        self.vBoxLayout.addWidget(self.event_data_card)
        self.vBoxLayout.addWidget(self.topography_card)
        self.vBoxLayout.addWidget(self.topology_time_series_card)
        self.vBoxLayout.addWidget(self.event_heatmap_card)
        self.vBoxLayout.addStretch(1)

class SingleChannelResponseCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Channel selection
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(BodyLabel("Channel", self))
        self.channel_dropdown = ComboBox(self)
        self.channel_dropdown.clicked.connect(self.refresh_channels)  # Add click event handler
        self.refresh_channels()  # Initial population of channels
        channel_layout.addWidget(self.channel_dropdown)
        layout.addLayout(channel_layout)

        # Hemoglobin type selection
        hb_layout = QHBoxLayout()
        hb_layout.addWidget(BodyLabel("Hemoglobin Type:", self))
        self.hbo_checkbox = CheckBox("HbO", self)
        self.hbr_checkbox = CheckBox("HbR", self)
        self.hbt_checkbox = CheckBox("HbT", self)
        hb_layout.addWidget(self.hbo_checkbox)
        hb_layout.addWidget(self.hbr_checkbox)
        hb_layout.addWidget(self.hbt_checkbox)
        layout.addLayout(hb_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_single_channel)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()  # Initially hide the preview
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def refresh_channels(self):
        """Update channel list when dropdown is clicked"""
        current_text = self.channel_dropdown.currentText()
        self.channel_dropdown.clear()
        if self.fnirs_data and self.fnirs_data.channel_names:
            unique_channels = sorted(set([ch.split(' ')[0] for ch in self.fnirs_data.channel_names]))
            self.channel_dropdown.addItems(unique_channels)
            if current_text in unique_channels:
                self.channel_dropdown.setCurrentText(current_text)

    def plot_single_channel(self):
        channel_base = self.channel_dropdown.currentText()
        hemoglobin_types = []
        if self.hbo_checkbox.isChecked():
            hemoglobin_types.append('HbO')
        if self.hbr_checkbox.isChecked():
            hemoglobin_types.append('HbR')
        if self.hbt_checkbox.isChecked():
            hemoglobin_types.append('HbT')

        if not hemoglobin_types:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Select At Least One Hemoglobin Type",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            self.current_figure = self.fnirs_data.plot_single_channel_response(channel_base, hemoglobin_types)
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            # Convert plot to QPixmap for preview
            # buf = io.BytesIO()
            # self.current_figure.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # pixmap = QPixmap.fromImage(image)
            # self.image_preview.setPixmap(pixmap.scaled(450, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # self.image_preview.show()  # Show the preview after plotting

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )

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

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

class EventDataCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_layout.addWidget(BodyLabel("Event", self))
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        layout.addLayout(event_layout)

        # Hemoglobin type selection
        hb_layout = QHBoxLayout()
        hb_layout.addWidget(BodyLabel("Hemoglobin Type", self))
        self.hbo_checkbox = CheckBox("HbO", self)
        self.hbr_checkbox = CheckBox("HbR", self)
        self.hbt_checkbox = CheckBox("HbT", self)
        hb_layout.addWidget(self.hbo_checkbox)
        hb_layout.addWidget(self.hbr_checkbox)
        hb_layout.addWidget(self.hbt_checkbox)
        layout.addLayout(hb_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_event_data)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()  # Initially hide the preview
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        events = self.fnirs_data.get_events()
        event_names = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_names)
        if current_text in event_names:
            self.event_dropdown.setCurrentText(current_text)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_event_data(self):
        event_name = self.event_dropdown.currentText()
        hb_types = []
        if self.hbo_checkbox.isChecked():
            hb_types.append('HbO')
        if self.hbr_checkbox.isChecked():
            hb_types.append('HbR')
        if self.hbt_checkbox.isChecked():
            hb_types.append('HbT')

        if not hb_types:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Select At Least One Hemoglobin Type",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            self.current_figure = self.fnirs_data.plot_event_data(event_name, hb_types=hb_types)
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            # Convert plot to QPixmap for preview
            # buf = io.BytesIO()
            # self.current_figure.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # pixmap = QPixmap.fromImage(image)
            # self.image_preview.setPixmap(pixmap.scaled(450, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # self.image_preview.show()  # Show the preview after plotting

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )

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

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

class TopographyCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_layout.addWidget(BodyLabel("Event", self))
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        layout.addLayout(event_layout)

        # Hemoglobin type selection
        hb_layout = QHBoxLayout()
        hb_layout.addWidget(BodyLabel("Hemoglobin Type", self))
        self.hb_type_dropdown = ComboBox(self)
        self.hb_type_dropdown.addItems(['HbO', 'HbR', 'HbT'])
        hb_layout.addWidget(self.hb_type_dropdown)
        layout.addLayout(hb_layout)

        # Time points input
        time_layout = QHBoxLayout()
        time_label = BodyLabel("Time Points", self)
        time_label.setFixedWidth(215)
        time_layout.addWidget(time_label)
        self.time_input = LineEdit(self)
        self.time_input.setFixedWidth(215)
        self.time_input.setPlaceholderText("Input Time Points, Separated By Commas (Optional)")
        time_layout.addWidget(self.time_input)
        time_layout.addStretch(1)
        layout.addLayout(time_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_topography)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()  # Initially hide the preview
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        events = self.fnirs_data.get_events()
        event_names = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_names)
        if current_text in event_names:
            self.event_dropdown.setCurrentText(current_text)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_topography(self):
        event_name = self.event_dropdown.currentText()
        hb_type = self.hb_type_dropdown.currentText().lower()

        times = None
        if self.time_input.text():
            try:
                times = [float(t.strip()) for t in self.time_input.text().split(',')]
            except ValueError:
                # InfoBar.error(
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.error(
                    title='Error',
                    content="Please Input Valid Time Points",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

        try:
            self.current_figure = self.fnirs_data.plot_topography(event_name, hb_type, times)
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            # Convert plot to QPixmap for preview
            # buf = io.BytesIO()
            # self.current_figure.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # pixmap = QPixmap.fromImage(image)
            # self.image_preview.setPixmap(pixmap.scaled(450, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # self.image_preview.show()  # Show the preview after plotting

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )

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

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

class TopologyTimeSeriesCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_layout.addWidget(BodyLabel("Event", self))
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        layout.addLayout(event_layout)

        # Hemoglobin type selection
        hb_layout = QHBoxLayout()
        hb_layout.addWidget(BodyLabel("Hemoglobin Type", self))
        self.hb_type_dropdown = ComboBox(self)
        self.hb_type_dropdown.addItems(['HbO', 'HbR', 'HbT'])
        hb_layout.addWidget(self.hb_type_dropdown)
        layout.addLayout(hb_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_data)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()  # Initially hide the preview
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        events = self.fnirs_data.get_events()
        event_names = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_names)
        if current_text in event_names:
            self.event_dropdown.setCurrentText(current_text)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_data(self):
        event = self.event_dropdown.currentText()
        hb_type = self.hb_type_dropdown.currentText().lower()

        try:
            self.current_figure = self.fnirs_data.plot_topology_time_series(event, hb_type)
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            # Convert plot to QPixmap for preview
            # buf = io.BytesIO()
            # self.current_figure.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # pixmap = QPixmap.fromImage(image)
            # self.image_preview.setPixmap(pixmap.scaled(450, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # self.image_preview.show()  # Show the preview after plotting

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )

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

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()

class EventHeatmapCard(CardWidget):
    def __init__(self, title, fnirs_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.fnirs_data = fnirs_data
        self.current_figure = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_layout.addWidget(BodyLabel("Event:", self))
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        layout.addLayout(event_layout)

        # Hemoglobin type selection
        hb_layout = QHBoxLayout()
        hb_layout.addWidget(BodyLabel("Hemoglobin Type:", self))
        self.hb_type_dropdown = ComboBox(self)
        self.hb_type_dropdown.addItems(['HbO', 'HbR', 'HbT'])
        hb_layout.addWidget(self.hb_type_dropdown)
        layout.addLayout(hb_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_data)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = QLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()  # Initially hide the preview
        # self.image_preview.mousePressEvent = self.on_image_click
        # layout.addWidget(self.image_preview)

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        events = self.fnirs_data.get_events()
        event_names = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_names)
        if current_text in event_names:
            self.event_dropdown.setCurrentText(current_text)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_data(self):
        event = self.event_dropdown.currentText()
        hb_type = self.hb_type_dropdown.currentText().lower()

        try:
            self.current_figure = self.fnirs_data.plot_event_heatmap(event, hb_type)
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()
            # # Convert plot to QPixmap for preview
            # buf = io.BytesIO()
            # self.current_figure.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # pixmap = QPixmap.fromImage(image)
            # self.image_preview.setPixmap(pixmap.scaled(450, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            # self.image_preview.show()  # Show the preview after plotting

            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Event Heatmap Generated Successfully", 
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

    def on_image_click(self, event):
        if self.current_figure:
            dialog = ImageViewerDialog(self.current_figure, self)
            dialog.exec_()