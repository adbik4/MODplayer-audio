from __future__ import annotations
from dataclasses import dataclass, field, fields

from audio.effects import *


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
    effect: Effect


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


# Stores information about effects
class Effect:
    _effect_lookup = [
        arpeggio, slide_up, slide_down, portamento,
        vibrato, portamento_w_vol_slide, vibrato_w_vol_slide, tremolo,
        None, set_offset, vol_slide, pos_jump,
        set_vol, pattern_break, None, set_speed,
        set_filter, fineslide_up, fineslide_down, glissando,
        set_vibrato, set_loop, jump_to_loop, set_tremolo,
        None, retrig_note, fine_vol_slide_up, fine_vol_slide_down,
        note_cut, note_delay, pattern_delay, invert_loop
    ]

    def __init__(self, id: int = 0, arg1: int = None, arg2: int = None):
        self._id = id
        self._arg1 = arg1
        self._arg2 = arg2

    def __call__(self, data: NDArray[np.float32]) -> NDArray[np.float32]:
        if self._arg2 is not None:
            return self._effect_lookup[self._id](self._arg1, self._arg2, data)
        else:
            return self._effect_lookup[self._id](self._arg1, data)


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
    current_effect: Effect = Effect()

    def trigger(self, new_note: Note):
        self.current_frame = 0
        self.current_sample = new_note.sample_idx
        self.current_period = new_note.period
        self.current_effect = new_note.effect

    def increment(self, continued_note: Note):
        self.current_frame += 1
        self.current_effect = continued_note.effect
