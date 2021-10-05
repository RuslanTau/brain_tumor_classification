import os
import sys
import json
import glob
import random
import re
import collections
import time

import numpy as np
import pandas as pd
import pydicom
import cv2

import torch
from torch import nn
from torch.utils import data as torch_data
from sklearn import model_selection as sk_model_selection
from torch.nn import functional as torch_functional

from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score


def load_dicom_image(path, img_size: int = 256):
    dicom = pydicom.read_file(path)
    data = dicom.pixel_array
    if np.min(data) == np.max(data):
        data = np.zeros((img_size, img_size))
        return data

    data = cv2.resize(data, (img_size, img_size))
    return data


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def load_dicom_images_3d(data_directory, scan_id, num_imgs: int = 64, img_size: int = 256, mri_type="FLAIR", split="train"):
    files = natural_sort(glob.glob(f"{data_directory}/{split}/{scan_id}/{mri_type}/*.dcm"))

    every_nth = len(files) / num_imgs
    indexes = [min(int(round(i * every_nth)), len(files) - 1) for i in range(0, num_imgs)]

    files_to_load = [files[i] for i in indexes]

    img3d = np.stack([load_dicom_image(f) for f in files_to_load]).T

    img3d = img3d - np.min(img3d)
    if np.max(img3d) != 0:
        img3d = img3d / np.max(img3d)

    return np.expand_dims(img3d, 0)


class Dataset(torch_data.Dataset):
    def __init__(self, data_dir, paths, targets=None, mri_type=None, split="train"):
        self.data_dir = data_dir
        self.paths = paths
        self.targets = targets
        self.mri_type = mri_type
        self.split = split

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        scan_id = self.paths[index]
        if self.targets is None:
            data = load_dicom_images_3d(self.data_dir,
                                        str(scan_id).zfill(5),
                                        mri_type=self.mri_type[index],
                                        split=self.split)
        else:
            data = load_dicom_images_3d(self.data_dir,
                                        str(scan_id).zfill(5),
                                        mri_type=self.mri_type[index],
                                        split="train")

        if self.targets is None:
            return {"X": data, "id": scan_id}
        else:
            return {"X": data, "y": torch.tensor(self.targets[index], dtype=torch.float)}