# coding: utf-8
from PyQt5.QtCore import QObject


class Translator(QObject):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.fnirs = self.tr('fNIRS Analysis')
        self.eeg = self.tr('EEG Analysis') 
        self.et = self.tr('Eye Tracking Analysis')
        self.qu = self.tr('Questionnaires')
        self.project = self.tr('Data Management')
        self.viewer = self.tr('Multi-data Visualization')
        self.help = self.tr('Help')
        self.settings = self.tr('Settings')