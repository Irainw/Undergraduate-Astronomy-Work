#!/usr/bin/env python3

from numpy import savetxt
from .Device_Drivers.ROACH import ROACH
from .Fit_Cores import CoreFit

class SetupROACH:
    """
    Handles bootup and control of ROACH via low-rate PPC/CPU connection

    Interfaces with ROACH.py (class ROACH)  for bitcode programming and
    output port assignment

    Interfaces with Fit_Cores.py (class CoreFit) for ADC calibration fits
    """
    def __init__(self, dsoc_desc = ("0.0.0.0",4003), ADCs = 1, spec_avg = 2, FFT_ch = 8192):
        if (ADCs == 2):
            if(FFT_ch == 32768):
                self.driver=ROACH('He6CRES_roach', dsoc_desc,
                                  boffile = "he6_2adc_n32768_f150_a2_2021_Nov_09_2020.bof",
                                  ADC_cards = 2, do_cal = False)
            elif (FFT_ch == 8192):
                #self.driver=ROACH('He6CRES_roach', dsoc_desc,
                #                  boffile = "he6_2adc_n8192_f200_a2_2022_Feb_17_1332.bof",
                #                  ADC_cards = 2, do_cal = False)
                self.driver=ROACH('He6CRES_roach', dsoc_desc,
                                  boffile = "he6_2adc_n8192_f75_LEDs_2022_Mar_16_1535.bof",
                                  ADC_cards = 2, do_cal = False)
            elif (FFT_ch == 4096):
                self.driver=ROACH('He6CRES_roach', dsoc_desc,
                                  boffile = "he6_2adc_n4096_f200_a2_2022_Feb_15_1729.bof",
                                  ADC_cards = 2, do_cal = False)
        else:
            if(FFT_ch == 32768):
                self.driver=ROACH('He6CRES_roach', dsoc_desc,
                                  boffile = "he6_1adc_n32768_f150_a2_2021_Nov_09_1610.bof",
                                  ADC_cards = 1, do_cal = False)
            elif (FFT_ch == 4096):
                self.driver=ROACH('He6CRES_roach', dsoc_desc,
                                  boffile = "he6_1adc_n4096_f200_a2_2022_Feb_18_1442.bof",
                                  ADC_cards = 1, do_cal = False)

    def fit_ADC_OGP(self, name=None, rpt=1, zdok=0, sigFreq=100.0, sampFreq=2800.0):
        """
        Given an input signal in the form of a sine wave at a given frequency,
        gets a snapshot from 4 cores on the ADC card connected to a given zdok
        and fits the result for offset, gain, and phase parameters.
        Calls self.driver.adc_snap() for an interleaved data snapshot from 1 ADC
        Calls fit_cores.fit_snap() to do sine wave fitting

        ----------Parameters----------
        name(char_string): The name of the file into which the snapshot is
            written. 5 other files are written. "name.c1" .. "name.c4" contain
            the measurements from cores A, B, C, and D. Note that data is taken
            from cores in the order A, C, B, D.
            name defaults to if0 or if1, depending on zdok
        zdok(int): The number of the zdok connector corresponding to the ADC
             under test. Should be 0 or 1
        sigFreq(float): The frequency of the analog input signal, in MHz
        sampFreq(float): The ADC sampling frequency, in MHz

        ------------Outputs------------
        ogp (tuple): freq (MHz), followed by average zero offset (mV), amp.
        (as a percentage of full range), and delay (ps). Followed by zero point
        values for each core, as well as amp, phase devaitions from average for
        each core
        example: #155.00 MHz zero(mV) amp(%)  dly(ps)
                     #avg    -0.0182 37.8536 961.8898
                     core A   9.5117  0.6284  -2.5052
                     core B   9.4719  0.4009  -4.4980
                     core C  -9.5454 -0.0974   3.0043
                     core D  -9.5112 -0.9318   3.9989
        avg_pwr_sinad/rpt
        """
        if name == None:
            name = "if%d" % (zdok)
        avg_pwr_sinad = 0
        snap_name = 'snap_{0}_snapshot'.format(zdok)
        for i in range(rpt):
            snap = self.driver.adc_snap(zdok)
            if i == rpt-1:
                savetxt(name,snap,fmt='%d')
            fitter = CoreFit()
            ogp = fitter.fit_snap(snap, sigFreq, sampFreq, name)
            #avg_pwr_sinad += pwr_sinad
        return ogp
