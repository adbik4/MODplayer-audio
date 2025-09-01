from __future__ import annotations
from dataclasses import dataclass, field
from numpy.typing import NDArray
from typing import BinaryIO
import numpy as np

from core.types import Sample, Note, Pattern, Effect
from core.constants import MAX_NOTE_COUNT, CHANNEL_COUNT

MAGIC_IDS = ['M.K', '4CHN', '6CHN', '8CHN', 'FLT4', 'FLT8']
NO_LOOP = 2

# addresses:
SONGNAME_OFFSET = 0x0000
SONGNAME_LEN = 20
# ----
SAMPLEARR_OFFSET = 0x0014
SAMPLENAME_LEN = 22
SAMPLEBLOCK_SIZE = 30
# ----
SONGLENGTH_OFFSET = 0x03B6
# ----
SEARCHUNTIL_OFFSET = 0x03B7
# ----
PATTERNPOS_OFFSET = 0x3B8
PATTERNPOS_LEN = 128
# ----
MAGIC_OFFSET = 0x0438
# ----
PATTERNS_OFFSET = 0x043C
PATTERN_SIZE = 1024
NOTE_SIZE = 4


@dataclass(frozen=True)     # immutable
class ModFile:  # holds all the information about a .MOD file
    name: str   # name of the song
    length: int  # length of the song in patterns
    repeat_idx: int  # pattern index where the tracker should loop
    pattern_order: list[int]  # order in which the patterns will be played
    patternlist: list[Pattern]  # list of all the patterns (4 channels each)
    samplelist: list[Sample] = field(default=list[Sample], compare=False,
                                     hash=False)  # list of all the sample recordings

    @staticmethod
    def open(filepath: str) -> ModFile:
        parser = ModParser()
        return parser.parse(filepath)

    def setSampleList(self, new_samplelist: list[Sample]):
        object.__setattr__(self, "samplelist", new_samplelist)

    def __str__(self):
        output = "---- SONG INFO ----\n"
        output += "Name: " + self.name + "\n"
        output += "Sample list:\n"
        for sample in self.samplelist:
            output += "\t" + ("[null]" if sample.name == '' else sample.name) + "\n"
        output += "Length: " + str(self.length) + "\n"
        output += "Repeat index: " + str(self.repeat_idx) + "\n"
        output += "Pattern order: " + str(self.pattern_order) + "\n"
        return output


# ---- the loader class:

# an object which can read a given .MOD file
class ModParser:
    def __init__(self):
        self.max_sample_count = 31
        self._song_length = 0
        self._pattern_count = 0

    # public method
    def parse(self, filepath: str) -> ModFile:
        f = open(filepath, "rb")
        if not f.readable():
            print("File couldn't be read")
            quit()

        # reset after the previous file probably changed it
        self._pattern_count = 0
        self._song_length = 0
        # ----

        # hardcoding because there are way too many variants out there to cover
        # for negligible memory savings
        self.max_sample_count = 31

        name = self._readSongName(f)
        length = self._readSongLength(f)
        repeat_idx = self._readRepeatIdx(f)
        pattern_order = self._loadPatternPositions(f)
        patternlist = self._loadPatternData(f)
        samplelist = self._loadSampleData(f)

        f.close()
        return ModFile(name, length, repeat_idx, pattern_order, patternlist, samplelist)

    # private methods:
    # ---- file operations
    @staticmethod
    def _toString(data: bytes) -> str:
        return data.translate(None, b'\0').decode("CP437")

    @staticmethod
    def _toUInt_LE(data: bytes) -> int:
        return int.from_bytes(data, "little", signed=False)

    @staticmethod
    def _toUInt_BE(data: bytes) -> int:
        return int.from_bytes(data, "big", signed=False)

    @staticmethod
    def _readBlock(f: BinaryIO, offset: int, length: int) -> bytes:
        f.seek(offset)
        return f.read(length)

    @staticmethod
    def _tofloat32_np(data: list[int]) -> NDArray[np.float32]:
        return np.array(data, dtype=np.int8).astype(np.float32) / 127

    # ---- data processing

    # extract a smaller sequence of bits from a bytes object. Returns an int
    def _extractBits(self, data: bytes, start: int, end: int, as_type: str = 'int'):
        wordlen = len(data) * 8
        if wordlen == 0:
            print("_extractBits() ERROR: can't accept empty data")
            quit()

        result = 0
        if (wordlen > start >= 0) and (wordlen > end >= 0) and (start <= end):
            value = self._toUInt_BE(data)
            shifted = value >> (wordlen - end - 1)
            result = shifted & (2 ** (end - start + 1) - 1)
        else:
            print(start, end)
            print("_extractBits() ERROR: end must be after the start")
            quit()

        if as_type == 'int':
            return result
        elif as_type == 'bytes':
            result_size = int(np.ceil((end-start) / 8))
            return result.to_bytes(result_size, byteorder='big')

    # unpacks raw effect data
    def _extractEffectInfo(self, data: bytes) -> Effect:
        id = self._extractBits(data, 0, 3)
        print(id)

        # E commands
        if id == 14:
            id = 16 + self._extractBits(data, 4, 7)
            arg1 = self._extractBits(data, 8, 11)
            return Effect(id, arg1)

        # single argument commands
        elif id in [1, 2, 3, 9, 11, 12, 13, 15]:
            arg1 = self._extractBits(data, 4, 11)
            return Effect(id, arg1)

        # dual argument commands
        elif id in [0, 4, 5, 6, 7, 10]:
            arg1 = self._extractBits(data, 4, 7)
            arg2 = self._extractBits(data, 8, 11)
            return Effect(id, arg1, arg2)

    # unpacks raw note data
    def _extractNoteInfo(self, data: bytes) -> tuple[int, int, Effect]:
        sample = (self._extractBits(data, 0, 3) << 4) + self._extractBits(data, 16, 19) - 1
        period = self._extractBits(data, 4, 15)
        raw_effect = self._extractBits(data, 20, 31, as_type='bytes')
        effect = self._extractEffectInfo(raw_effect)
        return sample, period, effect

    # ---- data structure operations

    # name of the song
    def _readSongName(self, f: BinaryIO) -> str:
        data = self._readBlock(f, SONGNAME_OFFSET, SONGNAME_LEN)
        return self._toString(data)

    # information about the samples
    # DON'T CALL DIRECTLY
    def _loadSampleInfo(self, f: BinaryIO) -> list[Sample]:
        sample_array = []
        for i in range(self.max_sample_count):
            f.seek(SAMPLEARR_OFFSET + SAMPLEBLOCK_SIZE * i)
            name = self._toString(f.read(SAMPLENAME_LEN))
            length = self._toUInt_BE(f.read(2)) * 2
            finetune = self._extractBits(f.read(1), 4, 7)    # lower nibble
            volume = self._toUInt_BE(f.read(1))
            loopstart = self._toUInt_BE(f.read(2)) * 2
            looplength = self._toUInt_BE(f.read(2)) * 2
            has_loop = False if (looplength == NO_LOOP) else True

            sample_array.append(Sample(name, length, finetune, volume, loopstart, looplength, has_loop))
        return sample_array

    # length of the song
    def _readSongLength(self, f: BinaryIO) -> int:
        data = self._readBlock(f, SONGLENGTH_OFFSET, 1)
        self._song_length = self._toUInt_BE(data)
        return self._song_length

    # noisetracker uses this byte for restart before the end of file
    def _readRepeatIdx(self, f: BinaryIO) -> int:
        data = self._readBlock(f, SEARCHUNTIL_OFFSET, 1)
        return self._toUInt_BE(data)

    # reads a given channel (0-3) of a given pattern
    def _readChannel(self, f: BinaryIO, pattern_no: int, channel_no: int) -> list[Note]:
        notelist = []
        for note_idx in range(MAX_NOTE_COUNT):
            base_addr = PATTERNS_OFFSET + pattern_no * PATTERN_SIZE + channel_no * NOTE_SIZE
            note_addr = base_addr + note_idx * NOTE_SIZE * CHANNEL_COUNT
            note_data = self._readBlock(f, note_addr, 4)

            sample_idx, period, effect = self._extractNoteInfo(note_data)
            notelist.append(Note(sample_idx, period, effect))
        return notelist

    # 128 positions that tell the tracker what pattern (0-63) to play at that position (0-127)
    # CALL BEFORE loadPatternData() and loadSampleData()
    def _loadPatternPositions(self, f: BinaryIO) -> list[int]:
        data = list(self._readBlock(f, PATTERNPOS_OFFSET, PATTERNPOS_LEN))[0:self._song_length]
        self._pattern_count = max(data) + 1  # save for later
        return data

    # the actual note layout and rhythm information
    # CALL loadPatternPositions() FIRST, because of pattern_count
    def _loadPatternData(self, f: BinaryIO) -> list[Pattern]:
        pattern_array = []
        for pattern_idx in range(self._pattern_count):
            pattern = Pattern()
            for channel_idx in range(CHANNEL_COUNT):
                pattern[channel_idx] = self._readChannel(f, pattern_idx, channel_idx)
            pattern_array.append(pattern)
        return pattern_array

    # the actual sample recordings
    # CALL loadPatternPositions() FIRST, because of pattern_count
    def _loadSampleData(self, f: BinaryIO) -> list[Sample]:
        sample_array = self._loadSampleInfo(f)

        offset = 0
        sample_count = len(sample_array)
        for i in range(sample_count):
            sample = sample_array[i]
            base_addr = PATTERNS_OFFSET + self._pattern_count * PATTERN_SIZE
            address = base_addr + offset
            sample.data = self._tofloat32_np(list(self._readBlock(f, address, sample.length)))
            offset += sample.length
        return sample_array

    # reads the magic 4 bytes which indicate the module version
    def _readMagic(self, f: BinaryIO) -> str:
        data = self._readBlock(f, MAGIC_OFFSET, 4)
        return self._toString(data)
