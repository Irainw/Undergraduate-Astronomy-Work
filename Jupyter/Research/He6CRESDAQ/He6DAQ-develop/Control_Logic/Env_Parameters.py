from datetime import datetime, timezone
import numpy as np
import pandas as pd
import socket
import typing
from typing import List
import requests
import urllib.request

# Local modules.
from .PostgreSQL_Interface import he6cres_db_query


class EnvParams:
    def __init__(self, roach_avg, analog_inputs, freq_ch, roach_nyquist, requant_gain):

        # Roach parameters. Get from initialization of CLI.
        self.roach_avg = roach_avg
        self.analog_inputs = analog_inputs
        self.roach_nyquist = roach_nyquist
        self.freq_ch = freq_ch
        self.requant_gain = requant_gain

        # User set at time of data acquisition.
        self.isotope = None
        self.set_field = None
        self.run_notes = None
        self.acq_length_ms = None
        self.rf_side = None

        # Env params from insturments.
        self.true_field = None
        self.trap_config = None
        self.monitor_on = None
        self.nmr_on = None

        # RGA pressures
        self.rga_tot = None
        self.rga_nitrogen = None
        self.rga_helium = None
        self.rga_c02 = None
        self.rga_hydrogen = None
        self.rga_water = None
        self.rga_oxygen = None
        self.rga_krypton = None
        self.rga_argon = None
        self.rga_cf3 = None
        self.rga_ne19 = None

        # Parameter to keep track of slewing thread.
        self.slewing = None

        return None

    def get(self):

        self.get_field()
        self.get_monitor_status()
        self.get_nmr_status()
        self.get_rga_pressures()

        # Check to make sure slewing is on
        if self.trap_config is not None:

            if self.trap_config[:4] == "slew":
                if not self.slewing.is_alive():
                    self.trap_config = "OFF. Slewing stopped."

        return self.__dict__

    def get_field(self):

        # read field value from nmr probe
        sock = socket.socket()
        sock.settimeout(5)

        try:
            sock.connect(("10.66.192.40", 1234))
            true_field = sock.recv(128).decode("utf-8")
            self.true_field = np.nan
            if true_field:
                if true_field[0] == "N":
                    print("Warning: NMR not locked.")
                else:
                    self.true_field = true_field[1:-1]

        except socket.error as err:
            print("Error connecting to nmr_probe: {}".format(err))
            self.true_field = None

        return None

    def get_monitor_status(self):
        monitor_query = """SELECT * FROM he6cres_runs.monitor 
                           ORDER BY monitor_id DESC LIMIT 1
                        """

        monitor_return = he6cres_db_query(monitor_query)

        most_recent_monitor_write_utc = pd.to_datetime(
            monitor_return.created_at[0], utc=True
        )
        current_time_utc = pd.to_datetime(datetime.now(timezone.utc), utc=True)

        time_diff = (current_time_utc - most_recent_monitor_write_utc).total_seconds()
        time_diff_s = np.abs(time_diff)

        print("Last monitor rate recorded {} s ago.".format(time_diff_s))

        self.monitor_on = str(time_diff_s < 60)

        print("monitor_on: {}".format(self.monitor_on))

        return None

    def get_nmr_status(self):

        nmr_query = """SELECT * FROM he6cres_runs.nmr 
                           ORDER BY nmr_id DESC LIMIT 1
                        """

        nmr_return = he6cres_db_query(nmr_query)

        most_recent_nmr_write_utc = pd.to_datetime(nmr_return.created_at[0], utc=True)
        current_time_utc = pd.to_datetime(datetime.now(timezone.utc), utc=True)

        time_diff = (current_time_utc - most_recent_nmr_write_utc).total_seconds()
        time_diff_s = np.abs(time_diff)

        nmr_locked = nmr_return.locked[0]
        print("Last nmr rate recorded {} s ago.".format(time_diff_s))
        print("nmr is currently locked: {}.".format(nmr_locked))

        # Note that nmr_on will be true only if there was a probe measurement
        # in the last 60 s and the field was locked for that measurement.
        self.nmr_on = str((time_diff_s < 60) & (nmr_locked))

        print("nmr_on: {}".format(self.nmr_on))

        return None

    def get_rga_pressures(self):

        species_list = [
            "Nitrogen",
            "Helium",
            "CO2",
            "Hydrogen",
            "Water",
            "Oxygen",
            "Krypton",
            "Argon",
            "CF3",
            "Ne19",
        ]

        pressure_array = self.pressures(species_list)
        # for i, stuff in enumerate(zip(species_list, pressure_array)):
        #     print("pressure: ", i, ",", stuff)

        self.rga_nitrogen = pressure_array[0]
        self.rga_helium = pressure_array[1]
        self.rga_c02 = pressure_array[2]
        self.rga_hydrogen = pressure_array[3]
        self.rga_water = pressure_array[4]
        self.rga_oxygen = pressure_array[5]
        self.rga_krypton = pressure_array[6]
        self.rga_argon = pressure_array[7]
        self.rga_cf3 = pressure_array[8]
        self.rga_ne19 = pressure_array[9]

        # Only sum the positive pressures.
        self.rga_tot = pressure_array[pressure_array > 0].sum()

        return None

    def pressures(self, species_list: List[str]) -> np.ndarray:

        pressure_list = []

        for species in species_list:

            try:
                rga_url = "http://10.95.100.45:5000/"

                # Grab output and split the string based on spaces.
                response = requests.get(rga_url + species, timeout=10)
                rga_out = response.text.split()
                response.close()
                time_since_write = float(rga_out[3])

                # Verify the rga pressure is recent to within 60s
                if time_since_write > 60.0:
                    print(
                        "The rga pressure was last written over 60s ago. \
                        Are the rga and rga flask app running?"
                    )
                    pressure_list.append(0)
                else:
                    pressure = float(rga_out[0])
                    pressure_list.append(pressure)

            except Exception as error:

                pressure_list = [0] * len(species_list)
                print("RGA error: ", error)

                break

        return np.array(pressure_list)
