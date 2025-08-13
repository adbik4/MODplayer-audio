import pyinstrument
import sys
import functools
from pyinstrument.renderers import HTMLRenderer
from multiprocessing import Lock, Event
from modformat import Note, MAX_NOTE_COUNT
from settings import BPM, TPB, PLAYBACK_RATE, USE_PROFILER
from dataclasses import dataclass

# global constants
TICK_RATE = 60 / (BPM * TPB)
BUFFER_SIZE = int(TICK_RATE * PLAYBACK_RATE)


# Keeps track of where the player currently is in the track so all the channels
# are always perfectly synchronised and can resume from any moment in the song

@dataclass
class BeatPtr:
    length: int = 127
    repeat_idx: int = 127

    pattern_idx: int = 0
    note_idx: int = 0

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

# Increments the shared beat pointer
def increment_beat_ptr(beat_ptr: dict):
    # Increment note
    new_note = beat_ptr["note_idx"] + 1
    if new_note < MAX_NOTE_COUNT:
        # Still in bounds
        beat_ptr["note_idx"] = new_note
    else:
        # Reset note
        beat_ptr["note_idx"] = 0

        # Increment pattern
        new_pattern = beat_ptr["pattern_idx"] + 1
        if new_pattern < beat_ptr["length"] and new_pattern < beat_ptr["repeat_idx"]:
            # Still in bounds
            beat_ptr["pattern_idx"] = new_pattern
        else:
            # Completely reset
            beat_ptr["note_idx"] = 0
            beat_ptr["pattern_idx"] = 0


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


# Contains the flags, events and locks for the channel thread
@dataclass
class ChannelProcInfo:
    channel_locks:  list[Lock]
    stop_flag:      Event


# Contains the flags, events and locks for the mixer thread
@dataclass
class MixerThreadInfo:
    channel_locks:  list[Lock]
    stop_flag:      Event


# Contains the flags, events and locks for the player thread
@dataclass
class PlayerThreadInfo:
    stop_flag:      Event


# --- decorators
def profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global profiler
        if USE_PROFILER:
            profiler = pyinstrument.Profiler()
            profiler.start()
        # ---- profiled code
        func(*args, **kwargs)
        # ---- end of profiled code
        if USE_PROFILER:
            profiler.stop()
            profiler.output(HTMLRenderer(show_all=True, timeline=True))
            profiler.open_in_browser(timeline=False)

        # exit normally
        # cleanup
        print(f"exiting {func.__name__}")
        sys.exit(0)

    return wrapper
