

--------------------------------------------------------------------------------
# He6DAQ

This repo contains...

--------------------------------------------------------------------------------
### Run an analysis then make interactive plots of cres track features!

#### DAQapp GUI 
This GUI is designed to allow for real-time monitoring of key sensors (the monitor rate and magnetic field) and the database, as well as generate commands for the user to guide them through the commandline interface of data acquisition. Additionally, the GUI has integrated plotting of noise floors and thresholded spectrograms. 

<p align="center"><img width="100%" src="/Documentation/readme_imgs/He6DAQGui.png" />

--------------------------------------------------------------------------------

## Instructions:
* To use the GUI you must first be connected to the CENPA VPN.
* Do not run the GUI on the DAQ computer (10.66.192.48), Instead run it from a laptop or workstation.
* Navigate to He6DAQ/pyqt5_GUI and launch the GUI with
		$ python3 main.py
* At the top are the beta monitor and NMR probe boxes. The plots automatically pull the most recent number of records from the nmr_log and monitor_log tables in the Postgress database at 10.66.192.47. The number of records to pull and plot is set bu the user with the "Records" slider bellow the plots. To start writing to these databases, choose the interval you want (default 10s) and click "Start". You should then see the plot begin to update as new records are added to those tables. Remember to click "Stop" at the end of the data collection! The number displayed in the top right of these boxes is the last measured record. The colored box in the NMR Probe box indicates locked (green) or unlocked (red).
* To take data, open a separate terminal. You will use this to ssh into the DAQ computer in CAVE1.
* The DAQ box generates bash commands for the user in an organized way.
	* Follow the DAQ Hardware set up instructions.
	* In the separate terminal window, enter the commands in the order, starting with those shown under Start DAQ
	* Choose your bitcode and requantization gain and click "Get CLI Command". This makes an instance of LiveDaq and sends the correct bitcode to the ROACH.
	* After sending a new bitcode, callibrate the ADC cores. After calibration, arrange wires for data acquisition.
	* Use the options under Run Parameters to choose the trap config, set field, isotope, RF side, and number of seconds of data to take. This is designed to be idiot-proof and won't let you choose the wrong isotope or trap sign for the main field sign. NOTE that the Set Field goes from -7.00T to 7.00T.
	* The "Get TrapCommand" button will generate the CLI command to program the Kepco power supply that controls the trap coils. Check on the scope that the trap is correct.
	* "Get Acquire Command" generates the data acquisition command for CLI. If you want to edit the length of each acquisition in ms, you can do it here but the default is 1s. You can also type in your run notes in the appropriate place (between the single quotes!)
* The table at the bottom pulls from the run_id table on the database and updates ever second. This lets you see the information for the last 10 run_ids.
* The two boxes on the right allow the user to inspect data after a run is completed. The Noise Profile plot allows you to plot up to 4 noise floors on top of each other. Just enter the run_id(s) and choose what file in acquisition to load (default is the first one). This directory, /pyqt5_GUI, has a directory within it called /temp where spec files are stored. When you press "Plot", the application first looks for the spec file you asked fro in the temp directory. If it is not there, it goes and looks for it on the Cave1 server and downloads it. This will take about a minute per file. Download progress is shown in the DAQ gui terminal to look at that and be patient.
* The Sparse Spectrogram plot lets you inspect a single spec file (given the run_id and file_in_aqq). The user can change the SNR threshold and the plot automatically regenerates. Color corresponds to power for the points over threshold. It is recommended you do not plot more than 1000 slices at a time as you run into RAM problems. Start Packet and Slices options are still being debugged.

### Get set up: 

* pull from google docs.
* Add my monitor ipynb as a visual helper?