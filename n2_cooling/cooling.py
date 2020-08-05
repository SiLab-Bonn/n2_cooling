import time
import zmq
import logging
import numpy as np
import matplotlib.pyplot as plt

from basil.dut import Dut
from online_monitor.utils import utils

logger = logging.getLogger(__name__)


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
"""valve: initial valve value
   setpoint: setpoint in C, None is just monitor (no feedback)"""
def run(s, e, valve=0x000000, setpoint=-20, feedback="on",logfile="202003_DESY_temperature.log", socket=None):
    if feedback== "open":
        mode=8
    elif feedback=="close":
        mode=3
    else: #"on"
        mode=4
    e.set_control_mode(mode)
    ret=e.get_control_mode()
    if ret==mode:
        print_log ("Valve started with valve %s"%feedback)
    else:
        print_log("ERR: Control mode cannot be set ret=%s"%str(ret))

    interval=10
    #### init buffers
    plt.ion()
    temp=np.ones(10000)*float("NaN")
    i=0

    #setpoint=-16.5
    e.set_valve_output(0x000000)
    if mode == 4:
        e.set_valve_output(valve)
    time.sleep(1)
    print_log("valve 0x%x,0x%x"%(e.get_valve_output(),e.get_measure()),
              logfile=logfile)
    pre=s.get_temperature()[0]
    flg=0
    while True:
        temps = s.get_temperature()
        temp[i%len(temp)]=temps[0]
        try:
            humids = s.get_humidity()
            print_log("%.2fC %.2f RH" % (temp[i%len(temp)], humids[0]),logfile=logfile)
        except:
            print_log("%.2fC Humidity read error" % (temp[i%len(temp)]),logfile=logfile)

        if socket:
            send_data(socket, data=np.array([temps, humids], dtype=np.float64))

        plt.clf()
        plt.plot(temp)
        plt.plot([i%len(temp),i%len(temp)],[np.min(temp[np.bitwise_not(np.isnan(temp))]),np.max(temp[np.bitwise_not(np.isnan(temp))])])
        plt.xlabel("Time [s]")
        plt.title("%.2fC %s"%(temp[i%len(temp)],time.ctime()))
        plt.ylabel("Sensirion Temp [C]")
        plt.pause(0.001)
        time.sleep(1)

        if flg > 1:
            flg=flg-1
        elif flg==1 and temp[i%len(temp)] > setpoint-0.5 and e.get_valve_output()!=0 and mode==4:
            e.set_valve_output(0x000000)
            print_log("valve 0x%x,0x%x"%(e.get_valve_output(),e.get_measure()),
                      logfile=logfile)
            flg=20 
        elif temp[i%len(temp)] < setpoint-0.2 and e.get_valve_output()==0 and mode==4:
            e.set_valve_output(0x800000)  # open valve, was originally 0x800000
            flg=10
            print_log("valve 0x%x,0x%x"%(e.get_valve_output(),e.get_measure()),
                      logfile=logfile)
            pre=temp[i%len(temp)]
        elif temp[i%len(temp)] > setpoint and e.get_valve_output()!=0 and mode==4:
            e.set_valve_output(0x000000)
            flg=50
            print_log("valve 0x%x,0x%x"%(e.get_valve_output(),e.get_measure()),
                      logfile=logfile)
        i=i+1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(usage="cooling.py --setpoint=X(C) --valve=0x000000",
        description='Temperature control',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--setpoint', type=float, default=-20.0,
                        help="Target temperature in Celsius")
    parser.add_argument('--valve', type=int, default=0,
                        help="Valve initial value (max open=0xFFFFFF, closed=0x0)", metavar='0...65535')
    parser.add_argument('--feedback', type=str, default="on",
                        help="on: feedback on, open: open completely, close: close completely")
    parser.add_argument('--logfile', type=str, default="2020-08_DESY_temperature.log",
                        help="log file")
    parser.add_argument('--monitor', type=str, default="", help="Online monitor address including port")
    args = parser.parse_args()

    dut = Dut("../examples/cooling.yaml")
    dut.init()
    s = dut["sensirion"]
    e = dut["bronkhorst"]

    if args.monitor:
        try:
            context = zmq.Context()
            socket = context.socket(zmq.PUB)
            socket.bind(args.monitor)
            logger.info("Sending data to server %s" % args.monitor)
        except zmq.error.ZMQError:
            logger.warning("Cannot connect to socket for data sending")
            socket = None
    else:
        socket = None

    run(s, e, setpoint=args.setpoint,valve=args.valve, feedback=args.feedback,
        logfile=args.logfile, socket=socket)
    print_log("setpoint:%d, valve:0x%x"%(args.setpoint,args.valve),
              logfile=args.logfile)

