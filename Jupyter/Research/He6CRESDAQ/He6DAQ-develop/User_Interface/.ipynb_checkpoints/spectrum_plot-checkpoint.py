#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 20 14:28:54 2019

@author: brent
"""

import matplotlib.pyplot as pp

def plotPacket(self, nyquist_freq = 2000.0, num_bins = 8192):
    """
    Acquire a single packet and make a line plot of the enclosed payload/data.
    
    ----------Parameters----------
    nyquist_freq (double): The peak power spectrum frequency, in MHz.
    num_bins (int): The number of frequency bins in a power spectrum.         
    """
    freq = [None] * num_bins # define numpy array for frequency bins
    for b in range(1,num_bins):
        freq[b] = nyquist_freq*b/num_bins # assign frequencies to bin numbers
    
    spectrum = portal.one_packet_payload() # get the data array/payload from one packet
    pp.figure(num=None, figsize=(12, 9), dpi=80, facecolor='w', edgecolor='k')
    pp.plot(freq, spectrum)
    pp.tick_params(axis='both', which='major', labelsize=20)
    pp.ylabel('Power', fontsize = 20)
    pp.xlabel('Frequency (MHz)', fontsize = 20)
    pp.title('Single packet data', fontsize = 20)
    pp.show()