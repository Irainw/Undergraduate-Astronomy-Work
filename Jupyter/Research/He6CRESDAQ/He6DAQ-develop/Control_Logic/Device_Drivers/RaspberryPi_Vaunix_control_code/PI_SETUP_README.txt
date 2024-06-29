This is version 0.2 of the Vaunix LMS Python library. It assumes you have
a Raspberry Pi running Jessie or something similarly recent and that
you are connected to the internet so it can install the necessary code.

A handy install script is included to update your Pi and install stuff. To run
it, bring up a terminal, 'cd' to this directory and run the script by typing

   ./pi_setup.sh

You will probably see that some installations are already done and that's okay. If
the updates try to update other things we don't use here, it's up to you.

After the installation is complete you can run the sample Python script by typing

   sudo python3 LMS_test.py

or by going into IDLE and then loading the file 'LMS_test.py'. Be sure to 
use sudo when you start IDLE.

   sudo idle3

Ths files in this release are:

LMShid.c ---------------------- The LMS C library, version 1.02
LMShid.h ---------------------- The LMS C library include, version 1.02
LMS_module.c ------------------ The C code for the Python3 extensions, version 0.1
LMS_test.py ------------------- A test/example script written in Python
makefile ---------------------- Builds the C code
pi_setup.sh ------------------- A BASH script to install stuff you need
README_FIRST.txt -------------- This file
Sample test script output.txt - An example of what the LMS_test program outputs
setup.py ---------------------- The Python script that PIP uses to install the extension
test.c ------------------------ A C version of LMS_test.py (from C version 1.02)
