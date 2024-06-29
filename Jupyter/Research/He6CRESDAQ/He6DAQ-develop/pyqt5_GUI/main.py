from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import QProcess, QObject, QThread, pyqtSignal, QAbstractTableModel, Qt
from pyqtgraph import PlotWidget
from pyqtgraph import ImageView
import pyqtgraph as pg
import numpy as np
import pandas as pd
import sys
import os
import paramiko
import re
import time
from paramiko.client import SSHClient
from datetime import datetime
from pyqtgraph import DateAxisItem
from scp import SCPClient
from os import path
import qdarktheme
import subprocess


#path to local imports
sys.path.append("/home/heather/He6DAQ/")
from Control_Logic import PostgreSQL_Interface as he6db
from Control_Logic import Data_Quality_Control as DQC
from Control_Logic.Monitor import Monitor
from Control_Logic.NMR import NMR

# Create a worker class to donload large spec files
class Worker(QObject):
	finished = pyqtSignal()
	def __init__(self, rid_path):
		super().__init__()
		finished = pyqtSignal()
		self.rid_path = rid_path

	# Define progress callback that prints the current percentage completed for the file
	def progress(self, filename, size, sent):
		sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent)/float(size)*100) )


	def getFile(self):
		"""Long-running task."""

		# First look for files on Cave 1 server
		try:
			# Create object of SSHClient and
			# connecting to SSH
			ssh = paramiko.SSHClient()
			# here we are loading the system host keys
			ssh.load_system_host_keys()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect('10.66.192.48', port=22, username='daq', password='cenpa123', timeout=3)
			# SCPCLient takes a paramiko transport as its only argument
			scp = SCPClient(ssh.get_transport(), progress = self.progress)
			print("checking for files on the Cave 1 server.")

			scp.get(self.rid_path, "./temp/")
			scp.close()
			ssh.close()
		except:
			print("I did not find that file on the Cave 1 server. Now trying ROCKS.")
		try:
			print('in second try!')
			# Create object of SSHClient and
			# connecting to SSH
			ssh = paramiko.SSHClient()
			# here we are loading the system host keys
			ssh.load_system_host_keys()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
			ssh.connect(hostname="172.25.100.1", username="harringtonh", password='LIGHT', timeout=12)
			scp = SCPClient(ssh.get_transport(), progress = self.progress)
			print("checking for files on ROCKS at /data/eliza4/he6_cres/"+self.rid_path[5:])

			scp.get("/data/eliza4/he6_cres/"+self.rid_path[5:], "./temp/")
			scp.close()
			ssh.close()
		except:
			print("I did not find that file on ROCKS.")
		

		self.finished.emit()

class pandasModel(QAbstractTableModel):

	def __init__(self, data):
		QAbstractTableModel.__init__(self)
		self._data = data

	def rowCount(self, parent=None):
		return self._data.shape[0]

	def columnCount(self, parnet=None):
		return self._data.shape[1]

	def data(self, index, role=Qt.DisplayRole):
		if index.isValid():
			if role == Qt.DisplayRole:
				return str(self._data.iloc[index.row(), index.column()])
		return None

	def headerData(self, col, orientation, role):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			return self._data.columns[col]
		return None

# Create a livedaq class
class LiveDAQ(QObject):
	finished = pyqtSignal()
	def __init__(self):
		super().__init__()
		# Create object of SSHClient and
		# connecting to SSH
		self.ssh = paramiko.SSHClient()
		# here we are loading the system host keys
		self.ssh.load_system_host_keys()
		self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
 
		self.ssh.connect('10.66.192.48', port=22, username='daq',
			password='cenpa123', timeout=3)

		#Make a remote shell
		self.chan = self.ssh.invoke_shell()
		print('Instance of LiveDAQ made!')

	def kill(self):
		self.ssh.close()
		self.finished.emit()

	def start(self):
		self.run_cmd('pwd')

		#self.execute('pwd')
		# below line command will actually
		# execute in your remote machine
		#(stdin, stdout, stderr) = self.ssh.exec_command('cd He6DAQ/ && pwd')
		#(stdin, stdout, stderr) = self.ssh.exec_command('pwd')
		 
		# redirecting all the output in cmd_output
		# variable
		cmd_output = stdout.read()
		print('log printing: ', cmd_output)

	def run_cmd(self,cmd):
		buff = ''
		while not buff.endswith(':~# '):
			resp = self.chan.recv(len(self.chan.in_buffer)).decode('utf-8')
			buff += resp
			print(resp)

		# Send command, wait for response, print response.
		self.chan.send(cmd + '\n')

		buff = ''
		while True:
			resp = self.chan.recv(len(self.chan.in_buffer)).decode('utf-8')
			buff += resp
			print(resp)


class MainWindow(QtWidgets.QMainWindow):

	def __init__(self, *args, **kwargs):
		super(MainWindow, self).__init__(*args, **kwargs)

		#Load the UI Page
		uic.loadUi('He6CRESDAQGUI.ui', self)
		self.setWindowTitle("Main DAQ Window")

		self.monitorRange = 1000
		self.nmrRange = 1000
		self.rgaRange = 1000

		self.monitorScale.valueChanged[int].connect(self.monitorScaleChange)
		self.nmrScale.valueChanged[int].connect(self.nmrScaleChange)
		self.rgaScale.valueChanged[int].connect(self.rgaScaleChange)

	
		self.query_monitor_log = '''
					SELECT monitor_id, rate, created_at
					FROM he6cres_runs.monitor
					ORDER BY monitor_id DESC LIMIT 100
				  '''
		self.query_nmr_log = '''
					SELECT nmr_id, field, created_at, locked
					FROM he6cres_runs.nmr
					ORDER BY nmr_id DESC LIMIT 100
				  '''
		self.query_rga_log = '''
					SELECT run_id, created_at, rga_nitrogen, rga_helium, rga_c02, rga_hydrogen, rga_water, rga_krypton, rga_argon, rga_cf3, rga_ne19, rga_oxygen, rga_tot
					FROM he6cres_runs.run_log
					ORDER BY run_id DESC LIMIT 100
					'''
		self.query_rid_log = '''
					SELECT run_id, created_at, num_spec_acq, monitor_rate, true_field, Isotope, rf_side, run_notes, trap_config
					FROM he6cres_runs.run_log
					ORDER BY run_id DESC LIMIT 10
					'''
		#print(type(self.query_nmr_log))


		#self.t = np.array([])
		#self.B = np.array([])
		#self.marks = np.array([])
		self.monitor_log = he6db.he6cres_db_query(self.query_monitor_log)
		self.nmr_log = he6db.he6cres_db_query(self.query_nmr_log)
		self.rga_log = he6db.he6cres_db_query(self.query_rga_log)
		self.rid_log = he6db.he6cres_db_query(self.query_rid_log)

		#put run_ids in table from db
		#self.runIDTableWidget = TableWidget(df, self)
		model = pandasModel(self.rid_log)
		self.runIDTableView.setModel(model)

		#print(self.monitor_log)
		#self.nmr_log["seattle_time"] = self.nmr_log["created_at"].dt.tz_localize('UTC').dt.tz_convert('US/Pacific').dt.strftime('%H:%M:%S')
		#self.nmr_log["seattle_time"] = self.nmr_log["created_at"].dt.tz_localize('UTC').dt.tz_convert('US/Pacific').dt.tz_localize(None)

		#NOT tz-aware so it's not time-zone local to seattle
		self.monitor_log["UTC_time"] = pd.to_datetime(self.monitor_log["created_at"]).astype('long')/ 10**9
		self.nmr_log["UTC_time"] = pd.to_datetime(self.nmr_log["created_at"]).astype('long')/ 10**9
		self.rga_log["UTC_time"] = pd.to_datetime(self.rga_log["created_at"]).astype('long')/ 10**9

		# Create an axis with a date-time axis (timestamps on x-axis) and attach it to a plot
		axis1 = DateAxisItem(orientation='bottom')
		self.betaMonitorPlot.setAxisItems({'bottom':axis1})
		self.betaMonitorPlot.setLabel(axis='left', text='Rate (Hz)')
		self.betaMonitorPlot.setLabel(axis='bottom', text='Time')
		# show the grids  on the graph
		self.betaMonitorPlot.showGrid(x=True, y=True)

		axis2 = DateAxisItem(orientation='bottom')
		self.nmrPlot.setAxisItems({'bottom':axis2})
		self.nmrPlot.setLabel(axis='left', text='Field (Tesla)')
		self.nmrPlot.setLabel(axis='bottom', text='Time')
		# show the grids  on the graph
		self.nmrPlot.showGrid(x=True, y=True)

		axis3 = DateAxisItem(orientation='bottom')
		self.rgaPlot.setAxisItems({'bottom':axis3})
		self.rgaPlot.setLabel(axis='left', text='Tor')
		self.rgaPlot.setLabel(axis='bottom', text='Time')
		# show the grids  on the graph
		self.rgaPlot.showGrid(x=True, y=True)

		pen = pg.mkPen(color=(0, 80, 239))

		#Field mean and standard deviation over last minute
		self.stdB = self.nmr_log["field"].iloc[0:6].std()
		self.meanB = self.nmr_log["field"].iloc[0:6].mean()
		self.stdp = pg.InfiniteLine(pos=self.meanB+self.stdB, angle=0, movable=False, pen=pg.mkPen('y', width=1, style=QtCore.Qt.DashLine))
		self.stdm = pg.InfiniteLine(pos=self.meanB-self.stdB, angle=0, movable=False, pen=pg.mkPen('y', width=1, style=QtCore.Qt.DashLine))

		#print(np.full(self.nmr_log["UTC_time"].size, self.meanB+self.stdB))

		self.monitor_line = self.betaMonitorPlot.plot(self.monitor_log["UTC_time"], self.monitor_log["rate"], pen=pen)
		self.nmr_line = self.nmrPlot.plot(self.nmr_log["UTC_time"], self.nmr_log["field"], pen=pen)
		self.nmrPlot.addItem(self.stdp, ignoreBounds=True)
		self.nmrPlot.addItem(self.stdm, ignoreBounds=True)

		#All the RGA lines defined here
		self.rga_nitrogen_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_nitrogen"], pen=pg.mkPen(color=(115, 31, 25)))
		self.rga_helium_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_helium"], pen=pg.mkPen(color=(23, 0, 173)))
		self.rga_c02_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_c02"], pen=pg.mkPen(color=(13, 153, 11)))
		self.rga_hydrogen_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_hydrogen"], pen=pg.mkPen(color=(14, 149, 173)))
		self.rga_water_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_water"], pen=pg.mkPen(color=(255, 172, 56)))
		self.rga_oxygen_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_oxygen"], pen=pg.mkPen(color=(125, 250, 250)))
		self.rga_argon_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_argon"], pen=pg.mkPen(color=(251, 0, 255)))
		self.rga_krypton_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_krypton"], pen=pg.mkPen(color=(158, 146, 176)))
		self.rga_cf3_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_cf3"], pen=pg.mkPen(color=(255, 249, 77)))
		self.rga_ne19_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_ne19"], pen=pg.mkPen(color=(82, 0, 204)))
		self.rga_tot_line = self.rgaPlot.plot(self.rga_log["UTC_time"], self.rga_log["rga_tot"], pen=pg.mkPen(color=(255, 255, 255)))

		#beta monitor box
		self.bmStopButton.setEnabled(False)
		self.bmStartButton.setEnabled(True)
		self.bmStartButton.clicked.connect(self.StartMonitor)
		self.bmStopButton.clicked.connect(self.StopMonitor)

		#nmr probe box
		self.nmrStopButton.setEnabled(False)
		self.nmrStartButton.setEnabled(True)
		self.nmrStartButton.clicked.connect(self.StartNMR)
		self.nmrStopButton.clicked.connect(self.StopNMR)

		#Update plots
		#set default time interval
		self.interval = 1000 #ms

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.SecUpdate)
		print("plotting update interval: ", self.interval)
		self.timer.start(self.interval)

		#self.startDAQButton.clicked.connect(self.runRemoteDAQ)
		#self.killDAQButton.clicked.connect(self.killRemoteDAQ)
		self.getCLIButton.clicked.connect(self.UpdateLiveDAQCommand)
		self.getTrapButton.clicked.connect(self.UpdateTrapCommand)
		self.getAquireButton.clicked.connect(self.UpdateAquireCommand)

		self.SNRCut = self.SNRCutSlider.value()
		self.SNRCutSlider.valueChanged[int].connect(self.SNRThreshChange)
		self.noisePlotButton.clicked.connect(self.plotNoises)
		self.sparsePlotButton.clicked.connect(self.plotSparseSpec)

		self.noiseClearButton.clicked.connect(self.clearNoises)
		self.sparseClearButton.clicked.connect(self.clearSparseSpec)

		self.FieldDoubSpinBox.valueChanged.connect(self.SetFieldChange)	

	def SecUpdate(self):
		self.UpdatePlots()
		self.UpdateRunLog()

	def UpdatePlots(self):
		self.monitor_log = he6db.he6cres_db_query(self.query_monitor_log)
		self.nmr_log = he6db.he6cres_db_query(self.query_nmr_log)
		self.rga_log = he6db.he6cres_db_query(self.query_rga_log)

		#NOT tz-aware so it's not time-zone local to seattle
		self.monitor_log["UTC_time"] = pd.to_datetime(self.monitor_log["created_at"]).astype('long')/ 10**9
		self.nmr_log["UTC_time"] = pd.to_datetime(self.nmr_log["created_at"]).astype('long')/ 10**9
		self.rga_log["UTC_time"] = pd.to_datetime(self.rga_log["created_at"]).astype('long')/ 10**9

		self.monitor_line.setData(self.monitor_log["UTC_time"], self.monitor_log["rate"])  # Update the monitor data.
		self.nmr_line.setData(self.nmr_log["UTC_time"], self.nmr_log["field"])  # Update the nmr data.
		#update rga data
		self.rga_nitrogen_line.setData(self.rga_log["run_id"], self.rga_log["rga_nitrogen"])
		self.rga_helium_line.setData(self.rga_log["run_id"], self.rga_log["rga_helium"])
		self.rga_c02_line.setData(self.rga_log["run_id"], self.rga_log["rga_c02"])
		self.rga_hydrogen_line.setData(self.rga_log["run_id"], self.rga_log["rga_hydrogen"])
		self.rga_water_line.setData(self.rga_log["run_id"], self.rga_log["rga_water"])
		self.rga_oxygen_line.setData(self.rga_log["run_id"], self.rga_log["rga_oxygen"])
		self.rga_argon_line.setData(self.rga_log["run_id"], self.rga_log["rga_argon"])
		self.rga_krypton_line.setData(self.rga_log["run_id"], self.rga_log["rga_krypton"])
		self.rga_cf3_line.setData(self.rga_log["run_id"], self.rga_log["rga_cf3"])
		self.rga_ne19_line.setData(self.rga_log["run_id"], self.rga_log["rga_ne19"])
		self.rga_tot_line.setData(self.rga_log["run_id"], self.rga_log["rga_tot"])

		self.curMonitor.setText(str(self.monitor_log["rate"].iloc[0])+" Hz")
		self.curNMR.setText(str(self.nmr_log["field"].iloc[0])+" T")
		self.curPres.setText(str(self.rga_log["rga_tot"].iloc[0])+" Tor")

		if self.nmr_log["locked"].iloc[0] == True:
			self.LockedIndicator.setStyleSheet("background-color: green; border: 1px solid black;")
		else:
			self.LockedIndicator.setStyleSheet("background-color: red; border: 1px solid black;")

	def UpdateRunLog(self):
		model = pandasModel(self.rid_log)
		self.runIDTableView.setModel(model)
		self.rid_log = he6db.he6cres_db_query(self.query_rid_log)

	#Beta monitor box
	#--------------------------------------
	def StartMonitor(self):
		# getting current value chosen for the beta monitor interval 
		self.bmInterval = self.monitorIntSpinBox.value()
		# Start beta monitor bring written to database with that interval
		self.monitor = Monitor(self.bmInterval)
		self.monitor.start()
		print("Starting beta monitor!")
		self.bmStopButton.setEnabled(True)
		self.bmStartButton.setEnabled(False)

	def StopMonitor(self):
		#monitor.stop()
		print("Stopping beta monitor!")
		self.bmStopButton.setEnabled(False)
		self.bmStartButton.setEnabled(True)

	def monitorScaleChange(self):
		self.monitorRange = self.monitorScale.value()
		self.monitorPlotNumRecLabel.setText(str(self.monitorRange))
		self.query_monitor_log = '''
					SELECT monitor_id, rate, created_at
					FROM he6cres_runs.monitor
					ORDER BY monitor_id DESC LIMIT 
				  ''' + str(self.monitorRange)
	#---------------------------------------

	#NMR Probe box
	#---------------------------------------
	def StartNMR(self):
		# getting current value chosen for the beta monitor interval 
		self.nmrInterval = self.nmrIntSpinBox.value()
		# Start beta monitor bring written to database with that interval
		self.nmr = NMR(self.nmrInterval)
		self.nmr.start()
		print("Starting NMR probe write!")
		self.nmrStopButton.setEnabled(True)
		self.nmrStartButton.setEnabled(False)

	def StopNMR(self):
		self.nmr.stop()
		print("Stopping NMR probe write!")
		self.nmrStopButton.setEnabled(False)
		self.nmrStartButton.setEnabled(True)

	def nmrScaleChange(self):
		self.nmrRange = self.nmrScale.value()
		self.nmrPlotNumRecLabel.setText(str(self.nmrRange))
		self.query_nmr_log = '''
					SELECT nmr_id, field, created_at, locked
					FROM he6cres_runs.nmr
					ORDER BY nmr_id DESC LIMIT 
				  ''' + str(self.nmrRange)
	#---------------------------------------

	#RGAbox
	#--------------------------------------
	def rgaScaleChange(self):
		self.rgaRange = self.rgaScale.value()
		self.rgaPlotNumRecLabel.setText(str(self.rgaRange))
		self.query_rga_log = '''
					SELECT run_id, created_at, rga_nitrogen, rga_helium, rga_c02, rga_hydrogen, rga_water, rga_krypton, rga_argon, rga_cf3, rga_ne19, rga_oxygen, rga_tot
					FROM he6cres_runs.run_log
					ORDER BY run_id DESC LIMIT 
					''' + str(self.rgaRange)
	#---------------------------------------

	#Noise plot
	#--------------------------------------
	def plotNoises(self):
		slices=10000
		start_packet=0

		self.NoisePlot.setLabel(axis='left', text='arb. roach units')
		self.NoisePlot.setLabel(axis='bottom', text='freq bin')
		self.NoisePlot.addLegend(offset=5)
		self.NoisePlot.showGrid(x=True, y=True)

		if self.rid1.toPlainText() != "":
			print("Looking for run_id: "+ self.rid1.toPlainText() + " a" +self.fia.toPlainText())
			try:
				rid1_path, rid1_fc = DQC.get_spec_file_info(self.rid1.toPlainText(),self.fia.toPlainText())
				#print("Requested file: "+rid1_path)
			except:
				print("I did not find that run_id on the database.")
				return None

			#First check if the file is already local!
			if path.exists("./temp/"+rid1_path[14:]):
				print(rid1_path[14:] +" is already local in ./temp !")
			else:
				#If not local, go get it from DAQ computer in Cave 1
				self.thread = QThread()
				self.worker = Worker(rid1_path)
				self.worker.moveToThread(self.thread)
				# Step 5: Connect signals and slots
				self.thread.started.connect(self.worker.getFile)
				self.worker.finished.connect(self.thread.quit)
				self.worker.finished.connect(self.worker.deleteLater)
				self.thread.finished.connect(self.thread.deleteLater)
				#self.worker.progress.connect(self.reportProgress)

				#self.StopDownButton.clicked.connect(lambda: self.thread.quit)

				# Step 6: Start the thread
				self.thread.start()

				# Final resets
				self.thread.finished.connect(
					lambda: print("Done fetching first file!")
	   			)
			if path.exists("./temp/"+rid1_path[14:]):
				spec1_array = DQC.spec_to_array("./temp/"+rid1_path[14:], rid1_fc, slices=slices, start_packet=start_packet)
				self.noise1 = self.NoisePlot.plot(spec1_array.mean(axis=1), name = self.rid1.toPlainText(), pen=pg.mkColor(191,228,118))

		if self.rid2.toPlainText() != "":
			print("Looking for run_id: "+ self.rid2.toPlainText() + " a" +self.fia.toPlainText())
			try:
				rid2_path, rid2_fc = DQC.get_spec_file_info(self.rid2.toPlainText(),self.fia.toPlainText())
				#print("Requested file: "+rid2_path)
			except:
				print("I did not find that run_id on the database.")
				return None

			#First check if the file is already local!
			if path.exists("./temp/"+rid2_path[14:]):
				print(rid2_path[14:] +" is already local in ./temp !")
			else:
				#If not local, go get it from DAQ computer in Cave 1 and then ROCKS
				self.thread = QThread()
				self.worker = Worker(rid2_path)
				self.worker.moveToThread(self.thread)
				# Step 5: Connect signals and slots
				self.thread.started.connect(self.worker.getFile)
				self.worker.finished.connect(self.thread.quit)
				self.worker.finished.connect(self.worker.deleteLater)
				self.thread.finished.connect(self.thread.deleteLater)
				#self.worker.progress.connect(self.reportProgress)
				# Step 6: Start the thread
				self.thread.start()

				# Final resets
				self.thread.finished.connect(
					lambda: print("Done fetching second file!")	
		   		)
			if path.exists("./temp/"+rid2_path[14:]):
				spec2_array = DQC.spec_to_array("./temp/"+rid2_path[14:], rid2_fc, slices=slices, start_packet=start_packet)
				self.noise2 = self.NoisePlot.plot(spec2_array.mean(axis=1), name = self.rid2.toPlainText(), pen=pg.mkColor(154,206,223))

		if self.rid3.toPlainText() != "":
			print("Looking for run_id: "+ self.rid3.toPlainText() + " a" +self.fia.toPlainText())
			try:
				rid3_path, rid3_fc = DQC.get_spec_file_info(self.rid3.toPlainText(),self.fia.toPlainText())
				#print("Requested file: "+rid3_path)
			except:
				print("I did not find that run_id on the database.")
				return None

			#First check if the file is already local!
			if path.exists("./temp/"+rid3_path[14:]):
				print(rid3_path[14:] +" is already local in ./temp !")
			else:
				#If not local, go get it from DAQ computer in Cave 1 and then ROCKS
				self.thread = QThread()
				self.worker = Worker(rid3_path)
				self.worker.moveToThread(self.thread)
				# Step 5: Connect signals and slots
				self.thread.started.connect(self.worker.getFile)
				self.worker.finished.connect(self.thread.quit)
				self.worker.finished.connect(self.worker.deleteLater)
				self.thread.finished.connect(self.thread.deleteLater)
				#self.worker.progress.connect(self.reportProgress)
				# Step 6: Start the thread
				self.thread.start()

				# Final resets
				self.thread.finished.connect(
					lambda: print("Done fetching second file!")	
		   		)
			if path.exists("./temp/"+rid3_path[14:]):
				spec3_array = DQC.spec_to_array("./temp/"+rid3_path[14:], rid3_fc, slices=slices, start_packet=start_packet)
				self.noise3 = self.NoisePlot.plot(spec3_array.mean(axis=1), name = self.rid3.toPlainText(), pen=pg.mkColor(255, 189, 56))
		
		if self.rid4.toPlainText() != "":
			print("Looking for run_id: "+ self.rid4.toPlainText() + " a" +self.fia.toPlainText())
			try:
				rid4_path, rid4_fc = DQC.get_spec_file_info(self.rid4.toPlainText(),self.fia.toPlainText())
				#print("Requested file: "+rid4_path)
			except:
				print("I did not find that run_id on the database.")
				return None

			#First check if the file is already local!
			if path.exists("./temp/"+rid4_path[14:]):
				print(rid4_path[14:] +" is already local in ./temp !")
			else:
				#If not local, go get it from DAQ computer in Cave 1 and then ROCKS
				self.thread = QThread()
				self.worker = Worker(rid4_path)
				self.worker.moveToThread(self.thread)
				# Step 5: Connect signals and slots
				self.thread.started.connect(self.worker.getFile)
				self.worker.finished.connect(self.thread.quit)
				self.worker.finished.connect(self.worker.deleteLater)
				self.thread.finished.connect(self.thread.deleteLater)
				#self.worker.progress.connect(self.reportProgress)
				# Step 6: Start the thread
				self.thread.start()

				# Final resets
				self.thread.finished.connect(
					lambda: print("Done fetching second file!")	
		   		)
			if path.exists("./temp/"+rid4_path[14:]):
				spec4_array = DQC.spec_to_array("./temp/"+rid4_path[14:], rid4_fc, slices=slices, start_packet=start_packet)
				self.noise4 = self.NoisePlot.plot(spec4_array.mean(axis=1), name = self.rid4.toPlainText(), pen=pg.mkColor(95, 56, 193))

		elif ((self.rid1.toPlainText() == "") and (self.rid2.toPlainText() == "") and (self.rid3.toPlainText() == "") and (self.rid4.toPlainText() == "")):
			print("No run_ids selected! Please enter one or more run_ids and try again.")

	#Clear Noise plot
	#--------------------------------------
	def clearNoises(self):
		print("clearing noise!")
		self.NoisePlot.clear()
	#---------------------------------------

	#SNR Thresh Slider
	#--------------------------------------
	def SNRThreshChange(self):
		self.SNRCut = self.SNRCutSlider.value()
		self.SNRCutlabel.setText(str(self.SNRCut))
		self.plotSparseSpec()
	#---------------------------------------

	#Sparse spectrogram plot
	#--------------------------------------
	def plotSparseSpec(self):
		slices=1000
		start_packet=0
		start_packet = int(self.StartPacketText.toPlainText())
		#slices = int(self.SlicesText.toPlainText())

		# Set a custom color map
		colors = [
			(0, 0, 0),
			(0, 29, 255),
			(0, 160, 255),
			(0, 246, 255),
			(255, 255, 255)
		]
		# color map
		cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 5), color=colors)

		# setting color map to the image view
		self.SperseSpecPlot.setColorMap(cmap)

		#self.SperseSpecPlot.setLabel(axis='left', text='freq bin')
		#self.SperseSpecPlot.setLabel(axis='bottom', text='time slice')

		if self.rid1s.toPlainText() != "":
			rid1s_path, rid1s_fc = DQC.get_spec_file_info(self.rid1s.toPlainText(),self.fias.toPlainText())
			print("Requested file: "+rid1s_path)

			#First check if the file is already local!
			if path.exists("./temp/"+rid1s_path[14:]):
				print(rid1s_path[14:] +" is already local in ./temp !")
			else:
				#If not local, go get it from DAQ computer in Cave 1
				self.thread = QThread()
				self.worker = Worker(rid1s_path)
				self.worker.moveToThread(self.thread)
				# Step 5: Connect signals and slots
				self.thread.started.connect(self.worker.getFile)
				self.worker.finished.connect(self.thread.quit)
				self.worker.finished.connect(self.worker.deleteLater)
				self.thread.finished.connect(self.thread.deleteLater)
				#self.worker.progress.connect(self.reportProgress)

				#self.StopDownButton.clicked.connect(lambda: self.thread.quit)

				# Step 6: Start the thread
				self.thread.start()

				# Final resets
				self.thread.finished.connect(
					lambda: print("Done fetching first file!")
	   			)
			if path.exists("./temp/"+rid1s_path[14:]):
				spec1_array = DQC.spec_to_array("./temp/"+rid1s_path[14:], rid1s_fc, slices=slices, start_packet=start_packet)
				#cut_condition1 = np.array((spec1_array < np.expand_dims(spec1_array.mean(axis=1), axis=1) * self.SNRCut), dtype=int)
				spec1_array[spec1_array < (np.expand_dims(spec1_array.mean(axis=1), axis=1) * self.SNRCut)]=0

				self.SperseSpecPlot.setImage(spec1_array.T)
				self.SperseSpecPlot.view.invertY(False)

		else:
			print("No run_ids selected! Please enter one or more run_ids and try again.")

	#---------------------------------------

	#Clear spec plot
	#--------------------------------------
	def clearSparseSpec(self):
		print("clearing sparse spec!")
		self.SperseSpecPlot.clear()
	#---------------------------------------

	def SetFieldChange(self):
		if self.FieldDoubSpinBox.value()>0:
			self.He6Button.setCheckable(False)
			self.Ne19Button.setCheckable(True)
		elif self.FieldDoubSpinBox.value()<0:
			self.Ne19Button.setCheckable(False)
			self.He6Button.setCheckable(True)
		else:
			self.He6Button.setCheckable(False)
			self.Ne19Button.setCheckable(False)	

	def UpdateLiveDAQCommand(self):
		if self.bitcode12button.isChecked():
			freqBins = "4096"
		elif self.bitcode15button.isChecked():
			freqBins = "32768"
		else:
			print("no bitcode selected!")
		command = "CLI = LiveDAQ(freq_ch = " + freqBins +", requant_gain = "+ str(self.rGainSpin.value())+")"
		self.LiveDAQcommandBox_1.setPlainText(command)

	def UpdateTrapCommand(self):
		if self.trapoffB.isChecked():
			command = "CLI.trap_const_curr(curr = 0)"
		elif self.consttrapB.isChecked():
			F = self.FieldDoubSpinBox.value()
			I = round(F * (1.8/3.25),6)
			command = "CLI.trap_const_curr(curr = "+str(-I)+")"
		elif self.trapslewB.isChecked():
			F = self.FieldDoubSpinBox.value()
			I = round(F * (1.8/3.25),6)
			command = "CLI.trap_slew(curr_list =["+str(-I)+", 0.0], dwell_list = [0.035, 0.020])"
		else:
			print("no bitcode selected!")
		self.LiveDAQcommandBox_2.setPlainText(command)

	def UpdateAquireCommand(self):
		if self.Ne19Button.isChecked():
			isotope = '19Ne'
		elif self.He6Button.isChecked():
			isotope = '6He'
		else:
			print("no isotope selected!")
			isotope = 'NA'

		if self.IsideButton.isChecked():
			side = '1'
		elif self.UsideButton.isChecked():
			side = '0'
		else:
			print("no isotope selected!")

		command = "CLI.take_FD_data(acq_size = "+self.aquSizeBox.toPlainText()+", acq_length_ms = 1000, isotope = '"+isotope+"', set_field = "+str(self.FieldDoubSpinBox.value())+", run_notes = '' , rf_side ="+ side +")"
		self.LiveDAQcommandBox_3.setPlainText(command)


'''
	def runRemoteDAQ(self):

		self.thread = QThread()
		#self.livedaq = Worker(self.rGainSpin.value())
		self.livedaq = LiveDAQ()
		# Move livedaq to the thread
		self.livedaq.moveToThread(self.thread)
		# Connect signals and slots
		#self.livedaq.execute('pwd')
		self.thread.started.connect(self.livedaq.start)

		self.livedaq.finished.connect(self.thread.quit)
		self.livedaq.finished.connect(self.livedaq.deleteLater)
		self.thread.finished.connect(self.thread.deleteLater)
		# Start the thread
		self.thread.start()

		# Final resets
		self.thread.finished.connect(
			lambda: print("done!")
		)

	def killRemoteDAQ(self):
		self.livedaq.kill()
'''
		
def main():
	try:
		print("checking database connection")
		subprocess.check_output(["ping", "-c", "1", "10.66.192.47"])
		app = QtWidgets.QApplication(sys.argv)
		qdarktheme.setup_theme()
		main = MainWindow()
		main.show()
		sys.exit(app.exec_())				  
	except subprocess.CalledProcessError:
		print("Could not connect to SQL database at 10.66.192.47. Check VPN connection and try again.")
		quit()



if __name__ == '__main__':
	main()