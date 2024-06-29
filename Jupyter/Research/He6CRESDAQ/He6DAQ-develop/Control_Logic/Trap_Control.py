from time import sleep
from numpy.random import exponential
from .Device_Drivers.KepcoBOPDriver import *
from typing import List


class TrapControl:
    def __init__(self):
        """
        Initialize a KepcoBIT802E object.
        """
        self.driver = KepcoBIT802E()

    def const_curr(self, curr: float, max_volt: float = 10):
        """
        Calls the const_curr method of the driver.
        """
       

        # if self.driver.connected:
        self.driver.const_curr(curr, max_volt)
        #     trap_config = "const, curr: {}".format(curr)
        # else:
        #     trap_config = "not connected"

        return None

    def slew(
        self,
        duration: float = 30,
        curr_list: List[float] = [0.5, 0.0],
        dwell_list: List[float] = [0.1, 0.1],
    ) -> None:
        """
        Calls the const_curr method of the driver.
        """
        # trap_config = None
        # if self.driver.connected:
        self.driver.slew(duration, curr_list, dwell_list)
            
        # else:
        #     trap_config = "not connected"

        return None
