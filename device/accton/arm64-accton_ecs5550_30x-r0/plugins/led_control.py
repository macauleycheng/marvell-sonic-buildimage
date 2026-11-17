# led_control.py
#
# Platform-specific LED control functionality for SONiC
#

try:
    from swsscommon import swsscommon
    from sonic_led.led_control_base import LedControlBase
    import os.path
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")

CPLD_SYSFS_DIR = "/sys/bus/i2c/devices/i2c-1/1-0064"

port_fp_to_reg_bit = [
 ("bad", "bad"), # invalid fp port
 (0x9b, 3), # 1
 (0x9b, 2), # 2
 (0x9b, 1), # 3
 (0x9b, 0), # 4
 (0x9a, 7), # 5
 (0x9a, 6), # 6
 (0x9a, 5), # 7
 (0x9a, 4), # 8
 (0x9a, 3), # 9
 (0x9a, 2), # 10
 (0x9a, 1), # 11
 (0x9a, 0), # 12
 (0x9e, 3), # 13
 (0x9e, 2), # 14
 (0x9e, 1), # 15
 (0x9e, 0), # 16
 (0x9d, 7), # 17
 (0x9d, 6), # 18
 (0x9d, 5), # 19
 (0x9d, 4), # 20
 (0x9d, 3), # 21
 (0x9d, 2), # 22
 (0x9d, 1), # 23
 (0x9d, 0), # 24
]

class LedControl(LedControlBase):
    """Platform specific LED control class"""
    SONIC_PORT_NAME_PREFIX = "Ethernet"

    def __init__(self):
        self.__cpld_write(0x9a, 0xff)
        self.__cpld_write(0x9b, 0xff)
        self.__cpld_write(0x9c, 0xff)
        self.__cpld_write(0x9d, 0xff)
        self.__cpld_write(0x9e, 0xff)
        self.__cpld_write(0x9f, 0xff)

    def __read_txt_file(self, file_path):
        try:
            with open(file_path, 'r') as fd:
                data = fd.read()
                return data.strip()
        except IOError:
            pass
        return None

    def __write_txt_file(self, file_path, value):
        try:
            with open(file_path, 'w') as fd:
                fd.write(str(value))
        except Exception as error:
            print("An exception occurred:", error)
            return False
        return True

    def __cpld_read(self, reg):
        self.__write_txt_file(os.path.join(CPLD_SYSFS_DIR, "reg_offset"), hex(reg))
        ret = self.__read_txt_file(os.path.join(CPLD_SYSFS_DIR, "reg_value"))
        val = ret.split()[1]
        return int(val.split(':')[1], 16)

    def __cpld_write(self, reg, val):
        self.__write_txt_file(os.path.join(CPLD_SYSFS_DIR, "reg_offset"), hex(reg))
        self.__write_txt_file(os.path.join(CPLD_SYSFS_DIR, "reg_value"), hex(val))

    def __port_idx_to_reg(self, port_idx):
        return port_fp_to_reg_bit[port_idx][0]

    def __port_idx_to_bit(self, port_idx):
        return port_fp_to_reg_bit[port_idx][1]

    def __cpld_write_led_port_status(self, idx, is_10g):
        ena = 1 if is_10g else 0
        reg = self.__port_idx_to_reg(idx)
        bit = self.__port_idx_to_bit(idx)
        val = self.__cpld_read(reg)
        val = val & ~(1 << bit)
        val = val | (ena << bit)
        self.__cpld_write(reg, val)

    def __port_name_to_index(self, port_name):
        # Strip "Ethernet" off port name
        if not port_name.startswith(self.SONIC_PORT_NAME_PREFIX):
            return -1

        port_idx = int(port_name[len(self.SONIC_PORT_NAME_PREFIX):])
        return port_idx

    def port_link_state_change(self, portname, state):
        port_idx = self.__port_name_to_index(portname)
        speed = self.__intf_speed(portname)

        if speed and speed <= 10000:
            self.__cpld_write_led_port_status(port_idx+1, speed == 10000)

    def port_link_state_change(self, portname, state):
        pass

    def port_speed_change(self, portname, speed):
        port_idx = self.__port_name_to_index(portname)

        if speed <= 10000:
            self.__cpld_write_led_port_status(port_idx+1, speed == 10000)
