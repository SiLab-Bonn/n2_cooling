# N2_cooling
For a more detailed manual for the cooling system see [wiki](https://github.com/SiLab-Bonn/n2_cooling/wiki/Manual-for-the-N2-cooling-system). 
## Quick start
Clone this git repository and install the packages via:
```bash
pip install -e .
```
To set the path for the online-monitor go into the cloned git folder and use this command:
```bash
plugin_online_monitor n2_cooling/online_monitor
```
After you have connected all components and flashed the Arduino nano with the firmware, open two terminals. Execute the cooling.py in one terminal. In the other start the online-monitor via:
```bash
start_online_monitor online_monitor.yaml
```


