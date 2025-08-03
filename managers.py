import time
import pyaudio
from settings import *
from threading import Event
from dataclasses import dataclass
from audioprocessing import render
import numpy as np
from numpy.typing import NDArray

# ---- constants

TICK_RATE = 60 / (BPM * TPB)
MAX_NOTE_COUNT = 64

# ---- data types

# keeps track of where the player currently is in the track so all the channels
# are always perfectly synchronised and can resume from any moment in the song
@dataclass
class ClockState:
    tick_event : Event
    length : int = 127
    repeat_idx : int = 127

    pattern_idx : int = 0
    note_idx : int = 0
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
            
# ---- thread definitions

def clock(clk_state, stop_flag):
    while True:
        # Correct for any delay and wait
        now = time.perf_counter()
        time.sleep(max(0, clk_state.next_tick - now))
        
        # Broadcast tick event
        clk_state.tick_event.set()
        clk_state.tick_event.clear()
        
        # Update clock state
        clk_state.note_idx += 1
        clk_state.next_tick += TICK_RATE
        
        
def channel(channel_no, clk_state, song, channel_buffer, ready_flags, stop_flag):
    print("hello from channel", channel_no)
    
    while not stop_flag.is_set():
        # Unpack the current pattern
        pattern = song.patternlist[song.pattern_order[clk_state.pattern_idx]]
        
        # pass the note to the mixer
        channel_buffer[channel_no][:] = render(pattern[channel_no][clk_state.note_idx], song.samplelist)
        ready_flags[channel_no].set()
        
        # Wait for the next tick
        clk_state.tick_event.wait()

def mixer(channel_buffer, output_buffer: NDArray[np.int8], channel_flags: list[Event], output_flag: Event, stop_flag: Event):
    # Mix channels and pass the buffer to the player
    while not stop_flag.is_set():
        channel_flags[0].wait()
        print(channel_buffer[0])
        output_buffer[:] = channel_buffer[0]
        channel_flags[0].clear()
        output_flag.set()


def player(buffer: NDArray[np.int8], stream: pyaudio.Stream, output_flag: Event, stop_flag: Event):
    # Wait for the beginning of new frame and playback the buffer
    while not stop_flag.is_set():
        output_flag.wait()
        cache = buffer.tobytes()
        output_flag.clear()

        stream.write(cache)