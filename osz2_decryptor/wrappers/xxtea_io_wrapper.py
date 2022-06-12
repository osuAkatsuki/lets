import io

from osz2_decryptor.wrappers.xxtea_wrapper import XXTeaWrapper


class XXTeaIOWrapper(io.BytesIO):
    __slots__ = ("xxtea")

    def read_uleb128(self) -> int:
        val = shift = 0

        while True:
            b = self.read(1)[0]

            val |= (b & 0b01111111) << shift
            if (b & 0b10000000) == 0:
                break

            shift += 7

        return val

    def read_string(self) -> str:
        s_len = self.read_uleb128()
        return self.read(s_len).decode()

    def set_xxtea(self, xxtea: XXTeaWrapper) -> None:
        self.xxtea = xxtea

    def read(self, size: int) -> bytes:
        buf = io.BytesIO.read(self, size)
        return bytes(self.xxtea.decrypt(buf, 0, size))
