#!/usr/bin/env python3

from .adc5g.opb import *
from .adc5g.spi import *
from .adc5g.tools import *
from .adc5g.roach import *

try:
    from .adc5g.mlab_tools import *
except ImportError:
    pass

from .Corr.katcp_wrapper import FpgaClient
from datetime import datetime
import netifaces as ni
from numpy import (
    abs,
    array,
    concatenate,
    uint32,
    zeros,
    )
from struct import unpack
from time import sleep, time

class ROACH(object):
    """
    Encapsulate an object to interface with the ROACH.
    Based on the R2DAQ (aka ArtooDaq) class from Andre Young.
    """

    _TIMEOUT = 5
    _FPGA_CLOCK = 200e6

    @property
    def FPGA_CLOCK(self):
        return self._FPGA_CLOCK

    @property
    def CHANNEL_WIDTH(self):
        return self._CHANNEL_WIDTH

    @property
    def roach2(self):
        return self._roach2

    def __init__(self, hostname, socket = ("0.0.0.0",4001),
                 boffile = None, ADC_cards = 1, do_cal = False):

        """
        Initialize a He6CRES_DAQ object.

        ----------Parameters----------
        hostname (string): Address of the roach2 on the 1GbE (control) network.

        boffile (string): Program the device with this bitcode. The special
            filename 'latest-build' uses the current build of the bit-code.
            Default is None.
        """
        self.ADC_cards = ADC_cards

        # connect to roach and store local copy of FpgaClient
        r2 = FpgaClient(hostname)
        if not r2.wait_connected(self._TIMEOUT):
            raise RuntimeError("Unable to connect to ROACH2 named "
                                + "'{0}'".format(hostname))
        self._roach2 = r2
        # program bitcode
        if not boffile is None:
            self._start(boffile, socket, do_cal)

    def set_requant_gain(self, gain = 10):
        """
        Set post-FFT requantization gain to 2**gain-1.

        ----------Parameters----------
        gain: integer between 0 and 32 (inclusive). The gain on the
        requantization blocks will be set to 2**gain-1, in keeping with
        the tutorial approach to requantization
        """
        regname = 'requant_gain'
        if (gain >=0 and gain <= 32):
            s_32bit = uint32(2**gain-1)
            self.roach2.write_int(regname,s_32bit)
        else:
            print("ERROR: Gain must be set between 0 and 32 (inclusive)")

    def set_spi_OGP(self, zdok, fits):
        """
        Set spi register values on one ZDOK card according to content of fits[]
        For cores 1,2,3,4, offset vals (in mV) should be in fits[3], fits[6],
        fits[9], and fits[12], respectively
        For cores 1,2,3,4, gains (as a % of full range) should be in fits[4],
        fits[7], fits[10], and fits[13], respectively
        For cores 1,2,3,4, phase vals (in ps) should be in fits[5], fits[8],
        fits[11], and fits[14], respectively
        """

        for n in range (4):
            if (fits[3+3*n] > 50.0): fits[3+3*n] = 49.0
            if (fits[3+3*n] < -50.0): fits[3+3*n] = -49.0

        print(f"Setting Core A offset to {fits[3]} mV")
        set_spi_offset(self.roach2, zdok, 1, fits[3])
        print(f"Setting Core B offset to {fits[6]} mV")
        set_spi_offset(self.roach2, zdok, 2, fits[6])
        print(f"Setting Core C offset to {fits[9]} mV")
        set_spi_offset(self.roach2, zdok, 3, fits[9])
        print(f"Setting Core D offset to {fits[12]} mV")
        set_spi_offset(self.roach2, zdok, 4, fits[12])

        for n in range (4):
            if (fits[4+3*n] > 18.0): fits[4+3*n] = 17.5
            if (fits[4+3*n] < -18.0): fits[4+3*n] = -17.5

        print(f"Setting Core A gain to {fits[4]}")
        set_spi_gain(self.roach2, zdok, 1, fits[4])
        print(f"Setting Core B gain to {fits[7]}")
        set_spi_gain(self.roach2, zdok, 2, fits[7])
        print(f"Setting Core C gain to {fits[10]}")
        set_spi_gain(self.roach2, zdok, 3, fits[10])
        print(f"Setting Core D gain to {fits[13]}")
        set_spi_gain(self.roach2, zdok, 4, fits[13])

        for n in range (4):
            if (fits[5+3*n] > 14.0): fits[5+3*n] = 13.5
            if (fits[5+3*n] < -14.0): fits[5+3*n] = -13.5

        print(f"Setting Core A phase to {fits[5]}")
        set_spi_phase(self.roach2, zdok, 1, fits[5])
        print(f"Setting Core B phase to {fits[8]}")
        set_spi_phase(self.roach2, zdok, 2, fits[8])
        print(f"Setting Core C phase to {fits[11]}")
        set_spi_phase(self.roach2, zdok, 3, fits[11])
        print(f"Setting Core D phase to {fits[14]}")
        set_spi_phase(self.roach2, zdok, 4, fits[14])

    def snap_per_core(self, zdok, groups=1):
        """
        #Get a snapshot of 8-bit data per core from the ADC.

        ----------Parameters----------
        zdok (int):  ID of the ADC ZDOK slot, either 0 or 1
        groups (int): Each snapshot grabs groups*(2**16) samples per core
            (default value is groups=1, for 2**16=65536 samples).

        ------------Returns------------
        x (ndarray): A (groups*(2**16), 4)-shaped array in which data along the
            first dimension contains consecutive samples taken form the
            same core.

            The data is ordered such that the index along the second
            dimension matches core-indexing in the spi-family of functions used
            to tune the core parameters.
            For example, a 1x12 snapshot of values
            [1 2 3 4 5 6 7 8 9 10 11 12]
            becomes a 3x4 array
            [[ 1  3  2  4]
             [ 5  7  6  8]
             [ 9 11 10 12]]
        """
        x = zeros((0,4))
        for ig in range(groups):
            grab = self.roach2.snapshot_get('snap_{0}_snapshot'.format(zdok))
            x_ = array(unpack('%ib' %grab['length'], grab['data']))
            x_ = x_.reshape(int(x_.size/4),4)
            x = concatenate((x,x_))
        return x[:,[0,2,1,3]]


    def adc_snap(self,zdok):
        """
        Get a snapshot of interleaved data from 1 ADC

        ----------Parameters----------
        zdok (int):  ID of the ADC ZDOK slot, either 0 or 1

        ------------Returns------------
        x (array) an array of length 2^16 with data interleaved instead of
        separated by core
        """
        grab = self.roach2.snapshot_get('snap_{0}_snapshot'.format(zdok))
        x = array(unpack('%ib' %grab['length'], grab['data']))
        return x

    def _make_assignment(self,assign_dict):
        """
        Assign values to ROACH2 software registers.

        Assignments are made as roach2.write_int(key,val).

        Parameters
        ----------
        assign_dict : dict
            Each key in assign_dict should correspond to a valid ROACH2
            software register name, and each val should be int compatible.
        """
        for key in list(assign_dict.keys()):
            val = assign_dict[key]
            self.roach2.write_int(key,val)


    def _start(self, boffile='latest-build', socket = ("0.0.0.0",4003),
              do_cal=True, iface='enp4s0',verbose=10):

#    def _start(self, boffile='latest-build', socket = ("0.0.0.0",4003),
 #              do_cal=True, iface='enp65s0np0',verbose=10):

        """
        Program bitcode on device and set up data output on specified socket

        Parameters
        ----------
        boffile (string): Filename of the bitcode to program.
            If 'latest-build' then use the current build.

        do_cal (bool): If true then do ADC core calibration. Default is True.

        iface (string): Network interface connected to the data network. Will need to be changed if setting up 
		on new device

        verbose (int): The higher the more verbose, control the amount of
            output to the screen. Default is 10 (probably the highest).
        """

        if boffile == "latest-build":
            boffile = "he6_cres_correlator_2018_Sep_14_2002.bof"

        # program bitcode
        self.roach2.progdev(boffile)
        self.roach2.wait_connected()
        if verbose > 1:
            print("Bitcode '", boffile, "' programmed successfully")

        # display clock speed
        if verbose > 3:
            print("Board clock is ", self.roach2.est_brd_clk(), "MHz")
            if (self.roach2.est_brd_clk() > 299.0
                or self.roach2.est_brd_clk()<100.0):
                print("WrOnG INpuT cLoCK fREQuencY! trY AgAIN, FoOL!!!")

        # ADC interface calibration
        if verbose > 3:
            print("Performing ADC interface calibration on ZDOK0")
            set_test_mode(self.roach2, 0)
            sync_adc(self.roach2)
            opt0, glitches0 = calibrate_mmcm_phase(self.roach2, 0, ['snap_0_snapshot',])
            unset_test_mode(self.roach2, 0)

            if (self.ADC_cards == 2):
                print("Performing ADC interface calibration on ZDOK1")
                set_test_mode(self.roach2, 1)
                sync_adc(self.roach2)
                opt1, glitches1 = calibrate_mmcm_phase(self.roach2, 1, ['snap_1_snapshot',])
                unset_test_mode(self.roach2, 1)

        if verbose > 3:
            print("...ADC interface calibration done.")
        if verbose > 5:
            print("if0: opt0 = ",opt0, ", glitches0 = \n", array(glitches0))
            if (self.ADC_cards == 2):
                print("if1: opt1 = ",opt1, ", glitches0 = \n", array(glitches1))


        # ADC core calibration
        if do_cal:
            self.calibrate_adc_ogp(zdok=0,verbose=verbose)
            if (self.ADC_cards == 2):
                self.calibrate_adc_ogp(zdok=1,verbose=verbose)


        #self.roach2.read_int("tengbe_{0}_ctrl".format(ch))

        # hold master reset signal and arm the manual sync
        self.roach2.write_int('master_ctrl',0x00000001 | 0x00000002)
        master_ctrl = self.roach2.read_int('master_ctrl')

        # hold 10gbe reset signal
        self.roach2.write_int('tengbe_a_ctrl',0x80000000)

        # ip, port of data interface on receive side
        print("Establishing connection on interface "+iface)
        print("If connection is invalid, call netifaces.interfaces() for"
               " a list of available interfaces")

        dest_ip_str_cmp = ni.ifaddresses(iface)[2][0]['addr'].split('.')
        ip3 = int(dest_ip_str_cmp[0])
        ip2 = int(dest_ip_str_cmp[1])
        ip1 = int(dest_ip_str_cmp[2])
        ip0 = int(dest_ip_str_cmp[3])
        dest_ip = (0*2**32) +  (ip3*2**24) + (ip2*2**16) + (ip1*2**8) + ip0
        #dest_ip = 0
        dest_port = socket[1]

        # fill arp table on ROACH2
        #mac_iface = ni.ifaddresses(iface)[17][0]['addr']
        #hex_iface is the MAC address of the NIC ethernet interface converted to a decimal value


        # hex_iface = 18077468907216 # mellanox quadSFP card MAC address in hex

        hex_iface = 211135283342095  #======> enp4s0 hex MAC address
        arp = [0xffffffffffff] * 256
        arp[ip0] = hex_iface

        # ip, port, mac of data interface on transmit side
        src_ip = (ip3<<24) + (ip2<<16) + (ip1<<8) + 2
        src_port = 4000
        src_mac = (2<<40) + (2<<32) + src_ip
        self.roach2.config_10gbe_core('tengbe_a_core', src_mac,
                                      src_ip, src_port,arp)

        self.roach2.write_int('tengbe_a_ip',dest_ip)
        dest_ip_out = self.roach2.read_int("tengbe_a_ip")
        self.roach2.write_int('tengbe_a_port',dest_port)
        dest_port_out = self.roach2.read_int("tengbe_a_port")
        print("ROACH 10GbE output on IP",dest_ip_out,"and port",dest_port_out)

        # and release reset
        self.roach2.write_int('tengbe_a_ctrl',0x00000000)

        # set time, wait until just before a second boundary
        while(abs(datetime.utcnow().microsecond-9e5)>1e3):
            sleep(0.001)

        # when the system starts running it will be the next second
        ut0 = int(time())+1
        self.roach2.write_int('unix_time0',ut0)

        #self.set_fft_shift('1101010101010')

        # release master reset signal
        master_ctrl = self.roach2.read_int('master_ctrl')
        master_ctrl = master_ctrl & 0xFFFFFFFC
        self.roach2.write_int('master_ctrl',master_ctrl)
        if verbose > 1:
            print("Configuration done, system should be running")


    """
    def calibrate_adc_ogp(self,zdok=0,oiter=10,otol=0.005,giter=10,
                gtol=0.005,piter=0,ptol=1.0,verbose=10):

        #Attempt to match the cores within the ADC.

        #Each of the four cores internal to each ADC has an offset, gain,
        #phase, and a number of integrated non-linearity parameters that
        #can be independently tuned. This method attempts to match the
        #cores within the specified ADC by tuning a subset of these
        #parameters.

        #Parameters
        #----------
        #zdok : int
        #    ZDOK slot that contains the ADC, should be 0 (default is 0).
        #    (Second ADC card not in bitcode)
        #oiter : int
        #    Maximum number of iterations to fine-tune offset parameter
        #    (default is 10).
        #otol : float
        #    If the absolute value of the mean of snapshot data normalized to
        #    the standard deviation from one core is below this value then the
        #    offset-tuning is considered sufficient (default is 0.005).
        #giter : int
        #    Maximum number of iterations to fine-tune gain parameter (default
        #    is 10).
        #gtol : float
        #    If the standard deviation of the data in one
        #    core differs from the standard deviation in the data
        #    from core1 by less than this fractional value,
        #    then the gain-tuning is considered sufficient
        #    (default value is 0.5%).
        #    piter : int
        #    Phase calibration not yet implemented.
        #    ptol : float
        #    Phase calibration not yet implemented.
        #verbose : int
        #    The higher the more verbose, control the amount of output to
        #    the screen. Default is 10 (probably the highest).

        #Returns
        #-------
        #ogp : dict
        #    The returned parameter is a dictionary that contains the optimal
        #    settings for offset, gain and phase as solved during calibration.

        if verbose > 3:
            print("Attempting OGP-calibration for ZDOK{0}".format(zdok))
        co = self.calibrate_adc_offset(zdok=zdok,oiter=oiter,otol=otol,
        verbose=verbose)
        cg = self.calibrate_adc_gain(zdok=zdok,giter=giter,gtol=gtol,
        verbose=verbose)
        cp = self.calibrate_adc_phase(zdok=zdok,piter=piter,ptol=ptol,
        verbose=verbose)
        return {'offset': co, 'gain': cg, 'phase': cp}



    def calibrate_adc_offset(self,zdok=0,oiter=10,otol=0.005,verbose=10):

        #Attempt to match the core offsets within the ADC.
        #See ArtooDaq.calibrate_adc_ogp for more details.

        # offset controlled by float varying over [-50,50] mV with
        #0.4 mV resolution
        res_offset = 0.4
        offset_tweak = 1.0
        groups = 8
        test_step = 10*res_offset
        if verbose > 3:
            print("  Offset calibration ZDOK{0}:".format(zdok))
        for ic in range(1,5):
            set_spi_offset(self.roach2,zdok,ic,0)
        x1 = self.snap_per_core(zdok=zdok,groups=groups)
        sx1 = x1.std(axis=0)
        mx1 = x1.mean(axis=0)/sx1
        if verbose > 5:
            print("    ...offset: with zero-offsets, means are [{0}]".format(
                ", ".join(["{0:+7.4f}".format(imx) for imx in mx1])
            ))
        for ic in range(1,5):
            set_spi_offset(self.roach2,zdok,ic,test_step)
        x2 = self.snap_per_core(zdok=zdok,groups=groups)
        sx2 = x2.std(axis=0)
        mx2 = x2.mean(axis=0)/sx2
        if verbose > 5:
            print( "    ...offset: with {0:+4.1f} mV offset, means are [{1}]".format(
                test_step,
                ", ".join(["{0:+7.4f}".format(imx) for imx in mx2])
            ))
        d_mx = (mx2 - mx1)/test_step
        core_offsets = -mx1/d_mx
        for ic in range(1,5):
            set_spi_offset(self.roach2,zdok,ic,core_offsets[ic-1])
            core_offsets[ic-1] = get_spi_offset(self.roach2,zdok,ic)
        x = self.snap_per_core(zdok=zdok,groups=groups)
        sx = x.std(axis=0)
        mx = x.mean(axis=0)/sx
        if verbose > 5:
            print("    ...offset: solution offsets are [{0}] mV, means are [{1}]".format(
                ", ".join(["{0:+6.2f}".format(ico) for ico in core_offsets]),
                ", ".join(["{0:+7.4f}".format(imx) for imx in mx])
            ))
        if any(abs(mx) >= otol):
            if verbose > 5:
                print("    ...offset: solution not good enough, iterating (tol={0:4.4f},iter={1:d})".format(otol,oiter))
            for ii in range(0,oiter):
                tweak = offset_tweak/(ii+1)
                for ic in range(1,5):
                    if mx[ic-1] > otol:
                        #set_spi_offset(self.roach2,zdok,ic,core_offsets[ic-1]-res_offset)
                        set_spi_offset(self.roach2,zdok,ic,core_offsets[ic-1]-tweak)
                    elif mx[ic-1] < -otol:
                        #set_spi_offset(self.roach2,zdok,ic,core_offsets[ic-1]+res_offset)
                        set_spi_offset(self.roach2,zdok,ic,core_offsets[ic-1]+tweak)
                    core_offsets[ic-1] = get_spi_offset(self.roach2,zdok,ic)
                x = self.snap_per_core(zdok=zdok,groups=groups)
                sx = x.std(axis=0)
                mx = x.mean(axis=0)/sx
                if verbose > 7:
                    print("    ...offset: solution offsets are [{0}] mV, means are [{1}]".format(
                        ", ".join(["{0:+6.2f}".format(ico) for ico in core_offsets]),
                        ", ".join(["{0:+7.4f}".format(imx) for imx in mx])
                    ))
                if all(abs(mx) < otol):
                    if verbose > 5:
                        print("    ...offset: solution good enough")
                    break
                if ii==oiter-1:
                    if verbose > 5:
                        print("    ...offset: maximum number of iterations reached, aborting")
        else:
            if verbose > 5:
                print("    ...offset: solution good enough")
        return core_offsets

    def calibrate_adc_gain(self,zdok=0,giter=10,gtol=0.005,verbose=10):

        #Attempt to match the core gains within the ADC.
        #See ArtooDaq.calibrate_adc_ogp for more details.

        # gain controlled by float varying over [-18%,18%] with 0.14% resolution
        res_gain = 0.14
        max_delta = 18.0
        groups = 8
        test_step = 10*res_gain
        if verbose > 3:
            print("  Gain calibration ZDOK{0}:".format(zdok))
        for ic in range(1,5):
            set_spi_gain(self.roach2,zdok,ic,0)
        x1 = self.snap_per_core(zdok=zdok,groups=groups)
        sx1 = x1.std(axis=0)
        s0 = sx1[0]
        sx1 = sx1/s0
        if verbose > 5:
            print("    ...gain: with zero-offsets, stds are                                    [{0}]".format(
                ", ".join(["{0:+7.4f}".format(isx) for isx in sx1])
                ))
        # only adjust gains for last three cores, core1 is the reference
        for ic in range(2,5):
            set_spi_gain(self.roach2,zdok,ic,test_step)
        x2 = self.snap_per_core(zdok=zdok,groups=groups)
        sx2 = x2.std(axis=0)
        s0 = sx2[0]
        sx2 = sx2/s0
        if verbose > 5:
            print("    ...gain: with {0:+6.2f}% gain, stds are                                    [{1}]".format(
                test_step,
                ", ".join(["{0:+7.4f}".format(isx) for isx in sx2])
                ))
        d_sx = 100*(sx2 - sx1)/test_step
        # give differential for core1 a non-zero value, it won't be used anyway
        d_sx[0] = 1.0
        # gains are in units percentage
        core_gains = 100*(1.0-sx1)/d_sx
        # set core1 gain to zero
        core_gains[0] = 0
        for ic in range(2,5):
            if (core_gains[ic-1] > max_delta):
                core_gains[ic-1] = max_delta
            elif (core_gains[ic-1] < -1 * max_delta):
                core_gains[ic-1] = -1 * max_delta
            set_spi_gain(self.roach2,zdok,ic,core_gains[ic-1])
            core_gains[ic-1] = get_spi_gain(self.roach2,zdok,ic)
        x = self.snap_per_core(zdok=zdok,groups=groups)
        sx = x.std(axis=0)
        s0 = sx[0]
        sx = sx/s0
        if verbose > 5:
            print("    ...gain: solution gains are [{0}]%, stds are [{1}]".format(
                        ", ".join(["{0:+6.2f}".format(ico) for ico in core_gains]),
                        ", ".join(["{0:+7.4f}".format(isx) for isx in sx])
                        ))
        if any(abs(1.0-sx) >= gtol):
            if verbose > 5:
                print("    ...gain: solution not good enough, iterating (tol={0:4.4f},iter={1:d})".format(gtol,giter))
            for ii in range(0,giter):
                for ic in range(2,5):
                    if (1.0-sx[ic-1]) > gtol:
                        set_spi_gain(self.roach2,zdok,ic,core_gains[ic-1]+res_gain)
                    elif (1.0-sx[ic-1]) < -gtol:
                        set_spi_gain(self.roach2,zdok,ic,core_gains[ic-1]-res_gain)
                    core_gains[ic-1] = get_spi_gain(self.roach2,zdok,ic)
                x = self.snap_per_core(zdok=zdok,groups=groups)
                sx = x.std(axis=0)
                s0 = sx[0]
                sx = sx/s0
                if verbose > 7:
                    print("    ...gain: solution gains are [{0}]%, stds are [{1}]".format(
                        ", ".join(["{0:+6.2f}".format(ico) for ico in core_gains]),
                        ", ".join(["{0:+7.4f}".format(isx) for isx in sx])
                        ))
                if all(abs(1.0-sx) < gtol):
                    if verbose > 5:
                        print("    ...gain: solution good enough")
                    break
                if ii==giter-1:
                     if verbose > 5:
                        print("    ...gain: maximum number of iterations reached, aborting")
        else:
            if verbose > 5:
                print("    ...gain: solution good enough")
        return core_gains

    def calibrate_adc_phase(self,zdok=0,piter=0,ptol=1.0,verbose=10):

        #Attempt to match the core phases within the ADC.
        #See ArtooDaq.calibrate_adc_ogp for more details.

        # phase controlled by float varying over [-14,14] ps with 0.11 ps resolution
        res_phase = 0.11
        lim_phase = [-14.0,14.0]
        if verbose > 3:
            print("  Phase calibration ZDOK{0}:".format(zdok))
        core_phases = zeros(4)
        for ic in range(1,5):
            core_phases[ic-1] = get_spi_phase(self.roach2,zdok,ic)
        if verbose > 5:
            print("    ...phase: tuning not implemented yet,phase parameters "
                  "are [{0}]".format(", ".join(["{0:+06.2f}".format(icp)
                  for icp in core_phases])))
        return core_phases
    """
