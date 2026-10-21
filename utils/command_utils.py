from argparse import ArgumentError, ArgumentParser
from collections.abc import Callable
from pathlib import Path
from typing import Final
from math import ceil
from tqdm import tqdm

from ax25 import Frame
from interfaces import (
    OBC_UART_BAUD_RATE,
    RS_DECODED_DATA_SIZE,
)

from interfaces.obc_gs_interface.commands.python import (
    CmdCallbackId,
    CmdMsg,
    CmdResponseErrorCode,
    unpack_telem,
    TelemetryData,
    pack_command,
)
from interfaces.obc_gs_interface.commands.python.command_factories import COMMAND_FACTORIES
from interfaces.obc_gs_interface.commands.python.command_framing import command_multi_pack
from interfaces.obc_gs_interface.commands.python.command_response_callbacks import parse_command_response
from interfaces.obc_gs_interface.commands.python.command_response_classes import CmdRes
from serial import PARITY_NONE, STOPBITS_TWO, Serial

from interfaces.utils.encode_decode import CommsPipeline

# Refer to the bl_command_callbacks.c for the number
COMMAND_DATA_SIZE: Final[int] = 208

# This is a constant value set in the python and OBC side as to what length of I Frame the OBC will be waiting to
# receive. This must be followed or the obc will not function as expected
_PADDING_REQUIRED: Final[int] = 300

LOG_PATH: Path = (Path(__file__).parent / "../logs.log").resolve()


def send_command(args: str, com_port: str, timeout: int = 0) -> CmdRes | type[CmdRes] | list[TelemetryData] | None:
    """
    A function to send a command up to the cube satellite and awaits a response

    :param args: A string that contains all the arguments the user passed in
    :param com_port: The port that the board is connected to (i.e. which port the program should use)
    :return: A decoded frame if command is valid and has a response else None
    """
    # Using generate commands, we generate a command based on the arguments passed in
    command, is_timetagged = generate_command(args)

    # We do a check to see if the arguments were properly passed in otherwise we return None
    if command is None:
        return None

    # command_multi_pack takes in a list of commands to pack thus we create that list here.
    data = [command]

    # Initialize a helper class to help with encoding and decoding the message
    comms = CommsPipeline()

    # We pad the data to an amount that the OBC expects (See handleUplinkingState function in comms_manager.c)
    # Note also that command_multi_pack returns a list of byte strings with each string stuffed with \x00 to 223 bytes
    send_bytes = comms.encode_frame(command_multi_pack(data)[0]).ljust(_PADDING_REQUIRED, b"\x00")
    # Initialize pyserial
    with Serial(
        com_port,
        baudrate=OBC_UART_BAUD_RATE,
        parity=PARITY_NONE,
        stopbits=STOPBITS_TWO,
        timeout=timeout,
    ) as ser:
        # Reset the output buffer to ensure no previous data is lurking
        ser.reset_output_buffer()

        # Send the frames to the board
        ser.write(send_bytes)
        print("Frame Sent")

        return receive_cmd_res(command.id, ser, comms, is_timetagged, com_port, timeout)


def receive_cmd_res(command_id: CmdCallbackId, ser: Serial, comms: CommsPipeline, is_timetagged: bool, com_port: str, timeout: int = 0) -> CmdRes:
    """
    A function to recieve and part response bytes into a CmdRes

    :param command: The type of command awaiting a response
    :param comms: The comms object to be used
    :param is_timetagged: Whether the command is time tagged or not 
    :param com_port: The port that the board is connected to (i.e. which port the program should use)
    :return: A decoded frame if command is valid and has a response else None
    """
 
    # Await a response (This is set to an arbitrary large amount as the logger and stats collector might
    # send through data)
    read_bytes = bytearray(b"")

    counter = 0
    flags = 0
        
    if command_id == CmdCallbackId.CMD_EXEC_OBC_RESET:
        return CmdRes(CmdCallbackId.CMD_EXEC_OBC_RESET, CmdResponseErrorCode.CMD_RESPONSE_SUCCESS, 0)

    while(flags < 2):
        byte = ser.read(1)
        if(byte == b"\x7e"):
            flags += 1

        read_bytes.extend(byte)

        counter += 1

        if counter >= 100000:
            print("Frame not found within reasonable distance")
            return None

    start_index = read_bytes.find(b"\x7e")
    end_index = read_bytes.rfind(b"\x7e")

    if end_index - start_index <= 1:
        print("Frame positioning error. Try again")
        return None

    rcv_frame_bytes = None

    try:  
        # Check if a frame is what is sent back
        if start_index != -1:
            # These are all the bytes from other tasks that are not a part of the frame
            outer_bytes = read_bytes[:start_index] + read_bytes[end_index + 1 :]

            with open(LOG_PATH, "a") as file:
                file.write(str(outer_bytes.decode("utf-8")))

            # Isolate the frame
            rcv_frame_bytes = read_bytes[start_index : end_index + 1]

            rcv_frame = comms.decode_frame(rcv_frame_bytes)
            #TODO: Probably need a custom command parser for telem, make this less hacky
            telemCorrect = True
            if command_id == CmdCallbackId.CMD_DOWNLINK_TELEM.value:
                if rcv_frame is not None:
                    telem, data = unpack_telem(rcv_frame.data[:RS_DECODED_DATA_SIZE])
                    for telemetry in telem:
                        print(telemetry.id)
                        print(telemetry.timestamp)
                        if telemetry.id == 3:
                            print(telemetry.obcTemp)
                        else:
                            print(f"Frame data is none {telemetry.obcState}")
                            return None
                    return telem
                return None

            # TODO: Handle these return frames
            if rcv_frame is not None and not is_timetagged:
                return parse_command_response(rcv_frame.data[:RS_DECODED_DATA_SIZE])
            else:
                return None
        elif is_timetagged:
            print("Command is time tagged, enable and check logs for a response")
            return None
        else:
            # TODO: Handle bootloader recieve
            return parse_command_response(read_bytes[:RS_DECODED_DATA_SIZE])
    except Exception as e:
        if rcv_frame_bytes is not None:
            print(rcv_frame_bytes)
        else:
            print("Did not find frame")
        print(f"Error: {e}")
        return None


def send_conn_request(com_port: str, timeout: int = 0) -> Frame:
    """
    Sends the initial connection request to the board

    :param com_port: The port which the function should use to send and receive on
    :return: Returns decoded acknowledge frame. Will throw an IndexError if no frame is received
    """
    # Initialize pyserial with the correct parameters
    with Serial(
        com_port,
        baudrate=OBC_UART_BAUD_RATE,
        parity=PARITY_NONE,
        stopbits=STOPBITS_TWO,
        timeout=timeout,
    ) as ser:
        # Encode using AX25, remember these frames don't have data fields so there's no need for fec or aes128
        comms = CommsPipeline()
        send_bytes = comms.encode_frame(None)

        ser.write(send_bytes.ljust(30, b"\x00"))

        # We wait for an acknowledge from the board
        rcv_frame_bytes = ser.read(10000)
        start_index = rcv_frame_bytes.find(b"\x7e")
        end_index = rcv_frame_bytes.rfind(b"\x7e")
        # TODO: Handle invalid acknowledge frame

        # Write out any logs that we received while receiving the connection
        outer_bytes = rcv_frame_bytes[:start_index] + rcv_frame_bytes[end_index + 1 :]

        with open(LOG_PATH, "a") as file:
            file.write(str(outer_bytes.decode("utf-8")))

        # Decode the frame
        rcv_frame_bytes = rcv_frame_bytes[start_index : end_index + 1]
        rcv_frame = comms.decode_frame(rcv_frame_bytes)
        return rcv_frame

def uplink_bin(args: str, com_port: str, timeout: int = 0) -> None:
    """
    A function to uplink apn app image binary, and report success / failure
    
    :param args: A string that contains all the arguments the user passed in
    :param com_port: The port that the board is connected to (i.e. which port the program should use)
    :return: None at this time
    """

    parser = parse_bin_uplink()

    arguments = parser.parse_args(args.split())

    app_path = arguments.file 
    programming_session = 0 if arguments.app_slot == "A" else 0xF4 #TODO Temporary magic num, replace with macro later

    #TODO reflect cmake options  
    app_starting_address = 0x00040000 if arguments.app_slot == "A" else 0x000A0000 # This is a placeholder, awaiting proper implementation of flags

    app_obj = Path(app_path)
    app_bin = app_obj.read_bytes()

    commands_needed = ceil(len(app_bin) / COMMAND_DATA_SIZE)

    comms = CommsPipeline()

    # Open serial port and write binary to device via UART
    with Serial(
        com_port,
        baudrate=OBC_UART_BAUD_RATE,
        parity=PARITY_NONE,
        stopbits=STOPBITS_TWO,
        timeout=1,
    ) as ser:

        command_factories: list[Callable[..., CmdMsg]] = COMMAND_FACTORIES

        # We need to first erase the app slot
        data = pack_command(command_factories[CmdCallbackId.CMD_OBC_ERASE_APP](
            programming_session
        ))

        data = data.ljust(RS_DECODED_DATA_SIZE, b"\x00")
        
        send_bytes = comms.encode_frame(data).ljust(_PADDING_REQUIRED, b"\x00")
            
        ser.reset_output_buffer()
        ser.write(send_bytes)
 
        res = receive_cmd_res(CmdCallbackId.CMD_OBC_ERASE_APP, ser, comms, False, com_port, timeout)

        if res == None or not res.error_code == CmdResponseErrorCode.CMD_RESPONSE_SUCCESS:
            print(res)
            print("Failed to erase app slot")
            return None
        else:
            print("Succesfully erased the app!")

        # We create a progress bar with the tqdm library
        progress_bar = tqdm(
            desc="Packets Written: ", total=commands_needed, dynamic_ncols=True
        )

        for i in range(commands_needed - 1):
            data = pack_command(command_factories[CmdCallbackId.CMD_OBC_WRITE_APP](
                programming_session,
                COMMAND_DATA_SIZE,
                app_starting_address + i * COMMAND_DATA_SIZE,
            ))

            data = (data + app_bin[i * COMMAND_DATA_SIZE : (i + 1) * COMMAND_DATA_SIZE]).ljust(RS_DECODED_DATA_SIZE, b"\x00")  

            send_bytes = comms.encode_frame(data).ljust(_PADDING_REQUIRED, b"\x00")

            ser.reset_output_buffer()
            ser.write(send_bytes)

            res = receive_cmd_res(CmdCallbackId.CMD_OBC_WRITE_APP, ser, comms, False, com_port, timeout)
            if res == None or not res.error_code == CmdResponseErrorCode.CMD_RESPONSE_SUCCESS:
                print(res)
                print("Failed to write app data")
                return None
            else:
                progress_bar.update(1)
                ser.reset_output_buffer()
                ser.reset_input_buffer()

        data = pack_command(command_factories[CmdCallbackId.CMD_OBC_WRITE_APP](
            programming_session,
            len(app_bin[(commands_needed - 1) * COMMAND_DATA_SIZE:]),
            app_starting_address + (commands_needed - 1) * COMMAND_DATA_SIZE,
            ))

        data = (data + app_bin[(commands_needed - 1) * COMMAND_DATA_SIZE :]).ljust(RS_DECODED_DATA_SIZE, b"\x00")

        send_bytes = comms.encode_frame(data).ljust(_PADDING_REQUIRED, b"\x00")

        ser.reset_output_buffer()
        ser.write(send_bytes)
        
        res = receive_cmd_res(CmdCallbackId.CMD_OBC_WRITE_APP, ser, comms, False, com_port, timeout)
        if res == None or not res.error_code == CmdResponseErrorCode.CMD_RESPONSE_SUCCESS:
            print(res)
            print("Failed to write app data")
            return None
        else:
            print("Successfully wrote app!")
            progress_bar.update(1)
            progress_bar.close() 


# The following docstrings do not follow convention as their docstrings are used in the CLI for the help command
def arg_parse() -> ArgumentParser:
    """
    This is a parent argument parser for all commands since all commands share the timestamp and command name in common
    """
    # We set add_help False here to avoid the child parsers from raising errors.
    # exit_on_error is also set to False to allow us to handle errors ourselves
    parser = ArgumentParser(add_help=False, exit_on_error=False)

    # Command Argument
    parser.add_argument(
        "-c",
        "--command",
        required=True,
        dest="command",
        type=str,
        choices=[x.name for x in CmdCallbackId],
        help="The command to send to the board",
    )

    # Timestamp Argument
    parser.add_argument(
        "-t",
        "--timestamp",
        required=False,
        dest="timestamp",
        type=int,
        help="The time stamp for when the command should execute",
    )

    return parser

def parse_bin_uplink() -> ArgumentParser:
    """
    This parser is used specifically for parsing binary uplink requests. 
    """
    # We set add_help False here to avoid the child parsers from raising errors.
    # exit_on_error is also set to False to allow us to handle errors ourselves
    parser = ArgumentParser(add_help=False, exit_on_error=False)
    
    # File Argument
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        dest="file",
        type=str,
        help="The file path of the app binary",
    )
    
    # App Slot Argument
    parser.add_argument(
        "-s",
        "--slot",
        required=True,
        dest="app_slot",
        type=str,
        choices=["A", "B"],
        help="The app slot to flash to",
    )

    return parser

class SilentArgumentParser(ArgumentParser):
    def error(self, message):
        raise ArgumentError(None, message="Heh")

# The following are specific command parsers with one argument
# NOTE: Update these as you add enums and always set the destinations of variables to arg1, arg2, arg3 and make the
# arguments required. Additionally, keep the same arguments when initiailizing the ArgumentParser Class
def parse_cmd_rtc_time_sync() -> ArgumentParser:
    """
    A function to parse the argument for the rtc_time_sync command
    """
    parent_parser = arg_parse()
    parser = SilentArgumentParser(parents=[parent_parser], add_help=False, exit_on_error=False)
    parser.add_argument(
        "-rtc",
        "--rtc_sync_time",
        required=True,
        dest="arg1",
        type=int,
        help="The time that the should be used to sync",
    )
    return parser


def parse_cmd_downlink_logs_next_pass() -> ArgumentParser:
    """
    A function to parse the argument for the downlink_logs_next_pass command
    """
    parent_parser = arg_parse()
    parser = SilentArgumentParser(parents=[parent_parser], add_help=False, exit_on_error=False)
    parser.add_argument(
        "-lnp",
        "--log_next_pass",
        required=True,
        dest="arg1",
        type=int,
        help="The log level for when the logs are downlinked",
    )
    return parser


# End of specific command parsers


def generate_command(args: str) -> tuple[CmdMsg | None, bool]:
    """
    A function that parsed command arguments and returns the corresponding command frame

    :param args: The arguments to parse to create the command
    :return: CmdMsg structure with the requested command if the command is valid, else none
    """
    arguments = args.split()
    command = CmdMsg()

    # These are a list of parsers for commands that require additional arguments
    # NOTE: Update this list when another command with a specific parser is required
    child_parsers = [parse_cmd_downlink_logs_next_pass, parse_cmd_rtc_time_sync]
    is_timetagged = False

    # A list of Command factories for all commands
    # NOTE: Update these when a command is added and make sure to keep them in the order that the commands are described
    # in the CmdCallbackId Enum
    commmand_factories: list[Callable[..., CmdMsg]] = COMMAND_FACTORIES

    # Loop through each of the specific parses and see if we get a valid parse on any of them
    for func in child_parsers:
        try:
            parser = func()
            command_args = parser.parse_args(arguments)
        except ArgumentError:
            continue

        # Once we do get a valid parse we try to see if the command is in the list of commands by converting it to
        # the CmdCallbackId Enum
        try:
            command_enum = CmdCallbackId[command_args.command]
        except KeyError:
            print("Invalid Command")
            return None, False

        # We check how many arguments are in the parsed object and call functions accordingly.
        # This is the reason why it's important to use the arg1, arg2, arg3 naming convention when creating
        # specific parsers
        if hasattr(command_args, "arg3"):
            # This line is just accessing a function in the commmand_factories list and passing in arguments
            # via brackets
            # This line also shows why the order is important of the functions in that list
            command = commmand_factories[command_enum.value](
                command_args.arg1, command_args.arg2, command_args.arg3, command_args.timestamp
            )
        elif hasattr(command_args, "arg2"):
            command = commmand_factories[command_enum.value](
                command_args.arg1, command_args.arg2, command_args.timestamp
            )
        elif hasattr(command_args, "arg1"):
            command = commmand_factories[command_enum.value](command_args.arg1, command_args.timestamp)

        if command_args.timestamp is not None and command_args.timestamp > 0:
            is_timetagged = True
        return command, is_timetagged

    parser = arg_parse()
    # If the command did not pass any of the specific parsers, we try the general one
    try:
        command_args = parser.parse_args(arguments)
    except ArgumentError:
        print("Invalid Commands")
        return None, False

    # Same thing as before, we try to convert to a CmdCallbackId Enum to see if the command if valid
    try:
        command_enum = CmdCallbackId[command_args.command]
    except KeyError:
        print("Invalid Command")
        return None, False

    command = commmand_factories[command_enum.value](command_args.timestamp)

    if command_args.timestamp is not None and command_args.timestamp > 0:
        is_timetagged = True
    return command, is_timetagged


def poll(
    com_port: str,
    file_path: str | Path,
    timeout: int = 0,
    stop_flag: Callable[[], bool] | None = None,
) -> None:
    """
    A function that is supposed to run in the background to keep receiving logs from the board

    :param com_port: The port that the board is connected to so it can poll
    """

    comms = CommsPipeline()

    with (
        Serial(
            com_port,
            baudrate=OBC_UART_BAUD_RATE,
            parity=PARITY_NONE,
            stopbits=STOPBITS_TWO,
            timeout=timeout,
        ) as ser,
        open(file_path, "a") as file,
    ):
        while True:
            # We use a stop flag here in order to break the loop without raising KeyboardInterrupt
            if stop_flag and stop_flag():
                break

            data = ser.read(100000)
            start_index = data.find(b"\x7e")
            end_index = data.rfind(b"\x7e")

            # Check if a frame is in what is sent back
            if start_index != -1:
                # These are all the bytes from other tasks that are not a part of the frame
                command_res = None
                outer_bytes_left = data[:start_index]
                outer_bytes_right = data[end_index + 1 :]

                # Isolate the frame
                rcv_frame_bytes = data[start_index : end_index + 1]

                rcv_frame = comms.decode_frame(rcv_frame_bytes)
                # TODO: Handle these return frames
                if rcv_frame is not None and rcv_frame.data is not None:
                    command_res = parse_command_response(bytes(rcv_frame.data[:RS_DECODED_DATA_SIZE]))

                data_string = outer_bytes_left.decode("utf-8") + str(command_res) + outer_bytes_right.decode("utf-8")
                print("Time Tagged Command Response:")
            else:
                data_string = data.decode("utf-8")

            file.write(data_string)
            file.flush()
