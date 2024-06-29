# TO DO:
# * Don't put "list" in the name of a list. Change this.

import numpy as np
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import typing
from typing import List
import pathlib

# Local modules.
from . import PostgreSQL_Interface as he6db


def packetIDs(spec_path, BUFFERSIZE):
    dtype = np.dtype("B")
    try:
        with open(spec_path, "rb") as f:
            numpy_data = np.fromfile(f, dtype)
        # Parse spec file
        packet_num = int(numpy_data.size / BUFFERSIZE)
        numpy_data.shape = (packet_num, BUFFERSIZE)
        header_data = numpy_data[:, 0:4]
        packetID = header_data[:, 1] * 2**16 + header_data[:, 2] * 2**8 + header_data[:, 3]
        
    except IOError:
        print("Error While Opening the file!")
        packetID = None

    return packetID.astype(int)


def gap_report(spec_path, BUFFERSIZE, no_report):

    # Current convention:
    # -1 = No report run.
    # -2 = No file found in DAQ file system.

    if no_report:
        print("\nno_report = True")
        packets = -1
        num_dropped_packets = -1
        frac_of_packets_dropped = -1
        num_gaps = -1
        neg_gaps = -1
        mean_gap = -1
        std_gap = -1
        max_gap = -1

    else:

        packetID = packetIDs(spec_path, BUFFERSIZE)

        if packetID is None:

            packets = -2
            num_dropped_packets = -2
            frac_of_packets_dropped = -2
            num_gaps = -2
            neg_gaps = -2
            mean_gap = -2
            std_gap = -2
            max_gap = -2

        else:
            packets = len(packetID)
            gaps = (packetID[1:] - packetID[:-1]) - 1
            neg_gaps = np.count_nonzero(gaps < 0)
            gaps[gaps < 0] = 0
            num_gaps = np.count_nonzero(gaps)
            num_dropped_packets = gaps.sum()
            frac_of_packets_dropped = num_dropped_packets / packets
            if num_gaps == 0:
                mean_gap = 0
                std_gap = 0
            else:
                mean_gap = gaps[gaps > 0].mean()
                std_gap = gaps[gaps > 0].std()

            max_gap = gaps.max()

    return (
        packets,
        num_dropped_packets,
        frac_of_packets_dropped,
        num_gaps,
        neg_gaps,
        mean_gap,
        std_gap,
        max_gap,
    )


def packet_report(spec_file_list, BUFFERSIZE, no_report, delete_imperfect_files):

    for file_in_acq, spec_dict in enumerate(spec_file_list):

        spec_path = spec_dict["file_path"]
        (
            packets,
            num_dropped_packets,
            frac_of_packets_dropped,
            num_gaps,
            neg_gaps,
            mean_gap,
            std_gap,
            max_gap,
        ) = gap_report(spec_path, BUFFERSIZE, no_report)

        print("\nGap Report for file_in_acq: {} ".format(file_in_acq))
        print("packets: ", packets)
        print("num_dropped_packets: ", num_dropped_packets)
        print("frac_of_packets_dropped: ", frac_of_packets_dropped)
        print("neg_gaps: ", neg_gaps)
        print("num_gaps: ", num_gaps)
        print("mean_gap: ", mean_gap)
        print("std_gap: ", std_gap)
        print("max_gap: ", max_gap)

        spec_dict["num_dropped_packets"] = num_dropped_packets
        spec_dict["frac_of_packets_dropped"] = frac_of_packets_dropped
        spec_dict["num_gaps"] = num_gaps
        spec_dict["neg_gaps"] = neg_gaps
        spec_dict["mean_gap"] = mean_gap
        spec_dict["std_gap"] = std_gap
        spec_dict["max_gap"] = max_gap
        spec_dict["deleted"] = False

        if delete_imperfect_files and num_dropped_packets > 0:
            spec_dict["deleted"] = True

    return spec_file_list


# def flatten(t):
#     return [item for sublist in t for item in sublist]


def run_packet_report(run_ids: list, freq_ch: int = 4096) -> None:

    if freq_ch == 4096:
        BUFFERSIZE = 4128
    elif freq_ch == 32768:
        BUFFERSIZE = 8224
    else:
        raise ValueError(
            "freq_ch must currently be 4096 or 32768. You input {}.".format(freq_ch)
        )

    spec_lists = []
    spec_ids = []
    for run_id in run_ids:

        query_spec = """SELECT * FROM he6cres_runs.spec_files
               WHERE run_id = {}
               AND num_dropped_packets = -1
               ORDER BY run_id DESC LIMIT 10000
            """.format(
            run_id
        )

        spec_log = he6db.he6cres_db_query(query_spec)
        spec_file_path_list = spec_log.file_path.to_list()
        spec_id_list = spec_log.spec_id.to_list()

        print(
            "\nrun_id: {}. Running packet report on {} files.\n".format(
                run_id, len(spec_file_path_list)
            )
        )
        spec_list = []

        for i, (spec_file_path, spec_id) in enumerate(
            zip(spec_file_path_list, spec_id_list)
        ):

            # Fill this empty dict
            spec_dict = {
                "file_size_mb": None,
                "packets": None,
                "spec_id": spec_id,
                "file_path": spec_file_path,
                "file_in_acq": None,
            }

            spec_list.append(spec_dict)

        # Run packet report:
        spec_list = packet_report(spec_list, BUFFERSIZE, False, delete_imperfect_files)

        he6db.write_packet_report_to_he6db(spec_list)

    return None


def delete_files(spec_file_path_list: List):

    for file_path in spec_file_path_list:
        file_path = pathlib.Path(file_path)
        file_path.unlink(missing_ok=False)

        print(
            "\nfile_path: {}. deleted: {}.".format(file_path, not file_path.is_file())
        )

    return None


def delete_run_ids(run_id_list):
    """
    BE CAREFUL WITH THIS FUNCTION.
    """
    for run_id in run_id_list:

        query = """
                    SELECT spec_id, file_path 
                    FROM he6cres_runs.spec_files
                    WHERE run_id = {}
                  """.format(
            run_id
        )

        result = he6db.he6cres_db_query(query)
        spec_file_path_list = result.file_path.to_list()
        print(
            "\nDeleting run_id: {}, spec_ids: {} \n".format(
                run_id, result.spec_id.to_list()
            )
        )

        # Delete the list of files
        delete_files(spec_file_path_list)
        # Mark as deleted in the db:

        he6db.mark_spec_files_as_deleted(run_id)

    return None
