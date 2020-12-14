from PyQt5 import Qt
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
from pyqtgraph.dockarea import DockArea, Dock
import pyqtgraph.ptime as ptime
from datetime import datetime, date

from online_monitor.utils import utils
from online_monitor.receiver.receiver import Receiver


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%x %X") for value in values]


class N2Cooling(Receiver):
    def setup_receiver(self):
        self.set_bidirectional_communication()  # We want to change converter settings
        self.avg_window = 180

    def setup_widgets(self, parent, name):
        dock_area = DockArea()
        parent.addTab(dock_area, name)
        # Docks
        dock_values = Dock("Temperature and Humidity", size=(400, 400))
        dock_status = Dock("Status", size=(800, 40))
        dock_area.addDock(dock_values, "above")
        dock_area.addDock(dock_status, "top")

        # Status dock on top
        cw = QtGui.QWidget()
        cw.setStyleSheet("QWidget {background-color:white}")
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        self.avg_sensor_temp_label = QtGui.QLabel("Mean sensor temperature over last %d s\n" % self.avg_window)
        self.dewpoint_label = QtGui.QLabel("Dew point:\n-- C")
        self.last_timestamp_label = QtGui.QLabel("Last timestamp:\n%s" % "No data yet")
        self.avg_setting = Qt.QSpinBox()
        self.avg_setting.setMinimum(1)
        self.avg_setting.setMaximum(3600)
        self.avg_setting.setValue(self.avg_window)
        self.avg_setting.setPrefix("Average over ")
        self.avg_setting.setSuffix(" s")
        self.reset_button = QtGui.QPushButton("Reset")
        layout.addWidget(self.avg_sensor_temp_label, 0, 0, 1, 1)
        layout.addWidget(self.avg_setting, 0, 1, 1, 1)
        layout.addWidget(self.dewpoint_label, 0, 2, 1, 1)
        layout.addWidget(self.last_timestamp_label, 0, 3, 1, 1)
        layout.addWidget(self.reset_button, 0, 4, 1, 1)
        dock_status.addWidget(cw)

        # Connect widgets
        self.reset_button.clicked.connect(lambda: self.send_command("RESET"))
        self.avg_setting.valueChanged.connect(lambda value: self._update_avg_window(value))

        # particle rate dock
        cooling_graphics = pg.GraphicsLayoutWidget()
        cooling_graphics.show()

        # Temperature plots
        date_axis_temp = TimeAxisItem(orientation="bottom")
        date_axis_humid = TimeAxisItem(orientation="bottom")
        plot_temp = pg.PlotItem(axisItems={"bottom": date_axis_temp}, labels={"left": "Temperature / C"})
        plot_humidity = pg.PlotItem(axisItems={"bottom": date_axis_humid}, labels={"left": "rel. Humidity / %"})

        plot_humidity.setXLink(plot_temp)

        self.temp_sensor_curve = pg.PlotCurveItem(pen=pg.mkPen(color=(181, 0, 15), width=2))
        self.temp_box_curve = pg.PlotCurveItem(pen=pg.mkPen(color=(0, 181, 97), width=2))
        self.humid_sensor_curve = pg.PlotCurveItem(pen=pg.mkPen((181, 0, 15), width=2))

        # add legend
        legend_temp = pg.LegendItem(offset=(50, 1))
        legend_temp.setParentItem(plot_temp)
        legend_temp.addItem(self.temp_sensor_curve, "Sensor temperature close to DUT")
        legend_temp.addItem(self.temp_box_curve, "Box temperature with dry ice")
        legend_humid_sensor = pg.LegendItem(offset=(50, 1))
        legend_humid_sensor.setParentItem(plot_humidity)
        legend_humid_sensor.addItem(self.humid_sensor_curve, "Sensor humidity close to DUT")

        # add items to plots and customize plots viewboxes
        plot_temp.addItem(self.temp_sensor_curve)
        plot_temp.addItem(self.temp_box_curve)
        vb = plot_temp.vb.setBackgroundColor("#E6E5F4")
        plot_temp.getAxis("left").setZValue(0)
        plot_temp.getAxis("left").setGrid(155)
        plot_temp.getAxis("bottom").setStyle(showValues=False)

        plot_humidity.addItem(self.humid_sensor_curve)
        plot_humidity.vb.setBackgroundColor("#E6E5F4")
        plot_humidity.showGrid(x=True, y=True)
        plot_humidity.getAxis("left").setZValue(0)
        plot_humidity.getAxis("bottom").setGrid(155)

        cooling_graphics.addItem(plot_temp, row=0, col=1, rowspan=1, colspan=3)
        cooling_graphics.addItem(plot_humidity, row=1, col=1, rowspan=1, colspan=3)
        dock_values.addWidget(cooling_graphics)

        # add dict of all used plotcurveitems for individual handling of each plot
        self.plots = {
            "temp_sensor": self.temp_sensor_curve,
            "temp_box": self.temp_box_curve,
            "humidity_sensor": self.humid_sensor_curve,
        }
        self.plot_delay = 0

    def deserialize_data(self, data):
        _, meta = utils.simple_dec(data)
        return meta

    def handle_data_if_active(self, data):
        # look for TLU data in data stream
        if "temp" in data:
            for key in data["temp"]:
                self.plots[key].setData(data["time"], data["temp"][key], autoDownsample=True)
        if "humidity" in data:
            for key in data["humidity"]:
                self.plots[key].setData(data["time"], data["humidity"][key], autoDownsample=True)

        # set timestamp, plot delay and readour rate
        self.avg_sensor_temp_label.setText(
            "Mean sensor temperature over last %d s:\n%.2f C"
            % (self.avg_window, data["stats"]["avg"]["temp_sensor_avg"])
        )
        self.dewpoint_label.setText("Dew point:\n%.1f C" % data["stats"]["dp"])
        self.last_timestamp_label.setText(
            "Last timestamp:\n%s" % datetime.fromtimestamp(data["stats"]["last_timestamp"]).strftime("%x %X")
        )
        now = ptime.time()

    def _update_avg_window(self, value):
        self.avg_window = value
        self.send_command(str(value))
