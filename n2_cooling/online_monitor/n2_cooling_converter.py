import numpy as np

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
        self.n_values = 7200
        self.last_timestamp = 0

        # Init result hists
        self.reset()

    def interpret_data(self, data):
        data, meta_data = data[0][1]
        self.update_arrays(data, meta_data)

        # Calculate recent average of curves (timespan can be defined in GUI)
        selection = np.isfinite(self.temp_arrays["temp_sensor"])
        self.averages["temp_sensor_avg"] = np.mean(self.temp_arrays["temp_sensor"][selection][-self.avg_window :])

        interpreted_data = {
            "temp": self.temp_arrays,
            "humidity": self.humidity_arrays,
            "time": self.timestamps,
            "stats": {"avg": self.averages, "last_timestamp": self.last_timestamp},
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

    def reset(self):
        self.temp_arrays = {"temp_sensor": np.full(self.n_values, np.nan), "temp_box": np.full(self.n_values, np.nan)}
        self.humidity_arrays = {
            "humidity_sensor": np.full(self.n_values, np.nan),
            # 'humidity_box': np.full(18000,  np.nan)
        }
        self.timestamps = np.full(self.n_values, np.nan)

        self.averages = {
            "temp_sensor_avg": 0,
        }

        self.last_timestamp = 0
        self.avg_window = 180  # Amount of values to be taken into account for averaging

    def update_arrays(self, data, meta_data):
        for idx, key in enumerate(self.temp_arrays):
            self.temp_arrays[key] = np.roll(self.temp_arrays[key], -1)
            self.temp_arrays[key][-1] = data[0][idx]
        for idx, key in enumerate(self.humidity_arrays):
            self.humidity_arrays[key] = np.roll(self.humidity_arrays[key], -1)
            self.humidity_arrays[key][-1] = data[1][idx]
        self.timestamps = np.roll(self.timestamps, -1)
        self.timestamps[-1] = meta_data["timestamp"]
        self.last_timestamp = meta_data["timestamp"]
