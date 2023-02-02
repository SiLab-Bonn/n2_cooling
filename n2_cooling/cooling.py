import time
import zmq
import logging
import numpy as np
import tables as tb
import struct
import argparse

from simple_pid import PID

from online_monitor.utils import utils
import serial
from simple_pid import PID
from datetime import datetime
from datetime import date


# we will use the following ports and baudrate
ser_arduino = serial.Serial(port="/dev/ttyUSB0", baudrate=115200)
ser_bronk = serial.Serial(port="/dev/ttyUSB1", baudrate=38400)

FORMAT = '%(asctime)s [%(name)-15s] - %(levelname)-7s %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)

today = str(date.today())
now = datetime.now()

current_time = now.strftime("%H:%M:%S")


def send_data(socket, data, name="CoolingData"):
    data_meta_data = dict(
        name=name,
        dtype=str(data.dtype),
        shape=data.shape,
        timestamp=time.time()
    )

    try:
        data_ser = utils.simple_enc(data, meta=data_meta_data)
        socket.send(data_ser, flags=zmq.NOBLOCK)
    except zmq.Again:
        pass


class Cooling(object):
    def __init__(self, conf_file="../cooling.yaml", monitor=True):
        # Setup logging
        self.log = logging.getLogger('N2 Cooling')
        fh = logging.FileHandler('cooling_2021-05-12_2e15.log')
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(FORMAT))
        self.log.addHandler(fh)
    
        # Setup online monitor
        if monitor:
            try:
                context = zmq.Context()
                self.socket = context.socket(zmq.PUB)
                self.socket.bind(monitor)
                self.log.info("Sending data to server %s" % monitor)
            except zmq.error.ZMQError:
                self.log.warning("Cannot connect to socket for data sending")
                self.socket = None
        else:
            self.socket = None

        # Set up temperature log file
        self.temp_type = np.dtype([
            ('timestamp', 'u4'),
            ('temperature_box', 'f4'),
            ('temperature_dut', 'f4'),
            ('humidity_dut', 'f4'),
            ('valve', 'i4'),
            ('flow_in_l_min','f4'),
            ('flow_counter_in_l','f4')
        ])
        self.output_file = tb.open_file('measurement_' + today + current_time + '.h5', 'a')
        if '/temperature' in self.output_file:  # Table already exists
            self.temp_table = self.output_file.root.temperature
        else:
            self.temp_table = self.output_file.create_table(self.output_file.root,
                                                            name='temperature',
                                                            description=self.temp_type,
                                                            filters=tb.Filters(complevel=5, complib='blosc')
                                                            )            

    def __del__(self):
        self.output_file.close()

    def mean(self,list):
        sum_of_list = 0
        for i in range(len(list)):
            sum_of_list += list[i]
        average = sum_of_list/len(list)
        return average

    def get_valve(self):
        # get the valve opening
        ser_bronk.write(bytes(b':06800472417241\r\n'))
        
        # answer does read the confirmation of the command
        answer=ser_bronk.readline().decode()
       
        while len(answer)<20:
            answer = ser_bronk.readline().decode()
        answer=round(int(answer[11:-2], 16) * 5.96368684979e-6, 3)
        
        return answer

    def get_temps(self):
        '''
        This func will ask for data by writing "R" in the Serial port. It will receive a Array with 3 elements.
        ([tempNTC,tempSHT, humidityDHT])
        '''
        # start process in arduino with command 'R'
        ser_arduino.write(bytes(b'R'))
       
        time.sleep(1)

        # output is from type bytes. Convert to string
        read_values = ser_arduino.readline().decode("utf-8")
        values = read_values.split(" ")


        tempNTC = values[0]
        tempSHT = values[1]
        humidSHT = values[2]

        valve = self.get_valve()

        return [tempNTC, tempSHT, humidSHT, valve]

    def setvalve_readtemp(self, control_val, ports=serial.Serial(port="/dev/ttyUSB1", baudrate=38400)):
        '''
        This function will be used in the PID. Sets the Valve and returns the temp for the PID loop
        '''
        # set Mode 18 (setpoint will be controlling the valve)
        ser_bronk.write(bytes(b':058001010414\r\n'))

        control_val = str(hex(int(control_val)))[2:]
      
        if len(control_val) == 1:
            control_val='000' + str(control_val)
           
        if len(control_val) == 2:
            control_val='00' + str(control_val)

        if len(control_val)==3:
            control_val='0'+str(control_val)
            
        # writing the new setpoint
        ports.write(b':0680010121' + control_val.encode() + b'\r\n') 
        clearing_port = ports.readline()

        # let PID controller in valve settle
        time.sleep(.2)
        
        # SHT output
        temp = self.get_temps()[1]
 
        return float(temp)

    def PID_controller(self, user_input):
       
        logging.info('Starting cooling process...')

        with open('measurement_' + today + current_time + '.txt', 'w') as f:
            '''
            This function will include thw hole PID controller. It uses mainly the simple_PID package
            '''

            pid = PID(Kp=-3000, Ki=-80, Kd=-150,output_limits=(12800, 16640), setpoint=user_input)
            start = self.setvalve_readtemp(0)

            # writing the headline of the data file
            write_flg = 1
            rst_flg = 0

            while True:
                # Reset counter (counter returns floats) value 01 resets counter!
                if rst_flg == 0:
                    ser_bronk.write(bytes(b':058001730801\r\n'))
                    reader=ser_bronk.readline().decode("utf-8")
                    logging.info("Restarting flow counter: DONE")
                    
                    # read also capacity unit
                    ser_bronk.write(bytes(b':078004017F017F07\r\n'))
                    # unit will give you a hex string which can be converted to string. The last 7 bytes contain the data
                    unit_hex = ser_bronk.readline().decode("utf-8")
                    unit_string = bytes.fromhex(unit_hex[13:]).decode('utf-8')
                    rst_flg=1
                self.get_valve()
                # Compute new output from the PID according to the systems current value
                control = pid(start)

                # Feed the PID output to the system and get its current value
                start = self.setvalve_readtemp(control)

                # printing the measurement
                measurement=self.get_temps()
               
                print("VALVE: ", measurement[3], "%")
                print('TEMP NTC: ', measurement[0], "°C")
                print("TEMP SHT: ", measurement[1], "°C")
                print("HUMID: ", measurement[2], "% \r\n")#, humids = self.get_temps()

                ser_bronk.write(bytes(b':06030468416841\r\n'))
                counter = ser_bronk.readline().decode("utf-8")
                counter_float = struct.unpack('!f',bytes.fromhex(str(counter[11:])))[0]
                print("Flow counter: ", counter_float)

                # monitoring flow (the value has to be then calculated see manual!)
                ser_bronk.write(bytes(b':06800401210120\r\n'))
                flow_hex = ser_bronk.readline().decode()[11:-2]
                flow_int = int(flow_hex, 16)

                # Read capacity 100% (necessary for calculating flow, given in hex convert to float)
                ser_bronk.write(bytes(b':068004014D014D\r\n'))
                cap_hex = ser_bronk.readline().decode()[11:-2]
                cap = struct.unpack('!f',bytes.fromhex(str(cap_hex)))[0]

                # calculate flow as mentioned
                flow_in_unit = flow_int / 32000 * cap
                print("flow in ", unit_string," : ", round(flow_in_unit,2), '\n')
                print('_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n')

                # send data to online monitor (first in the converter)
                if self.socket:
                    send_data(self.socket, data=np.array([measurement[0],measurement[1],measurement[2]], dtype=np.float64)) 

                if write_flg == 1:
                    f.write('TEMP NTC in Celsius:   ')
                    f.write('TEMP SHT in Celsius:   ')
                    f.write('HUMIDITY in %:   ')
                    f.write('Valve Output in %:   ')
                    f.write('flow in l/min:   ')
                    f.write('flow counter in l:   ')
                    f.write('Time'   +'\n')
                    write_flg = 0

                f.write(measurement[0] + "                  ")
                f.write(measurement[1] + "                  ")
                f.write(measurement[2] + "                  ")
                f.write(str(measurement[3]) + "                  ")
                f.write(str(round(flow_in_unit,2)) + "                  ")
                f.write(str(round(counter_float,2)) + "                  ")
                f.write(str(int(time.time())) + "\n")

                self.temp_table.append([(int(time.time()), measurement[0], measurement[1], measurement[2], measurement[3], round(flow_in_unit, 2), round(counter_float, 2))])
                self.temp_table.flush()

                time.sleep(0.05)

    def run(self, valve=0x000000):
        time.sleep(2)

        logging.info('Starting...')
        logging.info('Type in cooling temperature in Celsius:  ')
        user_input = input()
        logging.info('To change the cooling temperature restart the cooling.py')
        self.PID_controller(float(user_input))


def main():
    parser = argparse.ArgumentParser(
        usage="cooling.py --setpoint=X(C) --monitor='tcp://127.0.0.1:5000'",
        description='Temperature control',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--setpoint', type=float, default=-20.0,
                        help="Target temperature in Celsius")
    parser.add_argument('--logfile', type=str, default="temperature.log",
                        help="Filename for log file")
    parser.add_argument('--monitor', type=str, default="tcp://127.0.0.1:5000",
                        help="Online monitor address including port")
    args = parser.parse_args()

    cooling = Cooling( monitor=args.monitor)
    cooling.run()


if __name__ == "__main__":
    main()

