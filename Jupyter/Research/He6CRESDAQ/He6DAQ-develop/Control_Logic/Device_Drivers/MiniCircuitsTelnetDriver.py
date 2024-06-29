from telnetlib import Telnet

class McTelnet:

    def __init__(self):
        self.tn = Telnet()
        self.address = ('10.66.192.34', 23)




    def setRF_on(self):
        """
        Turns RF power ON. Returns error condition 0 upon success
        """
        self.tn.open(self.address)
        self.tn.write(b"SET/PWR:RF:ON\r\n\r\n")
        self.tn.close()

        response = self.ds.recv(64)
        OK = response[63:64]
        if not OK:
            raise RuntimeError("Error: Unable to turn on RF")
        else:
            return 0
