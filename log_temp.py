import time
import datetime

# https://github.com/adafruit/Adafruit_Python_MCP9808
import Adafruit_MCP9808.MCP9808 as MCP9808

sensor = MCP9808.MCP9808()
sensor.begin()

while True:
	temp = str(sensor.readTempC())
	with open('temp.log', 'a') as outfile:
		outfile.write(datetime.datetime.now().isoformat(' ') + ',	' + temp + '\n')
	print datetime.datetime.now().isoformat(' ') + ' 	' + temp
	time.sleep(1)
