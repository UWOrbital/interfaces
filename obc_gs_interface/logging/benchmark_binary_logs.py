"""Benchmark compact OBC log encode/decode throughput.

Run with ``PYTHONPATH=.. python -m interfaces.obc_gs_interface.logging.benchmark_binary_logs``
from the interfaces repository.
"""

from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone

from .log_codec import LEVEL_NAMES, decode_log_stream, encode_log_entry, entry_to_text, load_file_id_mapping, parse_text_log_line

_MESSAGES = (
    "Executing log downlink command",
    "Executing OBC reset command",
    "Sending telemetry file",
    "Reached end of telemetry file",
    "Starting RTC Demo",
)
_ERROR_CODES = (2, 3, 5, 8, 15, 100, 301, 801, 1001, 1500)
_FILE_PATHS = load_file_id_mapping()


def _make_text_line(index: int, rng: random.Random) -> str:
    timestamp = datetime.fromtimestamp(1749483000 + index, tz=timezone.utc).strftime("%y-%m-%d_%H-%M-%S")
    payload = str(rng.choice(_ERROR_CODES)) if rng.random() < 0.3 else rng.choice(_MESSAGES)
    return (
        f"{timestamp} {rng.choice(LEVEL_NAMES):<5} -> {_FILE_PATHS[rng.randrange(len(_FILE_PATHS))]}:"
        f"{rng.randrange(1, 500)} - {payload}"
    )


def run_benchmark(record_count: int, seed: int = 42) -> tuple[float, float, bool]:
    """Return encode seconds, decode seconds, and round-trip correctness."""
    rng = random.Random(seed)
    lines = [_make_text_line(index, rng) for index in range(record_count)]
    start = time.perf_counter()
    encoded = b"".join(encode_log_entry(parse_text_log_line(line)) for line in lines)
    encode_seconds = time.perf_counter() - start
    start = time.perf_counter()
    decoded = decode_log_stream(encoded)
    decode_seconds = time.perf_counter() - start
    return encode_seconds, decode_seconds, len(decoded) == len(lines) and all(
        entry_to_text(entry) == line for entry, line in zip(decoded, lines)
    )


def main() -> None:
    """Run the benchmark for one or more record counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, nargs="+", default=[10_000, 100_000, 1_000_000])
    args = parser.parse_args()
    for count in args.records:
        encode_seconds, decode_seconds, valid = run_benchmark(count)
        print(
            f"{count:,} records: encode {encode_seconds:.2f}s, decode {decode_seconds:.2f}s, "
            f"round trip {'PASS' if valid else 'FAIL'}"
        )
        if not valid:
            raise SystemExit(1)


if __name__ == "__main__":
    main()