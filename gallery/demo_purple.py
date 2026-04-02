# # coding:utf-8
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
#         selection-background-color: #8a2be2;
#         selection-color: white;
#         font-family: 'IBM Plex Sans', 'Microsoft YaHei', sans-serif;
#         font-size: 13px;
#     }

#     QHBoxLayout {
#         selection-background-color: #8a2be2;
#         color: #6b6be1;
#         selection-color: #f5f0ff;
#     }

#     QVBoxLayout {
#         selection-background-color: #8a2be2;
#         color: #6b6be1;
#         selection-color: #f5f0ff;
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
#         border-radius: 10px;
#         padding: 15px;
#         box-shadow: 0 4px 12px rgba(138, 43, 226, 0.15);
#     }
    
#     .tech-card {
#         background: linear-gradient(135deg, #e6e6fa, #d8bfd8);
#         border-radius: 10px;
#         padding: 20px;
#         box-shadow: 0 4px 15px rgba(138, 43, 226, 0.2);
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
#         box-shadow: 0 4px 8px rgba(147, 112, 219, 0.3);
#     }
    
#     PushButton:hover, 
#     ToolButton:hover {
#         box-shadow: 0 6px 12px rgba(138, 43, 226, 0.4);
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
#         box-shadow: 0 6px 15px rgba(138, 43, 226, 0.4);
#     }
    
#     .tech-button:hover {
#         background: linear-gradient(90deg, #8a2be2, #da70d6);
#         box-shadow: 0 8px 18px rgba(138, 43, 226, 0.5);
#     }
    
#     .tech-button:pressed {
#         background: linear-gradient(90deg, #6a5acd, #ba55d3);
#     }
    
#     TableWidget {
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
#         border-bottom: 2px solid #6a5acd;
#     }
    
#     QTableCornerButton::section {
#         background: linear-gradient(to bottom, #9370db, #8a2be2);
#         border: none;
#         border-bottom: 2px solid #6a5acd;
#     }
    
#     LineEdit, 
#     TextEdit, 
#     ComboBox {
#         background-color: #e6e6fa;
#         border-radius: 6px;
#         padding: 8px 12px;
#         font-size: 14px;
#     }
    
#     LineEdit:focus, 
#     TextEdit:focus {
#         border: 2px solid #8a2be2;
#         box-shadow: 0 0 0 3px rgba(138, 43, 226, 0.2);
#     }
    
#     NavigationBar {
#         background-color: #e6e6fa;
#         border-radius: 8px;
#         padding: 5px;
#         border: 1px solid #d8bfd8;
#         box-shadow: 0 4px 10px rgba(138, 43, 226, 0.15);
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
#         background-color: #8a2be2;
#         color: white;
#         font-weight: 700;
#     }
    
#     .tech-display {
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-weight: 700;
#         font-size: 28px;
#         letter-spacing: 1px;
#         text-shadow: 0 2px 4px rgba(138, 43, 226, 0.3);
#     }
    
#     .glowing-border {
#         border: 2px solid #8a2be2;
#         border-radius: 10px;
#         box-shadow: 0 0 15px rgba(138, 43, 226, 0.5);
#     }
    
#     .animated-border {
#         position: relative;
#         border-radius: 10px;
#         overflow: hidden;
#         background: #e6e6fa;
#     }
    
#     .animated-border::before {
#         content: "";
#         position: absolute;
#         top: -2px;
#         left: -2px;
#         right: -2px;
#         bottom: -2px;
#         background: linear-gradient(45deg, 
#         z-index: -1;
#         animation: animate-border 4s linear infinite;
#         background-size: 400% 400%;
#     }
    
#     .gradient-text {
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
#         0% { transform: scale(1); opacity: 0.9; }
#         50% { transform: scale(1.02); opacity: 1; }
#         100% { transform: scale(1); opacity: 0.9; }
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
#         background-color: #8a2be2;
#         color: #8a2be2;
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
#         background-color: #d8bfd8;
#         height: 2px;
#     }
    
#     QScrollBar:vertical {
#         border: none;
#         background: #e6e6fa;
#         width: 12px;
#         margin: 0px 0px 0px 0px;
#         border-radius: 6px;
#     }
    
#     QScrollBar::handle:vertical {
#         background: #9370db;
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
#         background-color: #e6e6fa;
#         border-top: 2px solid #d8bfd8;
#         padding: 6px 12px;
#         font-family: 'Rajdhani', 'Microsoft YaHei', sans-serif;
#         font-size: 12px;
#         font-weight: 500;
#         color: #4b0082;
#     }
# """

# app.setStyleSheet(tech_style)

# w = MainWindow()

# w.show()

# w.raise_()
# w.activateWindow()

# QTimer.singleShot(100, lambda: w.setProperty('class', 'glowing-border'))

# app.exec_()
# coding:utf-8
# coding:utf-8
import os
import sys
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QColor, QLinearGradient, QPalette, QPainter, QBrush
from PyQt5.QtWidgets import (QApplication, QGraphicsOpacityEffect, QLabel, QVBoxLayout, QHBoxLayout, 
                             QWidget, QFrame, QStatusBar, QToolBar, QMainWindow)
from qfluentwidgets import (FluentTranslator, setTheme, Theme, NavigationBar, NavigationItemPosition, 
                           FluentIcon, setThemeColor, PushButton, CardWidget)
from qfluentwidgets import setCustomStyleSheet
from app.common.config import cfg
from app.view.main_window import MainWindow

QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_CompressHighFrequencyEvents)

setTheme(Theme.LIGHT)
setThemeColor("

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

def load_fonts():
    plex_families = []
    plex_files = [
        "fonts/IBMPlexSans-Regular.ttf",
        "fonts/IBMPlexSans-Medium.ttf",
        "fonts/IBMPlexSans-SemiBold.ttf",
        "fonts/IBMPlexSans-Bold.ttf"
    ]
    
    for file in plex_files:
        try:
            font_id = QFontDatabase.addApplicationFont(file)
            families = QFontDatabase.applicationFontFamilies(font_id)
            plex_families.extend(families)
            print(f"Loaded font: {families} from {file}")
        except:
            print(f"Failed to load font: {file}")
    
    rajdhani_families = []
    rajdhani_files = [
        "fonts/Rajdhani-Regular.ttf",
        "fonts/Rajdhani-Medium.ttf",
        "fonts/Rajdhani-SemiBold.ttf",
        "fonts/Rajdhani-Bold.ttf"
    ]
    
    for file in rajdhani_files:
        try:
            font_id = QFontDatabase.addApplicationFont(file)
            families = QFontDatabase.applicationFontFamilies(font_id)
            rajdhani_families.extend(families)
            print(f"Loaded font: {families} from {file}")
        except:
            print(f"Failed to load font: {file}")
    
    if plex_families:
        app_font = QFont(plex_families[0], 11)
        app.setFont(app_font)
    return plex_families, rajdhani_families

plex_families, rajdhani_families = load_fonts()
print("Available IBM Plex Sans families:", plex_families)
print("Available Rajdhani families:", rajdhani_families)

tech_style = 
navigation_style = 

tech_style += navigation_style
app.setStyle('Fusion')
app.setStyleSheet(tech_style)

w = MainWindow()
# setCustomStyleSheet(w, tech_style, tech_style)

w.show()

w.raise_()
w.activateWindow()

QTimer.singleShot(100, lambda: w.setProperty('class', 'glowing-border'))

app.exec_()