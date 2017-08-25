'''
Original code from: https://github.com/CINF/PyExpLabSys
Authors: Andersen Thomas, Robert Jensen
Forked by Floris van Breugel 1/26/2015

'''

import serial
import time


class Bronkhorst():

    def __init__(self, port, max_flow=10):
        self.ser = serial.Serial(port, 38400)
        self.max_setting = max_flow
        time.sleep(0.1)

    def comm(self, command):
        self.ser.write(command)
        time.sleep(0.3)
        return_string = self.ser.read(self.ser.inWaiting())
        return return_string

    def read_setpoint(self):
        read_setpoint = ':06800401210121\r\n'  # Read setpoint
        response = self.comm(read_setpoint)
        response = int(response[11:], 16)
        response = (response / 32000.0) * self.max_setting
        return response

    def read_measure(self):
        error = 0
        while error < 10:
            read_pressure = ':06800401210120\r\n'  # Read pressure
            val = self.comm(read_pressure)
            print len(val)
            try:
                val = val[-6:]
                num = int(val, 16)
                pressure = (1.0 * num / 32000) * self.max_setting
                break
            except ValueError:
                pressure = -99
                error = error + 1
        return pressure

    def set_setpoint(self, setpoint):
        if setpoint > 0:
            setpoint = (1.0 * setpoint / self.max_setting) * 32000
            setpoint = hex(int(setpoint))
            setpoint = setpoint.upper()
            setpoint = setpoint[2:].rstrip('L')
            if len(setpoint) == 3:
                setpoint = '0' + setpoint
        else:
            setpoint = '0000'
        set_setpoint = ':0680010121' + setpoint + '\r\n'  # Set setpoint
        response = self.comm(set_setpoint)
        response_check = response[5:].strip()
        if response_check == '000005':
            response = 'ok'
        else:
            response = 'error'
        return response

    def read_counter_value(self):
        read_counter = ':06030401210141\r\n'
        response = self.comm(read_counter)
        return str(response)

    def set_control_mode(self):
        set_control = ':058001010412\r\n'
        response = self.comm(set_control)
        return str(response)

    def read_serial(self):
        read_serial = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        error = 0
        while error < 10:
            response = self.comm(read_serial)
            response = response[13:-84]
            try:
                response = response.decode('hex')
            except TypeError:
                response = ''
            if response == '':
                error = error + 1
            else:
                error = 10
        return str(response)

    def read_unit(self):
        read_capacity = r':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        print response
        response = response[77:-26]
        response = response.decode('hex')
        return str(response)

    def read_capacity(self):
        read_capacity = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[65:-44]
        # response = response.decode('hex')
        return str(response)


if __name__ == '__main__':
#     ser = serial.Serial("COM4", 38400)
#     time.sleep(0.5)
#     ser.write(":06800401140114\r\n")
#     time.sleep(0.2)
#    print ser.read(1)
    bh = Bronkhorst('COM4', 100)
    bh.set_control_mode()
    #h.set_control_mode()  # sets the mode to RS232 so you can set the setpoint
   #bh.set_setpoint(75)  # sets the setpoint
    print bh.read_measure()  # returns the current flow rate
    #print bh.read_counter_value()  # returns the current flow rate
    
    
    '''
    #Addressiny MCP9808 to RPI
    import logging 
    import math
    
    # Default I2C address for device. 
    MCP9808_I2CADDR_DEFAULT        = 0x18 
    
 
    # Register addresses. 
    MCP9808_REG_CONFIG             = 0x01 
    MCP9808_REG_UPPER_TEMP         = 0x02 
    MCP9808_REG_LOWER_TEMP         = 0x03 
    MCP9808_REG_CRIT_TEMP          = 0x04 
    MCP9808_REG_AMBIENT_TEMP       = 0x05 
    MCP9808_REG_MANUF_ID           = 0x06 
    MCP9808_REG_DEVICE_ID          = 0x07 
 
    # Configuration register values. 
    MCP9808_REG_CONFIG_SHUTDOWN    = 0x0100 
    MCP9808_REG_CONFIG_CRITLOCKED  = 0x0080 
    MCP9808_REG_CONFIG_WINLOCKED   = 0x0040 
    MCP9808_REG_CONFIG_INTCLR      = 0x0020 
    MCP9808_REG_CONFIG_ALERTSTAT   = 0x0010 
    MCP9808_REG_CONFIG_ALERTCTRL   = 0x0008 
    MCP9808_REG_CONFIG_ALERTSEL    = 0x0002 
    MCP9808_REG_CONFIG_ALERTPOL    = 0x0002 
    MCP9808_REG_CONFIG_ALERTMODE   = 0x0001 
 
 def __init__(self, address=MCP9808_I2CADDR_DEFAULT, i2c=None, **kwargs): 
          """Initialize MCP9808 device on the specified I2C address and bus number. 
          Address defaults to 0x18 and bus number defaults to the appropriate bus 
          for the hardware. 
          """ 
          self._logger = logging.getLogger('Adafruit_MCP9808.MCP9808') 
          if i2c is None: 
              import Adafruit_GPIO.I2C as I2C 
              i2c = I2C 
          self._device = i2c.get_i2c_device(address, **kwargs) 
       
       OR   
          def __init__(self, address=MCP9808_I2CADDR_DEFAULT, busnum=I2C.get_default_bus()):  
          def __init__(self, address=MCP9808_I2CADDR_DEFAULT, i2c=None, **kwargs):  
              """Initialize MCP9808 device on the specified I2C address and bus number.  
              Address defaults to 0x18 and bus number defaults to the appropriate bus  
              for the hardware.  
              """  
              self._logger = logging.getLogger('Adafruit_MCP9808.MCP9808')  
              self._device = I2C.Device(address, busnum)  
              if i2c is None:  
                  import Adafruit_GPIO.I2C as I2C  
                  i2c = I2C  
                  self._device = i2c.get_i2c_device(address, **kwargs)  
                  '''


