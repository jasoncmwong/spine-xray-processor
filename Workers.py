from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
from PIL import Image
import itertools as it
import operator as op
import io
import skimage.exposure as skie

CROP_ROW = 100  # Ending row of sensitive information
DIV_RATIO = 8  # Ratio of image to reduce by to look for region of interest
HEAD_ROWS = 50  # Number of top rows to look for the head
CROP_WIDTH = 1000  # Desired width of region of interest from cropping


def sc_process(img):
    # Crop out sensitive info
    proc_img = Image.fromarray(img[CROP_ROW:, :])
    with io.BytesIO() as f:
        proc_img.save(f, format='jpeg')
        f.seek(0)
        proc_img = np.asarray(Image.open(f))

    # Narrow search area for the spinal column
    proc_img = proc_img[:, proc_img.shape[1] // DIV_RATIO:(proc_img.shape[1] * (DIV_RATIO - 1) // DIV_RATIO)]

    # Get the mean over the x-axis to look for the head
    x_proj = np.mean(proc_img[:HEAD_ROWS, :], axis=0)
    x_max = np.amax(x_proj)
    x_std = np.std(x_proj)
    x_ind = np.where(x_proj >= (x_max - 2 * x_std))[0]

    # Crop out regions far from the head
    for k, g in it.groupby(enumerate(x_ind), lambda l: l[0] - l[1]):
        crop_reg = list(map(op.itemgetter(1), g))
        if proc_img.shape[1] // 2 in crop_reg:
            break
    else:
        crop_reg = np.arange((proc_img.shape[1] - CROP_WIDTH) // 2, (proc_img.shape[1] + CROP_WIDTH) // 2)

    # Standardize width of the x-ray
    if len(crop_reg) > CROP_WIDTH:
        diff = len(crop_reg) - CROP_WIDTH
        crop_reg = crop_reg[diff // 2:]
        crop_reg = crop_reg[:CROP_WIDTH - len(crop_reg)]
    elif len(crop_reg) < CROP_WIDTH:
        diff = CROP_WIDTH - len(crop_reg)
        l_bound = crop_reg[0] - diff // 2
        r_bound = l_bound + CROP_WIDTH
        if l_bound < 0 and r_bound < proc_img.shape[1]:
            r_bound -= l_bound
            l_bound = 0
        elif l_bound >= 0 and r_bound >= proc_img.shape[1]:
            l_bound -= (r_bound - proc_img.shape[1] + 1)
            r_bound = proc_img.shape[1] - 1
        crop_reg = list(range(l_bound, r_bound))
    proc_xray = proc_img[:, crop_reg]

    # Performing contrast-limited adaptive histogram equalization
    proc_xray = skie.equalize_adapthist(proc_xray,
                                        nbins=256,
                                        kernel_size=(proc_xray.shape[0] // 8, proc_xray.shape[1] // 8),
                                        clip_limit=100 / 256)
    return skie.rescale_intensity(proc_xray, out_range=(0, 255)).astype(np.uint8)


def vb_process(img):
    return skie.rescale_intensity(skie.equalize_hist(img), out_range=(0, 255)).astype(np.uint8)


def ped_process(img):
    return skie.rescale_intensity(skie.equalize_adapthist(img), out_range=(0, 255)).astype(np.uint8)


class SingleWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal()
    proc_signal = pyqtSignal(np.ndarray)

    def __init__(self, img, mode):
        super().__init__()
        self.img = img
        self.mode = mode

    def single_measure(self):
        try:
            if self.mode == 0:
                self.proc_signal.emit(sc_process(self.img))
            elif self.mode == 1:
                self.proc_signal.emit(vb_process(self.img))
            else:
                self.proc_signal.emit(ped_process(self.img))
        except:
            self.error.emit()
        self.finished.emit()


class BatchWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal()
    load_signal = pyqtSignal(np.ndarray, str)
    proc_signal = pyqtSignal(np.ndarray)

    def __init__(self, img_paths, mode):
        super().__init__()
        self.img_paths = img_paths
        self.mode = mode

    def batch_measure(self):
        for path in self.img_paths:
            try:
                img = np.asarray(Image.open(path))
                img = img if len(img.shape) == 2 else img[:, :, 0]
                name = path[path.rfind('/')+1:]
                self.load_signal.emit(img, name)
                if self.mode == 0:
                    self.proc_signal.emit(sc_process(img))
                elif self.mode == 1:
                    self.proc_signal.emit(vb_process(img))
                else:
                    self.proc_signal.emit(ped_process(img))
            except:
                self.error.emit()
        self.finished.emit()
