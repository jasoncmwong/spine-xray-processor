from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

FONT_SIZE = 12


class QScrollBox(QScrollArea):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWidgetResizable(True)

        widget = QWidget(self)
        self.setWidget(widget)

        self.label = QLabel(widget)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setWordWrap(True)
        self.label.setFont(QFont('Courier', FONT_SIZE))

        self.text = ''

        scroll_bar = self.verticalScrollBar()
        scroll_bar.rangeChanged.connect(lambda: scroll_bar.setValue(scroll_bar.maximum()))

        layout = QVBoxLayout(widget)
        layout.addWidget(self.label)

    def add_msg(self, msg):
        # Update label with new message
        self.text += msg + '\n'
        self.label.setText(self.text)
