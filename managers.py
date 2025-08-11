import pyaudio
from typelib import *
from modformat import ModFile
from settings import CHANNELS, USE_PROFILER
from audioprocessing import render_frame, silence

import pyinstrument
from pyinstrument.renderers import HTMLRenderer


# ---- thread definitions

# Makes sure the channels are always perfectly synchronised
def clock(clk_state: ClockState, thread_info: ClockThreadInfo):
    # Wait until the Player is initialised
    thread_info.start_flag.wait()

    while not thread_info.stop_flag.is_set():
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
def channel(channel_no: int, clk_state: ClockState, song: ModFile, thread_info: ChannelThreadInfo):
    if USE_PROFILER:
        profiler = pyinstrument.Profiler()
        profiler.start()

    # ---- profiled code
    # Initialise the channel state
    channel_state = ChannelState()

    while not thread_info.stop_flag.is_set():
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
        print(channel_no, channel_state)  # for USE_PROFILER ONLY
        audio_data = render_frame(channel_state, song.samplelist)

        # Pass it to the mixer
        thread_info.channel_locks[channel_no].acquire()
        thread_info.channel_buffer[channel_no][:] = audio_data
        thread_info.channel_locks[channel_no].release()

        # Wait for the next tick
        clk_state.tick_event.wait()
    # ---- end of profiled code

    if USE_PROFILER:
        profiler.stop()
        profiler.output(HTMLRenderer(show_all=True, timeline=True))
        profiler.open_in_browser(timeline=False)


# Mixes channels and passes them to the player
def mixer(clk_state: ClockState, thread_info: MixerThreadInfo):
    if USE_PROFILER:
        profiler = pyinstrument.Profiler()
        profiler.start()

    # ---- profiled code
    while not thread_info.stop_flag.is_set():
        # Clear workspace
        tmp_buffer = silence(BUFFER_SIZE)

        # Wait for the buffer to be filled
        clk_state.tick_event.wait()

        # Mix
        for i in CHANNELS:
            thread_info.channel_locks[i].acquire()
            tmp_buffer += thread_info.channel_buffer[i]
            thread_info.channel_locks[i].release()

        # Average
        tmp_buffer = (tmp_buffer.astype(np.float32) / len(CHANNELS)).astype(np.int8)

        # Pass the output to the player
        thread_info.output_lock.acquire()
        thread_info.output_buffer[:] = tmp_buffer
        thread_info.output_lock.release()
    # ---- end of profiled code

    if USE_PROFILER:
        profiler.stop()
        profiler.output(HTMLRenderer(show_all=True, timeline=True))
        profiler.open_in_browser(timeline=False)


# Manages the sound settings, playback, creation and destruction of the audio stream
def player(buffer: NDArray[np.int8], thread_info: PlayerThreadInfo):
    if USE_PROFILER:
        profiler = pyinstrument.Profiler()
        profiler.start()

    # ---- profiled code
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt8,
                    channels=1,
                    rate=PLAYBACK_RATE,
                    input=False,
                    output=True)

    # signal that the player is ready
    thread_info.start_flag.set()

    # Wait for the beginning of new frame and playback the buffer
    while not thread_info.stop_flag.is_set():
        # Once the mixer stops writing, cache the buffer
        thread_info.output_lock.acquire()
        cache = buffer.tobytes()            # read
        thread_info.output_lock.release()

        # Playback
        stream.write(cache)

    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()
    # ---- end of profiled code

    if USE_PROFILER:
        profiler.stop()
        profiler.output(HTMLRenderer(show_all=True, timeline=True))
        profiler.open_in_browser(timeline=False)
