from collections import defaultdict
from collections.abc import Callable

from interfaces.obc_gs_interface.commands.python import CmdCallbackId, unpack_command_response
from interfaces.obc_gs_interface.commands.python.command_response_classes import (
    CmdCC1120RegisterReadRes,
    CmdI2CProbeRes,
    CmdRes,
    CmdRtcSyncRes,
    CmdVerifyCrcRes,
)


# Command specific parsing
def parse_cmd_with_no_data(cmd_response: CmdRes, data: bytes) -> CmdRes:
    """
    A function to parse the raw data from the response of CMD_EXEC_OBC_RESET

    :param cmd_response: Basic command response
    :param data: The raw bytes containing the data that needs to be parsed
    :return: CmdRes (i.e. A command response with no data for CMD_EXEC_OBC_RESET)
    """
    return cmd_response


def parse_cmd_rtc_sync(cmd_response: CmdRes, data: bytes) -> CmdRtcSyncRes:
    """
    A function to parse the raw data from the response of CMD_RTC_SYNC

    :param cmd_response: Basic command response
    :param data: The raw bytes containing the data that needs to be parsed
    :return: CmdRes (i.e. A command response with no data for CMD_RTC_SYNC)
    """
    # TODO: Implement this callback properly
    if cmd_response.cmd_id != CmdCallbackId.CMD_RTC_SYNC:
        raise ValueError("Wrong command id for parsing the rtc sync command")

    board_unixtime = int.from_bytes(data[:4], "little")

    return CmdRtcSyncRes(cmd_response.cmd_id, cmd_response.error_code, cmd_response.response_length, board_unixtime)


def parse_cmd_verify_crc(cmd_response: CmdRes, data: bytes) -> CmdVerifyCrcRes:
    """
    A function to parse the raw data from the response of CMD_VERIFY_CRC

    :param cmd_response: Basic command response
    :param data: The raw bytes containing the data that needs to be parsed
    :return: CmdVerifyCrcRes (i.e. The command response for CMD_VERIFY_CRC)
    """
    if cmd_response.cmd_id != CmdCallbackId.CMD_VERIFY_CRC:
        raise ValueError("Wrong command id for parsing the verify crc command")

    crc = int.from_bytes(data[:4], "little")
    return CmdVerifyCrcRes(cmd_response.cmd_id, cmd_response.error_code, cmd_response.response_length, crc)


def parse_cmd_i2c_probe(cmd_response: CmdRes, data: bytes) -> CmdI2CProbeRes:
    """
    A function to parse the raw data from the response of CMD_I2C_PROBE

    :param cmd_response: Basic command response
    :param data: The raw bytes containing the data that needs to be parsed
    :return: CmdVerifyCrcRes (i.e. The command response for CMD_I2C_PROBE)
    """
    if cmd_response.cmd_id != CmdCallbackId.CMD_I2C_PROBE:
        raise ValueError("Wrong command id for parsing the i2c probe command")

    valid_addresses: list[int] = []

    for i in range(cmd_response.response_length):
        valid_addresses.append(int.from_bytes(data[i : i + 1], "little"))

    return CmdI2CProbeRes(cmd_response.cmd_id, cmd_response.error_code, cmd_response.response_length, valid_addresses)

def parse_cc1120_register_read(cmd_response: CmdRes, data:bytes) -> CmdCC1120RegisterReadRes:
    """

    A function to parse the raw data from the response of CMD_CC1120_REGISTER_READ
    :param cmd_response: Basic command response
    :param: data: The raw bytes containing the data that needs to be parsed
    :return: CmdCC1120RegisterRead (i.e. A command response for CMD_CC1120_REGISTER_READ)
    """

    STANDARD_CC1120_REG_NAMES: dict[int, str] = {
        0x00: "IOCFG3",
        0x01: "IOCFG2",
        0x02: "IOCFG1",
        0x03: "IOCFG0",
        0x04: "SYNC3",
        0x05: "SYNC2",
        0x06: "SYNC1",
        0x07: "SYNC0",
        0x08: "SYNC_CFG1",
        0x09: "SYNC_CFG0",
        0x0A: "DEVIATION_M",
        0x0B: "MODCFG_DEV_E",
        0x0C: "DCFILT_CFG",
        0x0D: "PREAMBLE_CFG1",
        0x0E: "PREAMBLE_CFG0",
        0x0F: "FREQ_IF_CFG",
        0x10: "IQIC",
        0x11: "CHAN_BW",
        0x12: "MDMCFG1",
        0x13: "MDMCFG0",
        0x14: "SYMBOL_RATE2",
        0x15: "SYMBOL_RATE1",
        0x16: "SYMBOL_RATE0",
        0x17: "AGC_REF",
        0x18: "AGC_CS_THR",
        0x19: "AGC_GAIN_ADJUST",
        0x1A: "AGC_CFG3",
        0x1B: "AGC_CFG2",
        0x1C: "AGC_CFG1",
        0x1D: "AGC_CFG0",
        0x1E: "FIFO_CFG",
        0x1F: "DEV_ADDR",
        0x20: "SETTLING_CFG",
        0x21: "FS_CFG",
        0x22: "WOR_CFG1",
        0x23: "WOR_CFG0",
        0x24: "WOR_EVENT0_MSB",
        0x25: "WOR_EVENT0_LSB",
        0x26: "PKT_CFG2",
        0x27: "PKT_CFG1",
        0x28: "PKT_CFG0",
        0x29: "RFEND_CFG1",
        0x2A: "RFEND_CFG0",
        0x2B: "PA_CFG2",
        0x2C: "PA_CFG1",
        0x2D: "PA_CFG0",
        0x2E: "PKT_LEN",
    }

    EXTENDED_CC1120_REG_NAMES: dict[int, str] = {
        0x00: "IF_MIX_CFG",
        0x01: "FREQOFF_CFG",
        0x02: "TOC_CFG",
        0x03: "MARC_SPARE",
        0x04: "ECG_CFG",
        0x05: "CFM_DATA_CFG",
        0x06: "EXT_CTRL",
        0x07: "RCCAL_FINE",
        0x08: "RCCAL_COARSE",
        0x09: "RCCAL_OFFSET",
        0x0A: "FREQOFF1",
        0x0B: "FREQOFF0",
        0x0C: "FREQ2",
        0x0D: "FREQ1",
        0x0E: "FREQ0",
        0x0F: "IF_ADC2",
        0x10: "IF_ADC1",
        0x11: "IF_ADC0",
        0x12: "FS_DIG1",
        0x13: "FS_DIG0",
        0x14: "FS_CAL3",
        0x15: "FS_CAL2",
        0x16: "FS_CAL1",
        0x17: "FS_CAL0",
        0x18: "FS_CHP",
        0x19: "FS_DIVTWO",
        0x1A: "FS_DSM1",
        0x1B: "FS_DSM0",
        0x1C: "FS_DVC1",
        0x1D: "FS_DVC0",
        0x1E: "FS_LBI",
        0x1F: "FS_PFD",
        0x20: "FS_PRE",
        0x21: "FS_REG_DIV_CML",
        0x22: "FS_SPARE",
        0x23: "FS_VCO4",
        0x24: "FS_VCO3",
        0x25: "FS_VCO2",
        0x26: "FS_VCO1",
        0x27: "FS_VCO0",
        0x28: "GBIAS6",
        0x29: "GBIAS5",
        0x2A: "GBIAS4",
        0x2B: "GBIAS3",
        0x2C: "GBIAS2",
        0x2D: "GBIAS1",
        0x2E: "GBIAS0",
        0x2F: "IFAMP",
        0x30: "LNA",
        0x31: "RXMIX",
        0x32: "XOSC5",
        0x33: "XOSC4",
        0x34: "XOSC3",
        0x35: "XOSC2",
        0x36: "XOSC1",
        0x37: "XOSC0",
        0x38: "ANALOG_SPARE",
        0x39: "PA_CFG3",
    }

    if cmd_response.cmd_id != CmdCallbackId.CMD_CC1120_REGISTER_READ:
        raise ValueError("Wrong command id for parsing the CC1120 register read command")

    standard_registers = {}
    extended_registers = {}
    
    offset = 0

    stdCount = data[offset]
    offset += 1

    for addr in range(stdCount):
        value = data[offset]
        offset += 1

        name = STANDARD_CC1120_REG_NAMES.get(addr)
        standard_registers[name] = value

    extendedCount = data[offset]
    offset += 1

    for addr in range(extendedCount):
        value = data[offset]
        offset += 1
        
        name = EXTENDED_CC1120_REG_NAMES.get(addr)
        extended_registers[name] = value

    return CmdCC1120RegisterReadRes(cmd_response.cmd_id, cmd_response.error_code, cmd_response.response_length, standard_registers, extended_registers)

# Function array where each index corresponds to the command enum value + 1

parse_func_dict: dict[CmdCallbackId, Callable[..., CmdRes]] = defaultdict(lambda: parse_cmd_with_no_data)
parse_func_dict[CmdCallbackId.CMD_VERIFY_CRC] = parse_cmd_verify_crc
parse_func_dict[CmdCallbackId.CMD_RTC_SYNC] = parse_cmd_rtc_sync
parse_func_dict[CmdCallbackId.CMD_I2C_PROBE] = parse_cmd_i2c_probe
parse_func_dict[CmdCallbackId.CMD_CC1120_REGISTER_READ] = parse_cc1120_register_read


def parse_command_response(data: bytes) -> CmdRes:
    """
    A function that unpacks a command response and returns a response structure

    :param data: The bytes of data the command is packed in
    """
    cmd_response_raw, data_bytes = unpack_command_response(data)
    cmd_response = CmdRes(CmdCallbackId(cmd_response_raw.cmdId), cmd_response_raw.errCode, cmd_response_raw.dataLen)
    cmd_parsed = parse_func_dict[cmd_response.cmd_id](cmd_response, data_bytes)

    return cmd_parsed


if __name__ == "__main__":
    data_bytes = b"\x0b\x01\x04\x78\x56\x34\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    print(parse_command_response(data_bytes))
