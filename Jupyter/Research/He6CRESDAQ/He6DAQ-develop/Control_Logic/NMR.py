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


class NMR:
    def __init__(self, interval_s=30):

        self.field = None
        self.locked = None
        self.interval_s = interval_s
        self.nmr_thread = None

        return None

    def start(self):

        self.nmr_thread = RepeatedCall(self.interval_s, self.get_and_fill)
        return None

    def stop(self):

        self.nmr_thread.stop()

        return None

    def get_and_fill(self):
        self.get_nmr_field()
        if self.field != None:
            self.fill_nmr_table()
        return None

    def get_nmr_field(self):

        # Read field value from nmr probe.
        sock = socket.socket()
        sock.settimeout(5)

        self.field = None
        self.locked = False

        try:
            sock.connect(("10.66.192.40", 1234))
            field = sock.recv(128).decode("utf-8")
            if len(field) > 0:
                # Just grab the numeric value of the field.
                self.field = field[1:-1]

                # The first letter of the return value indicates if it's locked or not.
                if field[0] == "L":
                    self.locked = True
                else: 
                    print("Warning: NMR not locked.")

        except socket.error as err:
            print("Error connecting to nmr_probe: {}".format(err))


        return None

    def fill_nmr_table(self):

        connection = False
        try:

            connection = he6db.he6cres_db_connection()

            # Create a cursor to perform database operations
            cursor = connection.cursor()
            print("\nConnected to he6cres_db.\n")

            insert_statement = "INSERT INTO he6cres_runs.nmr (field, locked) Values ({},{}) RETURNING nmr_id".format(
                self.field, self.locked
            )

            cursor.execute(insert_statement)
            connection.commit()

            print("Inserted field and locked status into he6cres_runs.nmr.\n")
            nmr_id = cursor.fetchone()[0]

            print("Assigned nmr_id:", nmr_id)

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
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
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
