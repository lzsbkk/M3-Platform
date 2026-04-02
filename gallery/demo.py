# coding:utf-8
import os
import sys
from PyQt5.QtCore import Qt, QTranslator, QTimer
from PyQt5.QtGui import QFont, QSurfaceFormat
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator, setTheme, Theme
from PyQt5.QtGui import QGuiApplication

from app.common.config import cfg
from app.view.main_window import MainWindow

QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_CompressHighFrequencyEvents)

setTheme(Theme.LIGHT)


os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

w = MainWindow()

w.show()

w.raise_()
w.activateWindow()

app.exec_()

# coding:utf-8
# coding:utf-8
# import os
# import sys
# from PyQt5.QtCore import QSize, Qt, QTranslator, QTimer, QPoint, QPropertyAnimation, QEasingCurve
# from PyQt5.QtGui import QFont, QSurfaceFormat, QFontDatabase, QIcon, QColor, QLinearGradient, QPalette, QPainter, QBrush
# from PyQt5.QtWidgets import (QApplication, QGraphicsOpacityEffect, QLabel, QVBoxLayout, QHBoxLayout, 
#                              QWidget, QFrame, QStatusBar, QToolBar)
# from qfluentwidgets import (FluentTranslator, setTheme, Theme, NavigationBar, NavigationItemPosition, 
#                            FluentIcon, setThemeColor, PushButton)

# from app.common.config import cfg
# from app.view.main_window import MainWindow

# QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
# QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
# QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
# QApplication.setAttribute(Qt.AA_CompressHighFrequencyEvents)

# setTheme(Theme.DARK)
# setThemeColor("#3498db")
# # setThemeColor("#80007f")

# os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
# os.environ["QT_SCALE_FACTOR"] = "1"
# QApplication.setHighDpiScaleFactorRoundingPolicy(
#     Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

# app = QApplication(sys.argv)
# app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

# def load_fonts():
#     plex_families = []
#     plex_files = [
#         "fonts/IBMPlexSans-Regular.ttf",
#         "fonts/IBMPlexSans-Medium.ttf",
#         "fonts/IBMPlexSans-SemiBold.ttf",
#         "fonts/IBMPlexSans-Bold.ttf"
#     ]
    
#     for file in plex_files:
#         try:
#             font_id = QFontDatabase.addApplicationFont(file)
#             families = QFontDatabase.applicationFontFamilies(font_id)
#             plex_families.extend(families)
#             print(f"Loaded font: {families} from {file}")
#         except:
#             print(f"Failed to load font: {file}")
    
#     rajdhani_families = []
#     rajdhani_files = [
#         "fonts/Rajdhani-Regular.ttf",
#         "fonts/Rajdhani-Medium.ttf",
#         "fonts/Rajdhani-SemiBold.ttf",
#         "fonts/Rajdhani-Bold.ttf"
#     ]
    
#     for file in rajdhani_files:
#         try:
#             font_id = QFontDatabase.addApplicationFont(file)
#             families = QFontDatabase.applicationFontFamilies(font_id)
#             rajdhani_families.extend(families)
#             print(f"Loaded font: {families} from {file}")
#         except:
#             print(f"Failed to load font: {file}")
    
#     if plex_families:
#         app_font = QFont(plex_families[0], 11)
#         app.setFont(app_font)
#     return plex_families, rajdhani_families

# plex_families, rajdhani_families = load_fonts()
# print("Available IBM Plex Sans families:", plex_families)
# print("Available Rajdhani families:", rajdhani_families)

# tech_style = """
#     QWidget {
#         background-color: #0f1a2a;
#         color: #e0e0e0;
#         selection-background-color: #3498db;
#         selection-color: white;
#         font-family: 'IBM Plex Sans', 'Microsoft YaHei', sans-serif;
#         font-size: 13px;
#     }
    
#     TitleLabel, 
#     QLabel[title="true"] {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 600;
#         font-size: 18px;
#         letter-spacing: 0.8px;
#         text-transform: uppercase;
#         color: #ffffff;
#         margin-bottom: 10px;
#     }
    
#     SubtitleLabel, 
#     QLabel[subtitle="true"] {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 500;
#         font-size: 15px;
#         letter-spacing: 0.5px;
#         color: #3498db;
#         margin-bottom: 8px;
#     }
    
#     BodyLabel, 
#     QLabel[body="true"] {
#         font-family: 'IBM Plex Sans', 'Microsoft YaHei', sans-serif;
#         font-weight: 400;
#         font-size: 14px;
#         color: #b0b0b0;
#         line-height: 1.6;
#     }
    
#     StrongLabel, 
#     QLabel[strong="true"] {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 500;
#         font-size: 14px;
#         color: #2ecc71;
#     }
    
#     CaptionLabel, 
#     QLabel[caption="true"] {
#         font-family: 'IBM Plex Sans', 'Microsoft YaHei', sans-serif;
#         font-weight: 300;
#         font-size: 12px;
#         color: #7f8c8d;
#         letter-spacing: 0.2px;
#     }
    
#     CardWidget {
#         background-color: #1a2a3a;
#         border-radius: 6px;
#         border: 1px solid #2c3e50;
#         padding: 15px;
#     }
    
#     .tech-card {
#         background-color: #152435;
#         border: 1px solid #2c3e50;
#         border-radius: 8px;
#         padding: 20px;
#     }
    
#     PushButton, 
#     ToolButton {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 500;
#         font-size: 13px;
#         letter-spacing: 0.6px;
#         text-transform: uppercase;
#         background-color: #2c3e50;
#         color: #ecf0f1;
#         border-radius: 4px;
#         padding: 8px 16px;
#         border: 1px solid #3498db;
#         min-height: 32px;
#     }
    
#     PushButton:hover, 
#     ToolButton:hover {
#         background-color: #3498db;
#         color: white;
#     }
    
#     PushButton:pressed, 
#     ToolButton:pressed {
#         background-color: #2980b9;
#     }
    
#     .tech-button {
#         font-family: 'Rajdhani', sans-serif;
#         font-weight: 600;
#         font-size: 14px;
#         letter-spacing: 0.8px;
#         text-transform: uppercase;
#         background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
#             stop:0 #3498db, stop:1 #2ecc71);
#         color: white;
#         border-radius: 4px;
#         padding: 10px 20px;
#         border: none;
#         box-shadow: 0 2px 6px rgba(52, 152, 219, 0.3);
#     }
    
#     .tech-button:hover {
#         background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
#             stop:0 #2980b9, stop:1 #27ae60);
#         box-shadow: 0 4px 8px rgba(52, 152, 219, 0.4);
#     }
    
#     .tech-button:pressed {
#         background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
#             stop:0 #1c6ea4, stop:1 #219653);
#     }
    
#     TableWidget {
#         background-color: #152435;
#         alternate-background-color: #1a2a3a;
#         gridline-color: #2c3e50;
#         font-size: 13px;
#     }
    
#     QHeaderView::section {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 600;
#         font-size: 12px;
#         letter-spacing: 0.5px;
#         background-color: #1a2a3a;
#         color: #3498db;
#         padding: 8px;
#         border: none;
#         border-bottom: 2px solid #3498db;
#     }
    
#     QTableCornerButton::section {
#         background-color: #1a2a3a;
#         border: none;
#         border-bottom: 2px solid #3498db;
#     }
    
#     LineEdit, 
#     TextEdit, 
#     ComboBox {
#         background-color: #152435;
#         border: 1px solid #2c3e50;
#         border-radius: 4px;
#         padding: 6px 10px;
#         color: #ecf0f1;
#         font-size: 14px;
#     }
    
#     LineEdit:focus, 
#     TextEdit:focus {
#         border: 1px solid #3498db;
#         box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.3);
#     }
    
#     NavigationBar {
#         background-color: #1a2a3a;
#         border-radius: 6px;
#         padding: 5px;
#         border: 1px solid #2c3e50;
#     }
    
#     NavigationItem {
#         color: #b0b0b0;
#         padding: 8px 15px;
#         border-radius: 4px;
#         margin: 2px;
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 500;
#         font-size: 13px;
#         letter-spacing: 0.5px;
#         text-transform: uppercase;
#     }
    
#     NavigationItem:hover {
#         background-color: #2c3e50;
#     }
    
#     NavigationItem[selected=true] {
#         background-color: #3498db;
#         color: white;
#         font-weight: 600;
#     }
    
#     .tech-display {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 600;
#         font-size: 24px;
#         color: #2ecc71;
#         letter-spacing: 1px;
#         text-shadow: 0 0 10px rgba(46, 204, 113, 0.5);
#     }
    
#     .glowing-border {
#         border: 1px solid #3498db;
#         border-radius: 6px;
#         box-shadow: 0 0 8px rgba(52, 152, 219, 0.6);
#     }
    
#     .animated-border {
#         position: relative;
#         border-radius: 8px;
#         overflow: hidden;
#     }
    
#     .animated-border::before {
#         content: "";
#         position: absolute;
#         top: -2px;
#         left: -2px;
#         right: -2px;
#         bottom: -2px;
#         background: linear-gradient(45deg, 
#             #3498db, #2ecc71, #3498db, #2ecc71);
#         z-index: -1;
#         animation: animate-border 4s linear infinite;
#         background-size: 400% 400%;
#     }
    
#     .gradient-text {
#         background: linear-gradient(90deg, #3498db, #2ecc71);
#         -webkit-background-clip: text;
#         background-clip: text;
#         color: transparent;
#         font-weight: 700;
#     }
    
#     @keyframes animate-border {
#         0% { background-position: 0% 50%; }
#         50% { background-position: 100% 50%; }
#         100% { background-position: 0% 50%; }
#     }
    
#     @keyframes pulse {
#         0% { opacity: 0.6; }
#         50% { opacity: 1; }
#         100% { opacity: 0.6; }
#     }
    
#     .pulse-effect {
#         animation: pulse 2s infinite;
#     }
    
#     .status-indicator {
#         width: 12px;
#         height: 12px;
#         border-radius: 50%;
#         display: inline-block;
#         margin-right: 6px;
#     }
    
#     .status-active {
#         background-color: #2ecc71;
#         box-shadow: 0 0 8px rgba(46, 204, 113, 0.6);
#     }
    
#     .status-inactive {
#         background-color: #e74c3c;
#     }
    
#     .status-warning {
#         background-color: #f39c12;
#     }
    
#     HorizontalSeparator, VerticalSeparator {
#         background-color: #2c3e50;
#     }
    
#     QScrollBar:vertical {
#         border: none;
#         background: #1a2a3a;
#         width: 10px;
#         margin: 0px 0px 0px 0px;
#     }
    
#     QScrollBar::handle:vertical {
#         background: #3498db;
#         min-height: 20px;
#         border-radius: 5px;
#     }
    
#     QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
#         height: 0px;
#         background: none;
#     }
    
#     QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
#         background: none;
#     }
    
#     QStatusBar {
#         background-color: #1a2a3a;
#         border-top: 1px solid #2c3e50;
#         padding: 4px 10px;
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-size: 12px;
#     }
# """

# app.setStyleSheet(tech_style)

# w = MainWindow()

# def add_tech_decoration(window):
#     if not hasattr(window, 'statusBar'):
#         window.statusBar = QStatusBar()
#         window.setStatusBar(window.statusBar)
    
#     status_label = QLabel()
#     status_label.setText('<span class="status-indicator status-active"></span> SYSTEM ONLINE')
#     status_label.setStyleSheet("font-family: 'Rajdhani'; font-size: 12px; color: #2ecc71;")
#     window.statusBar().addPermanentWidget(status_label)
    
#     if hasattr(window, 'titleLabel'):
#         window.titleLabel.setProperty('class', 'gradient-text')
#         window.titleLabel.setStyleSheet("font-size: 24px; font-weight: 700;")
    
#     if hasattr(window, 'centralWidget'):
#         central = window.centralWidget()
#         central.setProperty('class', 'animated-border')
    
#     def create_data_panel(title, value, unit):
#         panel = QWidget()
#         panel.setProperty('class', 'tech-card')
#         panel.setFixedSize(180, 120)
        
#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(15, 15, 15, 15)
#         layout.setSpacing(10)
#         layout.setAlignment(Qt.AlignCenter)
        
#         title_label = QLabel(title)
#         title_label.setProperty('class', 'subtitle')
#         title_label.setStyleSheet("""
#             font-family: 'Rajdhani';
#             font-size: 14px;
#             font-weight: 500;
#             color: #3498db;
#             letter-spacing: 0.5px;
#             text-transform: uppercase;
#         """)
#         layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
#         value_layout = QHBoxLayout()
#         value_layout.setAlignment(Qt.AlignCenter)
        
#         value_label = QLabel(value)
#         value_label.setProperty('class', 'tech-display')
#         value_label.setStyleSheet("font-size: 28px;")
#         value_layout.addWidget(value_label)
        
#         if unit:
#             unit_label = QLabel(unit)
#             unit_label.setStyleSheet("""
#                 font-family: 'Rajdhani';
#                 font-size: 16px;
#                 color: #7f8c8d;
#                 margin-left: 5px;
#                 margin-bottom: 5px;
#             """)
#             value_layout.addWidget(unit_label, alignment=Qt.AlignBottom)
        
#         layout.addLayout(value_layout)
        
#         opacity_effect = QGraphicsOpacityEffect(panel)
#         panel.setGraphicsEffect(opacity_effect)
        
#         pulse_animation = QPropertyAnimation(opacity_effect, b"opacity")
#         pulse_animation.setDuration(2000)
#         pulse_animation.setStartValue(0.8)
#         pulse_animation.setEndValue(1.0)
#         pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)
#         pulse_animation.setLoopCount(-1)
#         pulse_animation.start()
        
#         return panel
    
#     if not hasattr(window, 'toolBar'):
#         window.toolBar = QToolBar("Tech Toolbar")
#         window.toolBar.setMovable(False)
#         window.toolBar.setFloatable(False)
#         window.addToolBar(Qt.TopToolBarArea, window.toolBar)
    
#     panel1 = create_data_panel("CPU", "42", "%")
#     panel2 = create_data_panel("MEM", "76", "%")
#     panel3 = create_data_panel("TEMP", "36", "°C")
    
#     window.toolBar.addWidget(panel1)
#     window.toolBar.addWidget(panel2)
#     window.toolBar.addWidget(panel3)
    
#     run_button = PushButton("RUN ANALYSIS")
#     run_button.setProperty("class", "tech-button")
#     run_button.setIcon(FluentIcon.PLAY)
#     run_button.setIconSize(QSize(20, 20))
#     window.toolBar.addWidget(run_button)

# # add_tech_decoration(w)

# w.show()

# w.raise_()
# w.activateWindow()

# QTimer.singleShot(100, lambda: w.setProperty('class', 'glowing-border'))

# app.exec_()

# coding:utf-8
# import os
# import sys
# from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
# from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QColor, QLinearGradient, QPalette, QPainter, QBrush
# from PyQt5.QtWidgets import (QApplication, QGraphicsOpacityEffect, QLabel, QVBoxLayout, QHBoxLayout, 
#                              QWidget, QFrame, QStatusBar, QToolBar, QMainWindow)
# from qfluentwidgets import (FluentTranslator, setTheme, Theme, NavigationBar, NavigationItemPosition, 
#                            FluentIcon, setThemeColor, PushButton, CardWidget)

# from app.common.config import cfg
# from app.view.main_window import MainWindow

# QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
# QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
# QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
# QApplication.setAttribute(Qt.AA_CompressHighFrequencyEvents)

# setTheme(Theme.LIGHT)

# os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
# os.environ["QT_SCALE_FACTOR"] = "1"
# QApplication.setHighDpiScaleFactorRoundingPolicy(
#     Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

# app = QApplication(sys.argv)
# app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

# def load_fonts():
#     plex_families = []
#     plex_files = [
#         "fonts/IBMPlexSans-Regular.ttf",
#         "fonts/IBMPlexSans-Medium.ttf",
#         "fonts/IBMPlexSans-SemiBold.ttf",
#         "fonts/IBMPlexSans-Bold.ttf"
#     ]
    
#     for file in plex_files:
#         try:
#             font_id = QFontDatabase.addApplicationFont(file)
#             families = QFontDatabase.applicationFontFamilies(font_id)
#             plex_families.extend(families)
#             print(f"Loaded font: {families} from {file}")
#         except:
#             print(f"Failed to load font: {file}")
    
#     rajdhani_families = []
#     rajdhani_files = [
#         "fonts/Rajdhani-Regular.ttf",
#         "fonts/Rajdhani-Medium.ttf",
#         "fonts/Rajdhani-SemiBold.ttf",
#         "fonts/Rajdhani-Bold.ttf"
#     ]
    
#     for file in rajdhani_files:
#         try:
#             font_id = QFontDatabase.addApplicationFont(file)
#             families = QFontDatabase.applicationFontFamilies(font_id)
#             rajdhani_families.extend(families)
#             print(f"Loaded font: {families} from {file}")
#         except:
#             print(f"Failed to load font: {file}")
    
#     if plex_families:
#         app_font = QFont(plex_families[0], 11)
#         app.setFont(app_font)
#     return plex_families, rajdhani_families

# plex_families, rajdhani_families = load_fonts()
# print("Available IBM Plex Sans families:", plex_families)
# print("Available Rajdhani families:", rajdhani_families)

# tech_style = """
#     QWidget {
#         color: #333333;
#         selection-background-color: #1e90ff;
#         selection-color: white;
#         font-family: 'IBM Plex Sans', 'Microsoft YaHei', sans-serif;
#         font-size: 13px;
#     }
    
#     TitleLabel, 
#     QLabel[title="true"] {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 700;
#         font-size: 20px;
#         letter-spacing: 0.8px;
#         margin-bottom: 10px;
#     }
    
#     SubtitleLabel, 
#     QLabel[subtitle="true"] {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 600;
#         font-size: 16px;
#         letter-spacing: 0.5px;
#         margin-bottom: 8px;
#     }
    
#     BodyLabel, 
#     QLabel[body="true"] {
#         font-family: 'IBM Plex Sans', 'Microsoft YaHei', sans-serif;
#         font-weight: 400;
#         font-size: 14px;
#         color: #333333;
#         line-height: 1.6;
#     }
    
#     StrongLabel, 
#     QLabel[strong="true"] {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 600;
#         font-size: 14px;
#     }
    
#     CaptionLabel, 
#     QLabel[caption="true"] {
#         font-family: 'IBM Plex Sans', 'Microsoft YaHei', sans-serif;
#         font-weight: 300;
#         font-size: 12px;
#         letter-spacing: 0.2px;
#     }
    
#     CardWidget {
#         background-color: #ffffff;
#         border-radius: 10px;
#         padding: 15px;
#         box-shadow: 0 4px 12px rgba(30, 144, 255, 0.15);
#     }
    
#     .tech-card {
#         background: linear-gradient(135deg, #e6f0ff, #ffffff);
#         border-radius: 10px;
#         padding: 20px;
#         box-shadow: 0 4px 15px rgba(30, 144, 255, 0.2);
#     }
    
#     PushButton, 
#     ToolButton {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 600;
#         font-size: 14px;
#         letter-spacing: 0.6px;
#         color: white;
#         border-radius: 6px;
#         padding: 8px 16px;
#         border: none;
#         min-height: 36px;
#         box-shadow: 0 4px 8px rgba(30, 144, 255, 0.3);
#     }
    
#     PushButton:hover, 
#     ToolButton:hover {
#         box-shadow: 0 6px 12px rgba(30, 144, 255, 0.4);
#     }
    
#     PushButton:pressed, 
#     ToolButton:pressed {
#     }
    
#     .tech-button {
#         font-family: 'Rajdhani', sans-serif;
#         font-weight: 700;
#         font-size: 15px;
#         letter-spacing: 0.8px;
#         color: white;
#         border-radius: 6px;
#         padding: 12px 24px;
#         border: none;
#         box-shadow: 0 6px 15px rgba(30, 144, 255, 0.4);
#     }
    
#     .tech-button:hover {
#         background: linear-gradient(90deg, #0077e6, #0099e6);
#         box-shadow: 0 8px 18px rgba(30, 144, 255, 0.5);
#     }
    
#     .tech-button:pressed {
#         background: linear-gradient(90deg, #005bbf, #0077bf);
#     }
    
#     TableWidget {
#         background-color: #ffffff;
#         font-size: 13px;
#         border-radius: 8px;
#     }
    
#     QHeaderView::section {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 700;
#         font-size: 13px;
#         letter-spacing: 0.5px;
#         color: white;
#         padding: 10px;
#         border: none;
#         border-bottom: 2px solid #005bbf;
#     }
    
#     QTableCornerButton::section {
#         background: linear-gradient(to bottom, #1e90ff, #0077e6);
#         border: none;
#         border-bottom: 2px solid #005bbf;
#     }
    
#     LineEdit, 
#     TextEdit, 
#     ComboBox {
#         background-color: #ffffff;
#         border-radius: 6px;
#         padding: 8px 12px;
#         color: #333333;
#         font-size: 14px;
#     }
    
#     LineEdit:focus, 
#     TextEdit:focus {
#         border: 2px solid #1e90ff;
#         box-shadow: 0 0 0 3px rgba(30, 144, 255, 0.2);
#     }
    
#     NavigationBar {
#         background-color: #ffffff;
#         border-radius: 8px;
#         padding: 5px;
#         border: 1px solid #d1e0ff;
#         box-shadow: 0 4px 10px rgba(30, 144, 255, 0.15);
#     }
    
#     NavigationItem {
#         padding: 10px 20px;
#         border-radius: 6px;
#         margin: 3px;
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 600;
#         font-size: 14px;
#         letter-spacing: 0.5px;
#     }
    
#     NavigationItem:hover {
#     }
    
#     NavigationItem[selected=true] {
#         background-color: #1e90ff;
#         color: white;
#         font-weight: 700;
#     }
    
#     .tech-display {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 700;
#         font-size: 28px;
#         letter-spacing: 1px;
#         text-shadow: 0 2px 4px rgba(30, 144, 255, 0.3);
#     }
    
#     .glowing-border {
#         border: 2px solid #1e90ff;
#         border-radius: 10px;
#         box-shadow: 0 0 15px rgba(30, 144, 255, 0.5);
#     }
    
#     .animated-border {
#         position: relative;
#         border-radius: 10px;
#         overflow: hidden;
#         background: white;
#     }
    
#     .animated-border::before {
#         content: "";
#         position: absolute;
#         top: -2px;
#         left: -2px;
#         right: -2px;
#         bottom: -2px;
#         background: linear-gradient(45deg, 
#             #1e90ff, #00bfff, #1e90ff, #00bfff);
#         z-index: -1;
#         animation: animate-border 4s linear infinite;
#         background-size: 400% 400%;
#     }
    
#     .gradient-text {
#         background: linear-gradient(90deg, #1e90ff, #00bfff);
#         -webkit-background-clip: text;
#         background-clip: text;
#         color: transparent;
#         font-weight: 700;
#     }
    
#     @keyframes animate-border {
#         0% { background-position: 0% 50%; }
#         50% { background-position: 100% 50%; }
#         100% { background-position: 0% 50%; }
#     }
    
#     @keyframes pulse {
#         0% { transform: scale(1); }
#         50% { transform: scale(1.02); }
#         100% { transform: scale(1); }
#     }
    
#     .pulse-effect {
#         animation: pulse 3s infinite;
#     }
    
#     .status-indicator {
#         width: 12px;
#         height: 12px;
#         border-radius: 50%;
#         display: inline-block;
#         margin-right: 6px;
#         box-shadow: 0 0 8px currentColor;
#     }
    
#     .status-active {
#         background-color: #1e90ff;
#         color: #1e90ff;
#     }
    
#     .status-inactive {
#         background-color: #ff6b6b;
#         color: #ff6b6b;
#     }
    
#     .status-warning {
#         background-color: #ffd43b;
#         color: #ffd43b;
#     }
    
#     HorizontalSeparator, VerticalSeparator {
#         background-color: #d1e0ff;
#         height: 2px;
#     }
    
#     QScrollBar:vertical {
#         border: none;
#         background: #e6f0ff;
#         width: 12px;
#         margin: 0px 0px 0px 0px;
#         border-radius: 6px;
#     }
    
#     QScrollBar::handle:vertical {
#         background: #1e90ff;
#         min-height: 30px;
#         border-radius: 6px;
#     }
    
#     QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
#         height: 0px;
#         background: none;
#     }
    
#     QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
#         background: none;
#     }
    
#     QStatusBar {
#         background-color: #e6f0ff;
#         border-top: 2px solid #d1e0ff;
#         padding: 6px 12px;
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-size: 12px;
#         font-weight: 500;
#         color: #1e3a8a;
#     }
# """

# app.setStyleSheet(tech_style)

# w = MainWindow()

# def add_tech_decoration(window):
#     if not hasattr(window, 'statusBar'):
#         window.statusBar = QStatusBar()
#         window.setStatusBar(window.statusBar)
    
#     status_label = QLabel()
#     status_label.setText('<span class="status-indicator status-active"></span> SYSTEM ONLINE')
#     status_label.setStyleSheet("font-family: 'Rajdhani'; font-size: 13px; color: #1e90ff; font-weight: 600;")
#     window.statusBar().addPermanentWidget(status_label)
    
#     if hasattr(window, 'titleLabel'):
#         window.titleLabel.setProperty('class', 'gradient-text')
#         window.titleLabel.setStyleSheet("font-size: 28px; font-weight: 700;")
    
#     if hasattr(window, 'centralWidget'):
#         central = window.centralWidget()
#         central.setProperty('class', 'animated-border')
    
#     def create_data_panel(title, value, unit):
#         panel = CardWidget()
#         panel.setProperty('class', 'tech-card pulse-effect')
#         panel.setFixedSize(200, 140)
        
#         layout = QVBoxLayout(panel)
#         layout.setContentsMargins(15, 15, 15, 15)
#         layout.setSpacing(10)
#         layout.setAlignment(Qt.AlignCenter)
        
#         title_label = QLabel(title)
#         title_label.setProperty('class', 'subtitle')
#         title_label.setStyleSheet("""
#             font-family: 'Rajdhani';
#             font-size: 16px;
#             font-weight: 600;
#             color: #1e3a8a;
#             letter-spacing: 0.5px;
#         """)
#         layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
#         value_layout = QHBoxLayout()
#         value_layout.setAlignment(Qt.AlignCenter)
        
#         value_label = QLabel(value)
#         value_label.setProperty('class', 'tech-display')
#         value_label.setStyleSheet("font-size: 32px;")
#         value_layout.addWidget(value_label)
        
#         if unit:
#             unit_label = QLabel(unit)
#             unit_label.setStyleSheet("""
#                 font-family: 'Rajdhani';
#                 font-size: 18px;
#                 color: #5c7cfa;
#                 margin-left: 5px;
#                 margin-bottom: 8px;
#                 font-weight: 600;
#             """)
#             value_layout.addWidget(unit_label, alignment=Qt.AlignBottom)
        
#         layout.addLayout(value_layout)
        
#         opacity_effect = QGraphicsOpacityEffect(panel)
#         panel.setGraphicsEffect(opacity_effect)
        
#         pulse_animation = QPropertyAnimation(opacity_effect, b"opacity")
#         pulse_animation.setDuration(1500)
#         pulse_animation.setStartValue(1.0)
#         pulse_animation.setEndValue(0.95)
#         pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)
#         pulse_animation.setLoopCount(-1)
#         pulse_animation.start()
        
#         return panel
    
#     if not hasattr(window, 'toolBar'):
#         window.toolBar = QToolBar("Tech Toolbar")
#         window.toolBar.setMovable(False)
#         window.toolBar.setFloatable(False)
#         window.addToolBar(Qt.TopToolBarArea, window.toolBar)
#         window.toolBar.setStyleSheet("""
#             QToolBar {
#                 background-color: #e6f0ff;
#                 border-bottom: 2px solid #d1e0ff;
#                 padding: 10px;
#                 spacing: 15px;
#             }
#         """)
    
#     panel1 = create_data_panel("CPU USAGE", "42", "%")
#     panel2 = create_data_panel("MEMORY", "76", "%")
#     panel3 = create_data_panel("TEMP", "36", "°C")
    
#     window.toolBar.addWidget(panel1)
#     window.toolBar.addWidget(panel2)
#     window.toolBar.addWidget(panel3)
    
#     run_button = PushButton("START ANALYSIS")
#     run_button.setProperty("class", "tech-button")
#     run_button.setIcon(FluentIcon.PLAY)
#     run_button.setIconSize(QSize(24, 24))
#     window.toolBar.addWidget(run_button)
    
#     window.toolBar.addSeparator()
    
#     refresh_button = PushButton("REFRESH DATA")
#     refresh_button.setProperty("class", "tech-button")
#     refresh_button.setIcon(FluentIcon.SYNC)
#     refresh_button.setIconSize(QSize(20, 20))
#     window.toolBar.addWidget(refresh_button)

# # add_tech_decoration(w)

# w.show()

# w.raise_()
# w.activateWindow()

# QTimer.singleShot(100, lambda: w.setProperty('class', 'glowing-border'))

# app.exec_()