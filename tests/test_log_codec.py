"""Protocol tests shared by firmware and ground-station consumers."""

import unittest

from interfaces.obc_gs_interface.logging import (
    FILE_ID_UNKNOWN,
    LEVEL_NAMES,
    LogCodecError,
    LogEntry,
    decode_log_entry,
    decode_log_stream,
    encode_log_entry,
    entry_to_text,
    file_id_from_path,
    file_path_from_id,
    load_file_id_mapping,
    parse_text_log_line,
)

_TIMESTAMP = 1735689600
_ERROR_BYTES = bytes([0xA8, 0x14, 0x07, 0x00, 0x7B, 0x00, 0x80, 0x85, 0x74, 0x67, 0x2D, 0x01, 0x00, 0x00])
_MESSAGE_BYTES = bytes([0xA8, 0x09, 0x02, 0x00, 0x0A, 0x00, 0x02, ord("H"), ord("i")])


class TestLogCodec(unittest.TestCase):
    """Verify the compact wire format against firmware golden vectors."""

    def assert_decoded_entry(self, expected: LogEntry, actual: LogEntry) -> None:
        self.assertEqual(actual.level, expected.level)
        self.assertEqual(actual.is_msg, expected.is_msg)
        self.assertEqual(actual.file_id, expected.file_id)
        self.assertEqual(actual.line, expected.line)
        self.assertEqual(actual.timestamp, expected.timestamp)
        self.assertEqual(actual.err_code, expected.err_code)
        self.assertEqual(actual.msg, expected.msg)
        self.assertEqual(actual.file_path, file_path_from_id(expected.file_id))

    def test_error_code_golden_vector(self) -> None:
        entry = LogEntry(level=4, is_msg=False, file_id=7, line=123, timestamp=_TIMESTAMP, err_code=301)
        self.assertEqual(encode_log_entry(entry), _ERROR_BYTES)
        decoded, consumed = decode_log_entry(_ERROR_BYTES)
        self.assertEqual(consumed, len(_ERROR_BYTES))
        self.assert_decoded_entry(entry, decoded)

    def test_message_golden_vector(self) -> None:
        entry = LogEntry(level=1, is_msg=True, file_id=2, line=10, msg="Hi")
        self.assertEqual(encode_log_entry(entry), _MESSAGE_BYTES)
        decoded, consumed = decode_log_entry(_MESSAGE_BYTES)
        self.assertEqual(consumed, len(_MESSAGE_BYTES))
        self.assert_decoded_entry(entry, decoded)

    def test_round_trip_variants(self) -> None:
        entries = [
            LogEntry(level=0, is_msg=True, file_id=0, line=1, msg="trace"),
            LogEntry(level=5, is_msg=False, file_id=FILE_ID_UNKNOWN, line=65535, timestamp=_TIMESTAMP, err_code=1001),
            LogEntry(level=2, is_msg=True, file_id=3, line=42, msg="a" * 128),
        ]
        for entry in entries:
            with self.subTest(entry=entry):
                decoded, consumed = decode_log_entry(encode_log_entry(entry))
                self.assertEqual(consumed, len(encode_log_entry(entry)))
                self.assert_decoded_entry(entry, decoded)

    def test_invalid_and_truncated_records(self) -> None:
        with self.assertRaises(LogCodecError):
            decode_log_entry(b"\x55" + _ERROR_BYTES[1:])
        with self.assertRaises(LogCodecError):
            decode_log_entry(_ERROR_BYTES[:-1])
        with self.assertRaises(LogCodecError):
            encode_log_entry(LogEntry(level=len(LEVEL_NAMES), is_msg=True, file_id=0, line=0))

    def test_stream_resynchronizes(self) -> None:
        entries = decode_log_stream(b"\x00\x01" + _ERROR_BYTES + b"\xde\xad" + _MESSAGE_BYTES + b"\xa8")
        self.assertEqual([entry.err_code for entry in entries], [301, None])
        self.assertEqual(entries[1].msg, "Hi")

    def test_mapping_and_text_round_trip(self) -> None:
        files = load_file_id_mapping()
        self.assertGreater(len(files), 0)
        for file_id, path in enumerate(files):
            self.assertEqual(file_path_from_id(file_id), path)
            self.assertEqual(file_id_from_path(path), file_id)
        line = "25-01-01_00-00-00 ERROR -> obc/app/modules/logger/logger.c:123 - 301"
        self.assertEqual(entry_to_text(decode_log_entry(encode_log_entry(parse_text_log_line(line)))[0]), line)


if __name__ == "__main__":
    unittest.main()