from ctypes import (
    POINTER,
    Structure,
    Union,
    c_bool,
    c_float,
    c_uint,
    c_uint8,
    c_uint16,
    c_uint32,
    pointer,
)
from enum import IntEnum
from typing import Final

from interfaces import MAX_CMD_MSG_SIZE, RS_DECODED_DATA_SIZE
from interfaces.obc_gs_interface import interface

# ######################################################################
# ||                                                                  ||
# ||          Ctype Declerations for Command Pack and Unpack          ||
# ||                                                                  ||
# ######################################################################


class RtcSyncCmdData(Structure):
    """
    The python equivalent class for the rtc_sync_cmd_data_t structure in the C implementation
    """

    _fields_ = [("unixTime", c_uint32)]


class DownlinkLogsNextPassCmdData(Structure):
    """
    The python equivalent class for the downlink_logs_next_pass_cmd_data_t structure in the C implementation
    """

    _fields_ = [("logLevel", c_uint8)]


class DownloadDataCmdData(Structure):
    """
    The python equivalent class for the download_data_cmd_data_t structure in the C implementation
    """

    _fields_ = [("programmingSession", c_uint), ("length", c_uint16), ("address", c_uint32), ("data", POINTER(c_uint8))]


class SetProgrammingSessionCmdData(Structure):
    """
    The python equivalent class for the set_programming_session_cmd_data_t structure in the C implementation
    """

    _fields_ = [("programmingSession", c_uint)]


# NOTE: When adding commands only add their data to the following union type as shown with RtcSyncCmdData and
# DownlinkLogsNextPassCmdData
class _U(Union):
    """
    Union class needed to create the CmdMsgType Class
    """

    _fields_ = [
        ("rtcSync", RtcSyncCmdData),
        ("downlinkLogsNextPass", DownlinkLogsNextPassCmdData),
        ("downloadData", DownloadDataCmdData),
        ("setProgrammingSession", SetProgrammingSessionCmdData),
    ]


class CmdMsg(Structure):
    """
    The python equivalent class for the cmd_msg_t structure in the C implementation
    NOTE: This class has a union so initialize accordingly
    """

    _anonymous_ = ("u",)
    _fields_ = [("u", _U), ("timestamp", c_uint32), ("isTimeTagged", c_bool), ("id", c_uint)]

    def __init__(self, unixtime_of_execution: int | None = None) -> None:
        """
        Constructor for the CmdMsg Class

        :param unixtime_of_execution: Can be an integer or None. If None the function will set isTimeTagged to false and
                                      make the timestamp 0. If an integer is passed in then the function sets
                                      isTimeTagged to True and timestamp to the integer passed in.
        """
        if unixtime_of_execution is None:
            # NOTE: By default these will be 0-initialized but, just for clarity the values are specified
            super().__init__(_U(), c_uint32(0), c_bool(False), c_uint())
        else:
            super().__init__(_U(), c_uint32(unixtime_of_execution), c_bool(True), c_uint())

class _TelemU(Union):
    """
    Union class needed to create the TelemetryData Class
    """

    _fields_ = [
        ("cc1120Temp", c_float),
        ("commsCustomTransceiverTemp", c_float),
        ("obcTemp", c_float),
        ("adcsMagBoardTemp", c_float),
        ("adcsSensorBoardTemp", c_float),
        ("epsBoardTemp", c_float),
        ("solarPanel1Temp", c_float),
        ("solarPanel2Temp", c_float),
        ("solarPanel3Temp", c_float),
        ("solarPanel4Temp", c_float),

        ("epsComms5vCurrent", c_float),
        ("epsComms3v3Current", c_float),
        ("epsMagnetorquer8vCurrent", c_float),
        ("epsAdcs5vCurrent", c_float),
        ("epsAdcs3v3Current", c_float),
        ("epsObc3v3Current", c_float),

        ("epsComms5vVoltage", c_float),
        ("epsComms3v3Voltage", c_float),
        ("epsMagnetorquer8vVoltage", c_float),
        ("epsAdcs5vVoltage", c_float),
        ("epsAdcs3v3Voltage", c_float),
        ("epsObc3v3Voltage", c_float),
        

        ("obcState", c_uint8),
        ("epsState", c_uint8),

        ("numCspPacketsRcvd", c_uint32),
    ]

class TelemetryData(Structure):
    """
    The python equivalent class for the telemetry_data_t structure in the C implementation
    NOTE: This class has a union so initialize accordingly
    """

    _anonymous_ = ("u",)
    _fields_ = [("u", _TelemU), ("telemetry_data_id_t", c_uint), ("timestamp", c_uint32)]

interface.unpackCmdMsg.argtypes = (POINTER(c_uint8 * MAX_CMD_MSG_SIZE), POINTER(c_uint32), POINTER(CmdMsg))
interface.unpackCmdMsg.restype = c_uint

interface.packCmdMsg.argtypes = (
    POINTER(c_uint8 * MAX_CMD_MSG_SIZE),
    POINTER(c_uint32),
    POINTER(CmdMsg),
    POINTER(c_uint8),
)
interface.packCmdMsg.restype = c_uint


# ######################################################################
# ||                                                                  ||
# ||     Ctype Declerations for Command Response Pack and Unpack      ||
# ||                                                                  ||
# ######################################################################


# NOTE: No modifications to this class are necessary when adding new responses
class CmdResponseHeader(Structure):
    """
    The python equivalent class for the cmd_unpacked_response_t structure in the C implementation
    """

    _fields_ = [("cmdId", c_uint), ("errCode", c_uint), ("dataLen", c_uint8)]


interface.packCmdResponse.argtypes = (POINTER(CmdResponseHeader), POINTER(c_uint8 * RS_DECODED_DATA_SIZE))
interface.packCmdResponse.restype = c_uint

interface.unpackCmdResponse.argtypes = (
    POINTER(c_uint8 * RS_DECODED_DATA_SIZE),
    POINTER(CmdResponseHeader),
    POINTER(c_uint8 * RS_DECODED_DATA_SIZE),
)
interface.unpackCmdResponse.restype = c_uint


interface.unpackTelemetry.argtypes = (POINTER(c_uint8 * MAX_CMD_MSG_SIZE), POINTER(c_uint32), POINTER(TelemetryData))
interface.unpackTelemetry.restype = c_uint
# ######################################################################
# ||                                                                  ||
# ||                        ENUM Declerations                         ||
# ||                                                                  ||
# ######################################################################
# NOTE: Update these files accordingly when the C Enums are updated


# Path to File: interfaces/obc_gs_interface/commands/obc_gs_command_id.h
class CmdCallbackId(IntEnum):
    """
    Enums corresponding to the C implementation of cmd_callback_id_t
    """

    CMD_END_OF_FRAME = 0
    CMD_EXEC_OBC_RESET = 1
    CMD_RTC_SYNC = 2
    CMD_DOWNLINK_LOGS_NEXT_PASS = 3
    CMD_MICRO_SD_FORMAT = 4
    CMD_PING = 5
    CMD_DOWNLINK_TELEM = 6
    CMD_UPLINK_DISC = 7
    CMD_SET_PROGRAMMING_SESSION = 8
    CMD_ERASE_APP = 9
    CMD_DOWNLOAD_DATA = 10
    CMD_VERIFY_CRC = 11
    CMD_I2C_PROBE = 12
    NUM_CMD_CALLBACKS = 13


# Path to File: interfaces/obc_gs_interface/commands/obc_gs_commands_response.h
class CmdResponseErrorCode(IntEnum):
    """
    Enums corresponding to the C implementation of the cmd_response_error_code_t
    """

    CMD_RESPONSE_SUCCESS = 0x01
    CMD_RESPONSE_ERROR = 0x7F


class ProgrammingSession(IntEnum):
    """
    Enums corresponding to the C implementation of the cmd_response_error_code_t
    """

    APPLICATION = 0


class TelemId(IntEnum):
    """
    Enums corresponding to the C implementation of telemetry_data_id_t
    """

    TELEM_NONE = 0

    # Temperature values
    TELEM_CC1120_TEMP = 1
    TELEM_COMMS_CUSTOM_TRANSCEIVER_TEMP = 2
    TELEM_OBC_TEMP = 3
    TELEM_ADCS_MAG_BOARD_TEMP = 4
    TELEM_ADCS_SENSOR_BOARD_TEMP = 5
    TELEM_EPS_BOARD_TEMP = 6
    TELEM_SOLAR_PANEL_1_TEMP = 7
    TELEM_SOLAR_PANEL_2_TEMP = 8
    TELEM_SOLAR_PANEL_3_TEMP = 9
    TELEM_SOLAR_PANEL_4_TEMP = 10

    # Current values
    TELEM_EPS_COMMS_5V_CURRENT = 11
    TELEM_EPS_COMMS_3V3_CURRENT = 12
    TELEM_EPS_MAGNETORQUER_8V_CURRENT = 13
    TELEM_EPS_ADCS_5V_CURRENT = 14
    TELEM_EPS_ADCS_3V3_CURRENT = 15
    TELEM_EPS_OBC_3V3_CURRENT = 16

    # Voltage values
    TELEM_EPS_COMMS_5V_VOLTAGE = 17
    TELEM_EPS_COMMS_3V3_VOLTAGE = 18
    TELEM_EPS_MAGNETORQUER_8V_VOLTAGE = 19
    TELEM_EPS_ADCS_5V_VOLTAGE = 20
    TELEM_EPS_ADCS_3V3_VOLTAGE = 21
    TELEM_EPS_OBC_3V3_VOLTAGE = 22

    TELEM_OBC_STATE = 23
    TELEM_EPS_STATE = 24

    TELEM_NUM_CSP_PACKETS_RCVD = 25
    TELEM_PONG = 26


# ######################################################################
# ||                                                                  ||
# ||             Command Pack and Unpack Implementations              ||
# ||                                                                  ||
# ######################################################################


_PACK_OFFSET_INITIAL: Final[int] = 0
_UNPACK_OFFSET_INITIAL: Final[int] = 0
_NUM_PACKED_INITIAL: Final[int] = 0


def pack_command(cmd_msg: CmdMsg) -> bytes:
    """
    This takes in a command message to be packed (see the C implementation for more on how that's exactly done)
    NOTE: When the class is initialized, it will use internal variables to keep a running count of the packOffset
    and numPacked parameters from the C implementation.

    :param cmd_msg: A c-style structure that hold the command message
    :return: Bytes of the packed message
    """
    buffer = (c_uint8 * MAX_CMD_MSG_SIZE)(*([0] * MAX_CMD_MSG_SIZE))
    offset = c_uint32(_PACK_OFFSET_INITIAL)
    res = interface.packCmdMsg(
        pointer(buffer),
        pointer(offset),
        pointer(cmd_msg),
        pointer(c_uint8(_NUM_PACKED_INITIAL)),
    )

    if res != 0:
        raise ValueError("Could not pack command. OBC Error Code: " + str(res))

    buffer_bytes = bytes(buffer)

    return buffer_bytes[: offset.value]


def unpack_command(cmd_msg_packed: bytes) -> tuple[list[CmdMsg], bytes]:
    """
    This takes in a data bytes to be unpacked into a command message (see the C implementation for more on how
    that's exactly done)
    NOTE: When the class is initialized, it will use internal variables to keep a running count of the unpackOffset
    parameter from the C implementation.

    :param cmd_msg_packed: Bytes of an already encoded message
    :return: An unpacked command message in the form of a structure
    """
    if len(cmd_msg_packed) > RS_DECODED_DATA_SIZE:
        raise ValueError("The encoded command data to unpack is too long")

    bytes_unpacked = c_uint32(0)
    cmd_msg_list = []
    total_bytes_unpacked = 0

    while bytes_unpacked.value < RS_DECODED_DATA_SIZE:
        if cmd_msg_packed[total_bytes_unpacked] == CmdCallbackId.CMD_END_OF_FRAME.value:
            break

        cmd_msg = CmdMsg()
        buffer_elements = list(cmd_msg_packed[total_bytes_unpacked : total_bytes_unpacked + 16])
        buff = (c_uint8 * MAX_CMD_MSG_SIZE)(*buffer_elements)
        res = interface.unpackCmdMsg(pointer(buff), pointer(bytes_unpacked), pointer(cmd_msg))
        total_bytes_unpacked += bytes_unpacked.value
        bytes_unpacked = c_uint32(0)
        if res != 0:
            raise ValueError("Could not unpack command. OBC Error Code: " + str(res))
        cmd_msg_list.append(cmd_msg)

    bytes_not_unpacked = cmd_msg_packed[total_bytes_unpacked:]

    return (cmd_msg_list, bytes_not_unpacked)


# ######################################################################
# ||                                                                  ||
# ||         Command Response Pack and Unpack Implementations         ||
# ||                                                                  ||
# ######################################################################


def pack_command_response(cmd_msg_response: CmdResponseHeader) -> bytes:
    """
    This takes a command message reponse to pack it (see the C implementation for more on how that's exactly done)

    :param cmd_msg_response: A c-style structure that hold the unpacked command message response
    :return: Bytes of the packed commmand response
    """
    buffer = (c_uint8 * RS_DECODED_DATA_SIZE)(*([0] * RS_DECODED_DATA_SIZE))
    res = interface.packCommandResponse(pointer(cmd_msg_response), pointer(buffer))

    if res != 0:
        raise ValueError("Could not pack command response. OBC Error Code: " + str(res))

    return bytes(buffer).rstrip(b"\x00")


def unpack_command_response(cmd_msg_packed: bytes) -> tuple[CmdResponseHeader, bytes]:
    """
    This takes in a bytes of data to be unpacked into a command response (see the C implementation for more on how
    that's exactly done)

    :param cmd_msg_packed: Bytes of an already encoded message
    :return: An unpacked command message in the form of a structure
    """
    if len(cmd_msg_packed) > RS_DECODED_DATA_SIZE:
        raise ValueError("The encoded command reponse data to unpack is too long")

    buffer_elements = list(cmd_msg_packed)
    buff = (c_uint8 * RS_DECODED_DATA_SIZE)(*buffer_elements)
    data_buffer = (c_uint8 * RS_DECODED_DATA_SIZE)()
    cmd_msg_response = CmdResponseHeader()

    res = interface.unpackCmdResponse(pointer(buff), pointer(cmd_msg_response), pointer(data_buffer))
    data_bytes = bytes(data_buffer)

    if res != 0:
        raise ValueError("Could not unpack command response. OBC Error Code: " + str(res))

    return cmd_msg_response, data_bytes

def unpack_telem(telem_packed: bytes) -> tuple[list[TelemetryData], bytes]:
    """
    This takes in bytes of date to be unpacked into a list of telemtry data (see the C implementation for more on 
    how that's exactly done)

    :param telem_packed: Bytes of an already packed telemtry data packet
    :return: A list of telem points
    """
    if len(telem_packed) > RS_DECODED_DATA_SIZE:
        raise ValueError("The encoded telem data to unpack is too long")

    bytes_unpacked = c_uint32(0)
    telem_data_list = []
    total_bytes_unpacked = 0

    while bytes_unpacked.value < RS_DECODED_DATA_SIZE:
        if telem_packed[total_bytes_unpacked] == TelemId.TELEM_NONE.value:
            break

        telemetry_data = TelemetryData()
        # TODO: see if this causes crashs when total_bytes_unpacked + 16 > RS_DECODED_DATA_SIZE
        buffer_elements = list(telem_packed[total_bytes_unpacked : total_bytes_unpacked + MAX_CMD_MSG_SIZE])
        buff = (c_uint8 * MAX_CMD_MSG_SIZE)(*buffer_elements)
        res = interface.unpackCmdMsg(pointer(buff), pointer(bytes_unpacked), pointer(telemetry_data))
        total_bytes_unpacked += bytes_unpacked.value
        bytes_unpacked = c_uint32(0)
        if res != 0:
            raise ValueError("Could not unpack telem. OBC Error Code: " + str(res))
        telem_data_list.append(telemetry_data)

    bytes_not_unpacked = telem_packed[total_bytes_unpacked:]

    return (telem_data_list, bytes_not_unpacked)
