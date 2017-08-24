import time
import datetime
import logging

# https://github.com/adafruit/Adafruit_Python_MCP9808
import Adafruit_MCP9808.MCP9808 as MCP9808


def get_sensors(adresses):
    sensors = []
    for address in addresses:
        try:
            sensor = MCP9808.MCP9808(address)
            sensor.begin(sensor)
            sensors.append()
        except IOError:
            logging.warning("Device at address %d not available", address)
    return sensors


def read_sensors(sensors, delay=1):
    """ Read the sensors and add to file.
    Delay readings in seconds
    """

    # Append header to indentifz sensors by id
    with open('temp.log', 'a') as outfile:
        s_str = []
        for sensor in sensors:
            did = sensor._device.readU16BE(MCP9808.MCP9808_REG_DEVICE_ID)
            s_str.append('{0:04X}'.format(did))
        s_str = '\t'.join(s_str)
        outfile.write("\t" + s_str)

    while True:
        temps = []
        for sensor in sensors:
            temps.append(str(sensor.readTempC()))
        with open('temp.log', 'a') as outfile:
            outfile.write(datetime.datetime.now().isoformat(
                ' ') + '\t'.join(temps) + '\n')
            logging.info(datetime.datetime.now().isoformat(
                ' ') + '%s', '\t'.join(temps))
        time.sleep(delay)


if __name__ == "__main__":
    addresses = [0x18, 0x19, 0x1a]
    sensors = get_sensors(addresses)
    read_sensors(sensors, delay=1)
