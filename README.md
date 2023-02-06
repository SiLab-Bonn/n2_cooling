# N2_cooling
For a more detailed manual for the cooling system see [wiki](https://github.com/SiLab-Bonn/n2_cooling/wiki/Manual-for-the-N2-cooling-system).
##Flashing the Arduino Nano with the firmware
First install the Arduino IDE and add the library [arduino-sht](https://www.arduinolibraries.info/libraries/arduino-sht). For that you can use the library manager in the IDE. Otherwise you can add the library from the firmware folder into your library folder in your sketchbook. That can be found in the IDE under file/preferences.
## Quick start
Clone this git repository and install the packages via:
```bash
pip install -e .
```
To set the path for the online-monitor go into the cloned git folder and use this command:
```bash
plugin_online_monitor n2_cooling/online_monitor
```
After you have connected all components and flashed the Arduino nano with the firmware, open two terminals. To start the cooling use:
```bash
n2cooling
```
Start the online-monitor via:
```bash
start_online_monitor online_monitor.yaml
```


