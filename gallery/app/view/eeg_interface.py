from PyQt5.QtCore import Qt, QSize,QTimer
from PyQt5.QtGui import QColor,QPixmap, QResizeEvent,QImage,QPainter
from PyQt5.QtWidgets import (QSpacerItem, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QTableWidgetItem, QGridLayout,QFormLayout,QDialogButtonBox,
                             QMainWindow, QSizePolicy, QStackedWidget, QLabel, QColorDialog,QFileDialog,QDialog,QDesktopWidget,QTreeWidgetItem)
from qfluentwidgets import (TreeWidget,FluentStyleSheet,CheckBox,InfoBar, InfoBarPosition, StrongBodyLabel, SmoothScrollArea, ScrollArea, Pivot, 
                            CardWidget, LineEdit, BodyLabel, ExpandLayout, InfoBarIcon, 
                            ColorDialog, Theme, setTheme, PushButton, ComboBox, SpinBox, 
                            TableWidget, IconWidget, FluentIcon, ToolTipFilter, ToolTipPosition,MessageBoxBase)
from qfluentwidgets import ThemeColor
from .gallery_interface import GalleryInterface
from ..common.translator import Translator
from ..common.style_sheet import StyleSheet
from ..gui.eeg_fnirs_viewer_widget import EEGfNIRSViewerWidget
from ..data.eeg_data import EEGData

import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import os
import io
import re
import sys
import time
import psutil
from functools import wraps
from memory_profiler import memory_usage
from ..common.monitor import PerformanceMonitor
import torch

# def get_process_memory():
#     process = psutil.Process(os.getpid())
# def get_accurate_memory():
#     psutil_mem = get_process_memory()
#     mprof_mem = memory_usage(-1, interval=0.5, timeout=1)[0]
#     return (psutil_mem + mprof_mem) / 2
# class PerformanceMonitor:
#     def __init__(self):
#         self.process = psutil.Process(os.getpid())
    
#     def __call__(self, func):
#         @wraps(func)
#         def wrapped(instance):
#             start_time = time.perf_counter()
#             # mem_before = memory_usage(-1, interval=0.1, timeout=1)[0]
#             mem_before = self.process.memory_info().rss / 1024 / 1024
#             cpu_before = self.process.cpu_percent(interval=None)
            
#             result = func(instance)
            
#             end_time = time.perf_counter()
#             # mem_after = memory_usage(-1, interval=0.1, timeout=1)[0]
#             mem_after = self.process.memory_info().rss / 1024 / 1024
#             cpu_after = self.process.cpu_percent(interval=None)
            
#             exec_time = end_time - start_time
#             mem_used = mem_after - mem_before
#             cpu_used = cpu_after - cpu_before
            
            
#             return result
#         return wrapped

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
        return float(self.start_input.text()), float(self.end_input.text())
    
class ICAComponentsWindow(QDialog):
    def __init__(self, fig_list, eeg_data, parent=None):
        super().__init__(parent)
        self.fig_list = fig_list
        self.eeg_data = eeg_data
        self.selected_components = []
        self.component_widgets = []
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("ICA Components")
        self.setMinimumSize(800, 800)
        self.setStyleSheet("""
        ICAComponentsWindow {
            background-color: white;
        }
        """)
        layout = QVBoxLayout(self)

        instruction_label = StrongBodyLabel("Choose ICA Components To Remove:")
        layout.addWidget(instruction_label)

        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.enableTransparentBackground()
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName('view')
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setSpacing(10)

        for i, fig in enumerate(self.fig_list):
            component_widget = self.create_component_widget(i, fig)
            self.component_widgets.append(component_widget)

        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)

        self.selected_label = StrongBodyLabel("Choosed Components:")
        layout.addWidget(self.selected_label)

        confirm_button = PrimaryPushButton("Confirm")
        confirm_button.clicked.connect(self.accept)
        confirm_button.setFixedHeight(40)
        layout.addWidget(confirm_button)

        QTimer.singleShot(0, self.adjustGridLayout)

    def create_component_widget(self, index, fig):
        component_widget = QWidget()
        component_layout = QVBoxLayout(component_widget)
        component_layout.setContentsMargins(0, 0, 0, 0)

        checkbox = CheckBox(f"{index}")
        checkbox.setFixedSize(100, 30)
        checkbox.stateChanged.connect(lambda state, idx=index: self.update_selected_components(state, idx))
        component_layout.addWidget(checkbox)

        canvas = FigureCanvas(fig)
        canvas.setFixedSize(100, 110)
        canvas.mpl_connect('button_press_event', lambda event, idx=index: self.on_component_click(event, idx))
        component_layout.addWidget(canvas)

        return component_widget

    def update_selected_components(self, state, index):
        if state == Qt.Checked:
            self.selected_components.append(index)
        else:
            self.selected_components.remove(index)
        self.update_selected_label()

    def update_selected_label(self):
        selected_text = ", ".join(map(str, sorted(self.selected_components)))
        self.selected_label.setText(f"Choose Components: {selected_text}")

    def get_selected_components(self):
        return sorted(self.selected_components)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustGridLayout()

    def adjustGridLayout(self):
        width = self.scroll_area.viewport().width()
        item_width = 120  
        max_cols = max(1, width // item_width)

        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)

        for i, widget in enumerate(self.component_widgets):
            row = i // max_cols
            col = i % max_cols
            self.grid_layout.addWidget(widget, row, col)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.adjustGridLayout)

    def on_component_click(self, event, index):
        if event.button == 1:  
            try:
                figs = self.eeg_data.plot_ica_topography(index)
                if not isinstance(figs, list):
                    figs = [figs]
                for fig in figs:
                    dialog = ImageViewerDialog(fig, self)
                    dialog.exec_()
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
                    content=f"Draw ICA Components Images Failed: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
class ImageViewerDialog(QDialog):
    
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        self.setup_ui()
        setTheme(Theme.LIGHT)
        QTimer.singleShot(0, self.update_image)

    def setup_ui(self):
        self.setWindowTitle("Image Viewer")
        # self.setStyleSheet("""
        # ImageViewerDialog {
        #     background-color: #323232;
        # }
        # """)
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

class EEGInterface(GalleryInterface):
    def __init__(self, parent=None, data_file_path=None, db_info=None, eeg_data=None):
        t = Translator()
        super().__init__(
            title='',
            subtitle='',
            parent=parent
        )
        self.setObjectName('EEGInterface')
        
        self.data_file_path = data_file_path
        self.db_info = db_info

        subject_data = self.get_subject_data()

        self.experiment = subject_data['experiment_name']
        self.name = subject_data['name']
        self.output_path = subject_data['full_output_path']
        self.montage_file_path = subject_data.get('eeg_montage_path')

        if eeg_data == None:
            self.eeg_data_raw = EEGData(filename=self.data_file_path, custom_montage=self.montage_file_path, output_path=self.output_path, db_info = self.db_info)
        else:
            self.eeg_data_raw = eeg_data

        self.eeg_data_process = EEGData.from_existing(self.eeg_data_raw)

        self.eeg_data_raw.viewmode = 'raw'
        self.eeg_data_raw.update_attributes()
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

        # self.eeg_viewer1 = EEGfNIRSViewerWidget(self.eeg_data_raw, ThemeColor.LIGHT_2.color())
        self.eeg_viewer2 = EEGfNIRSViewerWidget(self.eeg_data_process, ThemeColor.LIGHT_2.color())
        
        # left_layout.addWidget(self.createExampleCard(title='  Raw Data', widget=self.eeg_viewer2))
        right_layout.addWidget(self.createExampleCard(title='  EEG Data', widget=self.eeg_viewer2))
        # self.middle_layout.addWidget(self.createExampleCard(title='  Processed Data', widget=self.eeg_viewer2))

        self.pivot_interface = PivotInterface(self, eeg_data=self.eeg_data_process, eeg_viewer=self.eeg_viewer2)
        left_layout.addWidget(self.pivot_interface)

        main_layout.addWidget(left_column, 2)
        # main_layout.addWidget(middle_column, 1)
        main_layout.addWidget(right_column, 3)

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
            
            subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['eeg_output_path'])
            
            if subject_data.get('eeg_montage_path'):
                subject_data['eeg_montage_path'] = os.path.join(project.base_path, subject_data['eeg_montage_path'])
            else:
                subject_data['eeg_montage_path'] = None
            
            if subject_data.get('eeg_data_path'):
                subject_data['eeg_data_path'] = os.path.join(project.base_path, subject_data['eeg_data_path'])
            else:
                subject_data['eeg_data_path'] = None

            if self.data_file_path:
                self.data_file_path = os.path.join(project.base_path, self.data_file_path)
        else:
            raise ValueError("Unable to retrieve subject data from database")
        
        return subject_data
    
    def update_data_info(self):
        if hasattr(self.pivot_interface, 'infoDataInterface'):
            self.pivot_interface.infoDataInterface.update_data_info(self.eeg_data_raw, self.eeg_data_process)

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
    def __init__(self, parent=None, eeg_data=None, eeg_viewer=None):
        super().__init__(parent=parent)
        self.eeg_data = eeg_data
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
        self.preprocessingInterface = PreprocessingInterface(self, eeg_data=self.eeg_data, eeg_viewer=self.eeg_viewer)
        self.featureExtractionInterface = FeatureExtractionInterface(self,eeg_data=self.eeg_data)
        self.visualizationInterface = VisualizationInterface(self,eeg_data=self.eeg_data)

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
    
    def update_data_info(self, eeg_data_raw, eeg_data_process):
        self.infoDataInterface.update_data_info(eeg_data_raw, eeg_data_process)

    def update_processed_data_info(self, eeg_data_process):
        self.infoDataInterface.update_processed_data_info(eeg_data_process)

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

    def update_data_info(self, eeg_data_raw, eeg_data_process):
        
        # print(int(eeg_data_raw.num_channels))
        # print(f"{eeg_data_raw.sample_rate:.0f} Hz")
        # print(f"{eeg_data_process.sample_rate:.0f} Hz")
        # print(f"{eeg_data_process.num_samples}")
        # print(f"{eeg_data_process.data_time:.2f} s")
        self.info_cards["Channel Num"].content = str(int(eeg_data_raw.num_channels))
        self.info_cards["Raw Data Sampling Rate"].content = f"{eeg_data_raw.sample_rate:.0f} Hz"
        self.info_cards["Processed Data Sampling Rate"].content = f"{eeg_data_process.sample_rate:.0f} Hz"
        self.info_cards["Sampling Points"].content = f"{eeg_data_process.num_samples}"
        self.info_cards["Duration"].content = f"{eeg_data_process.data_time:.2f} s"

        for card in self.info_cards.values():
            # print("********")
            # print("here")
            # print("********")
            card.update_content()
    
    def update_processed_data_info(self, eeg_data_process):
        self.info_cards["Processed Data Sampling Rate"].content = f"{eeg_data_process.sample_rate:.0f} Hz"
        self.info_cards["Sampling Points"].content = f"{eeg_data_process.num_samples}"
        self.info_cards["Duration"].content = f"{eeg_data_process.data_time:.2f} s"

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
    def __init__(self, parent=None, eeg_data=None, eeg_viewer=None):
        super().__init__(parent)
        # self.monitor = PerformanceMonitor()
        self.eeg_data = eeg_data
        self.eeg_viewer = eeg_viewer
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel("Data Preprocessing", self)
        layout.addWidget(title_label)

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

        notch_layout = QHBoxLayout()
        self.notch_check = self.create_checkbox("Line Noise Filter")
        notch_layout.addWidget(self.notch_check)
        self.notch_dropdown = self.create_combo_box(["50Hz", "60Hz"])
        self.notch_dropdown.setFixedWidth(154)
        notch_layout.addWidget(self.notch_dropdown)
        notch_layout.addStretch(1)
        layout.addLayout(notch_layout)

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

        interpolate_layout = QHBoxLayout()
        self.interpolate_check = self.create_checkbox("Interpolate Bad Channels")
        interpolate_layout.addWidget(self.interpolate_check)
        self.interpolate_input = LineEdit(self)
        self.interpolate_input.setPlaceholderText("Format: Channel1,Channel2,...")
        interpolate_layout.addWidget(self.interpolate_input)
        layout.addLayout(interpolate_layout)

        reference_layout = QHBoxLayout()
        self.reference_check = self.create_checkbox("Re-referencing")
        reference_layout.setSpacing(28)
        reference_layout.addWidget(self.reference_check)
        self.reference_dropdown = self.create_combo_box(["Mastoid", "Average"])
        self.reference_dropdown.setFixedWidth(154)
        reference_layout.addWidget(self.reference_dropdown)
        reference_layout.addStretch(1)
        layout.addLayout(reference_layout)

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

    def update_ica_components(self):
        try:
            new_value = int(self.ica_components_input.text())
            self.eeg_data.set_ica_components(new_value)
        except ValueError:
            pass

    def run_ica(self):
        if self.eeg_data is None:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Data Not loaded",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            fig_list = self.eeg_data.plot_all_ica_components()
            self.show_ica_components(fig_list)
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
                content=f"ICA Analysis Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def show_ica_components(self, fig_list):
        dialog = ICAComponentsWindow(fig_list, self.eeg_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            selected_components = dialog.get_selected_components()
            self.ica_input.setText(','.join(map(str, selected_components)))

    def update_ica_exclude(self):
        if self.eeg_data is None:
            return

        input_text = self.ica_input.text().strip()
        if not input_text:
            self.eeg_data.ica_exclude = []
            return

        try:
            ica_components = [int(x.strip()) for x in input_text.split(',') if x.strip()]
            
            if all(x > 0 for x in ica_components):
                self.eeg_data.ica_exclude = ica_components
                print(f"ICA Removal Components Have Been Updated To: {ica_components}")  
            else:
                raise ValueError("All ICA Component Index Must Be Positive Integer")
        except ValueError as e:
            print(f"Error: {str(e)}")  

    def add_bad_segment(self):
        dialog = BadSegmentDialog(self)
        if dialog.exec_():
            start, end = dialog.get_segment()
            current_text = self.bad_segments_input.text()
            if current_text:
                new_text = f"{current_text},({start:.2f},{end:.2f})"
            else:
                new_text = f"({start:.2f},{end:.2f})"
            self.bad_segments_input.setText(new_text)

    # @PerformanceMonitor()
    def on_confirm(self):
        if self.eeg_data is None:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Data Not loaded",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            crop = (float(self.crop_tmin.text()), float(self.crop_tmax.text())) if self.crop_check.isChecked() else None
            bandpass = (float(self.bandpass_low.text()), float(self.bandpass_high.text())) if self.bandpass_check.isChecked() else None
            notch = float(self.notch_dropdown.currentText().replace('Hz', '')) if self.notch_check.isChecked() else None
            
            bad_segments = None
            if self.bad_segments_check.isChecked():
                bad_segments = self.parse_bad_segments(self.bad_segments_input.text())
                if bad_segments is None:
                    return  

            interpolate_bads = self.interpolate_input.text().split(',') if self.interpolate_check.isChecked() else None
            # ica_components = [int(x) for x in self.ica_input.text().split(',')] if self.ica_check.isChecked() else None
            reference = self.reference_dropdown.currentText() if self.reference_check.isChecked() else None
            resample = float(self.resample_freq.text()) if self.resample_check.isChecked() else None

            error = self.eeg_data.eeg_preprocessing_pipeline(
                crop=crop,
                bandpass=bandpass,
                notch=notch,
                bad_segments=bad_segments,
                interpolate_bads=interpolate_bads,
                # ica_components=ica_components,
                reference=reference,
                resample=resample
            )

            if error:
                # InfoBar.error(
                #     content=error,
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.error(
                    title='Error',
                    content=error,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                if hasattr(self.parent, 'update_processed_data_info'):
                    self.parent.update_processed_data_info(self.eeg_data)
                
                # InfoBar.success(
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.success(
                    title='Success',
                    content="Pre-processing Done",
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
                content=f"Pre-processing Failed: {str(e)}",
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
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='error',
                content="Invalid Bad Segment Format",
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

class ICARemovalCard(CardWidget):
    def __init__(self, parent=None, eeg_data=None, eeg_viewer=None):
        super().__init__(parent)
        self.eeg_data = eeg_data
        self.eeg_viewer = eeg_viewer
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel("ICA Removal", self)
        layout.addWidget(title_label)

        ica_layout = QHBoxLayout()
        ica_layout.addWidget(BodyLabel("ICA Removal", self))
        self.ica_input = LineEdit(self)
        self.ica_input.setPlaceholderText("Component Index")
        self.ica_input.textChanged.connect(self.update_ica_exclude)
        ica_layout.addWidget(self.ica_input)

        self.run_ica_button = PrimaryPushButton("Run ICA", self)
        self.run_ica_button.setFixedWidth(82)
        self.run_ica_button.clicked.connect(self.run_ica)
        ica_layout.addWidget(self.run_ica_button)

        layout.addLayout(ica_layout)

        self.confirm_button = PrimaryPushButton("Confirm", self)
        self.confirm_button.clicked.connect(self.on_confirm)
        layout.addWidget(self.confirm_button)

    def update_ica_exclude(self):
        if self.eeg_data is None:
            return

        input_text = self.ica_input.text().strip()
        if not input_text:
            self.eeg_data.ica_exclude = []
            return

        try:
            ica_components = [int(x.strip()) for x in input_text.split(',') if x.strip()]
            
            if all(x > 0 for x in ica_components):
                self.eeg_data.ica_exclude = ica_components
                print(f"ICA Removal Components Have Been Updated To: {ica_components}")
            else:
                raise ValueError("All ICA Index Must Be Positive Integer")
        except ValueError as e:
            print(f"Error: {str(e)}")

    def run_ica(self):
        if self.eeg_data is None:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Data Not loaded",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            fig_list = self.eeg_data.plot_all_ica_components()
            self.show_ica_components(fig_list)
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
                content=f"ICA Analysis Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def show_ica_components(self, fig_list):
        dialog = ICAComponentsWindow(fig_list, self.eeg_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            selected_components = dialog.get_selected_components()
            self.ica_input.setText(','.join(map(str, selected_components)))

    def on_confirm(self):
        if self.eeg_data is None:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Data Not loaded",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            ica_components = [int(x) for x in self.ica_input.text().split(',')] if self.ica_input.text() else None

            error = self.eeg_data.eeg_ICA_pipeline(ica_components=ica_components)

            if error:
                # InfoBar.error(
                #     content=error,
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.error(
                    title='Error',
                    content=error,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                if hasattr(self.parent, 'update_processed_data_info'):
                    self.parent.update_processed_data_info(self.eeg_data)
                
                # InfoBar.success(
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.success(
                    title='Success',
                    content="ICA Done",
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
                content=f"ICA Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

class EventWindowSettingCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
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
        events = self.eeg_data.get_events()
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
            tmin, tmax = self.eeg_data.default_event_window
            baseline = self.eeg_data.default_event_baseline
        else:
            tmin, tmax = self.eeg_data.get_event_window(selected_event)
            baseline = self.eeg_data.get_event_baseline(selected_event)
        
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
                self.eeg_data.set_default_event_window(tmin, tmax)
            else:
                self.eeg_data.set_event_window(selected_event, tmin, tmax)
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
            if baseline == "" or baseline.lower() == "none":
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
                        content="Baseline Time Must Be Less Than 0",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return  

            if selected_event == "Default Setting":
                self.eeg_data.set_default_event_baseline(baseline)
            else:
                self.eeg_data.set_event_baseline(selected_event, baseline)
        except ValueError:
            pass

class PreprocessingInterface(SmoothScrollArea):
    def __init__(self, parent=None, eeg_data=None, eeg_viewer=None):
        super().__init__(parent)
        self.eeg_data = eeg_data
        self.eeg_viewer = eeg_viewer
        self.parent = parent
        self.enableTransparentBackground()
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        # self.vBoxLayout.setSpacing(10)
        # self.vBoxLayout.setAlignment(Qt.AlignTop)
        # self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.setup_ui()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.scrollWidget.setObjectName('view')


    def setup_ui(self):
        self.preprocessing_card = PreprocessingCard(self, self.eeg_data, self.eeg_viewer)
        self.ica_removal_card = ICARemovalCard(self, self.eeg_data, self.eeg_viewer)
        self.event_annotation = EventAnnotationCard("Event Annotation")
        if self.eeg_data is not None and self.eeg_viewer is not None:
            self.event_annotation.set_data(self.eeg_data, self.eeg_viewer)
        else:
            print("Warning: eeg_data or eeg_viewer is None in PreprocessingInterface")
        self.event_window_setting_card = EventWindowSettingCard("Event Extraction", self.eeg_data)

        self.vBoxLayout.addWidget(self.preprocessing_card)
        self.vBoxLayout.addWidget(self.ica_removal_card)
        self.vBoxLayout.addWidget(self.event_annotation)
        self.vBoxLayout.addWidget(self.event_window_setting_card)

    def update_data_info(self):
        if hasattr(self.parent, 'update_data_info'):
            self.parent.update_data_info()
    
    def update_processed_data_info(self, eeg_data_process):
        if hasattr(self.parent, 'update_processed_data_info'):
            self.parent.update_processed_data_info(eeg_data_process)
    
    
class EventAnnotationCard(CardWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = None
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
        self.start_time.setPlaceholderText("Start Time (s), Separate Multiple Times With Commas")
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(BodyLabel("Duration", self))
        self.duration = LineEdit(self)
        self.duration.setPlaceholderText("Duration(s)")
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

    def set_data(self, eeg_data, eeg_viewer):
        self.eeg_data = eeg_data
        self.eeg_viewer = eeg_viewer
        self.load_events()
        self.update_event_table()

    def load_events(self):
        if self.eeg_data:
            for event in self.eeg_data.get_events():
                start_time, end_time, color, description = event
                duration = end_time - start_time
                self.add_event_to_table(start_time, duration, color, description)

    def add_events(self):
        if self.eeg_data is None:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Data Not loaded",
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
                title='Warnig',
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
        for event in self.eeg_data.get_events():
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
                self.eeg_data.add_event(event)
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
        if self.eeg_data:
            for event in self.eeg_data.get_events():
                start_time, end_time, color, description = event
                duration = end_time - start_time
                self.add_event_to_table(start_time, duration, color, description)

    def delete_event(self, row):
        if self.eeg_data is None or row >= len(self.eeg_data.get_events()):
            print(f"Warning: Cannot delete event at row {row}.")
            return

        event = self.eeg_data.get_events()[row]
        self.eeg_data.delete_event(event)
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
    def __init__(self, parent=None, eeg_data=None):
        super().__init__(parent)
        self.eeg_data = eeg_data
        self.parent = parent
        self.enableTransparentBackground()
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        # self.vBoxLayout.setSpacing(10)
        # self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        
        self.setup_ui()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollWidget.setObjectName('view')

    def setup_ui(self):
        self.eeg_feature_extraction_card = EEGFeatureExtractionCard("Time-Frequency Feature Extraction", self.eeg_data)
        self.eeg_model_analysis_card = EEGModelAnalysisCard("EEG Condition Predict", self.eeg_data)
        self.vBoxLayout.addWidget(self.eeg_feature_extraction_card)
        self.vBoxLayout.addWidget(self.eeg_model_analysis_card)
        # self.vBoxLayout.addWidget(self.feature_extraction_card)
        self.vBoxLayout.addStretch(1)


class EEGFeatureExtractionCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.frequency_bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 100)
        }
        self.all_features = ['Total Amplitude', 'Mean Amplitude', 'Amplitude Variance', 'Max Positive Peak', 'Max Negative Peak', 
                             'Latency Of Max Positive Peak', 'Latency Of Max Negative Peak', 'Total Energy', 'Peak Energy', 'Power Spectral Density']
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

        self.setMinimumHeight(720)

    def populate_channel_tree(self):
        self.channel_tree.clear()
        root = QTreeWidgetItem(self.channel_tree, ["All Channels"])
        root.setCheckState(0, Qt.Unchecked)
        for channel in self.eeg_data.channel_names:
            item = QTreeWidgetItem(root, [channel])
            item.setCheckState(0, Qt.Unchecked)
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
        else:
            self.update_parent_state(item.parent())

        tree_widget.blockSignals(False)  

    def set_all_checked(self, root_item, state):
        for i in range(root_item.childCount()):
            child_item = root_item.child(i)
            child_item.setCheckState(0, state)

    def update_parent_state(self, parent_item):
        child_count = parent_item.childCount()
        checked_count = sum(parent_item.child(i).checkState(0) == Qt.Checked for i in range(child_count))

        if checked_count == 0:
            parent_item.setCheckState(0, Qt.Unchecked)
        elif checked_count == child_count:
            parent_item.setCheckState(0, Qt.Checked)
        else:
            parent_item.setCheckState(0, Qt.PartiallyChecked)

    def populate_event_dropdown(self):
        self.event_dropdown.clear()
        events = self.eeg_data.get_events()
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

        if selected_channels == [] and selected_features == []:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Choose At Least One Channel And Feature",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        if selected_event == "":
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Choose A Event",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            # extraction_type = self.extraction_type_dropdown.currentText()
            results = self.eeg_data.extract_features(
                event_name=selected_event,
                channel_names=selected_channels if selected_channels is not None else None,
                features=selected_features if selected_features is not None else None,
                frequency_bands=self.frequency_bands,
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
                content="Features Extraction Done",
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
                content=f"Features Extraction Failed: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def get_selected_items(self, tree_widget):
        root = tree_widget.invisibleRootItem().child(0)  

        if root.checkState(0) == Qt.Checked:
            return None
        else:
            return [root.child(i).text(0) for i in range(root.childCount()) if root.child(i).checkState(0) == Qt.Checked]
        
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

class EEGModelAnalysisCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
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
        events = self.eeg_data.get_events()
        unique_events = set(event[3] for event in events)  # Assuming event[3] is the description
        self.event_dropdown.addItems(sorted(unique_events))

    def start_analysis(self):
        # condition = self.con_dropdown.currentText()
        modelPath = self.model_path.text()
        selected_event = self.event_dropdown.currentText()
        

        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("Analyzing...")

        try:
            predic_data = self.eeg_data.get_predict_data(selected_event)
            predic_data = predic_data[:,:,:-1]
            # predic_data.reshape((1,512,32))
            print(predic_data.shape)
            predication = app_predict(predic_data, modelPath)
            print(f"Condition: {predication}!")
            self.predict_text.setText(predication['class_label'])
            self.eeg_data.predict_to_csv(predication['class_label'], selected_event)
            InfoBar.success(
                title='Success',
                content=f"EEG Condition Predication Already Done!",
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

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFileDialog, QListWidgetItem
from PyQt5.QtCore import Qt
from qfluentwidgets import (CardWidget, ComboBox, LineEdit, PushButton, 
                            BodyLabel, SubtitleLabel, InfoBar, InfoBarPosition,
                            ListWidget, PrimaryPushButton, CheckBox, FlowLayout)


class VisualizationInterface(SmoothScrollArea):
    def __init__(self, parent=None, eeg_data=None):
        super().__init__(parent)
        self.eeg_data = eeg_data
        self.parent = parent
        self.enableTransparentBackground()
        self.scrollWidget = QWidget()
        self.vBoxLayout = QVBoxLayout(self.scrollWidget)
        # self.vBoxLayout.setSpacing(10)
        # self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        
        self.setup_ui()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollWidget.setObjectName('view')

    def setup_ui(self):
        self.single_channel_card = PowerSpectralDensity("Power Spectrum Plot", self.eeg_data)
        self.event_data_card = ICATopographyCard("ICA Topographic Map", self.eeg_data)
        self.topography_card = ICAOverlayCard("ICA Pre/Post-Processing Difference Map", self.eeg_data)
        self.topology_time_series_card = SegmentedDataPlotCard("Segmented Data Waveform", self.eeg_data)
        self.psd_topomap_card = PSDTopomapCard("Power Spectral Density Topomap", self.eeg_data)
        self.evokedtopomap_card = EvokedTopomapsCard("Time-Series Topographic Map", self.eeg_data)
        self.evokedjointplot_card = EvokedJointPlotCard("Joint Plot", self.eeg_data)
        self.evoked_image_plot_card = EvokedImagePlotCard("Channel-wise Heatmap", self.eeg_data)
        self.evoked_topo_plot_card = EvokedTopoPlotCard("Topographic Time-Series Plot", self.eeg_data)

        self.vBoxLayout.addWidget(self.single_channel_card)
        self.vBoxLayout.addWidget(self.event_data_card)
        self.vBoxLayout.addWidget(self.topography_card)
        self.vBoxLayout.addWidget(self.topology_time_series_card)
        self.vBoxLayout.addWidget(self.psd_topomap_card)
        self.vBoxLayout.addWidget(self.evokedtopomap_card)
        self.vBoxLayout.addWidget(self.evokedjointplot_card)
        self.vBoxLayout.addWidget(self.evoked_image_plot_card)
        self.vBoxLayout.addWidget(self.evoked_topo_plot_card)

        self.vBoxLayout.addStretch(1)

class PowerSpectralDensity(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.fig = None  
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        data_type_layout = QHBoxLayout()
        data_type_layout.addWidget(BodyLabel("Data Type", self))
        self.data_type_dropdown = ComboBox(self)
        self.data_type_dropdown.addItems(["Pre-processed Data", "Raw Data"])
        data_type_layout.addWidget(self.data_type_dropdown)
        layout.addLayout(data_type_layout)

        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_power_spectral_density)
        layout.addWidget(self.plot_button)


    def plot_power_spectral_density(self):
        data_type = self.data_type_dropdown.currentText()
        
        if data_type == "Pre-processed Data":
            data_type = "processed"
        elif data_type == "Raw Data":
            data_type = "raw"

        try:
            self.fig = self.eeg_data.plot_power_spectral_density(data_type=data_type)

            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()

            InfoBar.success(
                title='Success',
                content="Power spectral density plot generated successfully",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            InfoBar.error(
                title='Error',
                content=f"Fail To Draw: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

class ICATopographyCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.figs = None  
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        self.layout.addWidget(title_label)

        component_layout = QHBoxLayout()
        component_layout.addWidget(BodyLabel("ICA Components", self))
        self.component_dropdown = ComboBox(self)
        self.component_dropdown.clicked.connect(self.refresh_components)
        self.populate_component_dropdown()
        component_layout.addWidget(self.component_dropdown)
        self.layout.addLayout(component_layout)

        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_ica_topography)
        self.layout.addWidget(self.plot_button)


    def populate_component_dropdown(self):
        current_text = self.component_dropdown.currentText()
        self.component_dropdown.clear()
        self.component_dropdown.addItem("All")
        for i in range(self.eeg_data.ica_components):
            self.component_dropdown.addItem(f"Component {i}")
        if current_text:
            index = self.component_dropdown.findText(current_text)
            if index >= 0:
                self.component_dropdown.setCurrentIndex(index)

    def refresh_components(self):
        self.populate_component_dropdown()

    def plot_ica_topography(self):
        selected = self.component_dropdown.currentText()
        components = 'all' if selected == "All" else int(selected.split()[-1])

        try:
            self.figs = self.eeg_data.plot_ica_topography(components)
            if not isinstance(self.figs, list):
                self.figs = [self.figs]

            for fig in self.figs:
                dialog = ImageViewerDialog(fig, self)
                dialog.exec_()

            InfoBar.success(
                title='Success',
                content="ICA topography plot(s) generated successfully",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            InfoBar.error(
                title='Error',
                content=f"Fail To Draw: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)

class ICAOverlayCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # layout.addWidget(description)

        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_ica_overlay)
        layout.addWidget(self.plot_button)

        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def plot_ica_overlay(self):
        try:
            self.fig = self.eeg_data.plot_ica_overlay()
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # buf = io.BytesIO()
            # self.fig.set_size_inches(12, 8)
            # self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # pixmap = QPixmap.fromImage(image)
            
            # self.full_pixmap = pixmap

            # scaled_pixmap = pixmap.scaledToWidth(self.width() - 40, Qt.SmoothTransformation)
            # self.image_preview.setPixmap(scaled_pixmap)
            # self.image_preview.show()

            # new_height = self.height() - self.image_preview.height() + scaled_pixmap.height()
            # self.setMinimumHeight(new_height)
            # self.setMaximumHeight(new_height)

            # plt.close(fig)

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
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # if self.image_preview.pixmap():
        #     scaled_pixmap = self.full_pixmap.scaledToWidth(self.width() - 40, Qt.SmoothTransformation)
        #     self.image_preview.setPixmap(scaled_pixmap)

        #     new_height = self.height() - self.image_preview.height() + scaled_pixmap.height()
        #     self.setMinimumHeight(new_height)
        #     self.setMaximumHeight(new_height)

class SegmentedDataPlotCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(215)  
        event_layout.addWidget(event_label)
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.setFixedWidth(215)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)  
        layout.addLayout(event_layout)

        # Number of epochs input
        epochs_layout = QHBoxLayout()
        epochs_label = BodyLabel("Num Of Epoch", self)
        epochs_label.setFixedWidth(215)  
        epochs_layout.addWidget(epochs_label)
        self.epochs_input = LineEdit(self)
        self.epochs_input.setFixedWidth(215)
        self.epochs_input.setPlaceholderText("Input Integer (Default: 1)")
        epochs_layout.addWidget(self.epochs_input)
        epochs_layout.addStretch(1)  
        layout.addLayout(epochs_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_segmented_data)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()  # Initially hide the preview
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("Default")
        events = self.eeg_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "Default":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_segmented_data(self):
        event_name = self.event_dropdown.currentText()
        event_name = None if event_name == "Default" else event_name

        try:
            n_epochs = int(self.epochs_input.text()) if self.epochs_input.text() else 1
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
                content="Please Input Valid Integer",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            self.fig = self.eeg_data.plot_segmented_data(event_name=event_name, n_epochs=n_epochs)
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # # Convert plot to QPixmap for preview
            # buf = io.BytesIO()
            # self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # pixmap = QPixmap.fromImage(image)

            # # Scale the pixmap to fit the width of the card while maintaining aspect ratio
            # available_width = self.width() - 40  # Subtract margins
            # self.full_pixmap = pixmap
            # scaled_pixmap = pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
            
            # self.image_preview.setPixmap(scaled_pixmap)
            # self.image_preview.show()

            # # Adjust the card's height based on the scaled image height
            # new_height = self.height() - self.image_preview.height() + scaled_pixmap.height()
            # self.setMinimumHeight(new_height)
            # self.setMaximumHeight(new_height)

            # plt.close(fig)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # if self.image_preview.pixmap():
        #     available_width = self.width() - 40
        #     scaled_pixmap = self.full_pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
        #     self.image_preview.setPixmap(scaled_pixmap)

        #     # Adjust the card's height based on the scaled image height
        #     new_height = self.height() - self.image_preview.height() + scaled_pixmap.height()
        #     self.setMinimumHeight(new_height)
        #     self.setMaximumHeight(new_height)

    def on_image_click(self, event):
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()


class PowerSpectrumCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(215)
        event_layout.addWidget(event_label)
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.setFixedWidth(215)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)
        layout.addLayout(event_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_power_spectrum)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("All")
        events = self.eeg_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "All":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_power_spectrum(self):
        event_name = self.event_dropdown.currentText()
        event_name = None if event_name == "All" else event_name

        try:
            self.fig = self.eeg_data.plot_power_spectrum(event_name)
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # buf = io.BytesIO()
            # self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # self.full_pixmap = QPixmap.fromImage(image)

            # self.update_image_preview()

            # plt.close(fig)

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

    # def update_image_preview(self):
    #     if self.full_pixmap:
    #         available_width = self.width() - 40
    #         scaled_pixmap = self.full_pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # self.update_image_preview()

    def on_image_click(self, event):
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()

class PSDTopomapCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(215)
        event_layout.addWidget(event_label)
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.setFixedWidth(215)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)
        layout.addLayout(event_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_psd_topomap)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("All")
        events = self.eeg_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "All":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_psd_topomap(self):
        event_name = self.event_dropdown.currentText()
        event_name = None if event_name == "All" else event_name

        try:
            self.fig = self.eeg_data.plot_psd_topomap(event_name)
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # buf = io.BytesIO()
            # self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # self.full_pixmap = QPixmap.fromImage(image)

            # self.update_image_preview()

            # plt.close(fig)

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

    # def update_image_preview(self):
    #     if self.full_pixmap:
    #         available_width = self.width() - 40
    #         scaled_pixmap = self.full_pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # self.update_image_preview()

    def on_image_click(self, event):
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()

class EvokedTopomapsCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(215)
        event_layout.addWidget(event_label)
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.setFixedWidth(215)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)
        layout.addLayout(event_layout)

        # Time points input
        time_layout = QHBoxLayout()
        time_label = BodyLabel("Time Point", self)
        time_label.setFixedWidth(215)
        time_layout.addWidget(time_label)
        self.time_input = LineEdit(self)
        self.time_input.setFixedWidth(215)
        self.time_input.setPlaceholderText("Input Time Points, Separated By Commas")
        time_layout.addWidget(self.time_input)
        time_layout.addStretch(1)
        layout.addLayout(time_layout)

        # Average input
        average_layout = QHBoxLayout()
        average_label = BodyLabel("Analysis Time", self)
        average_label.setFixedWidth(215)
        average_layout.addWidget(average_label)
        self.average_input = LineEdit(self)
        self.average_input.setFixedWidth(215)
        self.average_input.setPlaceholderText("Input Analysis Time (Optional)")
        average_layout.addWidget(self.average_input)
        average_layout.addStretch(1)
        layout.addLayout(average_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_evoked_topomaps)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("All")
        events = self.eeg_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "All":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_evoked_topomaps(self):
        event_name = self.event_dropdown.currentText()
        event_name = None if event_name == "All" else event_name

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

        average = None
        if self.average_input.text():
            try:
                average = float(self.average_input.text())
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
                    content="Please Input Valid Average",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

        try:
            self.fig = self.eeg_data.plot_evoked_topomaps(event_name, times, average)
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # buf = io.BytesIO()
            # self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # self.full_pixmap = QPixmap.fromImage(image)

            # self.update_image_preview()

            # plt.close(fig)

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

    # def update_image_preview(self):
    #     if self.full_pixmap:
    #         available_width = self.width() - 40
    #         scaled_pixmap = self.full_pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # self.update_image_preview()

    def on_image_click(self, event):
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()

class EvokedJointPlotCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(215)
        event_layout.addWidget(event_label)
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.setFixedWidth(215)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)
        layout.addLayout(event_layout)

        # Time points input
        time_layout = QHBoxLayout()
        time_label = BodyLabel("Time Point", self)
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
        self.plot_button.clicked.connect(self.plot_evoked_joint)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("All")
        events = self.eeg_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "All":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_evoked_joint(self):
        event_name = self.event_dropdown.currentText()
        event_name = None if event_name == "All" else event_name

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
            self.fig = self.eeg_data.plot_evoked_joint(event_name, times)
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # buf = io.BytesIO()
            # self.fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # self.full_pixmap = QPixmap.fromImage(image)

            # self.update_image_preview()

            # plt.close(fig)

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

    # def update_image_preview(self):
    #     if self.full_pixmap:
    #         available_width = self.width() - 40
    #         scaled_pixmap = self.full_pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # self.update_image_preview()

    def on_image_click(self, event):
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
    
class EvokedImagePlotCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(215)
        event_layout.addWidget(event_label)
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.setFixedWidth(215)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)
        layout.addLayout(event_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_evoked_image)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("All")
        events = self.eeg_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "All":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_evoked_image(self):
        event_name = self.event_dropdown.currentText()
        event_name = None if event_name == "All" else event_name

        try:
            self.fig = self.eeg_data.plot_evoked_image(event_name)
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # buf = io.BytesIO()
            # self.fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # self.full_pixmap = QPixmap.fromImage(image)

            # self.update_image_preview()

            # plt.close(fig)

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

    # def update_image_preview(self):
    #     if self.full_pixmap:
    #         available_width = self.width() - 40
    #         scaled_pixmap = self.full_pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # self.update_image_preview()

    def on_image_click(self, event):
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()

class EvokedTopoPlotCard(CardWidget):
    def __init__(self, title, eeg_data, parent=None):
        super().__init__(parent)
        self.title = title
        self.eeg_data = eeg_data
        self.full_pixmap = None
        self.fig = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_label = StrongBodyLabel(self.title, self)
        layout.addWidget(title_label)

        # Event selection
        event_layout = QHBoxLayout()
        event_label = BodyLabel("Choose Event", self)
        event_label.setFixedWidth(215)
        event_layout.addWidget(event_label)
        self.event_dropdown = ComboBox(self)
        self.event_dropdown.setFixedWidth(215)
        self.event_dropdown.clicked.connect(self.refresh_events)
        self.populate_event_dropdown()
        event_layout.addWidget(self.event_dropdown)
        event_layout.addStretch(1)
        layout.addLayout(event_layout)

        # Plot button
        self.plot_button = PrimaryPushButton("Draw Image", self)
        self.plot_button.clicked.connect(self.plot_evoked_topo)
        layout.addWidget(self.plot_button)

        # Image preview
        # self.image_preview = BodyLabel(self)
        # self.image_preview.setAlignment(Qt.AlignCenter)
        # self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # self.image_preview.hide()
        # layout.addWidget(self.image_preview)

        # self.image_preview.mousePressEvent = self.on_image_click

    def populate_event_dropdown(self):
        current_text = self.event_dropdown.currentText()
        self.event_dropdown.clear()
        self.event_dropdown.addItem("All")
        events = self.eeg_data.get_events()
        event_descriptions = sorted(set(event[3] for event in events))
        self.event_dropdown.addItems(event_descriptions)
        if current_text in event_descriptions or current_text == "All":
            self.event_dropdown.setCurrentText(current_text)
        else:
            self.event_dropdown.setCurrentIndex(0)

    def refresh_events(self):
        self.populate_event_dropdown()

    def plot_evoked_topo(self):
        event_name = self.event_dropdown.currentText()
        event_name = None if event_name == "All" else event_name

        try:
            self.fig = self.eeg_data.plot_evoked_topo(event_name)
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()
            # buf = io.BytesIO()
            # self.fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            # buf.seek(0)
            # image = QImage.fromData(buf.getvalue())
            # self.full_pixmap = QPixmap.fromImage(image)

            # self.update_image_preview()

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

    # def update_image_preview(self):
    #     if self.full_pixmap:
    #         available_width = self.width() - 40
    #         scaled_pixmap = self.full_pixmap.scaledToWidth(available_width, Qt.SmoothTransformation)
    #         self.image_preview.setPixmap(scaled_pixmap)
    #         self.image_preview.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # self.update_image_preview()

    def on_image_click(self, event):
        if self.fig:
            dialog = ImageViewerDialog(self.fig, self)
            dialog.exec_()