import base64
import time
from argparse import ArgumentError, ArgumentParser
from collections.abc import Callable
from pathlib import Path
from typing import Final

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
)
from interfaces.obc_gs_interface.commands.python.command_factories import COMMAND_FACTORIES
from interfaces.obc_gs_interface.commands.python.command_framing import command_multi_pack
from interfaces.obc_gs_interface.commands.python.command_response_callbacks import parse_command_response
from interfaces.obc_gs_interface.commands.python.command_response_classes import CmdRes
from serial import PARITY_NONE, STOPBITS_TWO, Serial

from interfaces.utils.encode_decode import CommsPipeline

# This is a constant value set in the python and OBC side as to what length of I Frame the OBC will be waiting to
# receive. This must be followed or the obc will not function as expected
_PADDING_REQUIRED: Final[int] = 300

LOG_PATH: Path = (Path(__file__).parent / "../logs.log").resolve()

# AX.25 flag byte that delimits every frame on the wire.
_FRAME_FLAG: Final[int] = 0x7E
# A downlinked image frame whose first data byte is 0 marks the end of the image (matches
# IMAGE_END_MARKER in the OBC's downlink_encoder.c).
_IMAGE_END_MARKER: Final[int] = 0
# Wait this long for the first image bytes (covers the OBC capture time), then for the link to go idle.
_IMAGE_FIRST_DATA_TIMEOUT: Final[float] = 10.0
_IMAGE_IDLE_TIMEOUT: Final[float] = 3.0
_IMAGE_MAX_SECONDS: Final[float] = 180.0


def _receive_and_print_image(ser: Serial, comms: CommsPipeline) -> None:
    """Read the downlinked image frame stream and print the whole image as base64 to the console.

    The OBC streams a captured image as ordinary AX.25 / Reed-Solomon frames (the CMD_CAPTURE_IMAGE
    path), so each frame is decoded with the same CommsPipeline used for command responses. Inside
    each decoded 223-byte block the first byte is the number of image bytes it carries (0 marks the
    end); we concatenate those bytes and print them as one base64 string, the same base64-over-UART
    idea used by the test_app_arducam example. Paste the base64 into any base64 -> JPEG converter.

    :param ser: An open serial port, positioned right after the capture command was sent.
    :param comms: The CommsPipeline used to decode each frame.
    """
    ser.timeout = 0.5
    raw = bytearray()
    start = time.monotonic()
    last_data = start
    got_data = False
    while True:
        chunk = ser.read(8192)
        now = time.monotonic()
        if chunk:
            raw += chunk
            last_data = now
            got_data = True
        elif got_data and now - last_data > _IMAGE_IDLE_TIMEOUT:
            break
        elif not got_data and now - start > _IMAGE_FIRST_DATA_TIMEOUT:
            break
        if now - start > _IMAGE_MAX_SECONDS:
            break

    # Split the byte stream into flag-delimited frames, decode each, and strip the length prefix.
    image = bytearray()
    flag_positions = [index for index, byte in enumerate(raw) if byte == _FRAME_FLAG]
    for frame_start, frame_end in zip(flag_positions, flag_positions[1:], strict=False):
        frame = bytes(raw[frame_start : frame_end + 1])
        if len(frame) <= 2:  # empty back-to-back flags / noise
            continue
        try:
            decoded = comms.decode_frame(frame)
        except (ValueError, IndexError):
            continue  # non-frame bytes (e.g. log text) between frames
        if decoded is None or decoded.data is None:
            continue
        block = bytes(decoded.data)
        length = block[0]
        if length == _IMAGE_END_MARKER:
            break
        image += block[1 : 1 + length]

    print("----- BEGIN IMAGE BASE64 -----")
    print(base64.b64encode(bytes(image)).decode("ascii"))
    print("----- END IMAGE BASE64 -----")
    print(f"({len(image)} image bytes received)")


def send_command(args: str, com_port: str, timeout: int = 0) -> CmdRes | type[CmdRes] | None:
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

        # CMD_CAPTURE_IMAGE downlinks an image as its own stream of frames (no command response), so
        # read the whole stream and print it as base64 instead of trying to parse a single response.
        if command.id == CmdCallbackId.CMD_CAPTURE_IMAGE.value:
            _receive_and_print_image(ser, comms)
            return None

        # Await a response (This is set to an arbitrary large amount as the logger and stats collector might
        # send through data)
        read_bytes = ser.read(10000)
        start_index = read_bytes.find(b"\x7e")
        end_index = read_bytes.rfind(b"\x7e")

        rcv_frame_bytes = None

        try: 
            if command.id == CmdCallbackId.CMD_EXEC_OBC_RESET.value:
                print(read_bytes)
                return CmdRes(CmdCallbackId.CMD_EXEC_OBC_RESET, CmdResponseErrorCode.CMD_RESPONSE_SUCCESS, 0)
            
            # Check if a frame is what is sent back
            if start_index != -1:
                # These are all the bytes from other tasks that are not a part of the frame
                outer_bytes = read_bytes[:start_index] + read_bytes[end_index + 1 :]

                with open(LOG_PATH, "a") as file:
                    file.write(str(outer_bytes.decode("utf-8")))

                # Isolate the frame
                rcv_frame_bytes = read_bytes[start_index : end_index + 1]

                rcv_frame = comms.decode_frame(rcv_frame_bytes)

                if command.id == CmdCallbackId.CMD_DOWNLINK_TELEM.value:
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


# The following are specific command parsers with one argument
# NOTE: Update these as you add enums and always set the destinations of variables to arg1, arg2, arg3 and make the
# arguments required. Additionally, keep the same arguments when initiailizing the ArgumentParser Class
def parse_cmd_rtc_time_sync() -> ArgumentParser:
    """
    A function to parse the argument for the rtc_time_sync command
    """
    parent_parser = arg_parse()
    parser = ArgumentParser(parents=[parent_parser], add_help=False, exit_on_error=False)
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
    parser = ArgumentParser(parents=[parent_parser], add_help=False, exit_on_error=False)
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
