import time
import LMS_module

FALSE = 0
TRUE = not FALSE
TESTVERSION = "0.2 2017-08-02"

activeDevices = list(range(64))
nActive = 0
STATUS_OK = 0
BAD_PARAMETER = 0x80010000      # out of range input -- frequency outside min/max etc.
BAD_HID_IO = 0x80020000 # an error was returned by the lower level USB drivers
DEVICE_NOT_READY = 0x80030000   # device isn't open, no handle, etc.
ERROR_STATUS_MSK = 0x80000000   # the MSB is set for errors

# ---------------- Helper programs ----------------
# convert from our integer 10Hz representation to a floating point value in GHz
def FreqInGHz(frequency10Hz):
    return frequency10Hz / 1.0e8

# Takes a number and masks off all but the lowest 32 bits
#(hexadecimal 0xFFFFFFFF is equivalent to 0x000...000FFFFFFFF)
def Low32(n):
    return n & 0xFFFFFFFF

def AnyError(returnedResult):
    # Because of the 32-bit nature of the C code, we have conversion
    # issues getting values back and forth to/from C. Error values have the
    # high order bit set and are defined up above. We'll mask off all except
    # the lower 32 bits.
    #
    # Returns:
    #   TRUE if the result represents any of the known errors or
    #   FALSE if the result is a valid return value
    temp = Low32(returnedResult)
    if temp == BAD_PARAMETER or temp == BAD_HID_IO or temp == DEVICE_NOT_READY:
        return TRUE
    else:
        return FALSE

def SomeSpecificError(returnedResult, error):
# Because of the 32-bit nature of the C code, we have conversion
# issues getting values back and forth to/from C. Error values have the
# high order bit set and are defined up above. We'll mask off all except
# the lower 32 bits.
#
# Returns:
#   TRUE if the result is the error passed as an argument or
#   FALSE if the result is a valid return value
    temp = Low32(returnedResult)
    if temp == error:
        return TRUE
    else:
        return FALSE

def IsValid(returnedResult):
    return not AnyError(returnedResult)

# Because of the same 32/64 bit madness, the C perror() function gets
# confused with high bits as well. To get around this you have to call
# the extension like "LMS_module.fnLMS_perror(Low32(result))" but
# that's tedious so this helper does that for you.
def DecodeError(error):
    return LMS_module.fnLMS_perror(Low32(error))

class vaunix:
    def __init__(self):
        # The C library we're calling will be expecting us to have a list
        # of active devices. In C this is an array of zeroes but in Python we'll
        # substitute a list. The C header defines 'MAXDEVICES' which for the 1.02
        # library was 64. So we'll make our list that long.
        self.activeDevices = list(range(64))
        self.activeDevices = [0] * 64

        self.nDevices = LMS_module.fnLMS_GetNumDevices()
        self.nActive = LMS_module.fnLMS_GetDevInfo(self.activeDevices)
        LMS_module.fnLMS_InitDevice(self.activeDevices[0])

from flask import Flask

#declaring an object of the Flask class boots up the werkzeug server that
#does the work of fronting our code to the intertubes
app = Flask(__name__)

#declaring an object of the vaunix class enables us to do the initialization
#only once, making calls to the device via synth.activeDevices[0]
synth = vaunix()

#using the route method on our Flask object (named 'app') executes the function
#underneath whenever the associated URL gets a request over the tubes
@app.route('/')
def hello():
    return('Vaunix control python app running on 10.66.192.43:5000')

@app.route('/cheese') #just to make sure the route method functions properly
def cheese():
    return (':D')

@app.route('/getPower') #the power level is on a scale of 0.25dB
def getPower():
    powerLevel = LMS_module.fnLMS_GetPowerLevel(synth.activeDevices[0])
    outString = "{} dB".format(str(powerLevel/4))
    return (outString)

@app.route('/getFreq') #frequency is on a scale in increments of 10 Hz
def getFreq():
    freq = LMS_module.fnLMS_GetFrequency(synth.activeDevices[0])
    outString = "{} GHz".format(str(freq/100000000))
    return (outString)

@app.route('/getStartFreq')
def getStartFreq():
    result = LMS_module.fnLMS_GetStartFrequency(synth.activeDevices[0])
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetStartFrequency <br/>"
    else:
        outString = "{} GHz <br/>".format(result/100000000)
    return (outString)

@app.route('/getEndFreq') #frequency is on a scale in increments of 10 Hz
def getEndFreq():
    #LMS_test.py file consistently uses bitwise 0xFFFFFFFF in conjunction
    #with GetEndFrequency() -- not clear why
    result = 0xFFFFFFFF & LMS_module.fnLMS_GetEndFrequency(synth.activeDevices[0])
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetEndFrequency <br/>"
    else:
        outString = "{} GHz<br/>".format(result/100000000)
    return (outString)

@app.route('/getSweepTime') #sweep time is set in milliseconds
def getSweepTime():
    result = LMS_module.fnLMS_GetSweepTime(synth.activeDevices[0])
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetSweepTime <br/>"
    else:
        outString = "{} ms <br/>".format(result)
    return (outString)

@app.route('/setPower/<power>')
def setPower(power):
    if(float(power) > 0.0 or float(power) < -30.0):
        return("ERROR: Power must be set in dBm between 0.0 and -30.0")
    pow = 4 * float(power)
    result = LMS_module.fnLMS_SetPowerLevel(synth.activeDevices[0], int(pow))
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_setPowerLevel <br/>"
    else:
        outString = getPower()
    return (outString)

@app.route('/setFreq/<freq>')
def setFreq(freq):
    freq10 = 100000000 * float(freq)
    if(freq10 < 1000000000 or freq10 > 2000000000):
        return("ERROR: Frequency must be set in GHz between 10.0 and 20.0")
    else:
        result = LMS_module.fnLMS_SetFrequency(synth.activeDevices[0], int(freq10))
        if AnyError(result):
            outString = "ERROR: Status = " + str(hex(Low32(result)))
            outString += str(DecodeError(result))
            outString += " in LMS_module.fnLMS_SetFrequency <br/>"
        else:
            outString = getFreq()
        return outString

@app.route('/setStartFreq/<startFreq>')
def setStartFreq(startFreq):
    startFreq10 = float(startFreq) * 1.0e8
    if(startFreq10 < 1000000000 or startFreq10 > 2000000000):
        return("ERROR: Frequency must be set in GHz between 10.0 and 20.0")
    else:
        result = LMS_module.fnLMS_SetStartFrequency(synth.activeDevices[0], int(startFreq10))
        if AnyError(result):
            outString = "ERROR: Status = " + str(hex(Low32(result)))
            outString += str(DecodeError(result))
            outString += " in LMS_module.fnLMS_SetStartFrequency <br/>"
        else:
            outString = getStartFreq()
        return (outString)

@app.route('/setEndFreq/<endFreq>')
def setEndFreq(endFreq):
    endFreq10 = float(endFreq) * 1.0e8
    if(endFreq10 < 1000000000 or endFreq10 > 2000000000):
        return("ERROR: Frequency must be set in GHz between 10.0 and 20.0")
    else:
        #LMS_test.py file consistently uses bitwise 0xFFFFFFFF in conjunction
        #with Set(Get)EndFrequency() -- not clear why
        result = 0xFFFFFFFF & LMS_module.fnLMS_SetEndFrequency(synth.activeDevices[0], endFreq10)
        if AnyError(result):
            outString = "ERROR: Status = " + str(hex(Low32(result)))
            outString += str(DecodeError(result))
            outString += " in LMS_module.fnLMS_SetEndFrequency <br/>"
        else:
            outString = getEndFreq()
        return (outString)

@app.route('/setSweepTime/<sweepTime>')
def setSweepTime(sweepTime):
    if (float(sweepTime) < 1.0):
        return ("ERROR: sweep time must be 1 or more milliseconds")
    result = 0xFFFFFFFF & LMS_module.fnLMS_SetSweepTime(synth.activeDevices[0], int(sweepTime))
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_SetSweepTime <br/>"
    else:
        outString = getSweepTime()
    return (outString)

@app.route('/setRF_On')
def setRFON():
    result = LMS_module.fnLMS_SetRFOn(synth.activeDevices[0], TRUE)
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_SetRFOn <br/>"
    else:
        outString = "Set RF to ON. <br/>"
    return (outString)

@app.route('/setSweepUp')
def sweepUp():
    result = LMS_module.fnLMS_SetSweepDirection(synth.activeDevices[0], TRUE)
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_SetSweepDirection <br/>"
    else:
        outString = "Set sweep direction UP. <br/>"
    return (outString)

@app.route('/setSweepDown')
def sweepDown():
    result = LMS_module.fnLMS_SetSweepDirection(synth.activeDevices[0], FALSE)
    if AnyError(result):
        outString = "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_SetSweepDirection <br/>"
    else:
        outString = "Set sweep direction DOWN. <br/>"
    return (outString)

@app.route('/setSweepMode/Repeat')
def sweepOn():
    result = LMS_module.fnLMS_SetSweepMode(synth.activeDevices[0], TRUE)
    outString = "Set sweep repeating mode ON. <br/>"
    return (outString)

@app.route('/setSweepMode/Single')
def sweepOff():
    result = LMS_module.fnLMS_SetSweepMode(synth.activeDevices[0], FALSE)
    outString = "Set sweep repeating mode OFF. <br/>"
    return (outString)

@app.route('/setSweepType/Triangle')
def sweepTypeTri():
    result = LMS_module.fnLMS_SetSweepType(synth.activeDevices[0], TRUE)
    outString = "Set sweep type TRUE => Triangle mode. <br/>"
    return (outString)

@app.route('/setSweepType/Sawtooth')
def sweepTypeSaw():
    result = LMS_module.fnLMS_SetSweepType(synth.activeDevices[0], FALSE)
    outString = "Set sweep type FALSE => Sawtooth mode. <br/>"
    return (outString)

@app.route('/startSweep')
def startSweep():
    result = LMS_module.fnLMS_StartSweep(synth.activeDevices[0], TRUE)
    outString = "Started sweep. <br/>"
    return (outString)

@app.route('/stopSweep')
def stopSweep():
    result = LMS_module.fnLMS_StartSweep(synth.activeDevices[0], FALSE)
    outString = "Stopped sweep. <br/>"
    return (outString)

@app.route('/closeDevice')
def closeDevice():
    result = LMS_module.fnLMS_CloseDevice(synth.activeDevices[0])
    outString = "Closed device. Return Status = "
    outString += str(hex(Low32(result))) + "<br/>"
    return (outString)

@app.route('/runSelfTest')
def LMS_test():
    LMS_module.fnLMS_Init()
    LMS_module.fnLMS_SetTestMode(FALSE)
    nDevices = LMS_module.fnLMS_GetNumDevices()
    libVersion = LMS_module.fnLMS_LibVersion()
    outString = "LMS test using library version {} <br/>".format(libVersion)
    outString += "{} devices found <br/>".format(nDevices)

    cModelName = LMS_module.fnLMS_GetModelName(1)
    outString += "Device {} has model number {}<br/>".format(1,cModelName)

    nActive = LMS_module.fnLMS_GetDevInfo(activeDevices)
    outString += "We have {} active devices <br/>".format(nActive)

    result = LMS_module.fnLMS_InitDevice(activeDevices[0])
    #outString += "Init device result: " + str(result) + "<br/>"

    result = LMS_module.fnLMS_GetFrequency(activeDevices[0])
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetFrequency <br/>"
    else:
        outString += "Frequency = {} GHz  <br/>".format(result/100000000)

    result = LMS_module.fnLMS_GetStartFrequency(activeDevices[0])
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetStartFrequency <br/>"
    else:
        outString += "Sweep start freq. = {} GHz <br/>".format(result/100000000)

    #LMS_test.py file consistently uses bitwise 0xFFFFFFFF in conjunction
    #with GetEndFrequency() -- not clear why
    result = 0xFFFFFFFF & LMS_module.fnLMS_GetEndFrequency(activeDevices[0])
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetEndFrequency <br/>"
    else:
        outString += "Sweep end freq. = {} GHz<br/>".format(result/100000000)

    result = LMS_module.fnLMS_GetSweepTime(activeDevices[0])
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetSweepTime <br/>"
    else:
        outString += "Sweep time = {} sec <br/>".format(result/1000)

    result = LMS_module.fnLMS_GetPowerLevel(activeDevices[0])
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetPowerLevel <br/>"
    else:
        outString += "Power level = {} dBm <br/>".format(result/4)


    #Unlike most other functions, GetPulseOnTime returns floats
    fresult = LMS_module.fnLMS_GetPulseOnTime(activeDevices[0])
    if (fresult < 0):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetPulseOnTime <br/>"
    else:
        outString += "Pulse on time = {} sec <br/>".format(fresult)

    # Unlike most other functions, GetPulseOffTime returns floats
    fresult = LMS_module.fnLMS_GetPulseOffTime(activeDevices[0])
    if (fresult < 0):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetPulseOffTime <br/>"
    else:
        outString += "Pulse off time = {} sec <br/>".format(fresult)

    # --- set some values based on the range of the Lab Brick ---
    result = LMS_module.fnLMS_GetMinFreq(activeDevices[0])
    minFreq = result
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetMinFreq <br/>"
    else:
        outString += "Minimum frequency = {} GHz <br/>".format(result/1.0e8)

    result = LMS_module.fnLMS_GetMaxFreq(activeDevices[0])
    maxFreq = result
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetMaxFreq <br/>"
    else:
        outString += "Maximum frequency = {} GHz <br/>".format(result/1.0e8)

    # --- find the midpoint in the Lab Brick's frequency range ---
    halfRange = 0.5 * (maxFreq - minFreq)
    outString += "Midpoint freq. = {} GHz<br/>".format((minFreq+halfRange)/1.0e8)

    # --- set up a sweep ---
    sweepStart = minFreq + (halfRange * 0.33)
    sweepEnd = maxFreq - (halfRange * 0.33)

    result = LMS_module.fnLMS_SetFrequency(activeDevices[0], minFreq+halfRange)
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_SetFrequency <br/>"
    else:
        outString+="Mid freq. = {} GHz <br/>".format(1.0e-8*(minFreq+halfRange))

    result = LMS_module.fnLMS_SetStartFrequency(activeDevices[0], sweepStart)
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_SetStartFrequency <br/>"
    else:
        outString += "Set sweep start freq to {} GHz <br/>".format(sweepStart/1.0e8)

    #LMS_test.py file consistently uses bitwise 0xFFFFFFFF in conjunction
    #with Set(Get)EndFrequency() -- not clear why

    result = 0xFFFFFFFF & LMS_module.fnLMS_SetEndFrequency(activeDevices[0], sweepEnd)
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_SetEndFrequency <br/>"
    else:
        outString += "Set sweep end freq to {} GHz <br/>".format(sweepEnd/1.0e8)

    result = 0xFFFFFFFF & LMS_module.fnLMS_SetSweepTime(activeDevices[0], 20)
    outString += "Set sweep time to 20 ms. <br/>"

    result = LMS_module.fnLMS_GetSweepTime(activeDevices[0])
    outString += "Read sweep time = {} sec".format(result * .001) + "<br/>"

    # set the powerlevel to -15db, using our .25db units
    power = -15 * 4
    result = LMS_module.fnLMS_SetPowerLevel(activeDevices[0], power)
    outString+="Set power to -15 dBm. <br/>"

    result = LMS_module.fnLMS_GetPowerLevel(activeDevices[0])
    if AnyError(result):
        outString += "ERROR: Status = " + str(hex(Low32(result)))
        outString += str(DecodeError(result))
        outString += " in LMS_module.fnLMS_GetPowerLevel <br/>"
    else:
        outString += "Power level = {} dBm <br/>".format(result/4)

    result = LMS_module.fnLMS_SetRFOn(activeDevices[0], TRUE)
    outString += "Set RF to ON. <br/>"

    # --- turn on pulse modulation ---
    result = LMS_module.fnLMS_SetUseExternalPulseMod(activeDevices[0], FALSE)
    outString+="SetUseExternalPulseMod is FALSE. <br/>"

    result = LMS_module.fnLMS_SetFastPulsedOutput(activeDevices[0], .002, .05, TRUE)
    outString += "SetFastPulsedOutput to 2ms on every 50ms. <br/>"

    result = LMS_module.fnLMS_SetUseInternalRef(activeDevices[0], TRUE)
    outString += "Set UseInternalRef TRUE. <br/>"

    result = LMS_module.fnLMS_SetSweepDirection(activeDevices[0], TRUE)
    outString += "Set sweep direction TRUE. <br/>"

    result = LMS_module.fnLMS_SetSweepMode(activeDevices[0], TRUE)
    outString += "Set sweep mode TRUE. <br/>"

    result = LMS_module.fnLMS_SetSweepType(activeDevices[0], TRUE)
    outString += "Set sweep type TRUE. <br/>"

    result = LMS_module.fnLMS_StartSweep(activeDevices[0], TRUE)
    outString += "Started sweep. <br/>"

    #result = LMS_module.fnLMS_CloseDevice(activeDevices[0])
    #outString += "Closed device. Return Status = "
    #outString += str(hex(Low32(result))) + "<br/>"

    outString += "End of test."

    return (outString)

if __name__ == "__main__":
    app.run(host="192.168.0.29", debug=True, port=5000)
