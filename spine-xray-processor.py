import sys
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QFileDialog, QGridLayout, QComboBox
from PyQt5.QtGui import QPixmap
import os
from XrayPixmap import XrayPixmap
from PyQt5.QtCore import QThread, Qt
import numpy as np
import imageio
from PIL import Image
from PIL.ImageQt import ImageQt
from Workers import SingleWorker, BatchWorker
from QScrollBox import QScrollBox

VERSION = '0.1.0'
VAL_IMG_EXT = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
EXT_STR = '*' + ' *'.join(VAL_IMG_EXT)
MODES = {0: 'spinal column', 1: 'vertebral body', 2: 'pedicles'}


# Create folder for storing outputs if non-existent
if not os.path.exists('spine-xray-processor-outputs'):
    os.mkdir('spine-xray-processor-outputs')


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.status_bar = None
        self.load_action = None
        self.batch_action = None
        self.msg_display = None
        self.central_widget = QWidget()

        self.thread = None
        self.worker = None

        self.img_display = None
        self.proc_display = None
        self.proc_select = None
        self.img = None
        self.name = None
        self.proc_img = None

        self.init_ui()

    def init_ui(self):
        """
        Initializes the user interface with menu toolbars, window parameters, and a grid layout.
        """
        self.setWindowTitle('Spine X-ray Processor v' + VERSION)
        self.setGeometry(0, 0, 1280, 720)
        self.setCentralWidget(self.central_widget)
        self.setStyleSheet('background-color: #1e1d23')

        # Set up status bar and menu bar
        self.statusBar()
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet('background-color: #ffffff')
        file_menu = menu_bar.addMenu('File')
        self.load_action = QAction('Load image', self)
        self.load_action.setShortcut('Ctrl+O')
        self.load_action.setStatusTip('Load an image for processing')
        self.load_action.triggered.connect(self.file_load)
        file_menu.addAction(self.load_action)
        self.batch_action = QAction('Batch process', self)
        self.batch_action.setShortcut('Ctrl+B')
        self.batch_action.setStatusTip('Select a folder to process a batch of x-rays')
        self.batch_action.triggered.connect(self.batch_meas)
        file_menu.addAction(self.batch_action)

        # Set up grid layout
        grid = QGridLayout(self.central_widget)
        for i, j in enumerate([5, 365, 100, 365, 160, 5]):
            grid.setRowStretch(i, j)
        for i, j in enumerate([5, 395, 200, 395, 5]):
            grid.setColumnStretch(i, j)

        # Place components into the grid
        self.img_display = XrayPixmap()
        self.img_display.setStyleSheet('background-color: #525252')
        grid.addWidget(self.img_display, 1, 1, 3, 1)

        self.proc_select = QComboBox()
        self.proc_select.addItems(['Spinal column', 'Vertebral body', 'Pedicles'])
        self.proc_select.setStyleSheet('background-color: #a9b7c6')
        grid.addWidget(self.proc_select, 2, 2, 1, 1)

        self.proc_display = XrayPixmap()
        self.proc_display.setStyleSheet('background-color: #525252')
        grid.addWidget(self.proc_display, 1, 3, 3, 1)

        self.msg_display = QScrollBox(self)
        self.msg_display.setStyleSheet('background-color: #ffffff')
        grid.addWidget(self.msg_display, 4, 1, 1, 3)

        self.setLayout(grid)
        self.showMaximized()

        self.msg_display.add_msg('spine-xray-processor successfully started')

    def file_load(self):
        """
        Trigger function for file menu -> load image. Opens a file dialog to load an image for measurement.
        Updates 'img' class variable.
        """
        file_name = QFileDialog.getOpenFileName(self, 'Load image', os.getcwd(), 'Image files (' + EXT_STR + ')')[0]
        if not file_name:
            self.msg_display.add_msg('Load failed')
            return
        self.img = np.asarray(Image.open(file_name))
        self.img = self.img if len(self.img.shape) == 2 else self.img[:, :, 0]
        self.name = file_name[file_name.rfind('/')+1:]
        self.load_img()

        # Set up thread and worker
        self.thread = QThread()
        self.worker = SingleWorker(self.img, self.proc_select.currentIndex())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.toggle_actions(False))
        self.thread.started.connect(self.worker.single_measure)
        self.thread.finished.connect(lambda: self.toggle_actions(True))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.proc_signal.connect(self.img_processed)
        self.worker.error.connect(lambda: self.msg_display.add_msg('Error encountered during processing - '
                                                                   'skipping ' + self.name + '({0}). Ensure that the '
                                                                   'correct mode is selected.'.format(MODES[self.proc_select.currentIndex()])))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)

        self.thread.start()

    def batch_meas(self):
        """
        Trigger function for file menu -> batch measure. Opens a file dialog to load a folder and process all suitable
        images.
        Updates {img_display, proc_display} class variables.
        """
        # Get file paths for measurement
        folder_name = QFileDialog.getExistingDirectory(self, 'Select folder', os.getcwd())
        if not folder_name:
            self.msg_display.add_msg('Load failed')
            return

        img_paths = [c for c in os.listdir(folder_name) if c[c.rfind('.'):] in EXT_STR]
        img_paths = [folder_name+'/'+c for c in img_paths]
        if len(img_paths) == 0:
            self.msg_display.add_msg('No valid images found')

        # Set up thread and worker
        self.thread = QThread()
        self.worker = BatchWorker(img_paths, self.proc_select.currentIndex())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.toggle_actions(False))
        self.thread.started.connect(self.worker.batch_measure)
        self.thread.finished.connect(lambda: self.toggle_actions(True))
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.load_signal.connect(self.load_img)
        self.worker.proc_signal.connect(self.img_processed)
        self.worker.error.connect(lambda: self.msg_display.add_msg('Error encountered during processing - '
                                                                   'skipping ' + self.name + '({0}). Ensure that the '
                                                                   'correct mode is selected.'.format(MODES[self.proc_select.currentIndex()])))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)

        # Run image processing in a separate thread
        self.thread.start()

    def img_processed(self, proc_xray):
        """
        Trigger function for when a radiograph is processed. Updates the processed display with the new image.
        Updates 'proc_display' variable.
        """
        self.proc_display.setPixmap(QPixmap.fromImage(ImageQt(Image.fromarray(proc_xray))))
        self.save_results(proc_xray)

    def load_img(self, img=None, name=None):
        """
        Updates the image displays with the loaded radiograph
        """
        if img is not None:
            self.img = img
            self.name = name
        self.img_display.setPixmap(QPixmap.fromImage(ImageQt(Image.fromarray(self.img))))

    def toggle_actions(self, is_enabled):
        """
        Trigger function for when a worker thread starts. Enables/disables the measurement actions for when a worker
        thread ends/starts.
        Updates {load_action, batch_action} variables.
        Args:
            is_enabled (bool): Flag indicating whether to enable or disable the measurement actions
        """
        self.load_action.setEnabled(is_enabled)
        self.batch_action.setEnabled(is_enabled)
        self.proc_select.setEnabled(is_enabled)

    def save_results(self, proc_xray):
        """
        Saves processed image in the 'spine-xray-processor-outputs' folder
        """
        imageio.imwrite('spine-xray-processor-outputs/' + self.name, proc_xray)

        # Display measurement results in message log
        self.msg_display.add_msg('Finished ' + self.name + ' ({0})'.format(MODES[self.proc_select.currentIndex()]))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
