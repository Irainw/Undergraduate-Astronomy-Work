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

# The C library we're calling will be expecting us to have a list
# if active devices. In C this is an array of zeroes but in Python we'll
# substitute a list. The C header defines 'MAXDEVICES' which for the 1.02
# library was 64. So we'll make our list that long.
#
# One way of doing this is the following three lines:
#activeDevices = list(range(64))
#for i in range (0, len(activeDevices)):
#    activeDevices[i] = 0
# But here's a more fun way. :)
activeDevices = [0] * 64

# ---------------- Helper programs ----------------
#
# convert from our integer 10Hz representation to a floating point value in GHz
def FreqInGHz(frequency10Hz):
    return frequency10Hz / 1.0e8

# Takes a number and masks off all but the lowest 32 bits
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
# Kind of obvious, but this function tells you whether the result
# is valid or not. It uses AnyError() and simply returns the opposite
    return not AnyError(returnedResult)

# Because of the same 32/64 bit madness, the C perror() function gets confused with high bits as well.
# To get around this you have to call the extension like "LMS_module.fnLMS_perror(Low32(result))" but that's tedious
# so this helper does that for you.


def DecodeError(error):
    return LMS_module.fnLMS_perror(Low32(error))

# Humans like to see big numbers in groups of 3 with commas
# This only handles integers!!!
def PrettyPrint(n):
    ntemp = str(abs(n))
    retval = ""
    while len(ntemp) > 0:
        retval = "," + ntemp[-3:] + retval
        ntemp = ntemp[0:-3]
    # We're good to go except for a leading comma.
    retval = retval[1:]
    # If it was negative, fix that now
    if n < 0:
        retval = "-"+retval
    return retval

# ---------------- End of helper programs ----------------

LMS_module.fnLMS_Init()
LMS_module.fnLMS_SetTestMode(FALSE);
nDevices = LMS_module.fnLMS_GetNumDevices()
print("LMS test/demonstration program version",TESTVERSION,
      "using library version", LMS_module.fnLMS_LibVersion(),
      "and wrapper version",LMS_module.WrapperVersion())

print("I think there are",nDevices,"devices")
if 0 == nDevices:
c = input("No Vaunix LMS devices located. Would you like to run in test mode?")
if c == 'Y' or c == 'y':
  LMS_module.fnLMS_Init();
  LMS_module.fnLMS_SetTestMode(TRUE);
  nDevices = LMS_module.fnLMS_GetNumDevices()
print("Found",nDevices,"devices")

for i in range(1,1+nDevices):
print(i)
cModelName = LMS_module.fnLMS_GetModelName(i)
print("  Model",i,"is ",cModelName)

nActive = LMS_module.fnLMS_GetDevInfo(activeDevices)
print("We have",nActive,"active devices")

for i in range(0, nActive):
if i > 0:
  print("")
print("  Device",activeDevices[i]," is active")
result = LMS_module.fnLMS_InitDevice(activeDevices[i])
print("  Opened device",activeDevices[i],". Returned status",
hex(Low32(result)),"(",DecodeError(result),")")

print("Before we do any tests, let's let the system know the device...")
time.sleep(1)
# --- show the state of the device ---
 cModelName = LMS_module.fnLMS_GetModelName(activeDevices[i])
 result = LMS_module.fnLMS_GetSerialNumber(activeDevices[i])
 print("  Device",activeDevices[i],"(",cModelName,") has serial number",result)

 result = LMS_module.fnLMS_GetFrequency(activeDevices[i])
 if AnyError(result):
     print(" ERROR: Status=", hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_GetFrequency")
 else:
     print("  Frequency =", FreqInGHz(result)," GHz")

 result = LMS_module.fnLMS_GetStartFrequency(activeDevices[i])
 if AnyError(result):
     print(" ERROR: Status=", hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_GetStartFrequency")
 else:
     print("  Sweep start frequency =", FreqInGHz(result)," GHz")

 result = 0xFFFFFFFF & LMS_module.fnLMS_GetEndFrequency(activeDevices[i])
 if AnyError(result):
     print(" ERROR: Status=", hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_GetEndFrequency")
 else:
     print("  Sweep end frequency =", FreqInGHz(result)," GHz")

 result = LMS_module.fnLMS_GetSweepTime(activeDevices[i])
 if AnyError(result):
     print(" ERROR: Status=", hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_GetSweepTime")
 else:
     print("  Sweep time =", result*0.001," seconds")

 result = LMS_module.fnLMS_GetPowerLevel(activeDevices[i])
 if AnyError(result):
     print(" ERROR: Status=", hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_GetPowerLevel")
 else:
     print("  Power level =", result/4," db")

 # Unlike most of the other functions, GetPulseOnTime returns floating point
 fresult = LMS_module.fnLMS_GetPulseOnTime(activeDevices[i])
 if (fresult < 0):
     print(" ERROR: Status=", fresult," (",LMS_module.fnLMS_perror(fresult),") inLMS_module.fnLMS_GetPulseOnTime")
 else:
     print("  Pulse on time =", fresult," sec.")

         # Unlike most of the other functions, GetPulseOffTime returns floating point
         fresult = LMS_module.fnLMS_GetPulseOffTime(activeDevices[i])
         if (fresult < 0):
             print(" ERROR: Status=", result," (",LMS_module.fnLMS_perror(fresult),") inLMS_module.fnLMS_GetPulseOffTime")
         else:
             print("  Pulse off time =", fresult," sec.")

         # --- set some (arbitrary) values based on the range of the Lab Brick ---
         result = LMS_module.fnLMS_GetMinFreq(activeDevices[i])
         if AnyError(result):
             print(" ERROR: Status=", hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_GetMinFreq")
         else:
             print("  Minimum frequency =", FreqInGHz(result)," GHz")

         result = LMS_module.fnLMS_GetMaxFreq(activeDevices[i])
         if AnyError(result):
             print(" ERROR: Status=", hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_GetMaxreq")
         else:
             print("  Maximum frequency =", FreqInGHz(result)," GHz")

         # --- find the offset to the midpoint in the Lab Brick's frequency range ---
         midpoint = (LMS_module.fnLMS_GetMaxFreq(activeDevices[i]) - LMS_module.fnLMS_GetMinFreq(activeDevices[i])) / 2
         print("  Midpoint frequency = ",FreqInGHz(midpoint)," GHz above the min")

         # --- set up a sweep ---
          swp_start = (midpoint * 0.33) + LMS_module.fnLMS_GetMinFreq(activeDevices[i])   # start the sweep at 1/6 of the overall bandwidth
          swp_end = (midpoint * 0.66) + LMS_module.fnLMS_GetMinFreq(activeDevices[i])     # end the sweep at 1/3 of the overall bandwidth

          # --- find the frequency in the middle of the Lab Brick's range ---
          midpoint = midpoint + LMS_module.fnLMS_GetMinFreq(activeDevices[i])

          result = LMS_module.fnLMS_SetFrequency(activeDevices[i],  midpoint)
          if AnyError(result):
              print(" ERROR: Status=",hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_SetFrequency")
          else:
              print("  Set frequency to ",FreqInGHz(midpoint)," GHz.", )

          result = LMS_module.fnLMS_GetFrequency(activeDevices[i])
          print("  Read frequency back and got ",PrettyPrint(result)," in 10Hz units")

          result = LMS_module.fnLMS_SetStartFrequency(activeDevices[i], swp_start)
          if AnyError(result):
              print(" ERROR: Status=",hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_SetStartFrequency")
          else:
              print("  Set sweep start frequency to ",FreqInGHz(swp_start)," GHz.")

          result = 0xFFFFFFFF & LMS_module.fnLMS_SetEndFrequency(activeDevices[i], swp_end)
          if AnyError(result):
              print(" ERROR: Status=",hex(Low32(result))," (",DecodeError(result),") inLMS_module.fnLMS_SetEndFrequency")
              else:
                  print("  Set sweep end frequency to ",FreqInGHz(swp_end) ," GHz.")

              result = LMS_module.fnLMS_GetStartFrequency(activeDevices[i])
              print("  Read start frequency back and got ",PrettyPrint(result),"in 10Hz units")
              result = LMS_module.fnLMS_GetEndFrequency(activeDevices[i])
              print("  Read end frequency back and got ",PrettyPrint(result)," in 10Hz units")

              result = 0xFFFFFFFF & LMS_module.fnLMS_SetSweepTime(activeDevices[i], 20)
              print("  Set sweep time to 20 milliseconds. Status=",hex(Low32(result))," (",DecodeError(result),")")
              result = LMS_module.fnLMS_GetSweepTime(activeDevices[i])
              print("  Read sweep time =  ",result * .001," seconds")

              # set the powerlevel to -15db, using our .25db units
              powerlevel = -15 * 4
              result = LMS_module.fnLMS_SetPowerLevel(activeDevices[i], powerlevel)
              print("  Set power level to -15 db. Status=",hex(Low32(result))," (",DecodeError(result),")")
              result = LMS_module.fnLMS_GetPowerLevel(activeDevices[i])
              print("  Read power level = ",result/4," db")

              result = LMS_module.fnLMS_SetRFOn(activeDevices[i], TRUE)
              print("  Set RF on. Status=",hex(Low32(result))," (",DecodeError(result),")");

              # --- turn on pulse modulation ---
              result = LMS_module.fnLMS_SetUseExternalPulseMod(activeDevices[i], FALSE)

              print("  SetUseExternalPulseMod is FALSE. Status=",hex(Low32(result))," (",DecodeError(result),")",)

              result = LMS_module.fnLMS_SetFastPulsedOutput(activeDevices[i], .002, .05, TRUE)
              print("  SetFastPulsedOutput to 2ms on every 50ms, Status=",hex(Low32(result))," (",DecodeError(result),")")

             result = LMS_module.fnLMS_SetUseInternalRef(activeDevices[i], TRUE)
             print("  Set UseInternalRef TRUE. Status=",hex(Low32(result))," (",DecodeError(result),")")

             result = LMS_module.fnLMS_SetSweepDirection(activeDevices[i], TRUE)
             print("  Set sweep direction TRUE. Status=",hex(Low32(result))," (",DecodeError(result),")")

             result = LMS_module.fnLMS_SetSweepMode(activeDevices[i], TRUE)
             print("  Set sweep mode TRUE. Status=",hex(Low32(result))," (",DecodeError(result),")")

             result = LMS_module.fnLMS_SetSweepType(activeDevices[i], TRUE)
             print("  Set sweep type TRUE. Status=",hex(Low32(result))," (",DecodeError(result),")")

             result = LMS_module.fnLMS_StartSweep(activeDevices[i], TRUE)
             print("  Started sweep. Status=",hex(Low32(result))," (",DecodeError(result),")")

             result = LMS_module.fnLMS_CloseDevice(activeDevices[i])
             print("  Closed device ",activeDevices[i],". Return Status=",hex(Low32(result))," (",DecodeError(result),")")

         print("End of test")
