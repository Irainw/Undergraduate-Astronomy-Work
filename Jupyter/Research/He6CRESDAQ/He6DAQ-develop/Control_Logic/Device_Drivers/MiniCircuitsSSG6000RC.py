#!/usr/bin/env python2

from socket import socket, AF_INET, SOCK_DGRAM

class dsocket(socket):

    def sendMessage(self, message):
        try:
            self.send(str.encode(message))
        except RuntimeError:
            raise RuntimeError("Error: Synthesizer not responding")

class MCSSG:
    
    def __init__(self, dsoc_desc=("10.66.192.34",80)):
        """
        Initialize a minicircuits SSG; open a data socket from the client side 
        for communication

        ----------Parameters----------
        dsoc_desc (tuple): A tuple with the first element the IP address/port
            and the second element the port where data is to be received. 
        """
        self.ds = dsocket(AF_INET,SOCK_DGRAM)
        if not dsoc_desc is None:
            try:
                self.ds.connect(dsoc_desc)
            except RuntimeError:
                raise RuntimeError("Error: Unable to connect to server at {0}".format(dsoc_desc))
        self.ds.settimeout(30)

    def getRF_status(self):
        """
        Returns string representing RF status 'ON' or 'OFF'
        """
        self.ds.sendMessage("GET/PWR:RF?\r\n\r\n")
        response = self.ds.recv(128)
        length = response[58:60] 
        RF_status =  response[64:64+length]
        return RF_status
    
    def setRF_on(self):
        """
        Turns RF power ON. Returns error condition 0 upon success
        """
        self.ds.sendMessage("SET/PWR:RF:ON\r\n\r\n")  
        response = self.ds.recv(64)                    
        OK = response[63:64]
        if not OK:
            raise RuntimeError("Error: Unable to turn on RF")
        else:
            return 0
    
    def setRF_off(self):
        """
        Turns RF power OFF. Returns error condition 0 upon success
        """
        self.ds.sendMessage("SET/PWR:RF:OFF\r\n\r\n")                      
        response = self.ds.recv(64)
        OK = response[63:64]
        if not OK:
            raise RuntimeError("Error: Unable to turn off RF")
        else:
            return 0

    def getPower(self):
        """
        Returns float representing output power in dBm
        """
        self.ds.sendMessage("GET/PWR?\r\n\r\n")
        response = self.ds.recv(128)
        length  =  int(response[58:60])
        if length < 10:
            power =  float(response[63:63+length])
        else:
            power =  float(response[64:64+length])
        return power

    def getFreq(self):
        """
        Returns float representing output frequency in MHz
        """
        self.ds.sendMessage("GET/FREQ?\r\n\r\n")
        response = self.ds.recv(128)
        length  =  int(response[58:60])
        if length < 10:    
            frequency =  float(response[63:63+length])
        else:
            frequency =  float(response[64:64+length])
        return frequency

    def setPower(self, power):
        """
        Set fixed output power and verifies that RF is ON
        power (float): The output power in dBm
        Returns error condition 0 upon success
        """
        if power > 10.0:
            raise RuntimeError("Error: Attempted to set power above +10.0 dBm maximum")
        else:
            if self.setRF_on:
                raise RuntimeError("Error: Unable to turn on RF")
            else:
                self.ds.sendMessage("SET/PWR:{0}\r\n\r\n".format(power))                      
                response = self.ds.recv(64)
                OK = int(response[63:64])
                if not OK:
                    raise RuntimeError("Error: Unable to set power") 
                else:
                    return 0
    
    def setFreq(self, frequency):
        """
        Set fixed output frequency
        frequency (float): The output frequency in MHz
        Returns error condition 0 upon success
        """
        if frequency < 0.0 or frequency > 6000.0:
            raise RuntimeError("Error: Frequency is outside acceptable range of 0 to 6 GHz")
        else:
            self.ds.sendMessage("SET/FREQ:{0}\r\n\r\n".format(frequency))                      
            response = self.ds.recv(64)
            OK = int(response[63:64])
            if not OK:
                raise RuntimeError("Error: Unable to set frequency")
            else:
                return 0
                 
    def setupFreqSweep(self, f_start, f_stop, f_step, t_step, power):
        """
        Initiates frequency sweep output
        To stop a frequency sweep, call stopFreqSweep
        
        ----------Parameters----------
        f_start (float): The initial frequency in MHz
        f_stop (float): The final frequency in MHz
        f_step (float): The step size between each point in the ramp, in MHz
        t_step (float): The time between successive steps in the sweep, in ms
        power (float): The RF power to output at each point, in dBm

        Returns error condition 0 upon success, 
        """
        if f_start < 0.0 or f_start > 6000.0:
            raise RuntimeError("Error: Start frequency is outside acceptable range of 0 to 6 GHz")
        elif f_stop < 0.0 or f_stop > 6000.0:
            raise RuntimeError("Error: Stop frequency is outside acceptable range of 0 to 6 GHz")
        elif power > 10.0:
            raise RuntimeError("Error: Attempted to set power above +10.0 dBm maximum")
        else:
            self.ds.sendMessage("SET/FSWEEP:STARTFREQ:{0}\r\n\r\n".format(f_start))  
            response = self.ds.recv(64)
            OK = int(response[63:64])
            self.ds.sendMessage("SET/FSWEEP:STOPFREQ:{0}\r\n\r\n".format(f_stop))   
            response = self.ds.recv(64)
            OK = OK * int(response[63:64])
            self.ds.sendMessage("SET/FSWEEP:STEPSIZE:{0}\r\n\r\n".format(f_step))      
            response = self.ds.recv(64)
            OK = OK * int(response[63:64])
            self.ds.sendMessage("SET/FSWEEP:DWELL:{0}\r\n\r\n".format(t_step))                       
            response = self.ds.recv(64)
            OK = OK * int(response[63:64])
            self.ds.sendMessage("SET/FSWEEP:POWER:{0}\r\n\r\n".format(power))
            response = self.ds.recv(64)
            OK = OK * int(response[63:64])
            if not OK:
                raise RuntimeError("Error: Unable to set sweep")
            else:
                self.ds.sendMessage("SET/FSWEEP::MODE:ON\r\n\r\n")   
                response = self.ds.recv(64)
                OK = int(response[63:64])
                if OK:
                    return 0
                else:
                    return 1
                
        def stopFreqSweep(self):
            """
            Stop sweeping frequency output
            
            Returns error condition 0 upon success, 1 on failure 
            """
            self.ds.sendMessage("SET/FSWEEP::MODE:OFF\r\n\r\n")   
            response = self.ds.recv(64)
            OK = int(response[63:64])
            if not OK:
                raise RuntimeError("Error: Unable to stop frequency sweep")
            else:
                return 0
            
