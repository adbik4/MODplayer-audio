from dataclasses import dataclass
from settings import *
import time

# ---- constants

TICK_RATE = 60 / (BPM * TPB)
SAMPLE_RATE = 16574
MAX_NOTE_COUNT = 64

# ---- data types

# keeps track of where the player currently is in the track so all the channels
# are always perfectly synchronised and can resume from any moment in the song
@dataclass
class ClockState:
    length : int = 127
    repeat_idx : int = 127
    
    pattern_id : int = 0
    note_id : int = 0
    
    # Modulo and looping logic
    def __setattr__(self, key, value):
        if key == "note_id":
            if value < MAX_NOTE_COUNT:
                super().__setattr__("note_id", value)
            else:
                super().__setattr__("note_id", 0)
                self.__setattr__("pattern_id", self.pattern_id + 1)
        elif key == "pattern_id":
            new_value = value if (value < self.length and value < self.repeat_idx) else 0
            super().__setattr__("pattern_id", new_value)
        else:
            super().__setattr__(key, value)
            
# ---- thread definitions

def clock(tick_event, clk_state):
    next_tick = time.perf_counter() + TICK_RATE
    while True:
        # Correct for any delay and wait
        now = time.perf_counter()
        time.sleep(max(0, next_tick - now))
        
        # Broadcast tick event
        tick_event.set()
        tick_event.clear()
        
        # Update clock state
        clk_state.note_id += 1
        next_tick += TICK_RATE
        
        
def channel(channel_no, clk_state, song):
    print("hello from channel", channel_no)
    time.sleep(5)