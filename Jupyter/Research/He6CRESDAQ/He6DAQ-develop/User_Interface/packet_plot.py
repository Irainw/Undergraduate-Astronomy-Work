#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 15:11:49 2018

@author: brent
"""
import matplotlib.pyplot as pp
import os

dr = os.path.dirname(os.path.abspath(__file__))

def readIntegers(pathToFile):

    with open(pathToFile) as f:
        a = [int(x) for x in f.read().split()]
    return a

def readFloats(pathToFile):

    with open(pathToFile) as f:
        a = [float(x) for x in f.read().split()]
    return a

#Plot 100 points of snapshots of raw data
#snapshot = readFloats("./Jan09/150MHz-20dBm_snap_fft_shift.txt")
#time = [None] * 262144
#for t in range (0, 100):
#    time[t] = t
#figure(num=None, figsize=(12, 9), dpi=80, facecolor='w', edgecolor='k')
#pp.plot(time, snapshot)
#pp.ylabel('Amplitude')
#pp.xlabel('Sample #')
#pp.suptitle('150 MHz -20 dBm 1 ADC 8-bit raw data')
#pp.show()
#
##Take periodogram of raw data, plot it
#f, Pxx_den = signal.periodogram(snapshot, 32e8)
#figure(num=None, figsize=(12, 9), dpi=80, facecolor='w', edgecolor='k')
#pp.semilogy(f, Pxx_den)
#pp.ylim([1e-10, 1e-2])
#pp.xlabel('frequency [Hz]')
#pp.ylabel('PSD [Hz^-1]')
#pp.suptitle('150 MHz -20 dBm power spectrum density')
#pp.show()

freq = [None] * 4096

for b in range(1,4096):
    freq[b] = 1600.0*b/4096.0

spectrum = readIntegers(dr + "/Jan08/175MHz-20dBm_spec.txt")
pp.figure(num=None, figsize=(12, 9), dpi=80, facecolor='w', edgecolor='k')
pp.plot(freq, spectrum)
pp.tick_params(axis='both', which='major', labelsize=20)
pp.ylabel('Magnitude', fontsize = 20)
pp.xlabel('Frequency (MHz)', fontsize = 20)
pp.title('175 MHz -20 dBm input signal (FFT Gain = $2^{-7}$)', fontsize = 20)
pp.show()

