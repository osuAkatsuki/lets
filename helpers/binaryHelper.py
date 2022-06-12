"""That's basically packetHelper.py from pep.py, with some changes to make it work with replay files."""
import struct

from constants import dataTypes


def uleb128Encode(num):
    if num == 0:
        return bytearray(b"\x00")

    arr = bytearray()
    length = 0

    while num > 0:
        arr.append(num & 127)
        num >>= 7
        if num != 0:
            arr[length] |= 128
        length += 1
    return arr

_packtypes = {
    dataTypes.byte: struct.Struct('<B'), #lol
    dataTypes.uInt16: struct.Struct('<H'),
    dataTypes.sInt16: struct.Struct('<h'),
    dataTypes.uInt32: struct.Struct('<L'),
    dataTypes.sInt32: struct.Struct('<l'),
    dataTypes.uInt64: struct.Struct('<Q'),
    dataTypes.sInt64: struct.Struct('<q'),
    dataTypes.string: struct.Struct('<s'),
    dataTypes.ffloat: struct.Struct('<f')
}
def packData(__data, __dataType):
    data = bytearray()
    if __dataType == dataTypes.bbytes:
        data = __data
    elif __dataType == dataTypes.string:
        if len(__data) == 0:
            data += b"\x00"
        else:
            data += b"\x0B"
            encoded = __data.encode()
            data += uleb128Encode(len(encoded))
            data += encoded
            del encoded
    elif __dataType in _packtypes:
        data += _packtypes[__dataType].pack(__data)
    elif __dataType == dataTypes.rawReplay:
        data += packData(len(__data), dataTypes.uInt32)
        data += __data
    return data


def binaryWrite(structure = None):
    if not structure:
        structure = []
    packetData = bytearray()
    for i in structure:
        packetData += packData(i[0], i[1])
    return bytes(packetData)
