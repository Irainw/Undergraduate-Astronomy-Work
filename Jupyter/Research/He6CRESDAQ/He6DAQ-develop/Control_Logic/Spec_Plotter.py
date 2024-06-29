#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import random
import matplotlib.pyplot as plt
from time import time
from Frequency_Domain_Packet import FDpacket


freq_bins = FDpacket.BYTES_IN_PAYLOAD  #Number of bins per FFT
freq = np.linspace(0.0,1600.0,freq_bins)

spectrum = np.zeros(freq_bins)
start = time()

plt.ion()
fig = plt.figure()

ax = fig.add_subplot(111)



with open('/home/brent/He6_Data/Fake_spec_random_2020-04-10-12-19-450.spec','rb') as bin_file:
    #num_bytes = getSize(bin_file)
    #print(num_bytes)
    #num_pkts = int(num_bytes/FDpacket.BYTES_IN_PACKET)
    for i in range(50):
        bin_file.seek(i*FDpacket.BYTES_IN_PACKET)
        b = bin_file.read(FDpacket.BYTES_IN_PACKET)
        pack = FDpacket()
        packet = pack.from_byte_string(b)
        spectrum = packet.interpret_data()
        fig.clear()
        plt.plot(freq, spectrum)
        plt.ylabel('Power (Arb. Units)')
        plt.xlabel('Frequency(MHz)')
        plt.title('Spectrum Faker spec output')
        plt.draw()
        plt.pause(0.05)

plt.ioff()
plt.show()

print('Total time: {:2.2f} seconds'.format(time()-start))
