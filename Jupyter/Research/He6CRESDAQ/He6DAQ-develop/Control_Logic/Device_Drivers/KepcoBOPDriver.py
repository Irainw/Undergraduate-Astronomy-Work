# Kepco BOP Power Supply Driver. Author: Drew Byron. Email: wbyron@uw.edu

import socket
from socket import AF_INET, SOCK_DGRAM, SOCK_STREAM
import time
from typing import List


class KepcoBIT802E:
    def __init__(self, dsoc_desc=("10.66.192.42", 5025)):
        """
        Initialize a Kepco Power Supply controlled via the BIT 802E Digital Interface Card;
        open a data socket from the client side for communication.
        Note that after recieving a command the BIT 802E responds first with the command itself.
        This first response is denoted message_bounce.

        ----------Parameters----------
        dsoc_desc (tuple): A tuple with the first element the IP address
            and the second element the port where data is to be received.
        """

        self.sock = socket.socket(AF_INET, SOCK_STREAM)  # Note: SOCK_STREAM is default
        self.sock.settimeout(5)

        self.connected = False
        try:
            self.sock.connect(dsoc_desc) 
            self.connected = True

        except socket.error as err:
            print("Error connecting to kepco PS: {}".format(err))

        # Reset Kepco controls.
        self.MessageNoReturn("*RST")

    def MessageReturn(self, message):
        """
        Returns string representing KEPCO current in Amps
        """
        if self.connected: 
            self.sock.send(str.encode("{}\r\n".format(message)))
            response = self.sock.recv(100).decode("utf-8")[0:-2]
        else: 
            response = None
        return response

    def MessageNoReturn(self, message):
        """
        Returns string representing KEPCO current in Amps
        """

        if self.connected: 
            self.sock.send(str.encode("{}\r\n".format(message)))
        return None

    def set_mode_curr(self, max_volt):
        """
        Sets Kepco Mode to Curr.
        """
        self.MessageNoReturn("FUNC:MODE CURR")
        self.MessageNoReturn("CURR 0;:OUTP ON")
        self.MessageNoReturn("VOLT {}".format(max_volt))

        return None

    def set_curr(self, curr):

        """
        Set the current of the supply to Curr
        """

        self.MessageNoReturn("CURR {};:OUTP ON\r\n".format(curr))

        return None

    def get_curr(self):

        """
        Returns string representing KEPCO current in Amps.
        """
        query = "MEAS:CURR?"

        response = self.MessageReturn(query)

        return response

    def to_SCP_format(self, input_list: List[float]) -> str:

        # Drops brackets and removes spaces.
        output_str = str(input_list)[1:-1].replace(" ", "")

        return output_str

    # Functions to be used during data taking built from the above utility funtions.

    def const_curr(self, curr: float, max_volt: float = 10):
        """
        Provides constant current. Option to set maximum voltage provided by current mode.
        """
        self.set_mode_curr(max_volt=max_volt)
        self.set_curr(curr)

        current_returned = self.get_curr()
        print("Set current: {} A".format(current_returned))

        return None

    def slew(
        self,
        duration: float = 30,
        curr_list: List[float] = [0.5, 0.0],
        dwell_list: List[float] = [0.1, 0.1],
    ) -> None:
        """
        Slews the trap given a list of currents (A) and associated dwell times (s).
        """

        t_wait = 0.05

        time.sleep(t_wait)

        self.MessageNoReturn("*RST")
        time.sleep(t_wait)

        self.MessageNoReturn("FUNC:MODE CURR")
        time.sleep(t_wait)

        self.MessageNoReturn("VOLT 10")
        time.sleep(t_wait)

        self.MessageNoReturn("LIST:CLE")
        time.sleep(t_wait)

        self.MessageNoReturn("LIST:CURR {}".format(self.to_SCP_format(curr_list)))
        time.sleep(t_wait)

        self.MessageNoReturn("LIST:DWEL {}".format(self.to_SCP_format(dwell_list)))
        time.sleep(t_wait)

        print("curr_list recieved: ", self.MessageReturn("LIST:CURR?"))
        print("dwell_list recieved: ", self.MessageReturn("LIST:DWEL?"))

        # Note that the list mode can only hold so many items.
        self.MessageNoReturn("LIST:COUN 100")
        time.sleep(t_wait)

        self.MessageNoReturn("OUTP ON")
        cycle = 0
        print(
            "Slewing started. Duration: {} s. Cycle length: {} s".format(
                duration, sum(dwell_list) * 100
            )
        )
        timeout_start = time.time()
        while time.time() < timeout_start + duration:

            self.MessageNoReturn("CURR:MODE LIST")
            time.sleep(sum(dwell_list) * 100)
            cycle += 1

        print("Slewing stopped. Went through {} cycles.".format(cycle))
        return None
