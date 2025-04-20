import clr  # pythonnet library is required
import os

# Load the OpenHardwareMonitor library
abspath = os.path.abspath("openhardwaremonitor-v0.9.6/OpenHardwareMonitor/OpenHardwareMonitorLib.dll")
print(f"Loading OpenHardwareMonitor from {abspath}")
clr.AddReference(abspath)
from OpenHardwareMonitor import Hardware

# Initialize the computer object
computer = Hardware.Computer()
computer.CPUEnabled = True  # Enable CPU monitoring
computer.GPUEnabled = True  # Enable GPU monitoring
computer.Open()

# Iterate through hardware components
for hardware in computer.Hardware:
    hardware.Update()  # Update the hardware data
    print(f"Hardware: {hardware.Name}")
    for sensor in hardware.Sensors:
        print(f"  Sensor: {sensor.Name}, Type: {sensor.SensorType}, Value: {sensor.Value}")