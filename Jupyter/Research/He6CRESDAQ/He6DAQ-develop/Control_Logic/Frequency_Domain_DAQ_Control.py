#!/usr/bin/env python3

from time import time
from datetime import datetime
from multiprocessing import Process, Queue
from .Frequency_Domain_Packet_Receiver import FDPreceiver

class DAQ_SpecWriter:
    """
    Handles input of frequency-domain packets from 10GbE interface and
    saving to multiple SSDs simultaneously via multithreading

    Interfaces with Frequency_Domain_Packet_Receiver (class FDPreceiver)
    for packet input
    """

    def __init__(self,  boffile = 'he6_cres_correlator_2021_Mar_23_1937.bof',
                 dsoc_desc = ("0.0.0.0",4003)):
        self.receiver = FDPreceiver(dsoc_desc)
        self.output_file = ("/mnt/sdb/data/" +
                            "Freq_data_0000-00-00-00-00-00_0000000.spec")

    def pipeline_to_disk (self, in_queue, baton, packets, out_dir,
    out_file_name, out_file_ext):
        """
        Write a given number of packets to binary files in a specified output
        directory. This method supports the use of queues and can
        simultaneously be run in multiple threads to acquire contiguous,
        non-overlapping blocks of data and write interleaved file sets onto
        separate disks.

        ----------Parameters----------
        in_queue (queue): The queue of blocks to acquire.
        baton (queue): The single-item queue to indicate whether data is being
            actively acquired by another thread running this method
        packets (int): The number of packets in a block to be acquired
        out_dir(char_string): The directory to write binary files to
        out_file_name (char_string): The common name that all files will have
        out_file_ext (char_string): the extension with which to name files

        ------------Outputs------------
        Output will be a set of files to out_dir, each with out_file_name
        followed by a unique number and a common extension.

        For example, output_test_test_1.txt, output_test_test_4.txt,
        output_test_test_7.txt, etc. would be written to /mnt/sdb/data/,
        while a separate thread running the same function would write
        output_test_2.txt, ouput_test_5.txt, output_test_8.txt, etc.
        to /mnt/sdc/data/. Each file will be in binary format containing
        raw packet data. The number of packets per file is specified by the
        packets argument.
        """
        # each pass will write one block of data to file
        while not in_queue.empty():
            # wait for other process(es) to finish getting packets
            if not baton.empty():
                # the 'baton' should be held by only one thread at a time
                baton.get()
                if (in_queue.empty()):  #this if statement prevents hanging
                    baton.put(1)
                    return 1
                # get the number of the output file from the queue
                file_num = in_queue.get()
                file_num_str = "{:06}".format(file_num)
                out_file = out_dir+out_file_name+file_num_str+out_file_ext
                # get the specified # of packets
                pkts = self.receiver.grab_packets(n = packets)
                # "pass the baton" to any process waiting to get packets
                baton.put(1)
                # Pass "wb" to write a new file
                with open(out_file, "wb") as binary_file:
                    for line_num in range(packets):
                        # Write packet to the file
                        binary_file.write(pkts[line_num])
                print("File {0} written".format(out_file))
                self.output_file = out_file

    def save_packets(self, acquisitions = 180, acq_length = 5000, descrip = ""):
        """
        Write a given number of binary files, each containing a given
        number of raw packets.

        ----------Parameters----------
        acquisitions (int): The number of files to save
        acq_length (int): The number of packets in an output file
        out_file_name (char_string): The common name that all files will have
        out_file_ext (char_string): the extension with which to name files

        ------------Outputs------------
        Output will be a set of files to out_dir, each with out_file_name
        followed by a unique number and a common extension. For example,
        output_test_test_1.txt, output_test_test_4.txt,
        output_test_test_7.txt, etc. would be written to /mnt/sdb/data/,
        while a separate thread running the same function would write
        output_test_2.txt, ouput_test_5.txt, output_test_8.txt, etc.
        to /mnt/sdc/data/. Each file will be in binary format containing
        raw packet data. The number of packets per file is specified by the
        packets argument.
        """

        if descrip == (""):
            print("Hey! YOU!")
            print("You're the one who knows what this data is for!")
            print("Write it down in the descrip() field!!")
            return

        descrip_strings = descrip.split(',')
        descrip_file_dir = "/mnt/sdb/data/"
        descrip_file_name = "Env_conditions_{:%Y-%m-%d-%H-%M-%S_}".format(datetime.now())
        descrip_file_ext = ".txt"
        descrip_file = descrip_file_dir+descrip_file_name+descrip_file_ext
        with open(descrip_file, "w") as dfile:
            for i in range (len(descrip_strings)):
                dfile.write(descrip_strings[i])
                dfile.write("\n")

        in_queue = Queue()
        for i in range(acquisitions):
            in_queue.put(i)

        baton = Queue()
        baton.put(1)

        start = time()

        out_file_name = "Freq_data_{:%Y-%m-%d-%H-%M-%S_}".format(datetime.now())
        out_file_ext = ".spec"

        out_dir_b = "/mnt/sdb/data/"
        line_b = Process(target = self.pipeline_to_disk,
        args=(in_queue, baton, acq_length, out_dir_b,
        out_file_name, out_file_ext))

        out_dir_c = "/mnt/sdc/data/"
        line_c = Process(target = self.pipeline_to_disk,
        args=(in_queue, baton, acq_length, out_dir_c,
        out_file_name, out_file_ext))

        out_dir_d = "/mnt/sdd/data/"
        line_d = Process(target = self.pipeline_to_disk,
        args=(in_queue, baton, acq_length, out_dir_d,
        out_file_name, out_file_ext))

        line_b.start()
        line_c.start()
        line_d.start()

        line_b.join()
        line_c.join()
        line_d.join()

        #print('Total time: {:2.2f} seconds'.format(time()-start))
