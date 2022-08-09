from PyQt5.QtWidgets import QLabel, QFrame
from PyQt5.QtGui import QPixmap, QPainter, QPen, QTransform
from PyQt5.QtCore import Qt, QPoint


class XrayPixmap(QLabel):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.pixmap = None

    def setPixmap(self, img):
        self.pixmap = QPixmap(img)
        self.update()

    def paintEvent(self, event):
        if self.pixmap:
            painter = QPainter(self)
            scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatio, transformMode=Qt.SmoothTransformation)
            ctr_shift = QPoint((self.size().width()-scaled.width())/2, (self.size().height()-scaled.height())/2)
            painter.drawPixmap(ctr_shift, scaled)
