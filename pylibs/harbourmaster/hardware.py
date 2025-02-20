
# System imports
import datetime
import fnmatch
import json
import math
import pathlib
import platform
import re
import zipfile

from pathlib import Path

# Included imports

from loguru import logger

# Module imports
from .config import *
from .info import *
from .util import *


HW_ANY = object()

HW_INFO = {
    # Anbernic Devices
    'rg552':   {'resolution': (1920, 1152), 'analogsticks': 2, 'cpu': 'rk3399', 'capabilities': ['5:3', '1920x1152', 'power', 'hires', 'wide']},
    'rg503':   {'resolution': ( 960,  544), 'analogsticks': 2, 'cpu': 'rk3566', 'capabilities': ['30:17', '960x544', 'power', 'hires', 'wide']},
    'rg351mp': {'resolution': ( 640,  480), 'analogsticks': 2, 'cpu': 'rk3326', 'capabilities': ['4:3', '640x480']},
    'rg351p':  {'resolution': ( 480,  320), 'analogsticks': 2, 'cpu': 'rk3326', 'capabilities': ['3:2', '480x320', 'lowres']},
    'rg353v':  {'resolution': ( 640,  480), 'analogsticks': 2, 'cpu': 'rk3366', 'capabilities': ['4:3', '640x480', 'power']},
    'rg353p':  {'resolution': ( 640,  480), 'analogsticks': 2, 'cpu': 'rk3366', 'capabilities': ['4:3', '640x480', 'power']},
    'rg353m':  {'resolution': ( 640,  480), 'analogsticks': 2, 'cpu': 'rk3366', 'capabilities': ['4:3', '640x480', 'power']},
    'rg351v':  {'resolution': ( 640,  480), 'analogsticks': 1, 'cpu': 'rk3326', 'capabilities': ['4:3', '640x480']},

    # Hardkernel Devices
    'oga': {'resolution': (480, 320), 'analogsticks': 1, 'cpu': 'rk3326', 'capabilities': ['3:2', '480x320', 'lowres']},
    'ogs': {'resolution': (854, 480), 'analogsticks': 2, 'cpu': 'rk3326', 'capabilities': ['427:240', '854x480', 'hires', 'wide']},
    'ogu': {'resolution': (854, 480), 'analogsticks': 2, 'cpu': 's922x',  'capabilities': ['427:240', '854x480', 'power', 'hires', 'wide']},

    # Powkiddy
    'x55':       {'resolution': (1280, 720), 'analogsticks': 2, 'cpu': 'rk3566', 'capabilities': ['16:9', '1280x720', 'power', 'hires', 'wide']},
    'rgb10max3': {'resolution': ( 854, 480), 'analogsticks': 2, 'cpu': 's922x',  'capabilities': ['427:240', '854x480', 'power', 'hires', 'wide']},
    'rgb10max2': {'resolution': ( 854, 480), 'analogsticks': 2, 'cpu': 'rk3326', 'capabilities': ['427:240', '854x480', 'hires', 'wide']},
    'rgb10max':  {'resolution': ( 854, 480), 'analogsticks': 2, 'cpu': 'rk3326', 'capabilities': ['427:240', '854x480', 'hires', 'wide']},
    'rgb10s':    {'resolution': ( 480, 320), 'analogsticks': 1, 'cpu': 'rk3326', 'capabilities': ['3:2', '480x320', 'lowres']},
    'rgb20s':    {'resolution': ( 640, 480), 'analogsticks': 2, 'cpu': 'rk3326', 'capabilities': ['4:3', '640x480']},
    'rk2023':    {'resolution': ( 640, 480), 'analogsticks': 2, 'cpu': 'rk3566', 'capabilities': ['4:3', '640x480', 'power']},
    'rk2020':    {'resolution': ( 480, 320), 'analogsticks': 1, 'cpu': 'rk3326', 'capabilities': ['3:2', '480x320', 'lowres']},

    # Gameforce Chi
    'chi':     {'resolution': (640, 480), 'analogsticks': 2, 'cpu': 'rk3326', 'capabilities': ['4:3', '640x480']},

    # Computer/Testing
    'pc':      {'resolution': (640, 480), 'analogsticks': 2, 'cpu': 'unknown', 'capabilities': ['4:3', '640x480', 'opengl', 'power']},

    # Default
    'default': {'resolution': (640, 480), 'analogsticks': 2, 'cpu': 'unknown', 'capabilities': ['4:3', '640x480']},
    }


CFW_INFO = {
    ## From PortMaster.sh from JELOS, all devices except x55 and rg10max3 have opengl
    ('jelos', 'x55'): {'capabilities': []},
    ('jelos', 'rgb10max3'): {'capabilities': []},
    ('jelos', HW_ANY): {'capabilities': ['opengl']},
    }


def safe_cat(file_name):
    if isinstance(file_name, str):
        file_name = pathlib.Path(file_name)

    elif not isinstance(file_name, pathlib.PurePath):
        raise ValueError(file_name)

    if str(file_name).startswith('~/'):
        file_name = file_name.expanduser()

    if not file_name.is_file():
        return ''

    return file_name.read_text()


def file_exists(file_name):
    return Path(file_name).exists()


def nice_device_to_device(raw_device):
    raw_device = raw_device.split('\0', 1)[0]

    pattern_to_device = (
        ('Hardkernel ODROID-GO-Ultra', 'ogu'),
        ('ODROID-GO Advance*', 'oga'),
        ('ODROID-GO Super*', 'ogs'),

        ('Powkiddy RGB10 MAX 3', 'rgb10max3'),
        ('Powkiddy RK2023',  'rk2023'),
        ('Powkiddy x55',     'x55'),

        ('Anbernic RG351MP*', 'rg351mp'),
        ('Anbernic RG351V*',  'rg351v'),
        ('Anbernic RG351*',   'rg351p'),
        ('Anbernic RG353MP*', 'rg353mp'),
        ('Anbernic RG353V*',  'rg353v'),
        ('Anbernic RG353P*',  'rg353p'),
        ('Anbernic RG552',    'rg552'),
        )

    for pattern, device in pattern_to_device:
        if fnmatch.fnmatch(raw_device, pattern):
            raw_device = device
            break
    else:
        raw_device = raw_device.lower()

    if raw_device not in HW_INFO:
        logger.debug(f"nice_device_to_device -->> {raw_device!r} <<--")
        raw_device = 'default'

    return raw_device.lower()


def new_device_info():
    if HM_TESTING:
        return {
            'name': platform.system(),
            'version': platform.release(),
            'device': 'pc',
            }

    info = {}

    ## Get Device

    # Works on ArkOS
    config_device = safe_cat('~/.config/.DEVICE')
    if config_device != '':
        info.setdefault('device', config_device.strip().lower())

    # Works on ArkOS
    plymouth = safe_cat('/usr/share/plymouth/themes/text.plymouth')
    if plymouth != '':
        for result in re.findall(r'^title=(.*?) \(([^\)]+)\)$', plymouth, re.I | re.M):
            info['name'] = result[0].split(' ', 1)[0].lower()
            info['version'] = result[1]

    # Works on uOS / JELOS / AmberELEC
    sfdbm = safe_cat('/sys/firmware/devicetree/base/model')
    if sfdbm != '':
        device = nice_device_to_device(sfdbm)
        if device != 'default':
            info.setdefault('device', device)

    # Works on AmberELEC / uOS / JELOS
    os_release = safe_cat('/etc/os-release')
    for result in re.findall(r'^([a-z0-9_]+)="([^"]+)"$', os_release, re.I | re.M):
        if result[0] in ('NAME', 'VERSION', 'OS_NAME', 'OS_VERSION', 'HW_DEVICE', 'COREELEC_DEVICE'):
            key = result[0].rsplit('_', 1)[-1].lower()
            value = result[1].strip()
            if key == 'device':
                value = nice_device_to_device(value)

            info.setdefault(key, value)

    if 'device' not in info:
        info['device'] = old_device_info()

    info.setdefault('name', 'unknown')
    info.setdefault('version', '0.0.0')

    return info


def old_device_info():
    # From PortMaster/control.txt
    if file_exists('/dev/input/by-path/platform-ff300000.usb-usb-0:1.2:1.0-event-joystick'):
        if file_exists('/boot/rk3326-rg351v-linux.dtb') or safe_cat("/storage/.config/.OS_ARCH").strip().casefold() == "rg351v":
            # RG351V
            return "rg351v"

        # RG351P/M
        return "rg351p"

    elif file_exists('/dev/input/by-path/platform-odroidgo2-joypad-event-joystick'):
        if "190000004b4800000010000001010000" in safe_cat('/etc/emulationstation/es_input.cfg'):
            return "oga"
        else:
            return "rk2020"

        return "rgb10s"

    elif file_exists('/dev/input/by-path/platform-odroidgo3-joypad-event-joystick'):
        if ("rgb10max" in safe_cat('/etc/emulationstation/es_input.cfg').strip().casefold()):
            return "rgb10max"

        if file_exists('/opt/.retrooz/device'):
            device = safe_cat("/opt/.retrooz/device").strip().casefold()
            if "rgb10max2native" in device:
                return "rgb10max"

            if "rgb10max2top" in device:
                return "rgb10max"

        return "ogs"

    elif file_exists('/dev/input/by-path/platform-gameforce-gamepad-event-joystick'):
        return "chi"

    return 'unknown'


def _merge_info(info, new_info):
    for key, value in new_info.items():
        if key not in info:
            info[key] = value
            continue

        if isinstance(value, list):
            info[key] = list(set(info[key]) | set(value))

        elif isinstance(value, (str, tuple, int)):
            info[key] = value

    return info


def find_device_by_resolution(resolution):
    for device, information in HW_INFO.items():
        if resolution == information['resolution']:
            return device

    return 'default'


__root_info = None
def device_info(override_device=None):
    global __root_info
    if override_device is None and __root_info is not None:
        return __root_info

    # Best guess at what device we are running on, and what it is capable of.
    info = new_device_info()

    if override_device is not None:
        info['device'] = override_device

    _merge_info(info, HW_INFO.get(info['device'], HW_INFO['default']))

    if (info['name'], info['device']) in CFW_INFO:
        _merge_info(info, CFW_INFO[(info['name'], info['device'])])

    elif (info['name'], HW_ANY) in CFW_INFO:
        _merge_info(info, CFW_INFO[(info['name'], HW_ANY)])

    logger.debug(f"DEVICE INFO: {info}")
    __root_info = info
    return info


__all__ = (
    'device_info',
    'find_device_by_resolution',
    'HW_INFO',
    )
