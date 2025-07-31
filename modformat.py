from typing import Literal
from dataclasses import dataclass, fields, field, astuple
from io import BufferedReader

ByteOrder = Literal["little", "big"]

# constants:
ENDIANNESS: ByteOrder = "little"
MAX_SAMPLE_COUNT = 31
CHANNEL_COUNT = 4
MAX_ROW_COUNT = 64

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

# data types:
@dataclass
class Sample:    # holds a sample track
    name        : str   # sample name
    length      : int   # number of samples
    finetune    : int   # finetune value for dropping or lifting the pitch
    volume      : int   # volume
    repeatpoint : int   # no of byte offset from start of sample
    looplen     : int   # no of samples in loop [in bytes]
    data        : list = field(default_factory=list)  # the actual sample data, empty at first

@dataclass
class Note:     # holds a note
    idx         : int
    period      : int
    effect      : int

@dataclass
class Pattern:  # holds a pattern with 4 channels with 64 notes each
    ch1: list[Note] = field(default_factory=list)
    ch2: list[Note] = field(default_factory=list)
    ch3: list[Note] = field(default_factory=list)
    ch4: list[Note] = field(default_factory=list)
    
    def __getitem__(self, index):
        return astuple(self)[index]

    def __setitem__(self, index, value):
        field_name = fields(self)[index].name
        setattr(self, field_name, value)

# definitions:
# ---- file operations
def toString(data: bytes) -> str:
    return data.translate(None, b'\0').decode("CP437")

def toInt(data:bytes) -> int:
    return int.from_bytes(data, ENDIANNESS)

def readBlock(f: BufferedReader, offset: int, length: int) -> bytes:
    f.seek(offset)
    return f.read(length)

# ---- data processing
def extractBits(data: bytes, start: int, end: int) -> int:
    wordlen = len(data) * 8
    if (start < wordlen and start >= 0) and (end < wordlen and end >= 0) and (start <= end):
        value = int.from_bytes(data, byteorder='big')
        shifted = value >> (wordlen - end - 1)
        result = shifted & (2**(end - start + 1) - 1)
        return result
    return -1

def extractNoteInfo(data: bytes) -> tuple[int, int, int]:
    sample = (extractBits(data, 0, 3) << 4) + extractBits(data, 15, 19)
    period = extractBits(data, 4, 15)
    effect = extractBits(data, 20, 31)
    return sample, period, effect

# ---- data structure operations

# name of the song
def getSongNameInfo(f: BufferedReader) -> str:
    data = readBlock(f, SONGNAME_OFFSET, SONGNAME_LEN)
    return toString(data)

# information about the samples
def loadSamplesInfo(f: BufferedReader) -> list[Sample]:
    sample_array = []
    for i in range(MAX_SAMPLE_COUNT):
        f.seek(SAMPLEARR_OFFSET + SAMPLEBLOCK_SIZE*i)
        name = toString(f.read(SAMPLENAME_LEN))
        length = toInt(f.read(2)) * 2
        finetune = extractBits(f.read(1), 0, 3) 
        volume = toInt(f.read(1)) 
        repeatpoint = toInt(f.read(2)) * 2
        looplen = toInt(f.read(2)) * 2

        sample_array.append(Sample(name, length, finetune, volume, repeatpoint, looplen))
    return sample_array

# length of the song
def getSongLengthInfo(f: BufferedReader) -> int:
    data = readBlock(f, SONGLENGTH_OFFSET, 1)
    return toInt(data)

# noisetracker uses this byte for restart before the end of file
def getSearchUntilInfo(f: BufferedReader) -> int:
    data = readBlock(f, SEARCHUNTIL_OFFSET, 1)
    return toInt(data)

# 128 positions that tell the tracker what pattern (0-63) to play at that position (0-127)
def loadPatternPositions(f: BufferedReader) -> list[int]:
    data = readBlock(f, PATTERNPOS_OFFSET, PATTERNPOS_LEN)
    return list(data)

def getMagicInfo(f: BufferedReader) -> str:
    data = readBlock(f, MAGIC_OFFSET, 4)
    return toString(data)

def getChannel(f: BufferedReader, pattern_no:int, channel_no: int) -> list[Note]:
    notelist = []
    for note_idx in range(MAX_ROW_COUNT):
        note_addr = PATTERNS_OFFSET + pattern_no*PATTERN_SIZE + channel_no*NOTE_SIZE + note_idx*(NOTE_SIZE*4)
        note_data = readBlock(f, note_addr , 4)
        sample, period, effect = extractNoteInfo(note_data)
        notelist.append(Note(sample, period, effect))
    return notelist

def loadPatternData(f: BufferedReader) -> list[Pattern]:
    num_patterns = max(loadPatternPositions(f)) + 1
    pattern_array = []
    for pattern_idx in range(num_patterns):
        pattern = Pattern()
        for channel_idx in range(CHANNEL_COUNT):
            pattern[channel_idx] = getChannel(f, pattern_idx, channel_idx)
        pattern_array.append(pattern)
    return pattern_array

# -----------------
# testing:
file = open("examples/remonitor.mod", "rb")
if (not file.readable()):
    print("File couldn't be read")
    quit()

pattern_data = loadPatternData(file)
pattern = pattern_data[4]
for i in range(16):
    print(pattern.ch1[i])

file.close()