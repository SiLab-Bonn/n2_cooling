# N2_cooling
Controller for the N2 Cooling System

## Getting started
You need to install the following python packages:
```bash
conda install numpy zeromq pyqtgraph pyqt
```
as well as
```bash
pip install basil-daq online_monitor
```

## Set up hardware
1. Connect all tubes as documented
2. Close cooling box and flush with lots of N2
3. Put small amount of dry ice in wooden box
4. Adjust valves to allow for stable operation
5. When system is stable put larger amounts of dry ice every few hours
    - It is possible to run the system for at least six to eight hours with one load of dry ice, possibly more

## Software
Just run `python cooling.py`, optional arguments are:
  - `setpoint` (default: `-20`) The target temperature for the feedback loop
  - `valve` (default: `0`) Initial valve value (`0xFFFFFF` closed, `0x0` open)
  - `feedback` (default: `on`) Activate feedback loop or just `open` or `close` valve
  - `logfile` (default: current directory) Path and name for log file including extension
  - `monitor` (default: `None`) Address and port for online monitor as `tcp://xxx.xxx.xxx.xxx:pppp`
  
  ## Tested valve settings
  Target temperature | Hot valve (lpm) | Cold valve (lpm) | Main valve (lpm)
  -------|---|----|----
  -15 °C | 6 | 15 | > 25