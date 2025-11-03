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
from .cooling import send_data


# we will use the following ports and baudrate
ser_arduino = serial.Serial(port="/dev/ttyUSB0", baudrate=115200)

FORMAT = '%(asctime)s [%(name)-15s] - %(levelname)-7s %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)

today = str(date.today())
now = datetime.now()

current_time = now.strftime("%H:%M:%S")


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

        return [tempNTC, tempSHT, humidSHT]

    def PID_controller(self):
        time.sleep(2)
       
        logging.info('Starting temperature logging...')

        with open('measurement_' + today + current_time + '.txt', 'w') as f:
            '''
            This function logs the temperature and humidity
            '''

            write_flg = True

            while True:

                # printing the measurement
                measurement=self.get_temps()
               
                print("VALVE: ", 0, "%")
                print('TEMP NTC: ', measurement[0], "°C")
                print("TEMP SHT: ", measurement[1], "°C")
                print("HUMID: ", measurement[2], "% \r\n")#, humids = self.get_temps()
                print('_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n')

                # send data to online monitor (first in the converter)
                if self.socket:
                    send_data(self.socket, data=np.array([measurement[0],measurement[1],measurement[2]], dtype=np.float64)) 

                if write_flg == True:
                    f.write('TEMP NTC in Celsius:   ')
                    f.write('TEMP SHT in Celsius:   ')
                    f.write('HUMIDITY in %:   ')
                    f.write('Time'   +'\n')
                    write_flg = False

                f.write(measurement[0] + "                  ")
                f.write(measurement[1] + "                  ")
                f.write(measurement[2] + "                  ")
                f.write(str(0) + "                  ")
                f.write(str(int(time.time())) + "\n")

                self.temp_table.append([(int(time.time()), measurement[0], measurement[1], measurement[2])])
                self.temp_table.flush()


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
    cooling.PID_controller()


if __name__ == "__main__":
    main()

