import time
import zmq
import logging
import numpy as np

from basil.dut import Dut
from online_monitor.utils import utils

FORMAT = '%(asctime)s [%(name)-20s] - %(levelname)-7s %(message)s'


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


def print_log(s,logfile="202008_DESY_temperature.log"):
    with open(logfile,"a") as f:
        f.write("%s %s\n"%(time.ctime(),s))
    print(s)

##### For the valve: open/close max(open)=0xFFFFFF, min(close)=0


##### monitor with plot
class Cooling(object):
    def __init__(self, conf_file="../examples/cooling.yaml", setpoint=-20, monitor=False):
        # Setup logging
        self.log = logging.getLogger('N2 Cooling')
        self.log.setLevel(logging.INFO)
        self.log.setFormatter(logging.Formatter(FORMAT))
        fh = logging.FileHandler('cooling.log')
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(FORMAT))
        self.log.addHandler(fh)
    
        # Setup online monitor
        if monitor:
            try:
                context = zmq.Context()
                self.socket = context.socket(zmq.PUB)
                self.socket.bind(args.monitor)
                self.log.info("Sending data to server %s" % args.monitor)
            except zmq.error.ZMQError:
                self.log.warning("Cannot connect to socket for data sending")
                self.socket = None
        else:
            self.socket = None
           
        self.setpoint = setpoint
        devices = Dut(conf_file)
        devices.init()
        self.temp_sensors = devices["sensirion"]
        self.valve = devices["bronkhorst"]

    def run(self, valve=0x000000, feedback="on"):
        if feedback== "open":
            mode=8
        elif feedback=="close":
            mode=3
        else: #"on"
            mode=4
        self.valve.set_control_mode(mode)
        ret = self.valve.get_control_mode()
        if ret == mode:
            self.log.info("Valve started with valve %s" % feedback)
        else:
            self.log.error("ERR: Control mode cannot be set, mode is %s" % str(ret))

        interval=10
        #### init buffers
        temp = np.ones(10000)*float("NaN")
        i=0

        self.valve.set_valve_output(0x000000)
        if mode == 4:
            self.valve.set_valve_output(valve)
        time.sleep(1)
        self.log.info("valve 0x%x,0x%x" % (self.valve.get_valve_output(), self.valve.get_measure()))
        pre = self.temp_sensors.get_temperature()[0]
        flg = 0
        while True:
            temps = self.temp_sensors.get_temperature()
            temp[i % len(temp)] = temps[0]
            try:
                humids = self.temp_sensors.get_humidity()
                self.log.info("%.2fC %.2f RH" % (temp[i % len(temp)], humids[0]))
            except:
                print_log("%.2fC Humidity read error" % (temp[i%len(temp)]),logfile=logfile)

            if socket:
                send_data(socket, data=np.array([temps, humids], dtype=np.float64))

            time.sleep(1)

            if flg > 1:
                flg=flg-1
            elif flg==1 and temp[i%len(temp)] > setpoint-0.5 and self.valve.get_valve_output()!=0 and mode==4:
                self.valve.set_valve_output(0x000000)
                print_log("valve 0x%x,0x%x"%(self.valve.get_valve_output(),self.valve.get_measure()),
                          logfile=logfile)
                flg = 20 
            elif temp[i%len(temp)] < setpoint-0.2 and self.valve.get_valve_output()==0 and mode==4:
                self.valve.set_valve_output(0x800000)  # open valve, was originally 0x800000
                flg = 10
                print_log("valve 0x%x,0x%x"%(self.valve.get_valve_output(),self.valve.get_measure()),
                          logfile=logfile)
                pre=temp[i%len(temp)]
            elif temp[i%len(temp)] > setpoint and self.valve.get_valve_output()!=0 and mode==4:
                self.valve.set_valve_output(0x000000)
                flg = 50
                print_log("valve 0x%x,0x%x"%(self.valve.get_valve_output(),self.valve.get_measure()),
                          logfile=logfile)
            i = i + 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(usage="cooling.py --setpoint=X(C) --monitor='tcp://127.0.0.1:5000'",
        description='Temperature control',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--setpoint', type=float, default=-20.0,
                        help="Target temperature in Celsius")
    parser.add_argument('--feedback', type=str, default="on",
                        help="on: feedback on, open: open completely, close: close completely")
    parser.add_argument('--logfile', type=str, default="2020-12_DESY_temperature.log",
                        help="log file")
    parser.add_argument('--monitor', type=str, default="", help="Online monitor address including port")
    args = parser.parse_args()

    cooling = Cooling(setpoint=setpoint, monitor=monitor)
    cooling.run()

