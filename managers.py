import time
import pyaudio
import numpy as np
from threading import Lock, Event
from numpy.typing import NDArray
from settings import PLAYBACK_RATE, CHANNELS
from typelib import ChannelState, ClockState, TICK_RATE, BUFFER_SIZE
from audioprocessing import render_frame, silence


# ---- thread definitions

# Makes sure the channels are always perfectly synchronised
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


# Keeps track of the current note to play and calls the render_frame function
def channel(channel_no: int, clk_state: ClockState, song, channel_buffer: NDArray[np.uint8], channel_locks: list[Lock], stop_flag: Event):
    # Initialise the channel state
    channel_state = ChannelState()

    while not stop_flag.is_set():
        # Unpack the current pattern
        pattern = song.patternlist[song.pattern_order[clk_state.pattern_idx]]

        # Reset the channel_state if there was a unique note
        new_note = pattern[channel_no][clk_state.note_idx]
        if new_note.sample_idx == -1:
            # Continue last note
            channel_state.increment(new_note)
        else:
            # Trigger new note
            channel_state.trigger(new_note)

        # Render new frame
        print(channel_no, channel_state)  # for DEBUG ONLY
        audio_data = render_frame(channel_state, song.samplelist)

        # Pass it to the mixer
        channel_locks[channel_no].acquire()
        channel_buffer[channel_no][:] = audio_data
        channel_locks[channel_no].release()

        # Wait for the next tick
        clk_state.tick_event.wait()


# Mixes channels and passes them to the player
def mixer(channel_buffer, output_buffer: NDArray[np.int8], channel_locks: list[Lock], clk_state: ClockState, output_lock: Lock, stop_flag: Event):
    while not stop_flag.is_set():
        # Clear workspace
        tmp_buffer = silence(BUFFER_SIZE)

        # Mix
        for i in CHANNELS:
            channel_locks[i].acquire()
            tmp_buffer += channel_buffer[i]
            channel_locks[i].release()

        # Pass the output to the player
        output_lock.acquire()
        output_buffer[:] = tmp_buffer
        output_lock.release()

        clk_state.tick_event.wait()


# Manages the sound settings, playback, creation and destruction of the audio stream
def player(buffer: NDArray[np.int8], output_lock: Lock, stop_flag: Event):
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt8,
                    channels=1,
                    rate=PLAYBACK_RATE,
                    input=False,
                    output=True)

    # Wait for the beginning of new frame and playback the buffer
    while not stop_flag.is_set():
        # Once the mixer stops writing, cache the buffer
        output_lock.acquire()
        cache = buffer.tobytes()            # read
        buffer[:] = silence(BUFFER_SIZE)    # clear
        output_lock.release()

        # Playback
        stream.write(cache)

    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()
