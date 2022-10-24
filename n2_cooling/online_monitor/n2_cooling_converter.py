import numpy as np
import time
from collections import deque #rolling lists

from online_monitor.utils import utils
from online_monitor.converter.transceiver import Transceiver


class N2CoolingConverter(Transceiver):
  

    def setup_transceiver(self):
        """ Called at the beginning
            We want to be able to change the histogrammmer settings
            thus bidirectional communication needed
        """

        self.set_bidirectional_communication()

    def deserialize_data(self, data):
        return utils.simple_dec(data)

    def setup_interpretation(self):
        # Maximum amount of values before override
        self.n_values = 500
        self.last_timestamp = time.time()

        # Init result hists
        self.reset()

    def reset(self):
        print('RESET')
        self.temp_arrays = {"temp_sensor": [], "temp_box": []}#, "Valve_output": []}
        print(self.temp_arrays)
        self.humidity_arrays = {
            "humidity_sensor": []
            
        }
        self.timestamps = []

        self.averages = {
            "temp_sensor_avg": 0,
        }
        self.dewpoint = None

        self.last_timestamp = time.time()
        self.avg_window = 180  # Amount of values to be taken into account for averaging    
        
    
    
    def update_arrays(self, data, meta_data):

        print("data")
        print('META DATA')
        # print(meta_data)
        for idx, key in enumerate(self.temp_arrays):
            #print(self.temp_arrays)
            #print(idx,key)
            #self.temp_arrays[key] = np.roll(self.temp_arrays[key], -1)
            # self.temp_arrays[key].extend(data[0])
            # print("updated")
            # print(self.temp_arrays[key])
            print(key)
            print(len(self.temp_arrays[key]))
            
            #set data_indx because for temp_box other index in data is needed than for temp_sensor (see output get_temps)
            
            if key=="temp_box":
                data_indx=0
            # if key=="Valve_output":
            #     data_indx=2
            else:
                data_indx=1
            
            
            if len(self.temp_arrays[key])<self.n_values:
                self.temp_arrays[key].append(data[data_indx])
                print("KEY", key)
                print("temp_arrays[KEY]",self.temp_arrays[key])
            else:
                self.temp_arrays[key]=self.temp_arrays[key][1:]
                self.temp_arrays[key].append(data[data_indx])
                print("KEY", key)
                print("temp_arrays[KEY]",self.temp_arrays[key])
        for idx, key in enumerate(self.humidity_arrays):
            #self.humidity_arrays[key] = np.roll(self.humidity_arrays[key], -1)
            if len(self.humidity_arrays[key])<self.n_values:
                self.humidity_arrays[key].append(data[2])
            else:
                self.humidity_arrays[key]=self.humidity_arrays[key][1:]
                self.humidity_arrays[key].append(data[2])
        # self.timestamps = np.roll(self.timestamps, -1)
            # print('Hier kommt die Metadata')
            # print(meta_data)
            # print(type(meta_data['timestamp']))
            # print(type(self.timestamps),self.timestamps)
            # self.timestamps.append(meta_data["timestamp"])
            # self.last_timestamp = meta_data['timestamp']
            if len(self.timestamps)<self.n_values:
                self.timestamps.append(meta_data["timestamp"])
            else:
                self.timestamps=self.timestamps[1:]
                self.timestamps.append(meta_data["timestamp"])
            # print(self.last_timestamp)
        
    
    
    
    def calculate_dewpoint(self, data):
        b, c = 17.67, 243.5
        temp = data[0]
        rh = data[1]
        gamma = np.log(rh / 100.) + b * temp / (c + temp)
        self.dewpoint = c * gamma / (b - gamma)
        
        
    
    def interpret_data(self, data):
        
        data, meta_data = data[0][1]
        # print("META DATA")
        print(data)
        self.update_arrays(data,meta_data)
        self.calculate_dewpoint(data)
        
        #print(data)
        # Calculate recent average of curves (timespan can be defined in GUI)
        #selection = np.isfinite(self.temp_arrays["temp_sensor"])
        #print(self.temp_arrays["temp_sensor"])
        #print(type(self.temp_arrays["temp_sensor"]))
        #extender=[0]*(self.avg_window-len(data))
        #selection = np.isfinite(self.temp_arrays["temp_sensor"])
        # print(self.temp_arrays["temp_sensor"])
        self.averages["temp_sensor_avg"] = np.mean(self.temp_arrays["temp_sensor"])

        interpreted_data = {
            "temp": self.temp_arrays,
            "humidity": self.humidity_arrays,
            "time": self.timestamps,
            "stats": {"avg": self.averages, "last_timestamp": self.last_timestamp, "dp": self.dewpoint},
        }

        return [interpreted_data]

    def serialize_data(self, data):
        return utils.simple_enc(None, data)

    def handle_command(self, command):
        # received signal is 'ACTIVETAB tab' where tab is the name (str) of the selected tab in online monitor
        if command[0] == "RESET":
            self.reset()
        else:
            self.avg_window = int(command[0])

    


        
   

