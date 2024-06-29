from datetime import datetime, timezone
import numpy as np
import pandas as pd
import socket
import typing
from typing import List
from threading import Timer
import requests
import urllib.request

# Local modules.
from . import PostgreSQL_Interface as he6db


class Monitor:

    def __init__(self, interval_s = 30 ):

        self.monitor_rate = None
        self.interval_s = interval_s
        self.monitor_thread = None

        return None

    def start(self): 

        self.monitor_thread = RepeatedCall(self.interval_s, self.get_and_fill)
        return None

    def stop(self): 

        self.monitor_thread.stop()

        return None

    def get_and_fill(self): 
        self.get_monitor_rate()
        self.fill_monitor_table()
        return None

    def get_monitor_rate(self):

        rate_url = "http://10.66.192.46"

        try:
            response = requests.get(rate_url)
            rate = float(response.text.split()[3])
            response.close()

        except Exception as error:
            print("Monitor error: ", error)
            rate = None

        self.monitor_rate = rate

        return None

    def fill_monitor_table(self):

        connection = False
        try:

            connection = he6db.he6cres_db_connection()

            # Create a cursor to perform database operations
            cursor = connection.cursor()
            print("\nConnected to he6cres_db.\n")

            insert_statement = "INSERT INTO he6cres_runs.monitor (rate) Values ({}) RETURNING monitor_id".format(
                self.monitor_rate
            )

            cursor.execute(insert_statement)
            connection.commit()

            print("Inserted rate into he6cres_runs.monitor.\n")
            monitor_id = cursor.fetchone()[0]

            print("Assigned monitor_id:", monitor_id)

        except Exception as error:
            print("Error while connecting to he6cres_db", error)

        finally:
            if connection:
                cursor.close()
                connection.close()
                print("\nConnection to he6cres_db closed.")

        return None



class RepeatedCall(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False