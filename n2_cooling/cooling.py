import time
import zmq
import logging
import numpy as np
import tables as tb

from simple_pid import PID

from basil.dut import Dut
from online_monitor.utils import utils

FORMAT = '%(asctime)s [%(name)-15s] - %(levelname)-7s %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)


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
    def __init__(self, conf_file="../examples/cooling.yaml", setpoint=-20, monitor=False):
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
        self.temp_type = np.dtype([('timestamp', 'u4'), ('temp_1', 'f4'), ('temp_2', 'f4'), ('humidity_1', 'f4'), ('humidity_2', 'f4')])
        self.output_file = tb.open_file('cooling.h5', 'a')
        if '/temperature' in self.output_file:  # Table already exists
            self.temp_table = self.output_file.root.temperature
        else:
            self.temp_table = self.output_file.create_table(self.output_file.root,
                                                            name='temperature',
                                                            description=self.temp_type,
                                                            filters=tb.Filters(complevel=5, complib='blosc')
                                                            )            

        self.setpoint = setpoint
        devices = Dut(conf_file)
        devices.init()
        self.temp_sensors = devices["sensirion"]
        self.valve = devices["bronkhorst"]

    def __del__(self):
        self.output_file.close()

    def get_temps(self):
        temps = self.temp_sensors.get_temperature()
        while not all(temps[:2]):  # Make sure to get proper values for sensor 1 and 2
            temps = self.temp_sensors.get_temperature()
            time.sleep(0.1)
        time.sleep(0.2)
        try:
            humids = self.temp_sensors.get_humidity()
            self.log.info("%.2f C %.2f % RH" % (temps[0], humids[0]))
        except Exception:
            humids = [np.nan for _ in range(4)]
            self.log.warning("%.2f C Humidity read error" % (temps[0]))

        # Log to file
        self.temp_table.append([(int(time.time()), temps[0], temps[1], humids[0], humids[1])])
        self.temp_table.flush()

        return temps, humids

    def open_valve(self, valve=0xFFFFFF):
        self.valve.set_control_mode(8)
        if self.valve.get_control_mode() == 8:
            self.valve.set_valve_output(valve)
            while True:
                temps, humids = self.get_temps()
                if self.socket:
                    send_data(self.socket, data=np.array([temps, humids], dtype=np.float64))
                time.sleep(1)
        else:
            self.log.error("Control mode cannot be set!")

    def close_valve(self, valve=0x0):
        self.valve.set_control_mode(3)
        if self.valve.get_control_mode() == 3:
            self.valve.set_valve_output(valve)
            while True:
                temps, humids = self.get_temps()
                if self.socket:
                    send_data(self.socket, data=np.array([temps, humids], dtype=np.float64))
                time.sleep(1)
        else:
            self.log.error("Control mode cannot be set!")

    def run(self, valve=0x000000):
        self.valve.set_control_mode(4)
        ret = self.valve.get_control_mode()
        if ret == 4:
            self.log.info("Starting...")
        else:
            self.log.error("Control mode cannot be set, mode is %s" % str(ret))

        # Init buffers
        temp = np.ones(10000) * float("NaN")
        i = 0
        # pid = PID(0.7, 0.001, 0, setpoint=-20, sample_time=.5)
        # pid.output_limits = (0, 1)

        self.valve.set_valve_output(0x000000)
        time.sleep(2)
        self.log.info("valve 0x%x,0x%x" % (self.valve.get_valve_output(), self.valve.get_measure()))
        pre = self.temp_sensors.get_temperature()[0]
        flg = 0
        while True:
            temps, humids = self.get_temps()
            if self.socket:
                send_data(self.socket, data=np.array([temps, humids], dtype=np.float64))
            time.sleep(1)

            # valve = 6500000 + (10000000 - 6500000) * pid(temps[0])
            # print("valve: ", int(valve))
            # self.valve.set_valve_output(int(valve))

            temp[i % len(temp)] = temps[0]

            if flg > 1:
                flg = flg - 1
            elif flg == 1 and temp[i % len(temp)] > self.setpoint - 0.5 and self.valve.get_valve_output() != 0:
                self.valve.set_valve_output(0x000000)
                self.log.info("valve 0x%x,0x%x" % (self.valve.get_valve_output(), self.valve.get_measure()))
                flg = 20 
            elif temp[i % len(temp)] < self.setpoint - 0.2 and self.valve.get_valve_output()==0:
                self.valve.set_valve_output(0x800000)  # open valve, was originally 0x800000
                flg = 10
                self.log.info("valve 0x%x,0x%x" % (self.valve.get_valve_output(), self.valve.get_measure()))
                pre=temp[i %len(temp)]
            elif temp[i % len(temp)] > self.setpoint and self.valve.get_valve_output() != 0:
                self.valve.set_valve_output(0x000000)
                flg = 50
                self.log.info("valve 0x%x,0x%x" % (self.valve.get_valve_output(), self.valve.get_measure()))
            i += 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(usage="cooling.py --setpoint=X(C) --monitor='tcp://127.0.0.1:5000'",
        description='Temperature control',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--setpoint', type=float, default=-20.0,
                        help="Target temperature in Celsius")
    parser.add_argument('--logfile', type=str, default="temperature.log",
                        help="Filename for log file")
    parser.add_argument('--monitor', type=str, default="tcp://127.0.0.1:5000",
                        help="Online monitor address including port")
    args = parser.parse_args()

    cooling = Cooling(setpoint=args.setpoint, monitor=args.monitor)
    cooling.run()
