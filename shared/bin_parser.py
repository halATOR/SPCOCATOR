"""
Shared binary parser for OMNIcheck .cal and .bin files.

Both file types use the same encoding:
- Strings: 4-byte big-endian length prefix + UTF-8 bytes
- Doubles: IEEE 754 big-endian (8 bytes)
- LabVIEW timestamps: 16 bytes (I64 seconds since 1/1/1904 + U64 fractional)
"""

import struct
from datetime import datetime, timedelta


# LabVIEW epoch: January 1, 1904 00:00:00 UTC
LABVIEW_EPOCH = datetime(1904, 1, 1)


class BinaryReader:
    """Sequential reader for OMNIcheck binary files."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    @property
    def remaining(self):
        return len(self.data) - self.pos

    def read_bytes(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ValueError(f"Cannot read {n} bytes at offset {self.pos:#x}, only {self.remaining} remaining")
        result = self.data[self.pos:self.pos + n]
        self.pos += n
        return result

    def read_u32(self) -> int:
        return struct.unpack(">I", self.read_bytes(4))[0]

    def read_i64(self) -> int:
        return struct.unpack(">q", self.read_bytes(8))[0]

    def read_u64(self) -> int:
        return struct.unpack(">Q", self.read_bytes(8))[0]

    def read_double(self) -> float:
        return struct.unpack(">d", self.read_bytes(8))[0]

    def read_float(self) -> float:
        return struct.unpack(">f", self.read_bytes(4))[0]

    def read_string(self) -> str:
        length = self.read_u32()
        raw = self.read_bytes(length)
        return raw.decode("utf-8")

    def read_labview_timestamp(self) -> datetime:
        seconds = self.read_i64()
        _fractional = self.read_u64()
        return LABVIEW_EPOCH + timedelta(seconds=seconds)

    def peek_u32(self) -> int:
        if self.pos + 4 > len(self.data):
            return 0
        return struct.unpack(">I", self.data[self.pos:self.pos + 4])[0]

    def skip(self, n: int):
        self.pos += n

    def at_end(self) -> bool:
        return self.pos >= len(self.data)
