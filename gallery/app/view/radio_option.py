from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from qfluentwidgets import RadioButton,BodyLabel

class RadioOption(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        self.radio = RadioButton(self)
        self.radio.setFixedWidth(25)  
        layout.addWidget(self.radio)

        self.label = BodyLabel(text, self)
        self.label.setWordWrap(True)  
        layout.addWidget(self.label)
