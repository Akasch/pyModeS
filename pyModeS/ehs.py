# Copyright (C) 2016 Junzi Sun (TU Delft)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
A python package for decoding ModeS (DF20, DF21) messages.
"""

import util
from util import crc


def df(msg):
    """Get the downlink format (DF) number

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        int: DF number
    """
    return util.df(msg)


def data(msg):
    """Return the data frame in the message, bytes 9 to 22"""
    return msg[8:22]


def icao(msg):
    """Calculate the ICAO address from an Mode-S message
    with DF4, DF5, DF20, DF21

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        String: ICAO address in 6 bytes hexadecimal string
    """

    if df(msg) not in (4, 5, 20, 21):
        # raise RuntimeError("Message DF must be in (4, 5, 20, 21)")
        return None

    c0 = util.bin2int(crc(msg, encode=True))
    c1 = util.hex2int(msg[-6:])
    icao = '%06X' % (c0 ^ c1)
    return icao


def checkbits(data, sb, msb, lsb):
    """Check if the status bit and field bits are consistency. This Function
    is used for checking BDS code versions.
    """

    # status bit, most significant bit, least significant bit
    status = int(data[sb-1])
    value = util.bin2int(data[msb-1:lsb])

    if not status:
        if value != 0:
            return False

    return True


# ------------------------------------------
# DF 20/21, BDS 2,0
# ------------------------------------------

def isBDS20(msg):
    """Check if a message is likely to be BDS code 2,0

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        bool: True or False
    """

    # status bit 1, 14, and 27
    d = util.hex2bin(data(msg))

    result = True

    if util.bin2int(d[0:4]) != 2 or util.bin2int(d[4:8]) != 0:
        result &= False

    cs = callsign(msg)

    if '#' in cs:
        result &= False

    return result


def callsign(msg):
    """Aircraft callsign

    Args:
        msg (String): 28 bytes hexadecimal message (BDS40) string

    Returns:
        string: callsign, max. 8 chars
    """
    chars = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ#####_###############0123456789######'

    d = util.hex2bin(data(msg))

    cs = ''
    cs += chars[util.bin2int(d[8:14])]
    cs += chars[util.bin2int(d[14:20])]
    cs += chars[util.bin2int(d[20:26])]
    cs += chars[util.bin2int(d[26:32])]
    cs += chars[util.bin2int(d[32:38])]
    cs += chars[util.bin2int(d[38:44])]
    cs += chars[util.bin2int(d[44:50])]
    cs += chars[util.bin2int(d[50:56])]

    return cs


# ------------------------------------------
# DF 20/21, BDS 4,0
# ------------------------------------------

def isBDS40(msg):
    """Check if a message is likely to be BDS code 4,0

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        bool: True or False
    """

    # status bit 1, 14, and 27
    d = util.hex2bin(data(msg))

    result = True

    result = result & checkbits(d, 1, 2, 13) \
        & checkbits(d, 14, 15, 26) & checkbits(d, 27, 28, 39)

    # bits 40-47 and 52-53 shall all be zero
    if util.bin2int(d[39:47]) != 0:
        result &= False

    if util.bin2int(d[51:53]) != 0:
        result &= False

    return result


def alt40mcp(msg):
    """Selected altitude, MCP/FCU

    Args:
        msg (String): 28 bytes hexadecimal message (BDS40) string

    Returns:
        int: altitude in feet
    """
    d = util.hex2bin(data(msg))
    alt = util.bin2int(d[1:13]) * 16    # ft
    return alt


def alt40fms(msg):
    """Selected altitude, FMS

    Args:
        msg (String): 28 bytes hexadecimal message (BDS40) string

    Returns:
        int: altitude in feet
    """
    d = util.hex2bin(data(msg))
    alt = util.bin2int(d[14:26]) * 16    # ft
    return alt


def p40baro(msg):
    """Barometric pressure setting

    Args:
        msg (String): 28 bytes hexadecimal message (BDS40) string

    Returns:
        float: pressure in millibar
    """
    d = util.hex2bin(data(msg))
    p = util.bin2int(d[27:39]) * 0.1 + 800    # millibar
    return p


# ------------------------------------------
# DF 20/21, BDS 4,4
# ------------------------------------------

def isBDS44(msg, rev=False):
    """Check if a message is likely to be BDS code 4,4
    Meteorological routine air report

    Args:
        msg (String): 28 bytes hexadecimal message string
        rev (bool): using revised version

    Returns:
        bool: True or False
    """

    d = util.hex2bin(data(msg))

    result = True

    if not rev:
        # status bit 5, 35, 47, 50
        result = result & checkbits(d, 5, 6, 23) \
            & checkbits(d, 35, 36, 46) & checkbits(d, 47, 48, 49) \
            & checkbits(d, 50, 51, 56)


    else:
        # status bit 5, 15, 24, 36, 49
        result = result & checkbits(d, 5, 6, 14) \
            & checkbits(d, 15, 16, 23) & checkbits(d, 24, 25, 35) \
            & checkbits(d, 36, 37, 47) & checkbits(d, 49, 50, 56)

    vw = wind44(msg, rev=rev)
    if vw and vw[0] > 250:
        result &= False

    # if temp44(msg):
    #     if temp44(msg) > 60 or temp44(msg) < -80:
    #         result &= False

    return result


def wind44(msg, rev=False):
    """reported wind speed and direction

    Args:
        msg (String): 28 bytes hexadecimal message (BDS44) string
        rev (bool): using revised version

    Returns:
        (int, float): speed (kt), direction (degree)
    """
    d = util.hex2bin(data(msg))

    if not rev:
        status = int(d[4])
        if not status:
            return None

        speed = util.bin2int(d[5:14])   # knots
        direction = util.bin2int(d[14:23]) * 180.0 / 256.0  # degree

    else:
        spd_status = int(d[4])
        dir_status = int(d[14])

        if (not spd_status) or (not dir_status):
            return None

        speed = util.bin2int(d[5:14])   # knots
        direction = util.bin2int(d[15:23]) * 180.0 / 128.0  # degree

    return round(speed, 0), round(direction, 1)


def temp44(msg, rev=False):
    """reported air temperature

    Args:
        msg (String): 28 bytes hexadecimal message (BDS44) string
        rev (bool): using revised version

    Returns:
        float: tmeperature in Celsius degree
    """
    d = util.hex2bin(data(msg))

    if not rev:
        sign = int(d[23])
        temp = util.bin2int(d[24:34]) * 0.125   # celsius
        temp = round(temp, 1)

    else:
        status = int(d[23])
        if not status:
            return None

        sign = int(d[24])
        temp = util.bin2int(d[25:35]) * 0.125   # celsius
        temp = round(temp, 1)

    return -1*temp if sign else temp


def p44(msg, rev=False):
    """reported average static pressure

    Args:
        msg (String): 28 bytes hexadecimal message (BDS44) string
        rev (bool): using revised version

    Returns:
        int: static pressure in hPa
    """
    d = util.hex2bin(data(msg))

    if not rev:
        status = int(d[34])
        if not status:
            return None

        p = util.bin2int(d[35:46])    # hPa

    else:
        status = int(d[35])
        if not status:
            return None

        p = util.bin2int(d[36:47])    # hPa

    return p


def hum44(msg, rev=False):
    """reported humidity

    Args:
        msg (String): 28 bytes hexadecimal message (BDS44) string
        rev (bool): using revised version

    Returns:
        float: percentage of humidity, [0 - 100] %
    """
    d = util.hex2bin(data(msg))

    if not rev:
        status = int(d[49])
        if not status:
            return None

        hm = util.bin2int(d[50:56]) * 100.0 / 64    # %

    else:
        status = int(d[48])
        if not status:
            return None

        hm = util.bin2int(d[49:56])    # %

    return round(hm, 1)


# ------------------------------------------
# DF 20/21, BDS 5,0
# Track and turn report
# ------------------------------------------

def isBDS50(msg):
    """Check if a message is likely to be BDS code 5,0
    (Track and turn report)

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        bool: True or False
    """

    # status bit 1, 12, 24, 35, 46
    d = util.hex2bin(data(msg))

    result = True

    result = result & checkbits(d, 1, 3, 11) & checkbits(d, 12, 13, 23) \
        & checkbits(d, 24, 25, 34) & checkbits(d, 35, 36, 45) \
        & checkbits(d, 46, 47, 56)

    if d[2:11] == "000000000":
        result &= True
    else:
        if abs(roll50(msg)) > 30:
            result &= False

    if gs50(msg) > 600:
        result &= False

    if tas50(msg) > 500:
        result &= False

    if abs(tas50(msg) - gs50(msg)) > 100:
        result &= False

    return result


def roll50(msg):
    """Roll angle, BDS 5,0 message

    Args:
        msg (String): 28 bytes hexadecimal message (BDS50) string

    Returns:
        float: angle in degrees,
               negative->left wing down, positive->right wing down
    """
    d = util.hex2bin(data(msg))
    sign = int(d[1])    # 1 -> left wing down
    value = util.bin2int(d[2:11]) * 45.0 / 256.0    # degree
    angle = -1 * value if sign else value
    return round(angle, 1)


def trk50(msg):
    """True track angle, BDS 5,0 message

    Args:
        msg (String): 28 bytes hexadecimal message (BDS50) string

    Returns:
        float: angle in degrees to true north (from 0 to 360)
    """
    d = util.hex2bin(data(msg))
    sign = int(d[12])   # 1 -> west
    value = util.bin2int(d[13:23]) * 90.0 / 512.0    # degree
    angle = 360 - value if sign else value
    return round(angle, 1)


def gs50(msg):
    """Ground speed, BDS 5,0 message

    Args:
        msg (String): 28 bytes hexadecimal message (BDS50) string

    Returns:
        int: ground speed in knots
    """
    d = util.hex2bin(data(msg))
    spd = util.bin2int(d[24:34]) * 2    # kts
    return spd


def rtrk50(msg):
    """Track angle rate, BDS 5,0 message

    Args:
        msg (String): 28 bytes hexadecimal message (BDS50) string

    Returns:
        float: angle rate in degrees/second
    """
    d = util.hex2bin(data(msg))
    sign = int(d[35])    # 1 -> minus
    value = util.bin2int(d[36:45]) * 8.0 / 256.0    # degree / sec
    angle = -1 * value if sign else value
    return round(angle, 3)


def tas50(msg):
    """Aircraft true airspeed, BDS 5,0 message

    Args:
        msg (String): 28 bytes hexadecimal message (BDS50) string

    Returns:
        int: true airspeed in knots
    """
    d = util.hex2bin(data(msg))
    tas = util.bin2int(d[46:56]) * 2   # kts
    return tas


# ------------------------------------------
# DF 20/21, BDS 5,3
# Air-referenced state vector
# ------------------------------------------

def isBDS53(msg):
    """Check if a message is likely to be BDS code 5,3
    (Air-referenced state vector)

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        bool: True or False
    """

    # status bit 1, 13, 24, 34, 47
    d = util.hex2bin(data(msg))

    result = True

    result = result & checkbits(d, 1, 3, 12) & checkbits(d, 13, 14, 23) \
        & checkbits(d, 24, 25, 33) & checkbits(d, 34, 35, 46) \
        & checkbits(d, 47, 49, 56)

    if ias53(msg) > 500:
        result &= False

    if mach53(msg) > 1:
        result &= False

    if tas53(msg) > 500:
        result &= False

    if abs(vr53(msg)) > 8000:
        result &= False

    return result


def hdg53(msg):
    """Magnetic heading, BDS 5,3 message

    Args:
        msg (String): 28 bytes hexadecimal message (BDS53) string

    Returns:
        float: angle in degrees to true north (from 0 to 360)
    """
    d = util.hex2bin(data(msg))
    sign = int(d[1])                               # 1 -> west
    value = util.bin2int(d[2:12]) * 90.0 / 512.0   # degree
    angle = 360 - value if sign else value
    return round(angle, 1)


def ias53(msg):
    """Indicated airspeed, DBS 5,3 message

    Args:
        msg (String): 28 bytes hexadecimal message

    Returns:
        int: indicated arispeed in knots
    """
    d = util.hex2bin(data(msg))
    ias = util.bin2int(d[13:23])    # knots
    return ias


def mach53(msg):
    """MACH number, DBS 5,3 message

    Args:
        msg (String): 28 bytes hexadecimal message

    Returns:
        float: MACH number
    """
    d = util.hex2bin(data(msg))
    mach = util.bin2int(d[24:33]) * 0.008
    return round(mach, 3)


def tas53(msg):
    """Aircraft true airspeed, BDS 5,3 message

    Args:
        msg (String): 28 bytes hexadecimal message

    Returns:
        float: true airspeed in knots
    """
    d = util.hex2bin(data(msg))
    tas = util.bin2int(d[34:46]) * 0.5   # kts
    return round(tas, 1)

def vr53(msg):
    """Vertical rate

    Args:
        msg (String): 28 bytes hexadecimal message (BDS60) string

    Returns:
        int: vertical rate in feet/minutes
    """
    d = util.hex2bin(data(msg))
    sign = d[47]                            # 1 -> minus
    value = util.bin2int(d[48:56]) * 64     # feet/min
    roc = -1*value if sign else value
    return roc


# ------------------------------------------
# DF 20/21, BDS 6,0
# ------------------------------------------

def isBDS60(msg):
    """Check if a message is likely to be BDS code 6,0

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        bool: True or False
    """
    # status bit 1, 13, 24, 35, 46
    d = util.hex2bin(data(msg))

    result = True

    result = result & checkbits(d, 1, 2, 12) & checkbits(d, 13, 14, 23) \
        & checkbits(d, 24, 25, 34) & checkbits(d, 35, 36, 45) \
        & checkbits(d, 46, 47, 56)

    if not (1 < ias60(msg) < 500):
        result &= False

    if not (0.0 < mach60(msg) < 1.0):
        result &= False

    if abs(vr60baro(msg)) > 5000:
        result &= False

    if abs(vr60ins(msg)) > 5000:
        result &= False

    return result


def hdg60(msg):
    """Megnetic heading of aircraft

    Args:
        msg (String): 28 bytes hexadecimal message (BDS60) string

    Returns:
        float: heading in degrees to megnetic north (from 0 to 360)
    """
    d = util.hex2bin(data(msg))
    sign = int(d[1])    # 1 -> west
    value = util.bin2int(d[2:12]) * 90 / 512.0  # degree
    hdg = 360 - value if sign else value
    return round(hdg, 1)


def ias60(msg):
    """Indicated airspeed

    Args:
        msg (String): 28 bytes hexadecimal message (BDS60) string

    Returns:
        int: indicated airspeed in knots
    """
    d = util.hex2bin(data(msg))
    ias = util.bin2int(d[13:23])    # kts
    return ias


def mach60(msg):
    """Aircraft MACH number

    Args:
        msg (String): 28 bytes hexadecimal message (BDS60) string

    Returns:
        float: MACH number
    """
    d = util.hex2bin(data(msg))
    mach = util.bin2int(d[24:34]) * 2.048 / 512.0
    return round(mach, 3)


def vr60baro(msg):
    """Vertical rate from barometric measurement

    Args:
        msg (String): 28 bytes hexadecimal message (BDS60) string

    Returns:
        int: vertical rate in feet/minutes
    """
    d = util.hex2bin(data(msg))
    sign = d[35]    # 1 -> minus
    value = util.bin2int(d[36:45]) * 32   # feet/min
    roc = -1*value if sign else value
    return roc


def vr60ins(msg):
    """Vertical rate messured by onbard equiments (IRS, AHRS)

    Args:
        msg (String): 28 bytes hexadecimal message (BDS60) string

    Returns:
        int: vertical rate in feet/minutes
    """
    d = util.hex2bin(data(msg))
    sign = d[46]    # 1 -> minus
    value = util.bin2int(d[47:56]) * 32   # feet/min
    roc = -1*value if sign else value
    return roc


def BDS(msg):
    """Estimate the most likely BDS code of an message

    Args:
        msg (String): 28 bytes hexadecimal message string

    Returns:
        String or None: Version: "BDS20", "BDS40", "BDS50", or "BDS60". Or None, if nothing matched
    """
    is20 = isBDS20(msg)
    is40 = isBDS40(msg)
    is44 = isBDS44(msg)
    is44rev = isBDS44(msg, rev=True)
    is50 = isBDS50(msg)
    is53 = isBDS53(msg)
    is60 = isBDS60(msg)

    BDS = ["BDS20", "BDS40", "BDS44", "BDS44REV", "BDS50", "BDS53", "BDS60"]
    isBDS = [is20, is40, is44, is44rev, is50, is53, is60]

    if sum(isBDS) == 0:
        return None
    if sum(isBDS) == 1:
        return BDS[isBDS.index(True)]
    else:
        return [bds for (bds, i) in zip(BDS, isBDS) if i]
