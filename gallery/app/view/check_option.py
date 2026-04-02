from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from qfluentwidgets import CheckBox,BodyLabel

class CheckOption(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        self.checkbox = CheckBox(text, self)
        self.checkbox.setFixedWidth(25)  
        layout.addWidget(self.checkbox)

        self.label = BodyLabel(text, self)
        self.label.setWordWrap(True)  
        layout.addWidget(self.label)
