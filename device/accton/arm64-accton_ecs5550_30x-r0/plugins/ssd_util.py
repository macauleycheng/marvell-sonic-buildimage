#
# ssd_health
#

from sonic_platform_base.sonic_ssd.ssd_base import SsdBase
from subprocess import Popen, PIPE
from re import findall
from os.path import exists

NOT_AVAILABLE = "N/A"

class SsdUtil(SsdBase):

    def __init__(self, diskdev):
        """
        Constructor
        Args:
            diskdev: Linux device name to get parameters for
        """
        if not isinstance(diskdev, str):
            raise TypeError("disk dev type wrong {}".format(type(diskdev)))

        self.diskdev = diskdev
        self.mmcdev = "/dev/mmcblk0"
        if not exists(self.mmcdev):
            raise RuntimeError("disk dev {} not found".format(self.mmcdev))

        self.model = NOT_AVAILABLE
        self.serial = NOT_AVAILABLE
        self.firmware = NOT_AVAILABLE
        self.temperature = NOT_AVAILABLE
        self.health = NOT_AVAILABLE

        # mmc extcsd read /dev/mmcblk0
        INNODISK = ["mmc", "extcsd", "read", self.mmcdev]
        self.ssd_info = self._execute_shell(INNODISK)
        #print(self.ssd_info)

        MODEL_NAME = ["cat", "/sys/class/mmc_host/mmc0/mmc0:0001/name"]
        SIZE = ["cat", "/sys/class/mmc_host/mmc0/mmc0:0001/block/mmcblk0/size"]
        SERIAL = ["cat", "/sys/class/mmc_host/mmc0/mmc0:0001/serial"]
        HEALTH = ["df -h | grep mmc | awk '{print $5}'"]

        self.model_name_str = self._execute_shell(MODEL_NAME)
        self.size_str = self._execute_shell(SIZE)
        self.serial_str = self._execute_shell(SERIAL)
        self.health_str = self._execute_shell(HEALTH, shell=True)
        #print("self.model_name_str", self.model_name_str)
        #print("self.size_str", self.size_str)
        #print("self.serial_str", self.serial_str)
        #print("self.health_str", self.health_str)

        self.model = self.model_name_str.strip()
        self.serial = self.serial_str.strip()
        self.firmware = self._parse_re(r'eMMC Firmware Version:\s*(.+?)\n', self.ssd_info).strip()
        #print("self.firmware", self.firmware)
        self.temperature = NOT_AVAILABLE
        self.health = self.health_str.strip()
        self.size = round(float(62160896) * 512 / 1024 / 1024 / 1024, 1)

        #self.model = self._parse_re(r'Model Name:\s*(.+?)\n', self.ssd_info)
        #self.serial = self._parse_re(r'Serial Number:\s*(.+?)\n', self.ssd_info)
        #self.firmware = self._parse_re(r'FW Version:\s*(.+?)\n', self.ssd_info)
        #self.temperature = self._parse_re(r'Temperature\s*\[\s*(.+?)\]', self.ssd_info)
        #self.health = self._parse_re(r'Health:\s*(.+?)', self.ssd_info)

    def _execute_shell(self, cmd, shell=False):
        process = Popen(cmd, universal_newlines=True, stdout=PIPE, shell=shell)
        output, _ = process.communicate()
        return output

    def _parse_re(self, pattern, buffer):
        res_list = findall(pattern, buffer)
        return res_list[0] if res_list else NOT_AVAILABLE

    def get_health(self):
        """
        Retrieves current disk health in percentages
        Returns:
            A float number of current ssd health
            e.g. 83.5
        """
        return float(self.health.strip('%'))

    def get_temperature(self):
        """
        Retrieves current disk temperature in Celsius
        Returns:
            A float number of current temperature in Celsius
            e.g. 40.1
        """
        return self.temperature

    def get_model(self):
        """
        Retrieves model for the given disk device
        Returns:
            A string holding disk model as provided by the manufacturer
        """
        return "{} {} GiB".format(self.model, str(self.size))

    def get_firmware(self):
        """
        Retrieves firmware version for the given disk device
        Returns:
            A string holding disk firmware version as provided by the manufacturer
        """
        return self.firmware

    def get_serial(self):
        """
        Retrieves serial number for the given disk device
        Returns:
            A string holding disk serial number as provided by the manufacturer
        """
        return self.serial

    def get_vendor_output(self):
        """
        Retrieves vendor specific data for the given disk device
        Returns:
            A string holding some vendor specific disk information
        """
        return self.ssd_info
