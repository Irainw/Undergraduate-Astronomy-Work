#!/usr/bin/env python2

from .Frequency_Domain_Packet import FDpacket
from socket import socket, AF_INET, SOCK_DGRAM

class FDPreceiver:

    def __init__(self, dsoc_desc=None):
        """
        Initialize an FDPreceiver object; open a socket for receiving packets

        ----------Parameters----------
        dsoc_desc (tuple): A tuple with the first element the IP address/port
            and the second element the port where data is to be received. This
            argument, if not None, is passed directly to socket.bind(); see
            documentation of that class for details. In this case a
            socket is opened and bound to the given address. If None, then
            the data socket is not opened. Default is None.
        """
        self._data_socket = socket(AF_INET,SOCK_DGRAM)
        if not dsoc_desc is None:
            try:
                self._data_socket.bind(dsoc_desc)
            except RuntimeError:
                raise RuntimeError(
                "Error: Unable to open data socket at {0}".format(dsoc_desc))
        print("Opened high-rate data socket at {0}".format(dsoc_desc))

    def one_packet_payload(self):
        """
        Get 1 packet using open data socket, remove header and interpret
        payload as array.

        ------------Returns------------
        x (array): A single array containing
        he6daq_packet.BYTES_IN_PAYLOAD uint8 entries
        """
        bytestring = self._data_socket.recv(FDpacket.BYTES_IN_PACKET)
        packet = FDpacket.from_byte_string(bytestring)
        return FDpacket.interpret_data(packet)

    def grab_packets(self, n=1):
        """
        Grab raw data packets using open data socket.

        ----------Parameters----------
        n (int): Number of packets to grab, default is 1.

        ------------Returns------------
        block (list): A list of bitstrings returned from _data_socket.recv
        """
        output = []
        for i in range(n):
            output.append(self._data_socket.recv(FDpacket.BYTES_IN_PACKET))
        return output

    def crack_packets(self, block, n=1):
        """
        Interpret a block of packets using he6daq_packet.from_byte_string.

        ----------Parameters----------
        block (list): A list of bitstrings returned from _data_socket.recv

        n (int): Number of packets in block, default is 1.

        ------------Returns------------
        output (list): A list of n he6daq_packet objects
        """
        output = []
        for x in range(n):
            output.append(FDpacket.from_byte_string(block[x]))
        return output

    def __del__(self):
        """Close socket used for data transmission"""
        self._data_socket.close()
        print("Closed high-rate data socket")
