# from PyQt5.QtCore import QUrl, QSize, Qt
# from PyQt5.QtGui import QIcon, QDesktopServices
# from PyQt5.QtWidgets import QApplication, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

# from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
#                             SplashScreen)
# from qfluentwidgets import setTheme, Theme
# from qfluentwidgets import FluentIcon as FIF

# import siui
# from siui.core import SiColor, SiGlobal
# from siui.templates.application.application import SiliconApplication


# from .gallery_interface import GalleryInterface
# from .fnirs_interface import FNIRSInterface
# from .eeg_interface import EEGInterface
# from .et_interface import ETInterface
# from .qu_interface import QUInterface
# from .project_interface import ProjectInterface
# from .setting_interface import SettingInterface
# from .viewer_interface import ViewerInterface
# from ..common.config import ZH_SUPPORT_URL, EN_SUPPORT_URL, cfg
# from ..common.icon import Icon
# from ..common.signal_bus import signalBus
# from ..common.translator import Translator
# from ..common import resource

# from ..data.eeg_data import EEGData
# from ..data.fnirs_data import FNIRSData
# from ..data.et_data import ETData

# import sys
# import os
# from qt_material import apply_stylesheet


# class MainWindow(FluentWindow):
#     """
#     """
#     def modify_navigation_layout(self):
#         """
#         """
#         nav_layout = self.navigationInterface.layout()
#         if nav_layout:
#             new_layout = QHBoxLayout()

#             for i in range(nav_layout.count()):
#                 item = nav_layout.takeAt(0)
#                 new_layout.addItem(item)

#             self.navigationInterface.setLayout(new_layout)

#             style = """
#             QWidget#NavigationInterface {
#                 background-color: transparent;
#             }
#             QToolButton {
#                 padding: 8px 16px;
#             }
#             """
#             self.navigationInterface.setStyleSheet(style)
#     def __init__(self):
#         super().__init__()
#         self.initWindow()
        
#         if getattr(sys, 'frozen', False):
#             self.application_path = os.path.dirname(sys.executable)
#         else:
#             self.application_path = os.path.dirname(os.path.abspath(__file__))
#         apply_stylesheet(self, theme='light_orange.xml')

#         # enable acrylic effect
#         self.navigationInterface.setAcrylicEnabled(True)
#         self.modify_navigation_layout()
#         # self.navigationInterface.setExpandWidth(1)
#         self.connectSignalToSlot()

#         # add items to navigation interface
#         self.t = Translator()
#         self.navigationInterface.addSeparator()

#         self.pos = NavigationItemPosition.SCROLL

#         # Initialize placeholders
#         self.fnirs_placeholder = None
#         self.eeg_placeholder = None
#         self.et_placeholder = None
#         self.qu_placeholder = None
#         self.viewer_placeholder = None

#         self.eeg_interface = None
#         self.fnirs_interface = None
#         self.et_interface = None
#         self.splashScreen.finish()

#         self.project_interface = ProjectInterface(main_window=self, parent=self)
#         self.addSubInterface(self.project_interface, FIF.FOLDER, self.t.project, self.pos)
#         # def addSubInterface(
#         #     self,
#         # ) -> NavigationTreeWidget
#         # self.navigationInterface.addItem(
#         #     routeKey='help',
#         #     icon=FIF.QUESTION,
#         #     text=self.t.help,
#         #     onClick=self.onSupport,
#         #     selectable=False,
#         #     tooltip=self.t.help,
#         #     position=NavigationItemPosition.BOTTOM
#         # )
#         # self.settingInterface = SettingInterface(self)
#         # self.addSubInterface(
#         #     self.settingInterface, FIF.SETTING, self.t.settings, NavigationItemPosition.BOTTOM)


#     def switchTo(self, interface):
#         """
        
#         interface : QWidget
            
#         """
#         super().switchTo(interface)
        
#         if isinstance(interface, ProjectInterface):
#             interface.refresh_interface()

#     def initWindow(self):
#         """
        
#         """
#         self.resize(1280, 720)
#         self.setMinimumWidth(720)
#         # self.setWindowIcon(QIcon(':/gallery/images/test1.png'))
#         self.setWindowTitle('Specialized Software for Integrated Visualization and Data Processing of Multimodal Physiological Signals')


#         self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

#         # create splash screen
#         self.splashScreen = SplashScreen(self.windowIcon(), self)
#         self.splashScreen.setIconSize(QSize(106, 106))
#         self.splashScreen.raise_()

#         desktop = QApplication.desktop().availableGeometry()
#         w, h = desktop.width(), desktop.height()
#         self.move(w//2 - self.width()//2, h//2 - self.height()//2)
#         self.show()
#         QApplication.processEvents()
    
#     def onSupport(self):
#         """
        
        
#         """
#         try:
#             # Get the manual path based on the application path
#             if getattr(sys, 'frozen', False):
#                 # If running as exe
#             else:
#                 # If running as Python script
#                 # Go up two levels from current file to reach project root
#                 project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
#             # Convert to absolute path
#             manual_path = os.path.abspath(manual_path)

#             # Check if file exists
#             if os.path.exists(manual_path):
#                 # Convert to URL format and open
#                 url = QUrl.fromLocalFile(manual_path)
#                 QDesktopServices.openUrl(url)
#             else:
#                 raise ValueError(
#                 )
#         except Exception as e:
#             raise ValueError(
#             )

#     def get_fnirs_subject_data(self, data_file_path, db_info):
#         """
        
#         data_file_path : str
#         db_info : dict
            
        
#         """
#         if not db_info:
#             raise ValueError("db_info is not provided")

#         project = db_info['project']
#         subject_id = db_info['subject_id']
#         subject_data = project.get_subject_data(subject_id)
        
#         if subject_data:
#             experiment = project.get_experiment_by_id(subject_data['experiment_id'])
#             if experiment:
#                 subject_data['experiment_name'] = experiment['name']
#             else:
#                 subject_data['experiment_name'] = "Unknown Experiment"
            
#             subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['fnirs_output_path'])
            
#             if subject_data.get('fnirs_data_path'):
#                 subject_data['fnirs_data_path'] = os.path.join(project.base_path, subject_data['fnirs_data_path'])
#             else:
#                 subject_data['fnirs_data_path'] = None

#             if data_file_path:
#                 subject_data['path'] = os.path.join(project.base_path, data_file_path)
#         else:
#             raise ValueError("Unable to retrieve subject data from database")
        
#         return subject_data
    
#     def load_fnirs_data(self, data_file_path, db_info=None):
#         """
        
#         data_file_path : str
            
#         """
#         print("Try To Load fnirs"+data_file_path)
#         subject_data = self.get_fnirs_subject_data(db_info=db_info, data_file_path=data_file_path)

#         output_path = subject_data['full_output_path']
#         data_file_path = subject_data['path']
#         age = subject_data['age']
#         return FNIRSData(filename=data_file_path, age = age, output_path=output_path, db_info=db_info)
    
#     def show_fnirs_interface(self, data_file_path, fnirs_data, db_info):
#         """
        
#         data_file_path : str
#         fnirs_data : FNIRSData
#         db_info : dict
#         """
#         if self.fnirs_placeholder is None:
#             self.fnirs_placeholder = QWidget()
#             self.fnirs_placeholder.setObjectName("FNIRSInterface")
#             self.addSubInterface(self.fnirs_placeholder, FIF.IOT, self.t.fnirs, self.pos)

#         self.fnirs_interface = FNIRSInterface(parent=self, data_file_path=data_file_path, db_info=db_info, fnirs_data=fnirs_data)
#         self.update_interface(self.fnirs_placeholder, self.fnirs_interface)
    
#     def get_eeg_subject_data(self, data_file_path, db_info):
#         """
        
#         data_file_path : str
#         db_info : dict
            
        
#         """
#         if not db_info:
#             raise ValueError("db_info is not provided")

#         project = db_info['project']
#         subject_id = db_info['subject_id']
#         subject_data = project.get_subject_data(subject_id)
        
#         if subject_data:
#             experiment = project.get_experiment_by_id(subject_data['experiment_id'])
#             if experiment:
#                 subject_data['experiment_name'] = experiment['name']
#             else:
#                 subject_data['experiment_name'] = "Unknown Experiment"
            
#             subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['eeg_output_path'])
            
#             if subject_data.get('eeg_montage_path'):
#                 subject_data['eeg_montage_path'] = os.path.join(project.base_path, subject_data['eeg_montage_path'])
#             else:
#                 subject_data['eeg_montage_path'] = None
            
#             if subject_data.get('eeg_data_path'):
#                 subject_data['eeg_data_path'] = os.path.join(project.base_path, subject_data['eeg_data_path'])
#             else:
#                 subject_data['eeg_data_path'] = None

#             if data_file_path:
#                 subject_data['path'] = os.path.join(project.base_path, data_file_path)
#         else:
#             raise ValueError("Unable to retrieve subject data from database")
        
#         return subject_data
    
#     def load_eeg_data(self, data_file_path, db_info=None):
#         """
        
#         data_file_path : str
            
#         """
#         print("Try To Load eeg"+data_file_path)
#         subject_data = self.get_eeg_subject_data(db_info=db_info,data_file_path=data_file_path)

#         output_path = subject_data['full_output_path']
#         montage_file_path = subject_data.get('eeg_montage_path')
#         data_file_path=subject_data['path']
#         return EEGData(filename=data_file_path, custom_montage=montage_file_path, output_path=output_path, db_info = db_info)
    
#     def show_eeg_interface(self, data_file_path, eeg_data, db_info):
#         """
        
#         data_file_path : str
#         eeg_data : EEGData
#         db_info : dict
#         """
#         if self.eeg_placeholder is None:
#             self.eeg_placeholder = QWidget()
#             self.eeg_placeholder.setObjectName("EEGInterface")
#             self.addSubInterface(self.eeg_placeholder, FIF.ASTERISK, self.t.eeg, self.pos)

#         self.eeg_interface = EEGInterface(parent=self, data_file_path=data_file_path, db_info=db_info, eeg_data=eeg_data)
#         self.update_interface(self.eeg_placeholder, self.eeg_interface)

#     def get_et_subject_data(self, data_file_path, db_info):
#         """
        
#         data_file_path : str
#         db_info : dict
            
        
#         """
#         if not db_info:
#             raise ValueError("db_info is not provided")

#         project = db_info['project']
#         subject_id = db_info['subject_id']
#         subject_data = project.get_subject_data(subject_id)
        
#         if subject_data:
#             experiment = project.get_experiment_by_id(subject_data['experiment_id'])
#             if experiment:
#                 subject_data['experiment_name'] = experiment['name']
#             else:
#                 subject_data['experiment_name'] = "Unknown Experiment"
            
#             subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['et_output_path'])
            
#             if subject_data.get('et_data_path'):
#                 subject_data['et_data_path'] = os.path.join(project.base_path, subject_data['et_data_path'])
#             else:
#                 subject_data['et_data_path'] = None

#             if data_file_path:
#                 subject_data['path'] = os.path.join(project.base_path, data_file_path)
#         else:
#             raise ValueError("Unable to retrieve subject data from database")
        
#         return subject_data
    
#     def load_et_data(self, data_file_path, db_info=None):
#         """
        
#         data_file_path : str
            
#         """
#         subject_data = self.get_et_subject_data(db_info=db_info, data_file_path=data_file_path)

#         output_path = subject_data['full_output_path']
#         data_file_path = subject_data['path']
#         return ETData(file_path=data_file_path, output_path=output_path, db_info=db_info)
    
#     def show_et_interface(self, data_file_path, et_data, db_info):
#         """
        
#         data_file_path : str
#         et_data : ETData
#         db_info : dict
#         """
#         if self.et_placeholder is None:
#             self.et_placeholder = QWidget()
#             self.et_placeholder.setObjectName("ETInterface")
#             self.addSubInterface(self.et_placeholder, FIF.VIEW, self.t.et, self.pos)

#         self.et_interface = ETInterface(parent=self, data_file_path=data_file_path, db_info=db_info, et_data=et_data)
#         self.update_interface(self.et_placeholder, self.et_interface)

#     def load_qu_interface(self, template_path: str, questionnaire_file_path: str, output_path: str, experiment: str, name: str):
#         """
        
#         template_path : str
#         questionnaire_file_path : str
#         output_path : str
#         experiment : str
#         name : str
#         """
#         if self.qu_placeholder is None:
#             self.qu_placeholder = QWidget()
#             self.qu_placeholder.setObjectName("QUInterface")
#             self.addSubInterface(self.qu_placeholder, FIF.LABEL, self.t.qu, self.pos)

        
#         new_interface = QUInterface(parent=self, template_path=template_path, questionnaire_file_path=questionnaire_file_path, output_path=output_path, experiment=experiment, name=name)
#         self.update_interface(self.qu_placeholder, new_interface)
        
#         # Check if at least one of eeg_interface, fnirs_interface, or et_interface is not None
#         if any([self.eeg_interface, self.fnirs_interface, self.et_interface]):
#             # Load ViewerInterface
#             self.load_viewer_interface(experiment, name)
#         else:
#             self.load_no_viewer_interface()

#     def load_no_eeg_interface(self):
#         self.eeg_interface = None
#         if self.eeg_placeholder is None:
#             self.eeg_placeholder = QWidget()
#             self.eeg_placeholder.setObjectName("EEGInterface")
#             self.addSubInterface(self.eeg_placeholder, FIF.ASTERISK, self.t.eeg, self.pos)
#         no_interface = GalleryInterface(title="Participant Don't Have This Data.", subtitle="Please Add In The Data Management.")
#         self.update_interface(self.eeg_placeholder, no_interface)

#     def load_no_fnirs_interface(self):
#         self.fnirs_interface = None
#         if self.fnirs_placeholder is None:
#             self.fnirs_placeholder = QWidget()
#             self.fnirs_placeholder.setObjectName("FNIRSInterface")
#             self.addSubInterface(self.fnirs_placeholder, FIF.IOT, self.t.fnirs, self.pos)
#         no_interface = GalleryInterface(title="Participant Don't Have This Data.", subtitle="Please Add In The Data Management.")
#         self.update_interface(self.fnirs_placeholder, no_interface)

#     def load_no_et_interface(self):
#         self.et_interface = None
#         if self.et_placeholder is None:
#             self.et_placeholder = QWidget()
#             self.et_placeholder.setObjectName("ETInterface")
#             self.addSubInterface(self.et_placeholder, FIF.VIEW, self.t.et, self.pos)
#         no_interface = GalleryInterface(title="Participant Don't Have This Data.", subtitle="Please Add In The Data Management.")
#         self.update_interface(self.et_placeholder, no_interface)

#     def load_viewer_interface(self, experiment, name):
#         if self.viewer_placeholder is None:
#             self.viewer_placeholder = QWidget()
#             self.viewer_placeholder.setObjectName("ViewerInterface")
#             self.addSubInterface(self.viewer_placeholder, FIF.PENCIL_INK, self.t.viewer, self.pos)

#         self.viewer_interface = ViewerInterface(parent=self, experiment=experiment, name=name)
#         self.update_interface(self.viewer_placeholder, self.viewer_interface)

#     def load_no_viewer_interface(self):
#         if self.viewer_placeholder is None:
#             self.viewer_placeholder = QWidget()
#             self.viewer_placeholder.setObjectName("ViewerInterface")
#             self.addSubInterface(self.viewer_placeholder, FIF.PENCIL_INK, self.t.viewer, self.pos)

#         no_interface = GalleryInterface(title="Participant Don't Have Visualization Data.", subtitle="Please Add In Data Management.")
#         self.update_interface(self.viewer_placeholder, no_interface)
        
#     def update_interface(self, placeholder, new_interface):
#         """
        
#         placeholder : QWidget
#         new_interface : QWidget
            
#         """
#         if placeholder.layout():
#             while placeholder.layout().count():
#                 item = placeholder.layout().takeAt(0)
#                 widget = item.widget()
#                 if widget:
#                     widget.deleteLater()
#             # Remove the old layout
#             QWidget().setLayout(placeholder.layout())

#         # Create a new layout for the placeholder
#         layout = QVBoxLayout(placeholder)
#         # Add the new interface to the layout
#         layout.addWidget(new_interface)
#         # Set the new layout to the placeholder
#         placeholder.setLayout(layout)

#         # Set the current widget to the placeholder
#         self.stackedWidget.setCurrentWidget(placeholder)

#     def connectSignalToSlot(self):
#         signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
#         signalBus.switchToSampleCard.connect(self.switchToSample)
#         signalBus.supportSignal.connect(self.onSupport)

#     def switchToSample(self, routeKey, index):
#         """ switch to sample """
#         interfaces = self.findChildren(GalleryInterface)
#         for w in interfaces:
#             if w.objectName() == routeKey:
#                 self.stackedWidget.setCurrentWidget(w, False)
#                 w.scrollToCard(index)

#     def resizeEvent(self, e):
#         super().resizeEvent(e)
#         if hasattr(self, 'splashScreen'):
#             self.splashScreen.resize(self.size())


####################################
from PyQt5.QtCore import QUrl, QSize, Qt
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import (QApplication, QPushButton, QHBoxLayout, QVBoxLayout, 
                            QWidget, QToolButton, QSpacerItem, QSizePolicy)

from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen, NavigationTreeWidget)
from qfluentwidgets import setTheme, Theme
from qfluentwidgets import FluentIcon as FIF

import siui
from siui.core import SiColor, SiGlobal
from siui.templates.application.application import SiliconApplication


from .gallery_interface import GalleryInterface
from .fnirs_interface import FNIRSInterface
from .eeg_interface import EEGInterface
from .et_interface import ETInterface
from .qu_interface import QUInterface
from .project_interface import ProjectInterface
from .setting_interface import SettingInterface
from .viewer_interface import ViewerInterface
from ..common.config import ZH_SUPPORT_URL, EN_SUPPORT_URL, cfg
from ..common.icon import Icon
from ..common.signal_bus import signalBus
from ..common.translator import Translator
from ..common import resource

from ..data.eeg_data import EEGData
from ..data.fnirs_data import FNIRSData
from ..data.et_data import ETData

import sys
import os
from qt_material import apply_stylesheet


class MainWindow(FluentWindow):
    
    from PyQt5.QtCore import QUrl, QSize, Qt
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import (QApplication, QPushButton, QHBoxLayout, QVBoxLayout, 
                            QWidget, QToolButton, QSpacerItem, QSizePolicy)

from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen)
from qfluentwidgets import setTheme, Theme
from qfluentwidgets import FluentIcon as FIF

import siui
from siui.core import SiColor, SiGlobal
from siui.templates.application.application import SiliconApplication

from .gallery_interface import GalleryInterface
from .fnirs_interface import FNIRSInterface
from .eeg_interface import EEGInterface
from .et_interface import ETInterface
from .qu_interface import QUInterface
from .project_interface import ProjectInterface
from .setting_interface import SettingInterface
from .viewer_interface import ViewerInterface
from ..common.config import ZH_SUPPORT_URL, EN_SUPPORT_URL, cfg
from ..common.icon import Icon
from ..common.signal_bus import signalBus
from ..common.translator import Translator
from ..common import resource

from ..data.eeg_data import EEGData
from ..data.fnirs_data import FNIRSData
from ..data.et_data import ETData

import sys
import os
from qt_material import apply_stylesheet


class MainWindow(FluentWindow):
    
    def __init__(self):
        super().__init__()
        self.initWindow()
        
        if getattr(sys, 'frozen', False):
            self.application_path = os.path.dirname(sys.executable)
        else:
            self.application_path = os.path.dirname(os.path.abspath(__file__))
        
        apply_stylesheet(self, theme='light_orange.xml')

        self.initHorizontalNavigation()  
        self.connectSignalToSlot()

        self.t = Translator()
        self.pos = NavigationItemPosition.SCROLL

        self.fnirs_placeholder = None
        self.eeg_placeholder = None
        self.et_placeholder = None
        self.qu_placeholder = None
        self.viewer_placeholder = None

        self.eeg_interface = None
        self.fnirs_interface = None
        self.et_interface = None
        self.splashScreen.finish()

        self.project_interface = ProjectInterface(main_window=self, parent=self)
        self.addSubInterface(self.project_interface, FIF.FOLDER, self.t.project, self.pos)

    def initHorizontalNavigation(self):
        
        self.navigationInterface.setVisible(False)

        self.horizontalNavContainer = QWidget()
        self.horizontalNavContainer.setObjectName("HorizontalNavigation")
        self.horizontalNavContainer.setStyleSheet("""
            #HorizontalNavigation {
                background-color: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
                padding: 5px 10px;
            }
        """)
        
        self.horizontalNavLayout = QVBoxLayout(self.horizontalNavContainer)
        self.horizontalNavLayout.setContentsMargins(20, 5, 20, 5)
        self.horizontalNavLayout.setSpacing(15)
        
        self.horizontalNavLayout.addItem(QSpacerItem(
            20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum
        ))

        main_layout = self.layout()
        if main_layout:
            main_layout.insertWidget(0, self.horizontalNavContainer)

        self.interfaceToBtnMap = {}

    def addSubInterface(self, interface, icon, text, position=NavigationItemPosition.TOP, parent=None):
        
        navItem = super().addSubInterface(interface, icon, text, position, parent)

        btn = QToolButton()
        btn.setIcon(icon.icon())
        btn.setText(text)
        
        ICON_SIZE = 20  
        btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        
        BUTTON_WIDTH = 120
        btn.setFixedWidth(BUTTON_WIDTH)
        
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setStyleSheet("""
            QToolButton {
                color: #333;
                padding: 6px 12px;
                border-radius: 4px;
                background-color: transparent;
                font-size: 14px;
                text-align: left;  
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            QToolButton:pressed, QToolButton:checked {
                background-color: rgba(255, 153, 0, 0.15);
                color: #ff7d00;
                font-weight: 500;
            }
        """)

        btn.clicked.connect(lambda: self.switchTo(interface))
        self.horizontalNavLayout.addWidget(btn)

        self.interfaceToBtnMap[interface] = btn
        return navItem

    def switchTo(self, interface):
        
        super().switchTo(interface)
        for w, btn in self.interfaceToBtnMap.items():
            btn.setChecked(w == interface)
        if isinstance(interface, ProjectInterface):
            interface.refresh_interface()

    def initWindow(self):
        
        self.resize(1280, 720)
        self.setMinimumWidth(720)
        # self.setWindowTitle('Specialized Software for Integrated Visualization and Data Processing of Multimodal Physiological Signals')
        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()



    def addSubInterface(self, interface, icon, text, position=NavigationItemPosition.TOP, parent=None):
        
        navItem = super().addSubInterface(interface, icon, text, position, parent)

        btn = QToolButton()
        btn.setIcon(icon.icon())
        btn.setText(text)
        btn.setIconSize(QSize(18, 18))
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  
        btn.setStyleSheet("""
            QToolButton {
                color: #333;
                padding: 6px 12px;
                border-radius: 4px;
                background-color: transparent;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            QToolButton:pressed, QToolButton:checked {
                background-color: rgba(255, 153, 0, 0.15);  
                color: #ff7d00;
                font-weight: 500;
            }
        """)

        btn.clicked.connect(lambda: self.switchTo(interface))
        self.horizontalNavLayout.addWidget(btn)

        self.interfaceToBtnMap[interface] = btn
        return navItem


    def switchTo(self, interface):
        
        super().switchTo(interface)
        for w, btn in self.interfaceToBtnMap.items():
            btn.setChecked(w == interface)
        if isinstance(interface, ProjectInterface):
            interface.refresh_interface()


    def initWindow(self):
        
        self.resize(1280, 720)
        self.setMinimumWidth(720)
        # self.setWindowTitle('Specialized Software for Integrated Visualization and Data Processing of Multimodal Physiological Signals')
        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

        self.interfaceToBtnMap = {}


    def onSupport(self):
        try:
            print("打开帮助")
            if getattr(sys, 'frozen', False):
                manual_path = os.path.join(os.path.dirname(sys.executable), 'resource', '用户手册.pdf')
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                manual_path = os.path.join(project_root, 'resource', '用户手册.pdf')
            
            manual_path = os.path.abspath(manual_path)
            if os.path.exists(manual_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(manual_path))
            else:
                raise ValueError(f"未能找到用户手册文件：\n{manual_path}")
        except Exception as e:
            raise ValueError(f"打开用户手册时发生错误：\n{str(e)}")


    def get_fnirs_subject_data(self, data_file_path, db_info):
        if not db_info:
            raise ValueError("db_info is not provided")
        project = db_info['project']
        subject_id = db_info['subject_id']
        subject_data = project.get_subject_data(subject_id)
        
        if subject_data:
            experiment = project.get_experiment_by_id(subject_data['experiment_id'])
            subject_data['experiment_name'] = experiment['name'] if experiment else "Unknown Experiment"
            subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['fnirs_output_path'])
            if subject_data.get('fnirs_data_path'):
                subject_data['fnirs_data_path'] = os.path.join(project.base_path, subject_data['fnirs_data_path'])
            else:
                subject_data['fnirs_data_path'] = None
            if data_file_path:
                subject_data['path'] = os.path.join(project.base_path, data_file_path)
        else:
            raise ValueError("Unable to retrieve subject data from database")
        return subject_data


    def load_fnirs_data(self, data_file_path, db_info=None):
        print("Try To Load fnirs"+data_file_path)
        subject_data = self.get_fnirs_subject_data(db_info=db_info, data_file_path=data_file_path)
        return FNIRSData(
            filename=subject_data['path'],
            age=subject_data['age'],
            output_path=subject_data['full_output_path'],
            db_info=db_info
        )


    def show_fnirs_interface(self, data_file_path, fnirs_data, db_info):
        if self.fnirs_placeholder is None:
            self.fnirs_placeholder = QWidget()
            self.fnirs_placeholder.setObjectName("FNIRSInterface")
            self.addSubInterface(self.fnirs_placeholder, FIF.IOT, self.t.fnirs, self.pos)
        self.fnirs_interface = FNIRSInterface(parent=self, data_file_path=data_file_path, db_info=db_info, fnirs_data=fnirs_data)
        self.update_interface(self.fnirs_placeholder, self.fnirs_interface)


    def get_eeg_subject_data(self, data_file_path, db_info):
        if not db_info:
            raise ValueError("db_info is not provided")
        project = db_info['project']
        subject_id = db_info['subject_id']
        subject_data = project.get_subject_data(subject_id)
        
        if subject_data:
            experiment = project.get_experiment_by_id(subject_data['experiment_id'])
            subject_data['experiment_name'] = experiment['name'] if experiment else "Unknown Experiment"
            subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['eeg_output_path'])
            if subject_data.get('eeg_montage_path'):
                subject_data['eeg_montage_path'] = os.path.join(project.base_path, subject_data['eeg_montage_path'])
            else:
                subject_data['eeg_montage_path'] = None
            if data_file_path:
                subject_data['path'] = os.path.join(project.base_path, data_file_path)
        else:
            raise ValueError("Unable to retrieve subject data from database")
        return subject_data


    def load_eeg_data(self, data_file_path, db_info=None):
        print("Try To Load eeg"+data_file_path)
        subject_data = self.get_eeg_subject_data(db_info=db_info, data_file_path=data_file_path)
        return EEGData(
            filename=subject_data['path'],
            custom_montage=subject_data.get('eeg_montage_path'),
            output_path=subject_data['full_output_path'],
            db_info=db_info
        )


    def show_eeg_interface(self, data_file_path, eeg_data, db_info):
        if self.eeg_placeholder is None:
            self.eeg_placeholder = QWidget()
            self.eeg_placeholder.setObjectName("EEGInterface")
            self.addSubInterface(self.eeg_placeholder, FIF.ASTERISK, self.t.eeg, self.pos)
        self.eeg_interface = EEGInterface(parent=self, data_file_path=data_file_path, db_info=db_info, eeg_data=eeg_data)
        self.update_interface(self.eeg_placeholder, self.eeg_interface)


    def get_et_subject_data(self, data_file_path, db_info):
        if not db_info:
            raise ValueError("db_info is not provided")
        project = db_info['project']
        subject_id = db_info['subject_id']
        subject_data = project.get_subject_data(subject_id)
        
        if subject_data:
            experiment = project.get_experiment_by_id(subject_data['experiment_id'])
            subject_data['experiment_name'] = experiment['name'] if experiment else "Unknown Experiment"
            subject_data['full_output_path'] = os.path.join(project.base_path, subject_data['et_output_path'])
            if data_file_path:
                subject_data['path'] = os.path.join(project.base_path, data_file_path)
        else:
            raise ValueError("Unable to retrieve subject data from database")
        return subject_data


    def load_et_data(self, data_file_path, db_info=None):
        subject_data = self.get_et_subject_data(db_info=db_info, data_file_path=data_file_path)
        return ETData(
            file_path=subject_data['path'],
            output_path=subject_data['full_output_path'],
            db_info=db_info
        )


    def show_et_interface(self, data_file_path, et_data, db_info):
        if self.et_placeholder is None:
            self.et_placeholder = QWidget()
            self.et_placeholder.setObjectName("ETInterface")
            self.addSubInterface(self.et_placeholder, FIF.VIEW, self.t.et, self.pos)
        self.et_interface = ETInterface(parent=self, data_file_path=data_file_path, db_info=db_info, et_data=et_data)
        self.update_interface(self.et_placeholder, self.et_interface)


    def load_qu_interface(self, template_path: str, questionnaire_file_path: str, output_path: str, experiment: str, name: str):
        if self.qu_placeholder is None:
            self.qu_placeholder = QWidget()
            self.qu_placeholder.setObjectName("QUInterface")
            self.addSubInterface(self.qu_placeholder, FIF.LABEL, self.t.qu, self.pos)
        new_interface = QUInterface(
            parent=self, template_path=template_path, questionnaire_file_path=questionnaire_file_path,
            output_path=output_path, experiment=experiment, name=name
        )
        self.update_interface(self.qu_placeholder, new_interface)
        
        if any([self.eeg_interface, self.fnirs_interface, self.et_interface]):
            self.load_viewer_interface(experiment, name)
        else:
            self.load_no_viewer_interface()


    def load_no_eeg_interface(self):
        self.eeg_interface = None
        if self.eeg_placeholder is None:
            self.eeg_placeholder = QWidget()
            self.eeg_placeholder.setObjectName("EEGInterface")
            self.addSubInterface(self.eeg_placeholder, FIF.ASTERISK, self.t.eeg, self.pos)
        no_interface = GalleryInterface(title="Participant Don't Have This Data.", subtitle="Please Add In The Data Management.")
        self.update_interface(self.eeg_placeholder, no_interface)


    def load_no_fnirs_interface(self):
        self.fnirs_interface = None
        if self.fnirs_placeholder is None:
            self.fnirs_placeholder = QWidget()
            self.fnirs_placeholder.setObjectName("FNIRSInterface")
            self.addSubInterface(self.fnirs_placeholder, FIF.IOT, self.t.fnirs, self.pos)
        no_interface = GalleryInterface(title="Participant Don't Have This Data.", subtitle="Please Add In The Data Management.")
        self.update_interface(self.fnirs_placeholder, no_interface)


    def load_no_et_interface(self):
        self.et_interface = None
        if self.et_placeholder is None:
            self.et_placeholder = QWidget()
            self.et_placeholder.setObjectName("ETInterface")
            self.addSubInterface(self.et_placeholder, FIF.VIEW, self.t.et, self.pos)
        no_interface = GalleryInterface(title="Participant Don't Have This Data.", subtitle="Please Add In The Data Management.")
        self.update_interface(self.et_placeholder, no_interface)


    def load_viewer_interface(self, experiment, name):
        if self.viewer_placeholder is None:
            self.viewer_placeholder = QWidget()
            self.viewer_placeholder.setObjectName("ViewerInterface")
            self.addSubInterface(self.viewer_placeholder, FIF.PENCIL_INK, self.t.viewer, self.pos)
        self.viewer_interface = ViewerInterface(parent=self, experiment=experiment, name=name)
        self.update_interface(self.viewer_placeholder, self.viewer_interface)


    def load_no_viewer_interface(self):
        if self.viewer_placeholder is None:
            self.viewer_placeholder = QWidget()
            self.viewer_placeholder.setObjectName("ViewerInterface")
            self.addSubInterface(self.viewer_placeholder, FIF.PENCIL_INK, self.t.viewer, self.pos)
        no_interface = GalleryInterface(title="Participant Don't Have Visualization Data.", subtitle="Please Add In Data Management.")
        self.update_interface(self.viewer_placeholder, no_interface)


    def update_interface(self, placeholder, new_interface):
        if placeholder.layout():
            while placeholder.layout().count():
                item = placeholder.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            QWidget().setLayout(placeholder.layout())
        layout = QVBoxLayout(placeholder)
        layout.addWidget(new_interface)
        placeholder.setLayout(layout)
        self.stackedWidget.setCurrentWidget(placeholder)


    def connectSignalToSlot(self):
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        signalBus.switchToSampleCard.connect(self.switchToSample)
        signalBus.supportSignal.connect(self.onSupport)


    def switchToSample(self, routeKey, index):
        interfaces = self.findChildren(GalleryInterface)
        for w in interfaces:
            if w.objectName() == routeKey:
                self.stackedWidget.setCurrentWidget(w, False)
                w.scrollToCard(index)


    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())