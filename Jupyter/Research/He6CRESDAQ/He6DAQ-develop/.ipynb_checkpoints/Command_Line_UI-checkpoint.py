#!/usr/bin/env python3

import yaml
import os
import subprocess
from subprocess import check_output
import socket
from time import time
from time import sleep
from datetime import datetime
from math import sqrt
import typing
from typing import List
import pandas as pd
from struct import unpack
from threading import Thread
import multiprocessing
from numpy import (
    uint8,
    uint32,
    uint64,
    array,
    average,
    std,
    copy,
    zeros,
    linspace,
    fromfile,
    packbits,
)

# from multiprocessing import Process
from numpy.random import seed, randint, uniform, normal, poisson, exponential
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.pyplot import figure, plot, tick_params, xlabel, ylabel, title, show

dr = os.path.dirname(os.path.abspath(__file__))
from Control_Logic.RF_Synthesizer_Control import SynthControl
from Control_Logic.DAQ_Setup import SetupROACH
from Control_Logic.Frequency_Domain_DAQ_Control import DAQ_SpecWriter
from Control_Logic.Frequency_Domain_Packet import FDpacket
from Control_Logic.Trap_Control import TrapControl
from Control_Logic.Env_Parameters import EnvParams
from Control_Logic.Spec_Packet_Report import packet_report, delete_files, delete_run_ids
import Control_Logic.PostgreSQL_Interface as he6db
import Control_Logic.Data_Quality_Control as DQC

from telnetlib import Telnet
from time import sleep


class LiveDAQ:
    """
    The top-level DAQ command-line interface.

    Interfaces with Frequency_Domain_DAQ_Control.ROACH for bootup and control of
    ROACH via low-rate PPC/CPU connection

    Interfaces with Frequency_Domain_DAQ_Control.FDPreceiver for receiving
    high-rate freq.domain data

    Interfaces with MiniCircuitsSSG6000RC for providing calibration signals to
    the ROACH ADCs at known power and frequency

    Interfaces with Trap_Driver for controlling the trap.
    """

    def __init__(
        self,
        roach_avg=2,
        analog_inputs=1,
        freq_ch=32768,
        roach_nyquist=1.2e9,
        requant_gain=20,
        socket=("0.0.0.0", 4003),
        boot_roach = True
    ):

        self.roach_avg = roach_avg
        self.analog_inputs = analog_inputs
        self.roach_nyquist = roach_nyquist
        self.freq_ch = freq_ch
        self.socket = socket
        self.requant_gain = requant_gain

        # Feed the above settings to EnvParams()
        self.params = EnvParams(
            roach_avg, analog_inputs, freq_ch, roach_nyquist, requant_gain
        )
        self.setup = False

        if self.freq_ch == 4096:
            self.BUFFERSIZE = 4128
            self.packets_per_slice = 1
        elif self.freq_ch == 32768:
            self.BUFFERSIZE = 8224
            self.packets_per_slice = 4
        else:
            raise ValueError(
                "freq_ch must currently be 4096 or 32768. You input {}.".format(
                    self.freq_ch
                )
            )
        if boot_roach: 
            self.setup_roach()

    def setup_roach(self):

        self.roach = SetupROACH(
            dsoc_desc=self.socket,
            ADCs=self.analog_inputs,
            spec_avg=self.roach_avg,
            FFT_ch=self.freq_ch,
        )
        # Set requant_gain:
        self.roach.driver.set_requant_gain(self.requant_gain)
        self.setup = True

        return None

    def take_FD_data(
        self,
        acq_size=1,
        acq_length_ms=1000,
        isotope=None,
        set_field=None,
        rf_side=None,
        run_notes=None,
        write_to_db=True,
        no_report=False,
        delete_imperfect_files=True,
    ):
        """
        Takes packets off of the high-rate data interface used to transmit power
        spectra from the ROACH, saves packets to binary (*.spec) files.
        Reference for fast writing of UDP packets:
        https://iopscience.iop.org/article/10.1088/1748-0221/15/09/T09005

        ----------Parameters----------
        acq (int): The number of files to save
        time (int): The length of the datastream written to each .spec file, in milliseconds
        isotope (str): Put either '19Ne', '6He', or '83Kr'.
        rf_side (bool): 0 = U side, 1 = I side.
        """
        if not self.setup:
            raise ValueError(
                "Must set up roach by calling CLI.roach_setup() before taking FD data."
            )

        time_per_slice_ms = 1000 * self.roach_avg * self.freq_ch / self.roach_nyquist

        packets_per_acq = int(
            self.packets_per_slice * acq_length_ms / time_per_slice_ms
        )

        # Set relevant enviornmental parameters.
        self.params.isotope = isotope
        self.params.set_field = set_field
        self.params.run_notes = run_notes
        self.params.acq_length_ms = acq_length_ms
        self.params.rf_side = rf_side

        if write_to_db:
            env_parameters = self.params.get()

            print("\nenv_parameters: \n")
            for key, value in env_parameters.items():
                print("{}: {}".format(key, value))
            print("\n")

        total_spec_file_list = []
        chunk_size = acq_size
        acquired = 0
        while acquired < acq_size:

            # Take data in chuncks of 10 files.
            udprx_out = []
            for i in range(chunk_size):
                print("\nReceiver active for file_in_acq: {}".format(acquired + i))

                process = subprocess.run(
                    [
                        "./UDP_receiver/build/udprx",
                        "{}".format(self.BUFFERSIZE),
                        "{}".format(packets_per_acq),
                        "{}".format(i % 3),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                udprx_out.append(process.stdout.decode("utf-8"))
                print("udprx_out: ", process.stdout.decode("utf-8"))  # Print file path.
                if process.stderr is not None:
                    # Print errors.
                    print("udprx errors: ", process.stderr.decode("utf-8"))

            spec_file_list = he6db.format_udprx_output(udprx_out)

            # Construct packet report and add to he6cres_db
            spec_file_list = packet_report(
                spec_file_list, self.BUFFERSIZE, no_report, delete_imperfect_files
            )

            if delete_imperfect_files:

                # Collect files to be deleted:
                files_to_delete = [
                    spec_dict["file_path"]
                    for spec_dict in spec_file_list
                    if spec_dict["num_dropped_packets"] > 0
                ]

                # Delete those files:
                delete_files(files_to_delete)
                acquired+= chunk_size - len(files_to_delete)
                chunk_size = acq_size - acquired

                # Keep only the perfect files in the spec_file_list
                spec_file_list = [spec_dict for spec_dict in spec_file_list
                    if spec_dict["num_dropped_packets"] == 0 
                ]

            else: 
                acquired += chunk_size

            total_spec_file_list += spec_file_list

        if write_to_db:
            # Fill the he6cres_db tables with this info.
            he6db.fill_he6cres_db(env_parameters, total_spec_file_list)


        return None

    def db_query(self, query: str) -> typing.Union[None, pd.DataFrame]:
        """document"""
        query_result = he6cres_db_query(query)

        return query_result

    def calibrate_adc_cores(
        self,
        card=0,
        f_sample=2400,
        fit_f_min=137,
        fit_f_max=1110,
        fit_num=5,
        set_ADC_OGP_regs=True,
        file_print=True,
    ):
        """
        Instantiate an obejct of type SynthControl(), output tones at a variety
        of frequencies, call self.daq.fit_ADC_OGP() for offset, gain, and
        phase fit information for each ADC card at each successive frequency.
        After fitting ADC OGP parameters at each frequency, average parameters
        across frequencies for each ADC card and write outputs to ROACH software
        registers

        ----------Parameters----------
        card(int): Number indicating which ADC card is to be calibrated (0 or 1)
        f_sample (int): ADC sampling frequecy, in MHz
        fit_f_min (int): Min. freq. to output for ADC OGP fitting, in MHz
        fit_f_max (int): Max. freq. to output for ADC OGP fitting, in MHz
        fit_num (int): The number of different frequencies at which OGP
                         fits will be performned
        setADC_regs (bool): If TRUE, sets ADC offset, gain, and phase registers
                            after each iteration of fitting loop. Set to FALSE
                            if only signal power info and SINAD info are desired
        """
        self.synth = SynthControl()
        self.OGP_fit = zeros((15), dtype=float)
        self.OGP = zeros((15), dtype=float)
        self.OGP_sum = zeros((15), dtype=float)
        self.tn = Telnet()

        """
        Harvard-Smithsonian paper (DOI: 10.1142/S2251171714500019)
        says the frequency values in the fitting interval should be chosen to
        have an even number of cycles in the time needed to capture a snapshot.
        Our snapshots are 65536 samples in length
        """
        snapshotTime = 1.0e6 * 65536 / f_sample  # snapshot length *in picoseconds*
        if fit_num > 2:
            delta_f = (fit_f_max - fit_f_min) / (fit_num - 2)
        else:
            delta_f = 0

        if set_ADC_OGP_regs == True:
            self.roach.driver.set_spi_OGP(card, self.OGP)  # start w/ regs set to 0
        for i in range(fit_num):

            """
            tweak the frequency of the signal input to the ROACH so that there
            are an even integer number of periods in the 65536-sample snapshot
            """
            if i <= 1:
                f_0 = fit_f_min  # repeat freq once with initial fits
            else:
                f_0 = fit_f_min + ((i - 1) * delta_f)  # signal freq
            f_0_period = 1.0e6 / f_0  # period *in picoseconds*
            f_0_cycles = snapshotTime / f_0_period  # non-integer number of periods
            remainder = f_0_cycles % 2.0
            dt = remainder * f_0_period  # ps for even number of periods
            f_cycles = f_0_cycles - remainder
            fit_freq = 1.0e6 * f_cycles / (snapshotTime - dt)

            # synth_set = self.synth.monotone(fit_freq, power = 0.0)
            """
            synth control via python socket library and HTTP isn't working for
            reasons unknown, controlling for now via the Telnet interface
            """
            msg = "SET/FREQ:{0}\r\n\r\n".format(fit_freq)
            with Telnet("10.66.192.34", 23) as tn:
                tn.write(str.encode(msg))
                sleep(1)  # turns out Telnet is really $%#!@# slow

            """
            the actual fitting is handled by the DaqControl class in
            Frequency_Domain_DAQ_Control through the CoreFit class in Fit_Cores
            """
            self.OGP_fit = self.roach.fit_ADC_OGP(
                name=None, rpt=1, zdok=card, sigFreq=fit_freq, sampFreq=f_sample
            )
            for j in range(15):
                self.OGP[j] += self.OGP_fit[j] / (1 + i / 2.0)
            if set_ADC_OGP_regs == True:
                self.roach.driver.set_spi_OGP(card, self.OGP)

    def trap_const_curr(self, curr: float, max_volt: float = 10) -> None:
        """
        Calls the const_curr method of the controller.
        """

        # First kill the slewing thread if it's already alive.
        if self.params.slewing is not None:
            if self.params.slewing.is_alive():
                print(
                    "Current slew thread is_alive() :", self.params.slewing.is_alive()
                )
                print("Teriminating slew thread.")
                self.params.slewing.terminate()
                self.params.slewing.join()
                print(
                    "Current slew thread is_alive() :", self.params.slewing.is_alive()
                )
                self.params.slewing.close()  # testing - WD 8/8/22
                self.params.slewing = None

        self.trap = TrapControl()

        if self.trap.driver.connected:

            self.trap.const_curr(curr, max_volt)
            self.params.trap_config = "const, curr: {}".format(curr)
        else:
            self.params.trap_config = "Not connected to Kepco."


        return None

    def trap_slew(
        self,
        curr_list: List[float] = [0.5, 0.0],
        dwell_list: List[float] = [0.1, 0.1],
        duration: float = 43200,
    ) -> None:
        """
        Calls the const_curr method of the controller. The default duration is 12 hrs. 
        This is to ensure the trap doesn't turn off during data taking. 
        """

        # First kill the slewing thread if it's already alive.
        if self.params.slewing is not None:
            print(self.params.slewing)
            if self.params.slewing.is_alive():
                print(
                    "Current slew thread is_alive() :", self.params.slewing.is_alive()
                )
                print("Teriminating slew thread.")
                self.params.slewing.terminate()
                self.params.slewing.join()
                print(
                    "Current slew thread is_alive() :", self.params.slewing.is_alive()
                )
                self.params.slewing.close()  # testing - WD 8/8/22
                self.params.slewing = None

        # Check to see if a trap slewing thread is alive, and if so, kill it.
        self.trap = TrapControl()

        if self.trap.driver.connected:

            self.params.slewing = multiprocessing.Process(
                target=self.trap.slew, args=(duration, curr_list, dwell_list)
            )
            self.params.slewing.start()
            self.params.trap_config = "slew, curr_list: {}, dwell_list: {}".format(
                curr_list, dwell_list
            )
        else:
            self.params.trap_config = "Not connected to Kepco."

        print(self.params.trap_config)

        return None

    def look_at_spec_file(
        self,
        run_id,
        file_in_acq=0,
        slices=1000,
        sparse_spec=True,
        noise_floor=True,
        snr_cut=5,
        start_packet=0,
    ):

        DQC.look_at_spec_file(
            run_id, file_in_acq, slices, sparse_spec, noise_floor, snr_cut, start_packet
        )

        return None

    def delete_run_ids(self, run_id_list): 

        delete_run_ids(run_id_list)

    def peak_find(self, avg=10):
        """
        the network interface card seems to buffer a few hundred packets worth
        of data--workaround is to pull 300 packets off the NIC and discard
        """
        peak_vals = zeros(avg)
        peak_bins = zeros(avg)
        for n in range(avg):
            buffer_packets = self.daq.receiver.grab_packets(n=300)

            test_packet = self.daq.receiver.grab_packets(n=1)

            data = self.daq.receiver.one_packet_payload()

            for freq_bin in range(len(data)):
                if data[freq_bin] > peak_vals[n]:
                    peak_vals[n] = data[freq_bin]
                    peak_bins[n] = freq_bin
            print(f"Peak val = {peak_vals[n]:4.1f} || Bin# {peak_bins[n]:5.1f}")
        peak_val_avg = average(peak_vals)
        peak_val_err = std(peak_vals) / sqrt(avg)
        peak_bin_avg = average(peak_bins)
        peak_bin_err = std(peak_bins) / sqrt(avg)
        print(f"Peak val = {peak_val_avg:4.1f} +/- {peak_val_err:4.2f}")
        print(f"Peak Bin = {peak_bin_avg:5.1f} +/- {peak_bin_err:4.2f}\n")

    def check_packet_continuity(self, input_file, packets):
        gaps = -1
        data_gaps = []
        with open(input_file, "rb") as infile:
            for n in range(packets):
                bytestr = infile.read(FDpacket.BYTES_IN_PACKET)
                packet = FDpacket.from_byte_string(bytestr)
                if n == 0:
                    prevPktNum = packet.pkt_in_batch - 1
                if packet.pkt_in_batch - prevPktNum != 1:
                    gaps += 1
                    data_gaps.append(n)
                prevPktNum = packet.pkt_in_batch
            print(f"Number of packet gaps = {gaps}")
            print(data_gaps)

    def list_packet_numbers(self, input_file, packets):
        with open(input_file, "rb") as infile:
            for n in range(packets):
                bytestr = infile.read(FDpacket.BYTES_IN_PACKET)
                packet = FDpacket.from_byte_string(bytestr)
                print(packet.pkt_in_batch)

    def list_packet_number_bits(self, input_file, packets):
        with open(input_file, "rb") as infile:
            for n in range(packets):
                bytestr = infile.read(FDpacket.BYTES_IN_PACKET)
                hdr = unpack(
                    ">{0}Q".format(FDpacket.BYTES_IN_HEADER // 8),
                    bytestr[: FDpacket.BYTES_IN_HEADER],
                )
                pktnum = uint32((hdr[0] >> uint32(32)) & 0xFFFFF)
                print(str(pktnum))


"""
    def plot_data(self, acq):

        freq = linspace(0.0, 2000.0, FDpacket.BYTES_IN_PAYLOAD)

        while(remaining_plots > 0 ):
            if(self.daq.output_file != prev_outfile):
                with open(self.daq.output_file, "rb") as binary_file:
                    bytestr = bin_file.read(FDpacket.BYTES_IN_PACKET)
                    packet = FDpacket.from_byte_string(bytestr)
                    spectrum = packet.interpret_data()
                    figure(num=None, figsize=(12, 9), dpi=80,
                           facecolor='w', edgecolor='k')
                    plot(freq, spectrum)
                    tick_params(axis='both', which='major', labelsize=20)
                    ylabel('Magnitude', fontsize = 20)
                    xlabel('Frequency (MHz)', fontsize = 20)
                    title('Spectrum', fontsize = 20)
                    show()
                prev_outfile = self.daq.output_file
            remaining_plots = remaining_plots - 1

    def display_data_stream(self, acquisitions, acq_length):
        start = time()
        acq = Process(target = self.take_data, args=(acquisitions, acq_length))
        plotter = Process(target = self.plot_data, args=(acquisitions))
        acq.start()
        plotter.start()
        acq.join()
        plotter.join()
"""


class FakeEventSet:

    """
    Generate a set of decay-event-like spectrograms with:
        1) given number of events
        2) range of frequency slopes,
        3) constant power per event (power chosen from flat dist.)
        4) Gaussian-distributed set of initial frequencies
        5) Poisson-distributed # of jumps
        6) exponentially-distributed jump size (with upper cutoff)
        7) exponentially-distributed track length

    creates an object containing lists of start freq, dfdt, power,
    and number of jumps for each event, as well as a list of all
    jump magnitudes in frequency space.

    ----------Attributes----------
    config_file (string): File to get experimental configuration from
    log_outfile (string): File to write event data to
    events (int): The number of events to generate
    dfdt_min (float): Min freq. change per unit time (MHz/ms)
    dfdt_max (float): Max freq. change per unit time (MHz/ms)
    power_min (float): Min RF power to output (in dBm)
    power_max (float): Max RF power to output (in dBm)
    avg_f_start (float): The center of the initial frequency dist.
    sigma_f_start (float): The width of the initial frequeny dist.
    lambda_j (int): The modal Poisson dist. of jumps per event
    jump_tau (float): Width of the exponential dist. of jumps in MHz
    track_tau (float): Distribution parameter passed to fake_event()
    """

    def read_config_file(self):
        with open(self.config_file, "r") as f:
            e = yaml.load(f, Loader=yaml.BaseLoader)
        self.noise = e["Experiment"]["noise_power_density(dBm/Hz)"]
        self.events = int(e["Spectrum"]["events"])
        self.dfdt_min = float(e["Spectrum"]["dfdt_min(MHz/ms)"])
        self.dfdt_max = float(e["Spectrum"]["dfdt_max(MHz/ms)"])
        self.power_min = float(e["Spectrum"]["power_min(dBm)"])
        self.power_max = float(e["Spectrum"]["power_max(dBm)"])
        self.avg_f_start = float(e["Spectrum"]["center_freq(MHz)"])
        self.sigma_f_start = float(e["Spectrum"]["freq_width(MHz)"])
        self.lambda_j = float(e["Spectrum"]["peak_jumps_per_event"])
        self.jump_tau = float(e["Spectrum"]["jump_1/e(MHz)"])
        self.track_tau = float(e["Spectrum"]["track_1/e(ms)"])
        self.max_freq = float(e["Spectrum"]["max_freq(MHz)"])
        self.log_name = e["Experiment"]["name"]
        self.log_date = "{:%Y-%m-%d-%H-%M-%S}".format(datetime.now())

        outfile = dr + "/Log_Files/" + self.log_name + self.log_date + ".yaml"

        with open(outfile, "w") as f:
            f.write(yaml.dump(e, default_flow_style=False))

    def __init__(
        self,
        config=dr + "/Config_Files/SpectrumFaker_config.yaml",
        log_output=dr + "/Log_Files/OUTFILE_NAME_UNSPECIFIED.txt",
    ):

        # Set default values for parameters
        self.events = 10
        self.dfdt_min = 0.001
        self.dfdt_max = 0.005
        self.power_min = -45.0
        self.power_max = -20.0
        self.avg_f_start = 1000.0
        self.sigma_f_start = 100.0
        self.lambda_j = 2
        self.jump_tau = 150
        self.track_tau = 25
        self.max_freq = 2000.0

        self.config_file = config
        self.log_outfile = log_output
        self.read_config_file()

        # get a set of initial freq. by drawing samples from a Gaussian dist.
        self.start_freqs = normal(self.avg_f_start, self.sigma_f_start, self.events)

        # get array of freq/time slopes for all events
        self.dfdt = uniform(self.dfdt_min, self.dfdt_max, self.events)

        # get array of powers for all events
        self.power = uniform(self.power_min, self.power_max, self.events)

        # get number of jumps for set of all events from a Poisson dist
        self.n_jumps_per_event = poisson(self.lambda_j, self.events)

        # add up jumps across event set; get array of magnitudes for all jumps
        total_jumps = 0
        for x in range(self.events):
            total_jumps += self.n_jumps_per_event[x]
        self.jump_mags = exponential(self.jump_tau, total_jumps)

        # get array of magnitudes for all tracks
        total_tracks = total_jumps + self.events
        self.track_lengths = exponential(self.track_tau, total_tracks)

        tracknum = 0
        self.event_times = zeros(self.events)
        for y in range(self.events):
            for z in range(1 + self.n_jumps_per_event[y]):
                self.event_times[y] += self.track_lengths[tracknum]
                tracknum += 1

        # write output file w/ start freq, dfdt, power, #of jumps for ea. event
        outfile = dr + "/Log_Files/" + self.log_name + self.log_date + ".csv"

        with open(outfile, "a") as f:
            f.write(
                "{:15}{:15}{:15}{:15}{:15}\n".format(
                    "     Freq(MHz),",
                    "  dfdt(MHz/ms),",
                    "    Power(dBm),",
                    "      Time(ms),",
                    "          Jumps",
                )
            )
            for k in range(self.events):
                # first column is 14 characters wide w 5 digits,
                # second is 14 chars wide w/ 4 digits, etc.
                # note data column width is less than header column
                # width b/c commas are added between data samples
                f.write(
                    "{:14.5},{:14.4},{:14.3},{:14.3},{:14d}\n".format(
                        self.start_freqs[k],
                        self.dfdt[k],
                        self.power[k],
                        self.event_times[k],
                        self.n_jumps_per_event[k],
                    )
                )


class SynthEventTransmitter:
    def __init__(self):
        self.synth = SynthControl()

    def output_to_synth(self, set):
        """
        executes a set of events one by one, passing start freq, dfdt, power,
        number of jumps, and slice of jump size array to SynthControl.fake_event

        ----------Parameters----------
        set (FakeEventSet): an object containing lists of start freq, dfdt,
        power, and number of jumps for each event, as well as a list of all
        jump magnitudes in frequency space.
        """

        jump_count = 0
        for i in range(set.events):
            self.synth.fake_event(
                set.n_jumps_per_event[i],
                set.jump_mags[jump_count : jump_count + set.n_jumps_per_event[i]],
                set.start_freqs[i],
                set.dfdt[i],
                set.power[i],
                track_tau=set.track_tau,
            )

            jump_count += set.n_jumps_per_event[i]


class SpecFileEventWriter:
    """
    writes a set of events to spec file on top of
    background generated by bootstrapping/sample-and-replacement method.

    ----------Parameters----------
    set (FakeEventSet): an object containing lists of start freq, dfdt,
    power, and number of jumps for each event, as well as a list of all
    jump magnitudes in frequency space.
    """

    def __init__(
        self, set, bkgd_file, spectra=5000, spec_bins=32768, FFT_avg=2, f_Ny=1200
    ):
        self.background_file = dr + "/Bootstrap_Data_Input/" + bkgd_file
        self.spectra = spectra  # number of spectra to be written to output .spec file
        self.bins = spec_bins  # bins per spectrum
        self.max_freq = f_Ny  # Nyquist frequency in MHz
        self.spec_time = spec_bins * FFT_avg / (1000000 * f_Ny)

    def output_to_spec(self, set):

        # select 100 spectra to serve as bootstrapped background set
        background = zeros((100, self.bins), dtype=uint8)  # allocate bkgd memory
        bkgdSpec = zeros(self.bins, dtype=uint8)  # dummy array for 4-packet spectra

        with open(
            self.background_file, "rb"
        ) as in_file:  # Pass "rb" to read a binary file
            b = in_file.read(FDpacket.BYTES_IN_PACKET)
            packet = FDpacket.from_byte_string(b)

            # determine which chunk of spectrum the packet corresponds to
            chunk = uint8(packet._reserved_1 >> uint64(56) & uint64(0xF0)) / 32

            # read extra packets worth of data to advance read pointer
            # to a packet that contains DC freq bin before filling bkgd array
            if chunk == 0.0:
                in_file.read(3 * FDpacket.BYTES_IN_PACKET)
            if chunk == 1.0:
                in_file.read(2 * FDpacket.BYTES_IN_PACKET)
            if chunk == 2.0:
                in_file.read(1 * FDpacket.BYTES_IN_PACKET)

            for i in range(100):
                for j in range(4):
                    b = in_file.read(FDpacket.BYTES_IN_PACKET)
                    packet = FDpacket.from_byte_string(b)
                    pktData = packet.interpret_data()
                    for k in range(int(self.bins / 4)):
                        bkgdSpec[int(self.bins / 4) * j + k] = pktData[k]
                background[i] = bkgdSpec

        # seed the pseudorandom number generator with current time
        seedval = int("{:%H%M%S}".format(datetime.now()))
        seed(seedval)

        # pick random numbers to serve as peak heights
        # peaks near 30 +/- 4 tend to stand out at the 4 to 4.5-sigma level
        peak_val = normal(30, 4, self.spectra)

        tracknum = 0
        for i in range(set.events):
            peak_bin_v_slice = zeros(self.spectra)  # peak freq. indexed by time slice
            initial_slice = randint(
                1, int(0.5 * self.spectra)
            )  # random start pt. in 1st 1/2 of file
            print("Initial event slice = ", initial_slice)
            slice = initial_slice  # set the initial slice number/time
            track_start_freq = set.start_freqs[i]  # set initial freq of the event
            print("Track start freq = ", track_start_freq)
            print("Number of jumps = ", set.n_jumps_per_event[i])
            for j in range(1 + set.n_jumps_per_event[i]):  # loop over tracks
                # convert track lengths (spec'd in milliseconds) to slice number
                track_slices = int(
                    (1 / 1000 * self.spec_time) * set.track_lengths[tracknum]
                )
                print("Track starting slice number = ", slice)
                print("Track length = ", track_slices, " slices")
                for k in range(track_slices):
                    bin = (self.bins / self.max_freq) * (
                        track_start_freq + k * 1000 * self.spec_time * set.dfdt[i]
                    )
                    peak_bin_v_slice[slice] = bin
                    slice += 1
                if j == set.n_jumps_per_event[i]:  # no more jumps in this event
                    break
                else:  # inc. start freq of next track by prev. track D_f + jump
                    track_start_freq += (
                        track_slices * 1000 * self.spec_time * set.dfdt[i]
                    )  # in MHz
                    track_start_freq += set.jump_mags[tracknum]  # jump freq (MHz)
                tracknum += 1

            self.output_file = (
                dr
                + "/Log_Files/"
                + set.log_name
                + set.log_date
                + "_{:06}.spec".format(i)
            )

            # Pass "wb" to write a binary file
            with open(self.output_file, "wb") as out_file:
                for a in range(self.spectra):  # loop over slices
                    data = zeros(self.bins, dtype=uint8)
                    # leave header blank for now
                    out_file.write(bytes(FDpacket.BYTES_IN_HEADER))
                    data = copy(background[randint(1, 100)])

                    if peak_bin_v_slice[a] != 0.0:  # if this slice has a track
                        channel = int(peak_bin_v_slice[a])  # assign to freq bin
                        if channel >= self.bins:  # don't go out of freq bin range
                            channel = self.bins - 1
                        print(
                            "Slice = ",
                            a,
                            "; Channel = ",
                            channel,
                            "; Value = ",
                            peak_val[a],
                        )
                        data[channel] = peak_val[a]
                    data.tofile(out_file)
