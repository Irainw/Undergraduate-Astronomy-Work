from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import socket
import typing
from typing import List
import requests
import urllib.request

# Local modules.
from .PostgreSQL_Interface import he6cres_db_query

# Note on this working with X11 forwarding (using these functions via ssh): 
# You need to have the following in the daq .bashrc to enable X11 forwarding by sudo: 
# xauth extract - $DISPLAY | sudo xauth merge -


def get_spec_file_info(run_id, file_in_acq=0):

    query = """SELECT file_path, freq_ch FROM he6cres_runs.spec_files
               INNER JOIN he6cres_runs.run_log
               ON spec_files.run_id = run_log.run_id
               WHERE spec_files.run_id = {} AND 
               spec_files.file_in_acq = {}
               LIMIT 1
           """.format(
        run_id, file_in_acq
    )

    results = he6cres_db_query(query)

    spec_path = results.file_path[0]
    freq_ch = results.freq_ch[0]
    print("\nspec_path: ", spec_path)
    print("freq_ch: ", freq_ch)

    return spec_path, int(freq_ch)


def spec_to_array(spec_path, freq_ch, slices=-1, start_packet=0):
    """
    TODO: Document.
    This function should work for both 2^12 and 2^15 bitcodes.
    """
    if freq_ch == 4096:

        BYTES_IN_PAYLOAD = freq_ch
        BYTES_IN_HEADER = 32
        BYTES_IN_PACKET = BYTES_IN_PAYLOAD + BYTES_IN_HEADER

    elif freq_ch == 32768:
        packets_per_slice = 4
        BYTES_IN_PAYLOAD = freq_ch // packets_per_slice
        BYTES_IN_HEADER = 32
        BYTES_IN_PACKET = BYTES_IN_PAYLOAD + BYTES_IN_HEADER
        slices = slices * packets_per_slice

    else:
        raise ValueError("Function currently only works for freq_ch = 4096 or 32768.")

    # def read_spec(spec_path, slices = -1):
    if slices == -1:
        spec_array = np.fromfile(spec_path, dtype="uint8", count=-1).reshape(
            (-1, BYTES_IN_PACKET)
        )[:, BYTES_IN_HEADER:]
    else:
        spec_array = np.fromfile(
            spec_path, dtype="uint8", count=BYTES_IN_PACKET * slices
        ).reshape((-1, BYTES_IN_PACKET))[:, BYTES_IN_HEADER:]

    if freq_ch == 32768:

        packets_per_slice = 4

        spec_flat_list = [
            spec_array[(start_packet + i) % packets_per_slice :: packets_per_slice]
            for i in range(packets_per_slice)
        ]
        spec_flat = np.concatenate(spec_flat_list, axis=1)
        spec_array = spec_flat

    return spec_array.T


def show_sparse_spec(spec_array, snr_cut=5):
    cut_condition = np.array(
        (spec_array > np.expand_dims(spec_array.mean(axis=1), axis=1) * snr_cut), dtype=int
    )

    fig, ax = plt.subplots(figsize=(12, 8))

    ax.imshow(
        1 - cut_condition,
        origin="lower",
        aspect="auto",
        interpolation=None,
        cmap="gray",
    )

    ax.set_title("sparse spectrogram")
    ax.set_xlabel("time slice")
    ax.set_ylabel("freq bin")

    plt.show()

    return None


def show_noise_floor(spec_array):

    fig, ax = plt.subplots(figsize=(12, 8))

    ax.plot(spec_array.mean(axis=1))

    ax.set_title("mean noise floor")
    ax.set_xlabel("freq bin")
    ax.set_ylabel("arb. roach units")

    plt.show()

    return None


def look_at_spec_file(
    run_id,
    file_in_acq=0,
    slices=1000,
    sparse_spec=True,
    noise_floor=True,
    snr_cut=5,
    start_packet=0,
):

    spec_path, freq_ch = get_spec_file_info(run_id, file_in_acq)
    spec_array = spec_to_array(
        spec_path, freq_ch, slices=slices, start_packet=start_packet
    )

    if sparse_spec:
        show_sparse_spec(spec_array, snr_cut=snr_cut)
    if noise_floor:
        show_noise_floor(spec_array)

    return None
