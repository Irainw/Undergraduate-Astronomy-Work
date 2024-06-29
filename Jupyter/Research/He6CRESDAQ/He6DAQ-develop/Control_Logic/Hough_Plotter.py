#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import seaborn as sns
import random
import matplotlib.pyplot as plt
from time import time
from Frequency_Domain_Packet import FDpacket

spectra = 5000    # Number of horizontal slices on the time axis
f_max = 2000.0    # Nyquist frequency in MHz
threshold = 1     # Power threshold for making binary spectrogram
freq_bins = FDpacket.BYTES_IN_PAYLOAD  # Number of frequency bins per FFT

start = time()

data = np.zeros((spectra, freq_bins))   
spectrum = np.zeros(freq_bins)
packet = FDpacket()
with open('/mnt/sdb/data/Freq_data_2020-03-05-15-10-17_000009.spec','rb') as bin_file:
    num_bytes = bin_file.tell()  # Get the file size
    num_pkts = int(num_bytes/(FDpacket.BYTES_IN_PACKET))
    for i in range(num_pkts):
        bin_file.seek(i*FDpacket.BYTES_IN_PACKET)
        bytestr = bin_file.read(FDpacket.BYTES_IN_PACKET)
        packet = FDpacket.FromByteString(bytestr)
        data[i] = packet.FromByteString(bytestr)

#initialize an array of zeros to match size of the data array
waterfall = np.zeros((freq_bins, spectra)) 

for i in range(freq_bins):
    for j in range(spectra):  
        waterfall[freq_bins-1-i][j] = data[j][i]

plt.figure(figsize=(5,25))
ax = sns.heatmap(waterfall, cmap="Blues")
plt.ylabel('Frequency Channel')
plt.xlabel('Sample #')
plt.title('Spectrogram')
plt.show()

print('Total time: {:2.2f} seconds'.format(time()-start))

