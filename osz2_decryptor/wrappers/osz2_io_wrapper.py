import clr
from Osz2Cryptors import Osz2Stream

clr.AddReference("Osz2Cryptors")


class Osz2IOWrapper:
    __slots__ = ("key", "file")

    def __init__(self, file: str, key: bytes) -> None:
        self.key = key
        self.file = file

    def read_osu(self, offset: int, size: int) -> bytes:
        return bytes(Osz2Stream.Read(self.file, offset, self.key, size))
