# eeg_plot_utils.py

import numpy as np
from PyQt5.QtGui import QPainterPath, QPen, QFont
from PyQt5.QtCore import QRectF, Qt
from qfluentwidgets import ThemeColor

class GridCalculator:
    @staticmethod
    def calculate_grid_interval(range_start, range_end, target_lines=5):
        range_width = range_end - range_start
        interval = range_width / target_lines
        magnitude = 10 ** np.floor(np.log10(interval))
        residual = interval / magnitude
        
        if residual < 1.5:
            return magnitude
        elif residual < 3:
            return 2 * magnitude
        elif residual < 7:
            return 5 * magnitude
        else:
            return 10 * magnitude

class CoordinateTransformer:
    def __init__(self, widget):
        self.widget = widget

    def time_to_x(self, t):
        return int((t - self.widget.time_range[0]) / 
                   (self.widget.time_range[1] - self.widget.time_range[0]) * 
                   (self.widget.width() - self.widget.left_margin - self.widget.right_margin)) + self.widget.left_margin

    def value_to_y(self, value):
        return int(self.widget.height() - self.widget.bottom_margin - 
                   (value - self.widget.y_range[0]) / 
                   (self.widget.y_range[1] - self.widget.y_range[0]) * 
                   (self.widget.height() - self.widget.top_margin - self.widget.bottom_margin))
    def x_to_time(self, x):
        return (
            (x - self.widget.left_margin) /
            (self.widget.width() - self.widget.left_margin - self.widget.right_margin) *
            (self.widget.time_range[1] - self.widget.time_range[0]) +
            self.widget.time_range[0]
        )

class WaveformDrawer:
    def __init__(self, widget, transformer):
        self.widget = widget
        self.transformer = transformer

    def draw(self, painter, data, time, sample_rate, pixels_per_second, wave_color=ThemeColor.LIGHT_2.color()):
        # print("***********")
        # print("***********")
        # print(dir(ThemeColor))
        # print("***********")
        # print("***********")
        # painter.setPen(QPen(ThemeColor.PRIMARY.color(), 2))
        painter.setPen(QPen(wave_color, 2))
        
        clip_rect = QRectF(self.widget.left_margin, self.widget.top_margin, 
                           self.widget.width() - self.widget.left_margin - self.widget.right_margin, 
                           self.widget.height() - self.widget.top_margin - self.widget.bottom_margin)
        painter.setClipRect(clip_rect)

        path = QPainterPath()
        first_point = True

        pixels_per_sample = pixels_per_second / sample_rate

        threshold = 10  

        for t, y in zip(time, data):
            x = self.transformer.time_to_x(t)
            y = self.transformer.value_to_y(y)
            
            if first_point:
                path.moveTo(x, y)
                first_point = False
            else:
                path.lineTo(x, y)

        painter.drawPath(path)

        if pixels_per_sample > threshold:
            painter.setPen(QPen(wave_color, 4))
            # painter.setPen(QPen(ThemeColor.PRIMARY.color(), 4))
            for t, y in zip(time, data):
                x = self.transformer.time_to_x(t)
                y = self.transformer.value_to_y(y)
                painter.drawPoint(x, y)

        painter.setClipping(False)

        if pixels_per_sample > threshold:
            # painter.setPen(QPen(ThemeColor.PRIMARY.color(), 4))
            painter.setPen(QPen(wave_color, 4))
            # painter.setPen(QPen(ThemeColor.DARK_1.color(), 4))
            for t, y in zip(time, data):
                x = self.transformer.time_to_x(t)
                y = self.transformer.value_to_y(y)
                x = max(self.widget.left_margin, min(x, self.widget.width() - self.widget.right_margin))
                y = max(self.widget.top_margin, min(y, self.widget.height() - self.widget.bottom_margin))
                painter.drawPoint(x, y)

        painter.setClipping(False)

class FontSizeCalculator:
    @staticmethod
    def calculate_font_size(painter, labels, max_width, is_horizontal=True, start_size=6, bold=False):
        font = QFont('Arial', start_size)
        font.setStyleStrategy(QFont.PreferAntialias)
        font.setBold(bold)
        
        while font.pointSize() > 4:
            painter.setFont(font)
            metrics = painter.fontMetrics()
            
            if is_horizontal:
                widths = [metrics.width(label) for label in labels]
                if sum(widths) <= max_width:
                    break
            else:
                if max(metrics.width(label) for label in labels) <= max_width:
                    break
            
            font.setPointSize(font.pointSize() - 1)
        
        return font