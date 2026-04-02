from PyQt5.QtCore import Qt, QSize,QTimer
from PyQt5.QtGui import QColor,QPixmap, QResizeEvent,QImage
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget, QFrame, QTableWidgetItem, QDialog,QDesktopWidget,
                             QMainWindow, QSizePolicy, QStackedWidget, QLabel, QColorDialog,QFileDialog,QTreeWidgetItem)
from qfluentwidgets import (CheckBox,InfoBar, InfoBarPosition, StrongBodyLabel, SmoothScrollArea, Pivot, 
                            CardWidget, LineEdit, BodyLabel, ExpandLayout, InfoBarIcon, 
                            ColorDialog, Theme, setTheme, PushButton, ComboBox, SpinBox, 
                            TableWidget, IconWidget, FluentIcon, ToolTipFilter, ToolTipPosition,TreeWidget)

from .gallery_interface import GalleryInterface
from ..common.translator import Translator
from ..common.style_sheet import StyleSheet
from ..gui.eeg_fnirs_viewer_widget import EEGfNIRSViewerWidget
from ..gui.multi_viewer_widget import MultiViewerWidget
from ..data.fnirs_data import FNIRSData
from ..data.multi_data import MultiData

import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import os
import io
import sys

class ViewerInterface(GalleryInterface):
    def __init__(self, parent=None, experiment=None, name=None):
        t = Translator()
        super().__init__(
            title='',
            subtitle='',
            parent=parent
        )
        self.setObjectName('ViewerInterface')
        
        # subject_data = self.get_subject_data()

        # self.experiment = subject_data['experiment_name']
        # self.name = subject_data['name']
        # self.age = subject_data['age']

        # if self.age:
        #     self.fnirs_data_raw = FNIRSData(filename=self.data_file_path, age=self.age, output_path=self.output_path, db_info = self.db_info)
        # else:
        #     self.fnirs_data_raw = FNIRSData(filename=self.data_file_path, output_path=self.output_path, db_info = self.db_info)
        # self.fnirs_data_process = FNIRSData.from_existing(self.fnirs_data_raw)
        
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        middle_column = QWidget()
        self.middle_layout = QVBoxLayout(middle_column)
        self.middle_layout.setObjectName("middle_layout")

        middle_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        # Safely get data from interfaces
        def safe_get_data(interface_name, attribute_name):
            interface = getattr(parent, f"{interface_name}_interface", None)
            return getattr(interface, attribute_name, None) if interface else None

        data_list = [
            # safe_get_data("eeg", "eeg_data_raw"),
            safe_get_data("eeg", "eeg_data_process"),  # Assuming you want raw data twice
            # safe_get_data("fnirs", "fnirs_data_raw"),
            safe_get_data("fnirs", "fnirs_data_process"),
            safe_get_data("et", "et_data")
        ]
        # data_names = ["EEG-raw", "EEG-processed", "fNIRS-raw", "fNIRS-processed", "ET"]
        data_names = ["EEG-data", "fNIRS-data", "ET"]
        
        multi_data = MultiData(data_list, data_names)
        self.eeg_viewer2 = MultiViewerWidget(multi_data=multi_data, experiment=experiment, subject_name=name)
        self.middle_layout.addWidget(self.createExampleCard(title='Multi-data Visulization', widget=self.eeg_viewer2))
        main_layout.addWidget(middle_column, 1)



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