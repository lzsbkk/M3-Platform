from PyQt5.QtCore import Qt, pyqtSignal,QThread, QPoint
from PyQt5.QtWidgets import (QGridLayout,QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QHeaderView, 
                             QInputDialog, QTableWidgetItem, QApplication, QToolBar)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from qfluentwidgets import (InfoBarPosition, InfoBar, ScrollArea, BodyLabel, ComboBox, LineEdit, Dialog, ListView, TableWidget, FluentIcon, CardWidget, 
                            ToolButton, MessageBox, PushButton, CheckBox)
from qfluentwidgets import FluentTranslator, setTheme, Theme
from ..data.project import Project
from .gallery_interface import GalleryInterface
from ..common.translator import Translator
import os
from ..common.monitor import PerformanceMonitor
from qfluentwidgets import RoundMenu, Action
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QGridLayout, QWidget
from qfluentwidgets import (IndeterminateProgressRing, LineEdit, ComboBox, MessageBox,
                            Dialog, FluentIcon, BodyLabel)
import os

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor,QPainter
from qfluentwidgets import IndeterminateProgressRing, BodyLabel, TransparentToolButton

setTheme(Theme.LIGHT)
class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        content_frame = QFrame(self)
        content_frame.setObjectName("loadingFrame")
        content_frame.setStyleSheet("""
            #loadingFrame {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 10px;
            }
        """)
        content_layout = QVBoxLayout(content_frame)

        self.progress_ring = IndeterminateProgressRing(self)
        self.progress_ring.setFixedSize(QSize(50, 50))
        content_layout.addWidget(self.progress_ring, alignment=Qt.AlignCenter)

        self.loading_label = BodyLabel("Loading Data...", self)
        content_layout.addWidget(self.loading_label, alignment=Qt.AlignCenter)

        layout.addWidget(content_frame)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))  

class DataLoadingThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)  # New signal for error handling

    def __init__(self, main_window, subject, selected_paths, db_info):
        super().__init__()
        self.main_window = main_window
        self.subject = subject
        self.selected_paths = selected_paths
        self.db_info = db_info
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            loaded_data = {}
            if not self._is_running:
                return

            if 'eeg' in self.selected_paths:
                loaded_data['eeg'] = self.main_window.load_eeg_data(
                    data_file_path=self.selected_paths['eeg'], 
                    db_info=self.db_info
                )
            else:
                loaded_data['eeg'] = 'no'

            if not self._is_running:
                return

            if 'fnirs' in self.selected_paths:
                loaded_data['fnirs'] = self.main_window.load_fnirs_data(
                    data_file_path=self.selected_paths['fnirs'], 
                    db_info=self.db_info
                )
            else:
                loaded_data['fnirs'] = 'no'

            if not self._is_running:
                return

            if 'et' in self.selected_paths:
                loaded_data['et'] = self.main_window.load_et_data(
                    data_file_path=self.selected_paths['et'], 
                    db_info=self.db_info
                )
            else:
                loaded_data['et'] = 'no'

            if not self._is_running:
                return

            if 'qu' in self.selected_paths:
                loaded_data['qu'] = True

            if self._is_running:
                self.finished.emit(loaded_data)

        except Exception as e:
            if self._is_running:
                self.error.emit(str(e))

class AddProjectDialog(Dialog):
    projectCreated = pyqtSignal(str, str)  

    def __init__(self, parent=None):
        # super().__init__(
        #     parent=parent
        # )
        super().__init__(
            title="Creat New Project",
            content="Please Choose The Project Location And Name It",
            parent=parent
        )
        self.setFixedSize(500, 200)
        self.project_path = ""
        self.initUI()

    def initUI(self):
        self.project_name_edit = LineEdit(self)
        self.project_name_edit.setPlaceholderText("Name")
        self.project_name_edit.setMinimumWidth(200)

        self.path_edit = LineEdit(self)
        self.path_edit.setPlaceholderText("Location")
        self.path_edit.setMinimumWidth(200)
        self.path_edit.setReadOnly(True)

        self.browse_btn = PushButton('Browse', self, FluentIcon.FOLDER)
        self.browse_btn.clicked.connect(self.browsePath)

        content_layout = QGridLayout()
        content_layout.addWidget(BodyLabel("Project Name:"), 0, 0)
        content_layout.addWidget(self.project_name_edit, 0, 1, 1, 2)
        content_layout.addWidget(BodyLabel("Location:"), 1, 0)
        content_layout.addWidget(self.path_edit, 1, 1)
        content_layout.addWidget(self.browse_btn, 1, 2)

        container = QWidget()
        container.setLayout(content_layout)
        self.textLayout.addWidget(container)

        self.yesButton.setText('Create')
        self.cancelButton.setText('Cancel')
        self.yesButton.clicked.connect(self.createProject)

    def browsePath(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Project Location", "")
        if path:
            self.project_path = path
            self.path_edit.setText(path)

    def createProject(self):
        project_name = self.project_name_edit.text().strip()
        if not project_name:
            # MessageBox(
            #     self
            # ).exec_()
            MessageBox(
                "Error",
                "Please Input Name",
                self
            ).exec_()
            return

        if not self.project_path:
            # MessageBox(
            #     self
            # ).exec_()
            MessageBox(
                "Error",
                "Please Choose Location",
                self
            ).exec_()
            return

        if not self.isValidProjectName(project_name):
            # MessageBox(
            #     self
            # ).exec_()
            MessageBox(
                "Error",
                "Please Avoid Using Special Characters In The Project Name",
                self
            ).exec_()
            return

        full_path = os.path.join(self.project_path, project_name)
        if os.path.exists(full_path):
            # MessageBox(
            #     self
            # ).exec_()
            MessageBox(
                "Error",
                f"Project '{project_name}' Already Exists",
                self
            ).exec_()
            return

        self.projectCreated.emit(self.project_path, project_name)
        self.accept()

    def isValidProjectName(self, name):
        import re
        return bool(re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$', name))
    
class AddExperimentDialog(Dialog):
    experimentAdded = pyqtSignal(str)

    def __init__(self, parent=None):
        # super().__init__(
        #     parent=parent
        # )
        super().__init__(
            title="Add Experiment",
            content="Please Input Experiment Name",
            parent=parent
        )
        self.setFixedSize(400, 200)
        self.initUI()

    def initUI(self):
        self.name_edit = LineEdit(self)
        self.name_edit.setPlaceholderText("Experiment Name")
        self.name_edit.setMinimumWidth(250)

        # Create the content widget
        content_widget = QWidget(self)
        content_layout = QVBoxLayout(content_widget)
        content_layout.addWidget(BodyLabel("Experiment Name:"))
        content_layout.addWidget(self.name_edit)
        content_layout.addStretch(1)

        # Add the content widget to the dialog's layout
        self.textLayout.addWidget(content_widget)

        # Customize buttons
        self.yesButton.setText('Confirm')
        self.cancelButton.setText('Cancel')
        self.yesButton.clicked.connect(self.confirm)

    def confirm(self):
        experiment_name = self.name_edit.text().strip()
        if experiment_name:
            self.experimentAdded.emit(experiment_name)
            self.accept()
        else:
            self.name_edit.setPlaceholderText("Please Input Valid Experiment Name")
            self.name_edit.setFocus()

class EditSubjectDialog(Dialog):
    subjectEdited = pyqtSignal(dict)

    def __init__(self, subject_data, parent=None):
        # super().__init__(
        #     parent=parent
        # )
        super().__init__(
            title="Edit Participant Information",
            content="Please Edit The Participant Information",
            parent=parent
        )
        self.subject_data = subject_data
        self.setFixedSize(550, 450)
        self.last_directory = ""
        self.initUI()

    def initUI(self):
        content_widget = QWidget(self)
        layout = QGridLayout(content_widget)
        
        layout.setContentsMargins(20, 40, 40, 40)
        layout.setSpacing(20)

        def create_label(text):
            label = BodyLabel(text)
            label.setFixedWidth(100)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return label

        layout.addWidget(create_label("Name:"), 0, 0)
        self.name_edit = LineEdit(self)
        self.name_edit.setText(self.subject_data['name'])
        layout.addWidget(self.name_edit, 0, 1, 1, 2)

        layout.addWidget(create_label("Gender:"), 1, 0)
        self.gender_combo = ComboBox(self)
        self.gender_combo.addItems(['Male', 'Female', 'Unknown'])
        self.gender_combo.setCurrentText(self.subject_data['gender'])
        layout.addWidget(self.gender_combo, 1, 1, 1, 2)

        layout.addWidget(create_label("Age:"), 2, 0)
        self.age_edit = LineEdit(self)
        self.age_edit.setText(str(self.subject_data['age']))
        layout.addWidget(self.age_edit, 2, 1, 1, 2)

        layout.addWidget(create_label("EEG Data:"), 3, 0)
        self.eeg_edit = LineEdit(self)
        self.eeg_edit.setText(self.subject_data.get('eeg_data_path', ''))
        layout.addWidget(self.eeg_edit, 3, 1)
        self.eeg_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.eeg_button.clicked.connect(lambda: self.browse_file(self.eeg_edit, "EEG Files (*.set *.edf *.bdf *.cnt *.vhdr *.pkl)"))
        layout.addWidget(self.eeg_button, 3, 2)

        layout.addWidget(create_label("Montage File:"), 4, 0)
        self.montage_edit = LineEdit(self)
        self.montage_edit.setText(self.subject_data.get('eeg_montage_path', ''))
        layout.addWidget(self.montage_edit, 4, 1)
        self.montage_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.montage_button.clicked.connect(self.browse_montage_file)
        layout.addWidget(self.montage_button, 4, 2)

        layout.addWidget(create_label("fNIRS Data:"), 5, 0)
        self.fnirs_edit = LineEdit(self)
        self.fnirs_edit.setText(self.subject_data.get('fnirs_data_path', ''))
        layout.addWidget(self.fnirs_edit, 5, 1)
        self.fnirs_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.fnirs_button.clicked.connect(lambda: self.browse_file(self.fnirs_edit, "fNIRS Files (*.snirf *.lufr *.pkl)"))
        layout.addWidget(self.fnirs_button, 5, 2)

        layout.addWidget(create_label("ET Data:"), 6, 0)
        self.et_edit = LineEdit(self)
        self.et_edit.setText(self.subject_data.get('et_data_path', ''))
        layout.addWidget(self.et_edit, 6, 1)
        self.et_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.et_button.clicked.connect(lambda: self.browse_file(self.et_edit, "Eye Tracking Files (*.pkl *.gz *.csv *.asc *.edf)"))
        layout.addWidget(self.et_button, 6, 2)

        self.vBoxLayout.insertWidget(2, content_widget)

        self.yesButton.setText('Update')
        self.cancelButton.setText('Cancel')
        self.yesButton.clicked.connect(self.confirm)

    def browse_file(self, edit, file_filter):
        initial_dir = self.last_directory if self.last_directory else None
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File", initial_dir, file_filter)
        if file_path:
            edit.setText(file_path)
            self.last_directory = os.path.dirname(file_path)

    def browse_montage_file(self):
        try:
            initial_dir = os.path.abspath("./resource/EEGMontage")
            if not os.path.exists(initial_dir):
                initial_dir = None
        except Exception:
            initial_dir = None

        file_path, _ = QFileDialog.getOpenFileName(self, "Choose Montage File", initial_dir, "Montage Files (*.locs)")
        if file_path:
            resource_dir = os.path.abspath("./resource/EEGMontage")
            if os.path.commonpath([resource_dir, file_path]) == resource_dir:
                relative_path = os.path.relpath(file_path, start=os.path.abspath("."))
                self.montage_edit.setText(relative_path)
            else:
                self.montage_edit.setText(file_path)

    def confirm(self):
        name = self.name_edit.text()
        if not name:
            MessageBox('Error', 'Please Input Name', self).exec_()
            return

        age = self.age_edit.text()
        if not age.isdigit():
            MessageBox('Error', 'Please Input Valid Age', self).exec_()
            return

        updated_data = {
            'name': name,
            'gender': self.gender_combo.currentText(),
            'age': int(age),
            'eeg_data_path': self.eeg_edit.text() or None,
            'eeg_montage_path': self.montage_edit.text() or None,
            'fnirs_data_path': self.fnirs_edit.text() or None,
            'et_data_path': self.et_edit.text() or None
        }
        self.subjectEdited.emit(updated_data)
        self.accept()

class AddSubjectDialog(Dialog):
    subjectAdded = pyqtSignal(dict)

    def __init__(self, parent=None):
        # super().__init__(
        #     parent=parent
        # )
        super().__init__(
            title="Add Participant",
            content="Please Enter The Participant Information",
            parent=parent
        )
        self.setFixedSize(550, 450)
        self.last_directory = ""
        self.initUI()

    def initUI(self):
        content_widget = QWidget(self)
        layout = QGridLayout(content_widget)
        
        layout.setContentsMargins(20, 40, 40, 40)
        layout.setSpacing(20)

        def create_label(text):
            label = BodyLabel(text)
            label.setFixedWidth(100)  
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  
            return label

        layout.addWidget(create_label("Name:"), 0, 0)
        self.name_edit = LineEdit(self)
        layout.addWidget(self.name_edit, 0, 1, 1, 2)

        layout.addWidget(create_label("Gender:"), 1, 0)
        self.gender_combo = ComboBox(self)
        self.gender_combo.addItems(['Male', 'Female', 'Unknown'])
        layout.addWidget(self.gender_combo, 1, 1, 1, 2)

        layout.addWidget(create_label("Age:"), 2, 0)
        self.age_edit = LineEdit(self)
        layout.addWidget(self.age_edit, 2, 1, 1, 2)

        layout.addWidget(create_label("EEG Data:"), 3, 0)
        self.eeg_edit = LineEdit(self)
        self.eeg_edit.setPlaceholderText('EEG Data File Path (Optional)')
        layout.addWidget(self.eeg_edit, 3, 1)
        self.eeg_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.eeg_button.clicked.connect(lambda: self.browse_file(self.eeg_edit, "EEG Files (*.set *.edf *.bdf *.cnt *.vhdr *.pkl)"))
        layout.addWidget(self.eeg_button, 3, 2)

        layout.addWidget(create_label("Montage File:"), 4, 0)
        self.montage_edit = LineEdit(self)
        self.montage_edit.setPlaceholderText('Montage File Path (Optional)')
        layout.addWidget(self.montage_edit, 4, 1)
        self.montage_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.montage_button.clicked.connect(lambda: self.browse_montage_file())
        layout.addWidget(self.montage_button, 4, 2)

        layout.addWidget(create_label("fNIRS Data:"), 5, 0)
        self.fnirs_edit = LineEdit(self)
        self.fnirs_edit.setPlaceholderText('fNIRS Data File Path (Optional)')
        layout.addWidget(self.fnirs_edit, 5, 1)
        self.fnirs_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.fnirs_button.clicked.connect(lambda: self.browse_file(self.fnirs_edit, "fNIRS Files (*.snirf *.lufr *.pkl)"))
        layout.addWidget(self.fnirs_button, 5, 2)

        layout.addWidget(create_label("ET Data:"), 6, 0)
        self.et_edit = LineEdit(self)
        self.et_edit.setPlaceholderText('ET Data File Path (Optional)')
        layout.addWidget(self.et_edit, 6, 1)
        self.et_button = PushButton('Browse', self, FluentIcon.FOLDER)
        self.et_button.clicked.connect(lambda: self.browse_file(self.et_edit, "Eye Tracking Files (*.pkl *.gz *.csv *.asc *.edf)"))
        layout.addWidget(self.et_button, 6, 2)

        self.vBoxLayout.insertWidget(2, content_widget)

        self.yesButton.setText('Confirm')
        self.cancelButton.setText('Cancel')
        self.yesButton.clicked.connect(self.confirm)

    def browse_file(self, edit, file_filter):
        initial_dir = self.last_directory if self.last_directory else None
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File", initial_dir, file_filter)
        if file_path:
            edit.setText(file_path)
            self.last_directory = os.path.dirname(file_path)

    def browse_montage_file(self):
        try:
            initial_dir = os.path.abspath("./resource/EEGMontage")
            if not os.path.exists(initial_dir):
                initial_dir = None
        except Exception:
            initial_dir = None

        file_path, _ = QFileDialog.getOpenFileName(self, "Choose Montage File", initial_dir, "Montage Files (*.locs)")
        if file_path:
            resource_dir = os.path.abspath("./resource/EEGMontage")
            if os.path.commonpath([resource_dir, file_path]) == resource_dir:
                relative_path = os.path.relpath(file_path, start=os.path.abspath("."))
                self.montage_edit.setText(relative_path)
            else:
                self.montage_edit.setText(file_path)

    def confirm(self):
        name = self.name_edit.text()
        if not name:
            MessageBox('Error', 'Please Input Participant Name', self).exec_()
            return

        age = self.age_edit.text()
        if not age.isdigit():
            MessageBox('Error', 'Please Input Valid Age', self).exec_()
            return

        subject_data = {
            'name': name,
            'gender': self.gender_combo.currentText(),
            'age': int(age),
            'eeg_data_path': self.eeg_edit.text(),
            'eeg_montage_path': self.montage_edit.text(),
            'fnirs_data_path': self.fnirs_edit.text(),
            'et_data_path': self.et_edit.text()
        }
        self.subjectAdded.emit(subject_data)
        self.accept()

class CenteredWidget(QWidget):
    def __init__(self, inner_widget, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(inner_widget, alignment=Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

class ProjectInterface(GalleryInterface):
    projectCreated = pyqtSignal(Project)
    projectLoaded = pyqtSignal(Project)

    def __init__(self, main_window = None, parent=None):
        t = Translator()
        super().__init__(
            title='',
            subtitle='',
            parent=parent
        )
        self.main_window = main_window
        # self.main_window.setStyleSheet("background-color: #5b5b8a;")
        self.setObjectName('ProjectInterface')
        self.project = None
        self.header_font_size = 30
        self.initUI()
        self.setupSubjectTable()

    def initUI(self):
        main_layout = QHBoxLayout(self)
        
        
        self.toolbar = QToolBar(self)
        # self.addToolBar(self.toolbar)

        
        # self.project_menu_btn = PushButton('Data Management', self, FluentIcon.FOLDER)
        self.project_menu_btn = PushButton('Data Management', self)
        # self.project_menu_btn.setStyleSheet("background-color: #b2b2cc;")
        self.toolbar.addWidget(self.project_menu_btn)
        
        self.project_menu = RoundMenu(parent=self)
        self.project_menu.addAction(Action(FluentIcon.ADD, 'Create Project', triggered=self.createProject))
        self.project_menu.addAction(Action(FluentIcon.FOLDER, 'Load Project', triggered=self.loadProject))
        self.project_menu.addSeparator()
        self.project_menu.addAction(Action(FluentIcon.ADD, 'Add Experiment', triggered=self.addExperiment))
        self.project_menu.addAction(Action(FluentIcon.DELETE, 'Delete Experiment', triggered=self.deleteExperiment))
        self.project_menu.addSeparator()
        self.project_menu.addAction(Action(FluentIcon.ADD, 'Add Participant', triggered=self.addSubject))
        self.project_menu_btn.clicked.connect(lambda: self.project_menu.exec_(self.project_menu_btn.mapToGlobal(
            self.project_menu_btn.rect().bottomLeft()
        )))
        

        # Left column
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.addWidget(self.toolbar)
        # Top buttons
        # top_buttons_layout = QHBoxLayout()
        # self.create_project_btn = PushButton('Create', self, FluentIcon.ADD)
        # self.load_project_btn = PushButton('Load', self, FluentIcon.FOLDER)
        # top_buttons_layout.addWidget(self.create_project_btn)
        # top_buttons_layout.addWidget(self.load_project_btn)
        # left_layout.addLayout(top_buttons_layout)
        # self.add_experiment_btn = PushButton('Add Exp', self, FluentIcon.ADD)
        # self.delete_experiment_btn = PushButton('Delete Exp', self, FluentIcon.DELETE)
        # # bottom_buttons_layout.addWidget(self.add_experiment_btn)
        # # bottom_buttons_layout.addWidget(self.delete_experiment_btn)
        # top_buttons_layout.addWidget(self.add_experiment_btn)
        # top_buttons_layout.addWidget(self.delete_experiment_btn)
        # # left_layout.addLayout(bottom_buttons_layout)
        # left_layout.addLayout(top_buttons_layout)
        # bottom_buttons_layout = QHBoxLayout()
        # self.add_experiment_btn = PushButton('Add Exp', self, FluentIcon.ADD)
        # self.delete_experiment_btn = PushButton('Delete Exp', self, FluentIcon.DELETE)
        # bottom_buttons_layout.addWidget(self.add_experiment_btn)
        # bottom_buttons_layout.addWidget(self.delete_experiment_btn)
        # # top_buttons_layout.addWidget(self.add_experiment_btn)
        # # top_buttons_layout.addWidget(self.delete_experiment_btn)
        # left_layout.addLayout(bottom_buttons_layout)
        # left_layout.addLayout(top_buttons_layout)
        # Experiment list
        
        experiment_card = CardWidget(self)
        # experiment_card.setStyleSheet("background-color: #8484ae;")
        card_layout = QVBoxLayout(experiment_card)
        self.experiment_list = ListView(self)
        card_layout.addWidget(self.experiment_list)
        left_layout.addWidget(experiment_card)

        # Bottom buttons
        # bottom_buttons_layout = QHBoxLayout()
        # self.add_experiment_btn = PushButton('Add Exp', self, FluentIcon.ADD)
        # self.delete_experiment_btn = PushButton('Delete Exp', self, FluentIcon.DELETE)
        # # bottom_buttons_layout.addWidget(self.add_experiment_btn)
        # # bottom_buttons_layout.addWidget(self.delete_experiment_btn)
        # top_buttons_layout.addWidget(self.add_experiment_btn)
        # top_buttons_layout.addWidget(self.delete_experiment_btn)
        # # left_layout.addLayout(bottom_buttons_layout)
        # left_layout.addLayout(top_buttons_layout)

        main_layout.addWidget(left_column, 1)

        # Right column
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # self.add_subject_btn = PushButton('Add Participant', self, FluentIcon.ADD)
        # right_layout.addWidget(self.add_subject_btn)

        self.subject_table = TableWidget(self)
        # self.subject_table.setStyleSheet("background-color: #b2b2cc;")
        right_layout.addWidget(self.subject_table)
        # self.add_subject_btn = PushButton('Add Participant', self, FluentIcon.ADD)
        # right_layout.addWidget(self.add_subject_btn)
        main_layout.addWidget(right_column, 9)

        self.setupConnections()

    def editSubject(self, subject):
        dialog = EditSubjectDialog(subject, self)
        dialog.subjectEdited.connect(lambda data: self.handleSubjectEdited(subject['id'], data))
        dialog.exec_()

    def handleSubjectEdited(self, subject_id, updated_data):
        original_subject = self.project.get_subject_data(subject_id)
        data_types = ['eeg', 'fnirs', 'et']
        
        for data_type in data_types:
            original_path = original_subject.get(f'{data_type}_data_path')
            updated_path = updated_data.get(f'{data_type}_data_path')

            if updated_path and not original_path:
                output_path = self.project.create_output_folder(subject_id, data_type)
                updated_data[f'{data_type}_output_path'] = output_path
            elif not updated_path and original_path:
                self.project.remove_output_folder(subject_id, data_type)
                updated_data[f'{data_type}_output_path'] = None
                updated_data[f'{data_type}_preprocessed_path'] = None
            elif updated_path != original_path:
                output_folder = os.path.join(self.project.base_path, original_subject[f'{data_type}_output_path'])
                if os.path.exists(output_folder):
                    for file in os.listdir(output_folder):
                        file_path = os.path.join(output_folder, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                updated_data[f'{data_type}_preprocessed_path'] = None

        self.project.update_subject(subject_id, **updated_data)
        
        self.updateSubjectTable(original_subject['experiment_id'])


    def setupConnections(self):
        # self.create_project_btn.clicked.connect(self.createProject)
        # self.load_project_btn.clicked.connect(self.loadProject)
        # self.add_experiment_btn.clicked.connect(self.addExperiment)
        # self.delete_experiment_btn.clicked.connect(self.deleteExperiment)
        # self.add_subject_btn.clicked.connect(self.addSubject)
        self.experiment_list.clicked.connect(self.onExperimentChanged)

    def setupSubjectTable(self):
        # headers = ["Action", "Name", 
        #            "EEG-raw", "EEG-processed", "EEG-output",
        #            "fNIRS-raw", "fNIRS-processed", "fNIRS-output",
        #            "ET-raw", "ET-processed", "ET-output",
        #            "Questionnaire"]
        headers = ["Action", "Name", 
                   "EEG-raw", "EEG-output",
                   "fNIRS-raw", "fNIRS-output",
                   "ET-raw", "ET-output",
                   "Questionnaire"]
        self.subject_table.setColumnCount(len(headers))
        self.subject_table.setHorizontalHeaderLabels(headers)
        
        # header = self.subject_table.horizontalHeader()
        # font = QFont()
        # font.setPointSize(self.header_font_size)
        # header.setFont(font)

        self.subject_table.setColumnWidth(0, 130)  
        for i in range(1, len(headers)):
            self.subject_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)

    def refresh_interface(self):
        
        if self.project:
            self.updateExperimentList()
            # current_index = self.experiment_list.currentIndex()
            # if current_index.isValid():
            #     experiment_id = current_index.data(Qt.UserRole)
            #     self.updateSubjectTable(experiment_id)
        else:
            self.experiment_list.setModel(QStandardItemModel())
            self.clearSubjectTable()

    def createProject(self):
        dialog = AddProjectDialog(self)
        dialog.projectCreated.connect(self.handleProjectCreated)
        dialog.exec_()

    def handleProjectCreated(self, base_path, project_name):
        try:
            self.project = Project(project_name, base_path)
            self.projectCreated.emit(self.project)
            self.clearSubjectTable()
            self.updateExperimentList()
            # InfoBar.success(
            #             orient=Qt.Horizontal,
            #             isClosable=True,
            #             position=InfoBarPosition.TOP,
            #             duration=2000,
            #             parent=self
            #         )
            InfoBar.success(
                        title='Success',
                        content=f"Project '{project_name}' Is Already Created!",
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
                content=f"Fail To Create Project: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def loadProject(self):
        project_path = QFileDialog.getExistingDirectory(self, "Please Choose A Project Folder", "")
        if project_path:
            project_name = os.path.basename(project_path)
            db_file_path = os.path.join(project_path, f"{project_name}.db")
            
            if os.path.isfile(db_file_path):
                try:
                    base_path = os.path.dirname(project_path)
                    self.project = Project(project_name, base_path)
                    
                    # Update the base_path of the project
                    self.project.base_path = base_path
                    
                    self.projectLoaded.emit(self.project)
                    self.clearSubjectTable()  
                    self.updateExperimentList()
                    # InfoBar.success(
                    #     orient=Qt.Horizontal,
                    #     isClosable=True,
                    #     position=InfoBarPosition.TOP,
                    #     duration=2000,
                    #     parent=self
                    # )
                    InfoBar.success(
                        title='Success',
                        content=f"Project '{project_name}' Is Already Loaded",
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
                        content=f"Fail To Load The Project: {str(e)}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
            else:
                # InfoBar.warning(
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=3000,
                #     parent=self
                # )
                InfoBar.warning(
                    title='Warning',
                    content=f"The Selected Folder Is Not A Valid Project Folder. Please Ensure It Contains A '{project_name}.db' File.",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )


    def addExperiment(self):
        if self.project:
            dialog = AddExperimentDialog(self)
            dialog.experimentAdded.connect(self.handleExperimentAdded)
            dialog.exec_()

    def handleExperimentAdded(self, experiment_name):
        experiment_id = self.project.add_experiment(experiment_name)
        if experiment_id is not None:
            self.updateExperimentList()
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content=f"Experiment '{experiment_name}' Added",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content="Fail to Add Experiment",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def deleteExperiment(self):
        current_index = self.experiment_list.currentIndex()
        if current_index.isValid() and self.project:
            experiment_id = current_index.data(Qt.UserRole)
            experiment_name = current_index.data(Qt.DisplayRole)
            
            # msgBox = MessageBox(
            #     self
            # )
            msgBox = MessageBox(
                "Confirm Deletion",
                f"Are you sure you want to delete experiment '{experiment_name}'? This action cannot be undone.",
                self
            )
            msgBox.yesButton.setText("Confirm")
            msgBox.cancelButton.setText("Cancel")
            
            if msgBox.exec_():
                if self.project.delete_experiment(experiment_id):
                    self.clearSubjectTable()
                    self.updateExperimentList()
                    # InfoBar.success(
                    #     orient=Qt.Horizontal,
                    #     isClosable=True,
                    #     position=InfoBarPosition.TOP,
                    #     duration=2000,
                    #     parent=self
                    # )
                    InfoBar.success(
                        title='Success',
                        content=f"Experiment '{experiment_name}' and its data were removed",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    # InfoBar.error(
                    #     orient=Qt.Horizontal,
                    #     isClosable=True,
                    #     position=InfoBarPosition.TOP,
                    #     duration=2000,
                    #     parent=self
                    # )
                    self.showWarningMessage("Error", "Fail To Delete Experiment")
                    InfoBar.error(
                        title='Error',
                        content="Fail to delete experiment",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )

    def addSubject(self):
        current_index = self.experiment_list.currentIndex()
        if current_index.isValid() and self.project:
            experiment_id = current_index.data(Qt.UserRole)
            dialog = AddSubjectDialog(self)
            dialog.subjectAdded.connect(lambda data: self.handleSubjectAdded(experiment_id, data))
            dialog.exec_()

    def handleSubjectAdded(self, experiment_id, data):
        existing_subjects = self.project.get_subjects(experiment_id)
        same_name_subjects = [s for s in existing_subjects if s['name'].startswith(data['name'])]
        
        if same_name_subjects:
            base_name = data['name']
            counter = 1
            while any(s['name'] == f"{base_name}_{counter}" for s in same_name_subjects):
                counter += 1
            data['name'] = f"{base_name}_{counter}"
            
            # msg_box = MessageBox(
                # self
            # )
            msg_box = MessageBox(
                'Warning!',
                f"'{base_name}' Already Exists. New Participant Will Be Named '{data['name']}'. Could You Continue?",
                self
            )
            msg_box.yesButton.setText('Yes')
            msg_box.cancelButton.setText('No')
            if not msg_box.exec_():
                return

        subject_id = self.project.add_subject(
            experiment_id,
            data['name'],
            data['gender'],
            data['age'],
            fnirs_data_path=data['fnirs_data_path'],
            eeg_data_path=data['eeg_data_path'],
            eeg_montage_path=data['eeg_montage_path'],
            et_data_path=data['et_data_path']
        )
        if subject_id is not None:
            self.updateSubjectTable(experiment_id)
            # InfoBar.success(
            #             orient=Qt.Horizontal,
            #             isClosable=True,
            #             position=InfoBarPosition.TOP,
            #             duration=2000,
            #             parent=self
            #         )
            InfoBar.success(
                        title='Success',
                        content=f"Participant '{data['name']}' Added",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
        else:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error!',
                content="Fail To Add Participant.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def onExperimentChanged(self, index):
        if index.isValid():
            experiment_id = index.data(Qt.UserRole)
            self.updateSubjectTable(experiment_id)
        else:
            self.subject_table.setRowCount(0)

    def updateExperimentList(self):
        model = QStandardItemModel()
        if self.project:
            experiments = self.project.get_experiments()
            for exp in experiments:
                item = QStandardItem(exp['name'])
                item.setData(exp['id'], Qt.UserRole)
                model.appendRow(item)
        self.experiment_list.setModel(model)

        if model.rowCount() > 0 and not self.experiment_list.currentIndex().isValid():
            self.experiment_list.setCurrentIndex(model.index(0, 0))
            self.onExperimentChanged(model.index(0, 0))

    def clearSubjectTable(self):
        self.subject_table.setRowCount(0)

    def updateSubjectTable(self, experiment_id):
        self.subject_table.setRowCount(0)
        if self.project:
            subjects = self.project.get_subjects(experiment_id)
            for subject in subjects:
                row_position = self.subject_table.rowCount()
                self.subject_table.insertRow(row_position)
                
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                view_btn = ToolButton(FluentIcon.VIEW, self)
                delete_btn = ToolButton(FluentIcon.DELETE, self)
                edit_btn = ToolButton(FluentIcon.EDIT, self)
                edit_btn.setFixedSize(30, 30)
                view_btn.setFixedSize(30, 30)
                delete_btn.setFixedSize(30, 30)
                action_layout.addWidget(view_btn)
                action_layout.addWidget(delete_btn)
                action_layout.addWidget(edit_btn)
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setSpacing(5)
                action_layout.setAlignment(Qt.AlignCenter)
                action_widget.setLayout(action_layout)
                self.project_menu_btn = PushButton('Data Management', self, FluentIcon.FOLDER)
                self.toolbar.addWidget(self.project_menu_btn)
                
                
                self.subject_table.setCellWidget(row_position, 0, action_widget)
                
                
                name_item = QTableWidgetItem(subject['name'])
                name_item.setTextAlignment(Qt.AlignCenter)
                self.subject_table.setItem(row_position, 1, name_item)

                data_types = ['eeg', 'fnirs', 'et']
                for i, data_type in enumerate(data_types):
                    self.setCellContent(row_position, 2 + i*2, subject.get(f'{data_type}_data_path'), 'raw')
                    # self.setCellContent(row_position, 3 + i*3, subject.get(f'{data_type}_preprocessed_path'), 'preprocessed')
                    self.setCellContent(row_position, 3 + i*2, subject.get(f'{data_type}_output_path'), 'output')

                self.setCellContent(row_position, 8, subject.get('qu_output_path'), 'output')

                view_btn.clicked.connect(lambda _, s=subject: self.viewSubjectData(s))
                delete_btn.clicked.connect(lambda _, s=subject: self.deleteSubject(s))
                edit_btn.clicked.connect(lambda _, s=subject: self.editSubject(s))

            for row in range(self.subject_table.rowCount()):
                self.subject_table.setRowHeight(row, 40)  

    def setCellContent(self, row, column, path, data_type):
        if path:
            if data_type in ['raw', 'preprocessed']:
                checkbox = CheckBox(self)
                checkbox.setChecked(data_type == 'raw')  
                checkbox.setStyleSheet("QCheckBox::indicator { width: 16px; height: 16px; }")  
                centered_widget = CenteredWidget(checkbox)
                self.subject_table.setCellWidget(row, column, centered_widget)
                
                if data_type == 'raw':
                    preprocessed_widget = self.subject_table.cellWidget(row, column + 1)
                    if isinstance(preprocessed_widget, CenteredWidget):
                        preprocessed_checkbox = preprocessed_widget.findChild(CheckBox)
                        if preprocessed_checkbox:
                            self.set_exclusive_checkboxes(checkbox, preprocessed_checkbox)
                elif data_type == 'preprocessed':
                    raw_widget = self.subject_table.cellWidget(row, column - 1)
                    if isinstance(raw_widget, CenteredWidget):
                        raw_checkbox = raw_widget.findChild(CheckBox)
                        if raw_checkbox:
                            self.set_exclusive_checkboxes(raw_checkbox, checkbox)
            else:  # output
                output_btn = PushButton("View", self)
                output_btn.clicked.connect(lambda _, p=path: self.openOutputFolder(p))
                centered_widget = CenteredWidget(output_btn)
                self.subject_table.setCellWidget(row, column, centered_widget)
        else:
            item = QTableWidgetItem('/')
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(Qt.ItemIsEnabled)
            self.subject_table.setItem(row, column, item)

    def set_exclusive_checkboxes(self, checkbox1, checkbox2):
        def update_checkboxes(state):
            if state == Qt.Checked:
                if checkbox1.isChecked() and checkbox2.isChecked():
                    sender = self.sender()
                    if sender == checkbox1:
                        checkbox2.setChecked(False)
                    else:
                        checkbox1.setChecked(False)

        checkbox1.stateChanged.connect(update_checkboxes)
        checkbox2.stateChanged.connect(update_checkboxes)

    def openOutputFolder(self, path):
        full_path = os.path.join(self.project.base_path, path)
        if os.path.exists(full_path):
            os.startfile(full_path)
        else:
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content= f"Folder is not existed: {full_path}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def get_questionnaire_template_path(self, experiment_id):
        experiment = next((exp for exp in self.project.get_experiments() if exp['id'] == experiment_id), None)
        if experiment:
            return os.path.join(self.project.base_path, self.project.project_name, experiment['name'], "Template.json")
        return None
    # @PerformanceMonitor
    def viewSubjectData(self, subject):
        try:
            self.selected_paths = self.getSelectedDataPaths(subject)
            if not self.selected_paths:
                # InfoBar.error(
                #     orient=Qt.AlignHorizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.error(
                    title='Error',
                    content="No files selected",
                    orient=Qt.AlignHorizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            self.loading_overlay = LoadingOverlay(self)
            self.loading_overlay.resize(self.size())
            self.loading_overlay.show()
            self.loading_overlay.raise_()

            self.db_info = {
                'project': self.project,
                'subject': subject,
                'subject_id': subject['id'],
                'experiment_id': subject['experiment_id']
            }

            self.loading_thread = DataLoadingThread(self.main_window, subject, self.selected_paths, self.db_info)
            self.loading_thread.finished.connect(self.onDataLoaded)
            self.loading_thread.error.connect(self.onLoadError)
            self.loading_thread.finished.connect(self.cleanupLoadingUI)
            self.loading_thread.error.connect(self.cleanupLoadingUI)
            self.loading_thread.start()

            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.setEnabled(False)

        except Exception as e:
            self.cleanupLoadingUI()
            # InfoBar.error(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.error(
                title='Error',
                content=f"Fail to load data: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def onLoadError(self, error_message):
        if hasattr(self, 'loading_thread'):
            self.loading_thread.stop()
            
        # InfoBar.error(
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=2000,
        #     parent=self
        # )
        InfoBar.error(
            title='Error',
            content=f"Fail to load data: {error_message}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def cleanupLoadingUI(self):
        if hasattr(self, 'loading_thread'):
            self.loading_thread.stop()
            self.loading_thread.wait()
            self.loading_thread.deleteLater()
            del self.loading_thread

        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.deleteLater()
            del self.loading_overlay

        QApplication.restoreOverrideCursor()
        self.setEnabled(True)

    def onDataLoaded(self, loaded_data):
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.deleteLater()
            del self.loading_overlay

        QApplication.restoreOverrideCursor()
        self.setEnabled(True)

        if 'eeg' in loaded_data:
            if loaded_data['eeg']=='no':
                self.main_window.load_no_eeg_interface()
            else:
                self.main_window.show_eeg_interface(data_file_path=self.selected_paths['eeg'], eeg_data=loaded_data['eeg'], db_info=self.db_info)
        if 'fnirs' in loaded_data:
            if loaded_data['fnirs']=='no':
                self.main_window.load_no_fnirs_interface()
            else:
                self.main_window.show_fnirs_interface(data_file_path=self.selected_paths['fnirs'], fnirs_data=loaded_data['fnirs'], db_info=self.db_info)
        if 'et' in loaded_data:
            if loaded_data['et']=='no':
                self.main_window.load_no_et_interface()
            else:
                self.main_window.show_et_interface(data_file_path=self.selected_paths['et'], et_data=loaded_data['et'], db_info=self.db_info)
        if 'qu' in loaded_data:
            experiment = self.project.get_experiment_by_id(self.db_info['experiment_id'])
            experiment_name = experiment['name'] if experiment else "Unknown Experiment"

            self.main_window.load_qu_interface(
                template_path=self.get_questionnaire_template_path(self.db_info['experiment_id']),
                questionnaire_file_path=os.path.join(self.project.base_path, self.selected_paths['qu']),
                output_path=os.path.join(self.project.base_path, self.db_info['subject']['qu_output_path']),
                experiment=experiment_name,
                name=self.db_info['subject']['name'],
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.resize(self.size())

    def getSelectedDataPaths(self, subject):
        selected_paths = {}
        for row in range(self.subject_table.rowCount()):
            name_item = self.subject_table.item(row, 1)
            if name_item and name_item.text() == subject['name']:
                data_types = ['eeg', 'fnirs', 'et']
                for i, data_type in enumerate(data_types):
                    raw_widget = self.subject_table.cellWidget(row, 2 + i*2)
                    # preprocessed_widget = self.subject_table.cellWidget(row, 3 + i*3)
                    
                    if isinstance(raw_widget, CenteredWidget):
                        raw_checkbox = raw_widget.findChild(CheckBox)
                        if raw_checkbox and raw_checkbox.isChecked():
                            selected_paths[data_type] = subject.get(f'{data_type}_data_path')
                    
                    # if isinstance(preprocessed_widget, CenteredWidget):
                    #     preprocessed_checkbox = preprocessed_widget.findChild(CheckBox)
                    #     if preprocessed_checkbox and preprocessed_checkbox.isChecked():
                    #         selected_paths[data_type] = subject.get(f'{data_type}_preprocessed_path')
                
                qu_widget = self.subject_table.cellWidget(row, 8)
                if isinstance(qu_widget, CenteredWidget):
                    qu_button = qu_widget.findChild(PushButton)
                    if qu_button:
                        selected_paths['qu'] = subject.get('qu_data_path')
                
                break
        return selected_paths

    def deleteSubject(self, subject):
        # msgBox = MessageBox(
        #     self
        # )
        msgBox = MessageBox(
            "Confirm Deletion",
            f"Are you sure you want to delete the record for participant '{subject['name']}'?  \n Note: This will only remove database records – actual files remain stored.",
            self
        )
        msgBox.yesButton.setText("Confirm")
        msgBox.cancelButton.setText("Cancel")
        
        if msgBox.exec_():
            try:
                if self.project.delete_subject(subject['id']):
                    self.updateSubjectTable(subject['experiment_id'])
                    # InfoBar.success(
                    #     orient=Qt.Horizontal,
                    #     isClosable=True,
                    #     position=InfoBarPosition.TOP,
                    #     duration=2000,
                    #     parent=self
                    # )
                    InfoBar.success(
                        title='Success',
                        content=f"The record for participant '{subject['name']}' has been successfully deleted.",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    # InfoBar.error(
                    #     orient=Qt.Horizontal,
                    #     isClosable=True,
                    #     position=InfoBarPosition.TOP,
                    #     duration=2000,
                    #     parent=self
                    # )
                    InfoBar.error(
                        title='Error',
                        content= "Fail to delete participant record.",
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
                    content= f"Question:{str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def showInfoMessage(self, title, content):
        msgBox = MessageBox(title, content, self)
        msgBox.yesButton.setText("Confirm")
        msgBox.cancelButton.hide()
        msgBox.exec_()

    def showWarningMessage(self, title, content):
        msgBox = MessageBox(title, content, self)
        msgBox.yesButton.setText("Confirm")
        msgBox.cancelButton.hide()
        msgBox.exec_()

    def closeEvent(self, event):
        if self.project:
            pass
        super().closeEvent(event)


if __name__ == "__main__":
    pass