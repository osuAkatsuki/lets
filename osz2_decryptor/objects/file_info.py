class FileInfo:
    __slots__ = ("name", "offset", "size", "hash", "created_date", "modified_date")

    def __init__(self, name: str, offset: int, size: int, hash: bytes, created_date: int, modified_date: int) -> None:
        self.name = name
        self.offset = offset
        self.size = size
        self.hash = hash
        self.created_date = created_date
        self.modified_date = modified_date
