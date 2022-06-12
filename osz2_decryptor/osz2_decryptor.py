import hashlib
from typing import Union

from osz2_decryptor.constants.map_meta_type import MapMetaType
from osz2_decryptor.objects.file_info import FileInfo
from osz2_decryptor.wrappers.bytes_io_wrapper import BytesIOWrapper
from osz2_decryptor.wrappers.osz2_io_wrapper import Osz2IOWrapper
from osz2_decryptor.wrappers.xtea_wrapper import XTeaWrapper
from osz2_decryptor.wrappers.xxtea_io_wrapper import XXTeaIOWrapper
from osz2_decryptor.wrappers.xxtea_wrapper import XXTeaWrapper


class Osz2Package:
    __slots__ = ("file", "file_path", "metadata", "file_infos", "files", 
        "meta_hash", "info_hash", "body_hash", "file_names", 
        "file_ids", "key", "metadata_only")

    def __init__(self, file_path: str, metadata_only: bool = False) -> None:
        with open(file_path, 'rb') as f:
            self.file = f.read()

        self.file_path: str = file_path
        self.metadata_only: bool = metadata_only
        self.metadata: dict[MapMetaType, str] = {}
        self.file_infos: dict[str, FileInfo] = {}
        self.files: dict[str, bytes] = {}
        self.file_names: dict[str, int] = {}
        self.file_ids: dict[int, str] = {}
      
    def read(self) -> bool:
        """Returns `True` if everything was parsed correctly and `False` if something happened"""
        reader = BytesIOWrapper(self.file)

        identifier = reader.read(3)

        if identifier != b'\xecHO':
            # log?
            return False

        writer = BytesIOWrapper()
        
        reader.read(1) # version (unused, always zero)

        reader.read(16) # iv (unused) 

        self.meta_hash = reader.read(16)
        self.info_hash = reader.read(16)
        self.body_hash = reader.read(16)

        meta_count_bytes = reader.read(4)

        writer.write(meta_count_bytes)

        meta_count = int.from_bytes(meta_count_bytes, byteorder='little')

        for i in range(0, meta_count):
            meta_type_bytes = reader.read(2)
            meta_value = reader.read_string()

            meta_type = MapMetaType(int.from_bytes(meta_type_bytes, byteorder='little'))

            if (MapMetaType.has_value(meta_type)):
                self.metadata[meta_type] = meta_value

            writer.write(meta_type_bytes)
            writer.write_string(meta_value)

        with writer.getbuffer() as buffer:
            meta_hash = self._compute_osz_hash(buffer, meta_count * 3, 0xa7)

        writer.close()

        if meta_hash != self.meta_hash:
            # log?
            return False

        maps_count = int.from_bytes(reader.read(4), byteorder='little')

        for i in range(0, maps_count):
            file_name = reader.read_string()
            beatmap_id = int.from_bytes(reader.read(4), byteorder='little')

            self.file_names[file_name] = beatmap_id
            self.file_ids[beatmap_id] = file_name

        seed = f'{self.metadata[MapMetaType.Creator]}yhxyfjo5{self.metadata[MapMetaType.BeatmapSetID]}'
        self.key = hashlib.md5(seed.encode()).digest()

        if not self.metadata_only:
            return self._read_files(reader)
        else:
            return True

    def _read_files(self, reader: BytesIOWrapper) -> bool:
        xtea = XTeaWrapper(self.key)
        xxtea = XXTeaWrapper(self.key)

        # TODO: do something with decrypted plain
        decrypted_plain = xtea.decrypt(reader.read(64), 0, 64)
        length = int.from_bytes(reader.read(4), byteorder='little')

        for i in range(0, 16, 2):
            length -= self.info_hash[i] | (self.info_hash[i + 1] << 17)

        # .osu files
        file_info = reader.read(length)

        file_offset = reader.tell()

        if len(file_info) % 8 != 0:
            file_info=file_info.zfill(len(file_info) & ~0b0111)

        file_reader = XXTeaIOWrapper(file_info)
        file_reader.set_xxtea(xxtea)

        info_count = int.from_bytes(file_reader.read(4), byteorder='little')

        info_hash = self._compute_osz_hash(bytearray(file_info), info_count * 4, 0xd1)

        if (info_hash != self.info_hash):
            # log?
            return False

        current_offset = int.from_bytes(file_reader.read(4), byteorder='little')

        for i in range(info_count):
            file_name = file_reader.read_string()
            file_hash = file_reader.read(16)

            file_created_date = int.from_bytes(file_reader.read(8), byteorder='little')
            file_modified_date = int.from_bytes(file_reader.read(8), byteorder='little')

            next_offset = 0

            if (i + 1 < info_count):
                next_offset = int.from_bytes(file_reader.read(4), byteorder='little')
            else:
                next_offset = len(reader.getvalue()) - file_offset
            
            file_length = next_offset - current_offset

            self.file_infos[file_name] = FileInfo(file_name, current_offset, file_length, file_hash, file_created_date, file_modified_date)

            current_offset = next_offset

        osz2_reader = Osz2IOWrapper(self.file_path, self.key)

        for file_name, file_info in self.file_infos.items():
            self.files[file_name] = osz2_reader.read_osu(file_offset + file_info.offset, file_info.size)

        reader.close()
        file_reader.close()
            
        return True

    @staticmethod
    def _compute_osz_hash(buffer: Union[memoryview, bytearray], pos: int, swap: int) -> bytes:
        buffer[pos] ^= swap
        hash = bytearray(hashlib.md5(buffer).digest())
        buffer[pos] ^= swap

        for i in range(8):
            tmp = hash[i]
            hash[i] = hash[i + 8]
            hash[i + 8] = tmp

        hash[5] ^= 0x2d

        return bytes(hash)
