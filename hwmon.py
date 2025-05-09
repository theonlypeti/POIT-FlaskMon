import logging
import os
import subprocess

import requests
from datetime import datetime

class HardwareMonitor:
    def __init__(self, base_url="http://localhost:8086", logger: logging.Logger = None):
        """Initialize hardware monitor with API endpoint"""
        self.base_url = base_url
        self.data = None
        self.logger = logger or logging.getLogger(__name__)
        self.last_updated = None

    def update(self):
        """Fetch latest hardware data from API"""
        self.data = self._fetch_data()
        self.last_updated = datetime.now()
        return self.data

    def _fetch_data(self):
        """Internal method to fetch data from API"""
        results = {}

        try:
            # Check if service is available
            try:
                available_response = requests.get(f"{self.base_url}/api/available", timeout=5)
                results["available"] = available_response.text.strip() == "True"
            except requests.exceptions.RequestException as e:
                self.logger.warning(e)
                results["available"] = False
                pass

            if not results["available"]:
                self.logger.info("starting OHM")
                if not self.run_ohm():
                    self.logger.warning("Hardware monitoring service not available")
                    results["available"] = False
                    return results
                else:
                    self.logger.info("Hardware monitoring service started")
                    results["available"] = True

            # Get version
            version_response = requests.get(f"{self.base_url}/api/version", timeout=5)
            results["version"] = version_response.text.strip()

            # Get full sensor tree
            rootnode_response = requests.get(f"{self.base_url}/api/rootnode", timeout=5)
            results["sensors"] = rootnode_response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error connecting to hardware monitor API: {e}")
            results["error"] = str(e)

        return results

    def get_cpu_info(self):
        """Get CPU information and metrics"""
        if not self.data or not self.data.get("available"):
            return None

        for hardware in self.data["sensors"]["Hardware"]:
            if hardware["HardwareType"] == "CPU":
                return hardware
        return None

    def get_cpu_temperature(self):
        """Get CPU package temperature"""
        cpu = self.get_cpu_info()
        if not cpu:
            return None

        for sensor in cpu["Sensors"]:
            if sensor["Type"] == "Temperature" and sensor["Name"] == "CPU Package":
                return sensor["Value"]
        return None

    def get_cpu_load(self):
        """Get CPU total load percentage"""
        cpu = self.get_cpu_info()
        if not cpu:
            return None

        for sensor in cpu["Sensors"]:
            if sensor["Type"] == "Load" and sensor["Name"] == "CPU Total":
                return sensor["Value"]
        return None

    def get_ram_info(self):
        """Get RAM information"""
        if not self.data or not self.data.get("available"):
            return None

        for hardware in self.data["sensors"]["Hardware"]:
            if hardware["HardwareType"] == "RAM":
                return hardware
        return None

    def get_ram_usage(self):
        """Get RAM usage percentage"""
        ram = self.get_ram_info()
        if not ram:
            return None

        for sensor in ram["Sensors"]:
            if sensor["Type"] == "Load" and sensor["Name"] == "Memory":
                return sensor["Value"]
        return None

    def get_gpu_info(self):
        """Get GPU information"""
        if not self.data or not self.data.get("available"):
            return None

        for hardware in self.data["sensors"]["Hardware"]:
            if hardware["HardwareType"].startswith("Gpu"):
                return hardware
        return None

    def get_gpu_temperature(self):
        """Get GPU temperature"""
        gpu = self.get_gpu_info()
        if not gpu:
            return None

        for sensor in gpu["Sensors"]:
            if sensor["Type"] == "Temperature" and sensor["Name"] == "GPU Core":
                return sensor["Value"]
        return None

    def get_storage_info(self):
        """Get storage drives information"""
        if not self.data or not self.data.get("available"):
            return None

        drives = []
        for hardware in self.data["sensors"]["Hardware"]:
            if hardware["HardwareType"] == "HDD":
                drives.append(hardware)
        return drives

    def run_ohm(self):
        self.logger.info("Running OHM")
        self.logger.info(os.listdir("./OHM"))
        os.makedirs(r"./OHM", exist_ok=True)
        if not os.path.exists(fr".\OHM\OpenHardwareMonitor.exe"):
            raise FileNotFoundError("""
            OpenHardwareMonitor not found. Please Download it from
            https://github.com/hexagon-oss/openhardwaremonitor/releases
            and install it in ./OHM folder.""")
            return False
        with open(fr".\OHM\OpenHardwareMonitor.settings", "w") as f:
            f.write(
                r"""
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <appSettings>
    <add key="hiddenMenuItem" value="true" />
    <add key="runWebServer" value="true" />
    <add key="allowRemoteAccessMenuItem" value="false" />
  </appSettings>
</configuration>
"""
            )
            # Check for existing process
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == 'OpenHardwareMonitor.exe':
                    self.logger.info("OpenHardwareMonitor is already running")
                    break
            else:

                ohm = subprocess.Popen(['OpenHardwareMonitor.exe'], cwd=r'./OHM')
                self.logger.info("OHM running")
            return True

        except ImportError:
            return False