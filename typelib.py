import time
from modformat import Note, MAX_NOTE_COUNT
from settings import BPM, TPB, PLAYBACK_RATE
from dataclasses import dataclass
from threading import Event, Lock
from numpy.typing import NDArray
import numpy as np

# global constants
TICK_RATE = 60 / (BPM * TPB)
BUFFER_SIZE = int(TICK_RATE * PLAYBACK_RATE)


# Keeps track of where the player currently is in the track so all the channels
# are always perfectly synchronised and can resume from any moment in the song

@dataclass
class ClockState:
    tick_event: Event
    length: int = 127
    repeat_idx: int = 127

    pattern_idx: int = 0
    note_idx: int = 0

    next_tick = time.perf_counter() + TICK_RATE

    # Modulo and looping logic
    def __setattr__(self, key, value):
        if key == "note_idx":
            if value < MAX_NOTE_COUNT:
                super().__setattr__("note_idx", value)
            else:
                super().__setattr__("note_idx", 0)
                self.__setattr__("pattern_idx", self.pattern_idx + 1)
        elif key == "pattern_idx":
            new_value = value if (value < self.length and value < self.repeat_idx) else 0
            super().__setattr__("pattern_idx", new_value)
        else:
            super().__setattr__(key, value)


# Keeps track of the currently playing note and which effects are playing

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


# Contains the flags, events and locks for the clock thread
@dataclass
class ClockThreadInfo:
    start_flag: Event
    stop_flag:  Event


# Contains the flags, events and locks for the channel thread
@dataclass
class ChannelThreadInfo:
    stop_flag:      Event
    channel_buffer: NDArray[np.int8]
    channel_locks:  list[Lock]


# Contains the flags, events and locks for the mixer thread
@dataclass
class MixerThreadInfo:
    channel_buffer: NDArray[np.int8]
    output_buffer:  NDArray[np.int8]
    channel_locks:  list[Lock]
    output_lock:    Lock
    stop_flag:      Event


# Contains the flags, events and locks for the player thread
@dataclass
class PlayerThreadInfo:
    output_buffer:  NDArray[np.int8]
    output_lock:    Lock
    start_flag:     Event
    stop_flag:      Event
