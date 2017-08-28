''' Simple Web app using plot.ly
'''

import remi.gui as gui
from remi import start, App
import threading
import random
import time
import datetime
import json
import logging

# https://github.com/adafruit/Adafruit_Python_MCP9808
import Adafruit_MCP9808.MCP9808 as MCP9808

data_lock = threading.Lock()


class LabelSpinBox(gui.HBox):
    def __init__(self, label='label', default_value=0,
                 min=0, max=100, step=1, labelWidth=100,
                 spinBoxWidth=80, *args):
        super(self.__class__, self).__init__(*args)

        self._label = gui.Label(label, width=labelWidth)
        self._spinbox = gui.SpinBox(default_value=default_value,
                                    min=min, max=max,
                                    step=step, width=spinBoxWidth)

        self.append(self._label, 'label')
        self.append(self._spinbox, 'spinbox')

        self.set_on_change_listener = self._spinbox.set_on_change_listener
        self.set_value = self._spinbox.set_value
        self.get_value = self._spinbox.get_value
        self.setValue = self.set_value


class PlotlyWidget(gui.Widget):
    def __init__(self, data, sensor_ids, **kwargs):
        super(PlotlyWidget, self).__init__(**kwargs)
        self.data = data
        javascript_code = gui.Tag()
        javascript_code.type = 'script'
        javascript_code.attributes['type'] = 'text/javascript'
        code = """
        var PLOT = document.getElementById('plot');
        var url = "plot/get_refresh";
        var plotOptions = {
                           title: 'Temperature'
                          ,xaxis: {title: 'Time'}
                          ,yaxis: {title: 'Temperature [C]',type: 'linear'}
                          };
        plotOptions['margin'] = {t:50, l:50, r:30};

        Plotly.d3.json(url,
            function(error, data) {
                Plotly.plot(PLOT, data, plotOptions);
            });
        """
        javascript_code.add_child('code',   # Add to Tag
                                  code % {'id': id(self), })
        self.add_child('javascript_code', javascript_code)   # Add to widget

    def get_refresh(self):
        if self.data is None:
            return None, None

        txt = json.dumps(self.data)
        headers = {'Content-type': 'text/plain'}
        return [txt, headers]


class MyApp(App):
    def __init__(self, *args):
        html_head = '<script src="https://cdn.plot.ly/plotly-latest.min.js">'
        html_head += '</script>'
        self.sensors = self.get_sensors(addresses=ADDRESSES)
        self.reset_data()
        super(MyApp, self).__init__(*args, html_head=html_head)

    def get_sensors(self, addresses):
        sensors = {}
        for address in addresses:
            try:
                sensor = MCP9808.MCP9808(address)
                sensor.begin()
                sensors[address] = sensor
            except IOError:
                logging.warning("Device at address %d not available", address)
        return sensors

    def reset_data(self):
        with data_lock:
            self.data = []
            for sensor_id in self.sensors:
                self.data.extend([{'x': [], 'y': [], 'type': 'scatter', 'mode':
                                   'markers+lines', 'name': '%s' % str(hex(sensor_id))}])

    def main(self):
        """ Interface is defined
        """
        wid = gui.HBox()
        wid.style['position'] = 'absolute'
        ctrl = gui.VBox(width=400)
        ctrl.style['justify-content'] = 'space-around'

        meas_buttons = gui.HBox(width=400)

        plotContainer = gui.Widget()

        self.plt = PlotlyWidget(data=self.data, id='plot',
                                sensor_ids=self.sensors.keys())
        plotContainer.append(self.plt)

        self.history_box = LabelSpinBox(default_value=100,
                                        min=1, max=10000000,
                                        step=1, label='History', labelWidth=200)
        self.delay_box = LabelSpinBox(default_value=1,
                                      min=1, max=3600,
                                      step=1, label='Delay [s]', labelWidth=200)
        temp_box = LabelSpinBox(default_value=20,
                                     min=-30, max=20,
                                     step=1, label='Temperature [C]', labelWidth=200)

        bt_meas = gui.Button('Measure temperature', width=200, height=30)
        bt_meas.style['margin'] = 'auto 50px'
        bt_meas.style['background-color'] = 'green'

        bt_clear = gui.Button('Clear', width=200, height=30)
        meas_buttons.append(bt_meas)
        meas_buttons.append(bt_clear)

        self.started = False

        # setting the listener for the interface widgets
        bt_meas.set_on_click_listener(self.on_meas_pressed, ctrl)
        bt_clear.set_on_click_listener(self.on_clear_pressed, ctrl)
        temp_box.set_on_change_listener(self.on_set_temp, ctrl)

        ctrl.append(self.history_box)
        ctrl.append(self.delay_box)
        ctrl.append(self.temp_box)
        ctrl.append(meas_buttons)

        # returning the root widget
        wid.append(ctrl)
        wid.append(plotContainer)

        return wid

    def run(self):
        """ Run when Measue Temperatur button is clicked.
        """
        while self.running:
            with data_lock:  # Aquire lock to access data
                for idx, sensor in enumerate(self.sensors.values()):
                    x = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.data[idx]['x'].append(x)
                    self.data[idx]['y'].append(sensor.readTempC())
                if len(self.data[0]['x']) == 1:  # Can't extend an empty plot
                    cmd = ''
                    for idx in range(len(self.data)):
                        lastx = self.data[idx]['x']
                        lasty = self.data[idx]['y']
                        cmd += """
                        PLOT.data[%(key)s].x = [%(x)s];
                        PLOT.data[%(key)s].y = [%(y)s];
                        Plotly.redraw(PLOT);""" % {'key': idx,
                                                   'x': lastx, 'y': lasty}
                else:
                    xarray = []
                    yarray = []
                    for idx in range(len(self.data)):
                        xarray.append([self.data[idx]['x'][-1]])
                        yarray.append([self.data[idx]['y'][-1]])
                    xarray = repr(xarray)
                    yarray = repr(yarray)
                    indices = repr(list(range(len(self.data))))
                    cmd = """
                    var update = {x:%(x)s, y:%(y)s};
                    Plotly.extendTraces(PLOT, update, %(indices)s,%(history)s);
                    """ % {'x': xarray, 'y': yarray, 'indices': indices,
                           'history': self.history_box._spinbox.get_value()}
                self.execute_javascript(cmd)
                # Lock is release
            time.sleep(int(self.delay_box._spinbox.get_value()))

    def stop(self):
        self.running = False
        self.thread.join()

    def on_meas_pressed(self, widget, settings):
        if not self.started:
            widget.style['background-color'] = 'red'
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
        else:
            self.stop()
            widget.style['background-color'] = 'green'
        self.started = not self.started

    def on_clear_pressed(self, widget, settings):
        self.reset_data()

    def on_set_temp(self, widget, settings):
        logging.info("Set temperature %d", settings)


if __name__ == "__main__":
    ADDRESSES = [0x19, 0x1a, 0x1c]
    start(MyApp, debug=False, port=8081,
          address='131.220.165.89',
          start_browser=True)
