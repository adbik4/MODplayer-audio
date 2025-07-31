from dataclasses import dataclass, fields, field, astuple
from io import BufferedReader

# constants:
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
# ---- helper data types:

@dataclass
class Sample:    # holds a sample track
    name        : str   # sample name
    length      : int   # number of samples
    finetune    : int   # finetune value for dropping or lifting the pitch
    volume      : int   # volume
    repeatpoint : int   # no of byte offset from start of sample
    looplen     : int   # no of samples in loop [in bytes]
    data        : list[int] = field(default_factory=list)  # the actual sample data, empty at first

@dataclass
class Note:     # holds a note
    idx         : int
    period      : int
    effect      : int

@dataclass
class Pattern:  # holds a pattern with 4 channels with 64 notes each
    ch1: list[Note] = field(default_factory=list)   # channel 1
    ch2: list[Note] = field(default_factory=list)   # channel 2
    ch3: list[Note] = field(default_factory=list)   # channel 3
    ch4: list[Note] = field(default_factory=list)   # channel 4
    
    # indexing support
    def __getitem__(self, index):
        return astuple(self)[index]

    # indexing support
    def __setitem__(self, index, value):
        field_name = fields(self)[index].name
        setattr(self, field_name, value)

# ---- the song type:

@dataclass (frozen=True)
class Song :    # holds all of the information from a .MOD file
    name            : str   # name of the song
    samplelist      : list[Sample]  # list of all the sample recordings
    length          : int   # length of the song in patterns
    repeat_idx    : int   # pattern index where the tracker should loop
    pattern_order   : list[int] # order in which the patterns will be played
    patternlist     : list[Pattern] # list of all the patterns (4 channels each)
    
    def __str__(self):
        output = "---- SONG INFO ----\n"
        output += "Name: "+ self.name + "\n"
        output += "Sample list:\n"
        for sample in self.samplelist:
            output+= "\t" + ("[null]" if sample.name == '' else sample.name) + "\n"
        output += "Length: "+ str(self.length) + "\n"
        output += "Repeat index: "+ str(self.repeat_idx) + "\n"
        output += "Pattern order: "+ str(self.pattern_order) + "\n"
        return output
    
# ---- the loader class:    

# an object which can read a given .MOD file
class Loader:
    # public method
    def loadSong(self, filepath: str):
        f = open(filepath, "rb")
        if (not f.readable()):
            print("File couldn't be read")
            quit()
            
        # reset after the previous file probably changed it
        self._pattern_count = 0    
        self._song_length = 0
        # ----
        
        magic = self.__readMagic(f)
        if (magic == "\0\0\0\0"):
            self.max_sample_count = 15
        elif (magic == "M.K."):
            self.max_sample_count = 31
        elif (magic == "FLT4" or magic == "FLT8"):
            self.max_sample_count = 64
        else:
            self.max_sample_count = 128
            
        name = self.__readSongName(f)
        samplelist = self.__loadSampleData(f)
        length = self.__readSongLength(f)
        repeat_idx = self.__readSearchUntil(f)
        pattern_order = self.__loadPatternPositions(f)
        patternlist = self.__loadPatternData(f)

        f.close()
        return Song(name, samplelist, length, repeat_idx, pattern_order, patternlist)
        
    # private methods:
    # ---- file operations
    def __toString(self, data: bytes) -> str:
        return data.translate(None, b'\0').decode("CP437")

    def __toInt_LE(self, data:bytes) -> int:
        return int.from_bytes(data, "little")

    def __toInt_BE(self, data:bytes) -> int:
        return int.from_bytes(data, "big")

    def __readBlock(self, f: BufferedReader, offset: int, length: int) -> bytes:
        f.seek(offset)
        return f.read(length)

    # ---- data processing

    # extract a smaller sequence of bits from a bytes object. Returns an int
    def __extractBits(self, data: bytes, start: int, end: int) -> int:
        wordlen = len(data) * 8
        if (start < wordlen and start >= 0) and (end < wordlen and end >= 0) and (start <= end):
            value = self.__toInt_BE(data)
            shifted = value >> (wordlen - end - 1)
            result = shifted & (2**(end - start + 1) - 1)
            return result
        return -1

    # unpacks raw note data
    def __extractNoteInfo(self, data: bytes) -> tuple[int, int, int]:
        sample = (self.__extractBits(data, 0, 3) << 4) + self.__extractBits(data, 15, 19)
        period = self.__extractBits(data, 4, 15)
        effect = self.__extractBits(data, 20, 31)
        return sample, period, effect

    # ---- data structure operations

    # name of the song
    def __readSongName(self, f: BufferedReader) -> str:
        data = self.__readBlock(f, SONGNAME_OFFSET, SONGNAME_LEN)
        return self.__toString(data)

    # information about the samples
    # DON'T CALL DIRECTLY
    def __loadSampleInfo(self, f: BufferedReader) -> list[Sample]:
        sample_array = []
        for i in range(self.max_sample_count):
            f.seek(SAMPLEARR_OFFSET + SAMPLEBLOCK_SIZE*i)
            name = self.__toString(f.read(SAMPLENAME_LEN))
            length = self.__toInt_BE(f.read(2)) * 2
            finetune = self.__extractBits(f.read(1), 0, 3) 
            volume = self.__toInt_LE(f.read(1)) 
            repeatpoint = self.__toInt_LE(f.read(2)) * 2
            looplen = self.__toInt_LE(f.read(2)) * 2

            sample_array.append(Sample(name, length, finetune, volume, repeatpoint, looplen))
        return sample_array
    
    # the actual sample recordings
    def __loadSampleData(self, f: BufferedReader) -> list[Sample]:
        sample_array = self.__loadSampleInfo(f)
        
        offset = 0
        sample_count = len(sample_array)
        for i in range(sample_count):
            sample = sample_array[i]
            base_addr = PATTERNS_OFFSET + self._pattern_count*PATTERN_SIZE
            address = base_addr + offset
            sample.data = list(self.__readBlock(f, address, sample.length))
            offset += sample.length
        return sample_array

    # length of the song
    def __readSongLength(self, f: BufferedReader) -> int:
        data = self.__readBlock(f, SONGLENGTH_OFFSET, 1)
        self._song_length = self.__toInt_LE(data)
        return self._song_length

    # noisetracker uses this byte for restart before the end of file
    def __readSearchUntil(self, f: BufferedReader) -> int:
        data = self.__readBlock(f, SEARCHUNTIL_OFFSET, 1)
        return self.__toInt_LE(data)

    # 128 positions that tell the tracker what pattern (0-63) to play at that position (0-127)
    def __loadPatternPositions(self, f: BufferedReader) -> list[int]:
        data = list(self.__readBlock(f, PATTERNPOS_OFFSET, PATTERNPOS_LEN))[0:self._song_length]
        self.pattern_count = max(data) + 1    # save for later
        return data
    
    # the actual note layout and rythm information
    # CALL loadPatternPositions() FIRST, because of pattern_count
    def __loadPatternData(self, f: BufferedReader) -> list[Pattern]:
        pattern_array = []
        for pattern_idx in range(self.pattern_count):
            pattern = Pattern()
            for channel_idx in range(CHANNEL_COUNT):
                pattern[channel_idx] = self.__readChannel(f, pattern_idx, channel_idx)
            pattern_array.append(pattern)
        return pattern_array

    # reads the magic 4 bytes which indicate the module version
    def __readMagic(self, f: BufferedReader) -> str:
        data = self.__readBlock(f, MAGIC_OFFSET, 4)
        return self.__toString(data)

    # reads a given channel (0-3) of a given pattern
    def __readChannel(self, f: BufferedReader, pattern_no:int, channel_no: int) -> list[Note]:
        notelist = []
        for note_idx in range(MAX_ROW_COUNT):
            base_addr = PATTERNS_OFFSET + pattern_no*PATTERN_SIZE + channel_no*NOTE_SIZE
            note_addr = base_addr + note_idx*(NOTE_SIZE*4)
            note_data = self.__readBlock(f, note_addr , 4)
            
            sample, period, effect = self.__extractNoteInfo(note_data)
            notelist.append(Note(sample, period, effect))
            
        return notelist