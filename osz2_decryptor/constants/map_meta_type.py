from enum import IntEnum, unique


@unique
class MapMetaType(IntEnum):
    Title = 0,
    Artist = 1,
    Creator = 2,
    Version = 3,
    Source = 4,
    Tags = 5,
    VideoDataOffset = 6,
    VideoDataLength = 7,
    VideoHash = 8,
    BeatmapSetID = 9,
    Genre = 10,
    Language = 11,
    TitleUnicode = 12,
    ArtistUnicode = 13,
    Unknown = 9999,
    Difficulty = 10000,
    PreviewTime = 10001,
    ArtistFullName = 10002,
    ArtistTwitter = 10003,
    SourceUnicode = 10004,
    ArtistUrl = 10005,
    Revision = 10006,
    PackId = 10007

    @classmethod
    def has_value(cls, value) -> bool:
        return value in cls._value2member_map_ 
