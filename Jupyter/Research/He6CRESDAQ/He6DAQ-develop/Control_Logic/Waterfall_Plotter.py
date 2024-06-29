#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 14:46:13 2019

@author: brent
"""

import numpy as np
import h5py
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import cm
from skimage.transform import hough_line, hough_line_peaks


hf = h5py.File('355MHz-25dBm.egg', 'r')
data = hf.get('/streams/stream0/acquisitions/0')
data = np.array(data)
hf.close()

f_max = 1600.0  # MHz
freq_bins = 4096     # Number of frequency bins per FFT
spectra = 1152   # Number of horizontal slices on the time axis
threshold = 100

waterfall = np.zeros((freq_bins, spectra))

for i in range(freq_bins):
    for j in range(spectra):  
        if data[j][i] >= threshold:
            waterfall[freq_bins-1-i][j] = 1.0
        else:
            waterfall[freq_bins-1-i][j] = 0.0

tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 360)
h, theta, d = hough_line(waterfall, theta=tested_angles)

#plt.figure(figsize=(10,25))
#ax = sns.heatmap(waterfall, cmap="Blues")
#plt.ylabel('Frequency Channel')
#plt.xlabel('Sample #')
#plt.suptitle('')
#plt.show()

fig, axes = plt.subplots(1, 3, figsize=(12, 6))
ax = axes.ravel()

ax[0].imshow(waterfall, cmap=cm.gray)
ax[0].set_title('Input image')
ax[0].set_axis_off()

ax[1].imshow(np.log(1 + h),
             extent=[np.rad2deg(theta[-1]), np.rad2deg(theta[0]), d[-1], d[0]],
             cmap=cm.gray, aspect=1/1.5)
ax[1].set_title('Hough transform')
ax[1].set_xlabel('Angles (degrees)')
ax[1].set_ylabel('Distance (pixels)')
ax[1].axis('image')

ax[2].imshow(waterfall, cmap=cm.gray)
origin = np.array((0, waterfall.shape[1]))
for _, angle, dist in zip(*hough_line_peaks(h, theta, d)):
    y0, y1 = (dist - origin * np.cos(angle)) / np.sin(angle)
    ax[2].plot(origin, (y0, y1), '-r')
ax[2].set_xlim(origin)
ax[2].set_ylim((waterfall.shape[0], 0))
ax[2].set_axis_off()
ax[2].set_title('Detected lines')

#plt.tight_layout()
plt.show()