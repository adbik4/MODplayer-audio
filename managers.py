import time
import pyaudio
import numpy as np
from threading import Event
from numpy.typing import NDArray
from settings import PLAYBACK_RATE
from typelib import ChannelState, ClockState, TICK_RATE, BUFFER_SIZE
from audioprocessing import render_frame

# ---- thread definitions

def clock(clk_state):
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
    # Initialise the channel state
    channel_state = ChannelState()

    while not stop_flag.is_set():
        # Unpack the current pattern
        pattern = song.patternlist[song.pattern_order[clk_state.pattern_idx]]
        
        # Reset the channel_state if there was a unique note
        new_note = pattern[channel_no][clk_state.note_idx]
        if new_note.sample_idx != 0:
            # Trigger new note
            channel_state.trigger(new_note, song.samplelist[new_note.sample_idx].volume)

        # else: Continue playing the last note

        # Render new frame according to the channel state
        if channel_state.current_note != None:
            audio_data = render_frame(channel_state, song.samplelist)
        else:
            audio_data = np.zeros(BUFFER_SIZE, dtype=np.int8)   # silence

        # Pass it to the mixer
        channel_buffer[channel_no][:] = audio_data
        ready_flags[channel_no].set()
        
        # Wait for the next tick
        clk_state.tick_event.wait()

def mixer(channel_buffer, output_buffer: NDArray[np.int8], channel_flags: list[Event], clk_state: ClockState, output_flag: Event, stop_flag: Event):
    # Mix channels and pass the buffer to the player
    while not stop_flag.is_set():
        channel_flags[0].wait()
        output_buffer[:] = channel_buffer[0]
        channel_flags[0].clear()
        output_flag.set()
        clk_state.tick_event.wait()

def player(buffer: NDArray[np.int8], output_flag: Event, stop_flag: Event):
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt8, channels=1, rate=PLAYBACK_RATE, input=False, output=True)

    # Wait for the beginning of new frame and playback the buffer
    while not stop_flag.is_set():
        output_flag.wait()
        cache = buffer.tobytes()
        output_flag.clear()

        stream.write(cache)

    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()