#!/bin/bash
if [ -f "LMS_setup_date.txt" ]
then
    rundate=$(<LMS_setup_date.txt)
    echo "I think you've already set up the Vaunix LMS support"
    echo "for Python3. I think so because I see a file called"
    echo "'LMS_setup_date.txt' that says this was run"
    echo "on $rundate. If you want to run it"
    echo "again, that's fine. Just delete 'LMS_setup_date.txt'"
    echo "and we should be good to go."
else
    # Let's remember that we've already done this
    date > LMS_setup_date.txt
    # Make sure the Pi knows about the latest updates
    sudo apt-get update
    # Get the basic building tools if they aren't here already
    sudo apt-get install build-essential
    # EMACS is a cool editor. Uncomment this to get it
    #sudo apt-get install emacs
    # Firefox is a better browser. Uncomment this to get it
    #sudo apt-get install iceweasel
    # We probably already have Python 3, but we'll make sure
    sudo apt-get install python3
    sudo apt-get upgrade python3
    # And get the dev tools for it
    sudo apt-get install python3.4-dev
    # This is the USB library
    sudo apt-get install libusb-1.0
    sudo apt-get install libusb-dev
    # Make sure that whole machine has the latest of everything. Uncomment if you like.
    #sudo apt-get upgrade
    # Build the LMS library and the C test program. We need the .o file
    #   to install the Python extension
    sudo make
    # Install the LMS Python extension and upgrade it if necessary
    sudo pip3 install . --upgrade
    #
    #
    # If we want to just run the test program now we can.
    #   Because the USB access is priveleged, you have to use 'sudo'
    #   to run Python and access the USB library.
    sudo python3 LMS_test.py
    #
    # Alternatively you can play with the test program interactively
    #   in IDLE. Once it starts, use File->Open to open 'LMS_test.py'
    #sudo idle3
    echo "Don't forget to use 'sudo' when you run Python."
    echo "'sudo python3 LMS_test.py' runs the sample test program."
    echo "'sudo idle3' brings up the interactive IDLE environment."
fi
