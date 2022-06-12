import io


class BytesIOWrapper(io.BytesIO):
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

    def write_uleb128(self, num: int):
        """ Write `num` into an unsigned LEB128. """
        if num == 0:
            return b'\x00'

        data = bytearray()
        length = 0

        while num > 0:
            data.append(num & 0b01111111)
            num >>= 7
            if num != 0:
                data[length] |= 0b10000000
            length += 1

        self.write(data)

    def write_string(self, s: str):
        """ Write `s` into bytes (ULEB128 & string). """
        if s:
            encoded = s.encode()
            self.write_uleb128(len(encoded))
            self.write(encoded)
        else:
            self.write(b'\x00')
