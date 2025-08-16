from __future__ import annotations

from dataclasses import dataclass, field, fields
from numpy.typing import NDArray
import numpy as np


@dataclass
class Sample:  # holds a sample track
    name: str  # sample name
    length: int  # number of samples
    finetune: int  # finetune value for dropping or lifting the pitch
    volume: int  # volume
    loopstart: int  # no of byte offset from start of sample
    looplength: int  # no of samples in loop
    has_loop: bool
    data: NDArray[np.float32] = field(default_factory=lambda: np.array([], dtype=np.float32))  # the actual sample data


@dataclass
class Note:  # holds a note
    sample_idx: int
    period: int
    effect: int


@dataclass
class Pattern:  # holds a pattern with 4 channels with 64 notes each
    ch1: list[Note] = field(default_factory=list)  # channel 1
    ch2: list[Note] = field(default_factory=list)  # channel 2
    ch3: list[Note] = field(default_factory=list)  # channel 3
    ch4: list[Note] = field(default_factory=list)  # channel 4

    # indexing support
    def __getitem__(self, index):
        field_names = [f.name for f in fields(self)]
        return getattr(self, field_names[index])

    # indexing support
    def __setitem__(self, index, value):
        field_name = fields(self)[index].name
        setattr(self, field_name, value)


# Keeps track of where the player currently is in the track so all the channels
# are always perfectly synchronised and can resume from any moment in the song
@dataclass
class BeatPtr:
    pattern_idx: int = 0
    note_idx: int = 0


# Keeps track of the progress in note rendering
@dataclass
class ChannelState:
    current_frame: int = 0

    current_sample: int = None
    current_period: int = 0
    current_effect: int = 0

    def trigger(self, new_note: Note):
        self.current_frame = 0
        self.current_sample = new_note.sample_idx
        self.current_period = new_note.period
        self.current_effect = new_note.effect

    def increment(self, continued_note: Note):
        self.current_frame += 1
        self.current_effect = continued_note.effect
