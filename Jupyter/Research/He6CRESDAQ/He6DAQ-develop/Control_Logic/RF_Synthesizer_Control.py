#!/usr/bin/env python3

from time import sleep
from numpy.random import exponential
from .Device_Drivers.MiniCircuitsSSG6000RC import *

class SynthControl():

    def __init__(self):
        """
        Initialize a syntheziser object
        """
        self.driver = MCSSG()

    def monotone(self, frequency, power):
        """
        Output a constant frequency at a given power

        ----------Parameters----------
        frequency (float): Initial frequency of the event, in MHz
        power (float): The RF power to output, in dBm
        """
        err = self.driver.setFreq(frequency)
        err += self.driver.setPower(power)
        return err

    def sweep_repeater(self, f_start = 500.0, f_stop = 600.0,
                       dfdt = 0.005, power = -35.0,):
        """
        Generate a repeating freq. sweep with a given slope and constant power

        ----------Parameters----------
        f_start (float): Initial frequency of the event, in MHz
        f_stop (float): Final frequency of the event, in MHz
        dfdt (float): Frequency change per unit time (between jumps) in MHz/ms
        power (float): The RF power to output, in dBm
        """
        t_step = 60
         #Can't change output frequency in less than 20 ms
        f_step = t_step*dfdt

        self.driver.setupFreqSweep(f_start, f_stop, f_step, t_step, power)

    def fake_event(self, jumps, jump_magnitudes, start_freq=1000.0,
                   max_freq=2000.0, dfdt=0.005, power=-35.0, track_tau=25):
        """
        Generate a single decay-event-like spectrogram with tracks and jumps.
        Track lengths should fit exponential dist. Each track will be output
        with constant power and constant frequency change per unit time.

        ----------Parameters----------
        jumps (float[]): An array of floats corresponding to the jump
            frequency spans, in MHz
        jump_magnitudes(float[]): Array of floats with jump magnitudes, in MHz
        start_freq(float): The initial event frequency, in MHz
        max_freq(float): The maximum DAQ frequency, in MHz
        dfdt (float): Frequency change per unit time (between jumps) in MHz/ms
        power (float): The RF power to output (in dBm)
        track_tau (float): 1/e point of distribution used for obtaining
            track lengths, in ms
        """

        frequency = start_freq
        if (frequency >= max_freq):
            frequency = max_freq
        self.driver.setFreq(start_freq)
        self.driver.setPower(power)

        #Minicircuits SSG6000 has a 20 ms min dwell time
        t_step = 60
        #Frequency step size derived from time step and df/dt
        f_step = t_step*dfdt

        #exponential() returns array of track lengths t_n
        #distributed according to exp(-t_n/tau)"""
        tracks = exponential(track_tau, jumps+1)

        for i in range(len(jumps)+1):
            steps = tracks[i]/t_step
            for j in range(steps):
                frequency += f_step
                if (frequency >= max_freq):
                    frequency = max_freq
                self.model.setFreq(frequency)
                sleep(t_step/1000)
            frequency += jumps[i]
