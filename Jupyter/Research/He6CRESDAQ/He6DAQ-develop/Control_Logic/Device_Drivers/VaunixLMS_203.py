import spur

class Vaunix:

    def __init__(self, hostname="192.168.0.30", u_name="pi", p_word="Vaunix"):
        """
        Initialize a Vaunix LMS-203 "Lab Brick" signal generator with a
        Raspberry Pi minicomputer acting as USB controller

        ----------Parameters----------
        hostname: the IP address/port of the Raspberry Pi
        u_name: the user name with wich to SSH into the Pi
        p_word: the password expected by the Pi SSH client
        """
        self.shell = spur.SshShell(hostname, u_name, p_word)

    def selfTest(self):
        """
        Runs the included self-tests from the Vaunix LMS SDK
        """
        result = self.shell.run(["sudo", "python3", "./LMS_test.py"])
        print(result.output)

    def getPower(self):
        """
        Returns the power level (in dBm) from the Vaunix
        """
        result = self.shell.run(["sudo", "python3", "./GetPower.py"])
        print(result.output)

    def getFreq(self):
        """
        Returns the frequency (in MHz) from the Vaunix
        """
        result = self.shell.run(["sudo", "python3", "./GetFreq.py"])
        print(result.output)

    def setPower(self):
        """
        Sets the power level (in dBm) output by the Vaunix
        """
        result = self.shell.run(["sudo", "python3", "./SetPower.py"])
        print(result.output)

    def setFreq(self):
        """
        Sets the frequency (in MHz) output by the Vaunix
        """
        result = self.shell.run(["sudo", "python3", "./SetFreq.py"])
        print(result.output)
