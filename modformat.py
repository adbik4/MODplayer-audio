from typing import Literal
from dataclasses import dataclass, fields, astuple
from io import BufferedReader

ByteOrder = Literal["little", "big"]

# constants:
ENDIANNESS: ByteOrder = "little"
MAX_SAMPLE_COUNT = 31
CHANNEL_COUNT = 4
MAX_NOTE_COUNT = 31

# addresses:
SONGNAME_OFFSET = 0x0000
SONGNAME_LEN = 20

SAMPLEARR_OFFSET = 0x0014
SAMPLENAME_LEN = 22
SAMPLEBLOCK_SIZE = 30

SONGLENGTH_OFFSET = 0x03B6

SEARCHUNTIL_OFFSET = 0x03B7

SONGPOS_OFFSET = 0x3B8
SONGPOS_LEN = 128

MAGIC_OFFSET = 0x0438

PATTERNS_OFFSET = 0x043C
NOTE_SIZE = 4

# data types:
@dataclass

class Sample: # holds a sample track
    name        : str   # sample name
    length      : int   # number of samples
    finetune    : int   # finetune value for dropping or lifting the pitch
    volume      : int   # volume
    repeatpoint : int   # no of byte offset from start of sample
    looplen     : int   # no of samples in loop [in bytes]
    data        : list[int] = [0]  # the actual sample data, empty at first

@dataclass # holds a note
class Note:
    period      : int = 0
    duration    : int = 0
    effect      : int = 0



@dataclass  # holds a pattern with 4 channels with 31 notes each
class Pattern:
    ch1: list[Note] = [Note()]
    ch2: list[Note] = [Note()]
    ch3: list[Note] = [Note()]
    ch4: list[Note] = [Note()]
    
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
        finetune = toInt(f.read(1)[0:4]) 
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
def loadSongPositions(f: BufferedReader) -> list[int]:
    data = readBlock(f, SONGPOS_OFFSET, SONGPOS_LEN)
    return list(data)

def getMagicInfo(f: BufferedReader) -> str:
    data = readBlock(f, MAGIC_OFFSET, 4)
    return toString(data)

def loadPatternData(f: BufferedReader) -> list[Pattern]:
    num_patterns = max(loadSongPositions(f))
    print("NUM PATTERNS:", num_patterns)
    
    for pattern_idx in range(num_patterns):
        p = Pattern()
        for channel_idx in range(CHANNEL_COUNT):
            notelist = []
            for note_idx in range(MAX_NOTE_COUNT):
                note_addr = PATTERNS_OFFSET + note_idx*NOTE_SIZE + channel_idx*NOTE_SIZE
                note_data = readBlock(f, note_addr , 1)
                notelist.append(Note())
            p[channel_idx] = notelist
    return None

# -----------------
# testing:
file = open("examples/70hz_refresh_chip.mod", "rb")
if (not file.readable()):
    print("File couldn't be read")
    quit()

# for sample in loadSamplesInfo(file):
#     print(sample.finetune)

file.close()