import pyaudio
from typelib import *
from modformat import ModFile
from settings import CHANNELS, USE_PROFILER
from audioprocessing import render_frame, silence

import pyinstrument
from pyinstrument.renderers import HTMLRenderer


# ---- thread definitions

# Keeps track of the current note to play and calls the render_frame function
def channel(channel_no: int, song: ModFile, thread_info: ChannelThreadInfo):
    if USE_PROFILER:
        profiler = pyinstrument.Profiler()
        profiler.start()

    # ---- profiled code
    # Initialise the channel state
    channel_state = ChannelState()

    while not thread_info.stop_flag.is_set():
        pattern_idx = thread_info.beat_ptr.pattern_idx
        note_idx = thread_info.beat_ptr.note_idx

        # Unpack the current pattern
        pattern = song.patternlist[song.pattern_order[pattern_idx]]

        # Reset the channel_state if there was a unique note
        new_note = pattern[channel_no][note_idx]
        if new_note.sample_idx == -1:
            # Continue last note
            channel_state.increment(new_note)
        else:
            # Trigger new note
            channel_state.trigger(new_note)

        # Render a new frame and pass it to the mixer
        thread_info.channel_locks[channel_no].acquire()
        audio_data = render_frame(channel_state, song.samplelist)
        thread_info.channel_buffer[channel_no][:] = audio_data
        thread_info.channel_locks[channel_no].release()

    # ---- end of profiled code

    if USE_PROFILER:
        profiler.stop()
        profiler.output(HTMLRenderer(show_all=True, timeline=True))
        profiler.open_in_browser(timeline=False)


# Mixes channels and passes them to the player
def mixer(output_queue: queue, thread_info: MixerThreadInfo):
    if USE_PROFILER:
        profiler = pyinstrument.Profiler()
        profiler.start()

    # ---- profiled code
    while not thread_info.stop_flag.is_set():
        # Clear workspace
        buffer = silence(BUFFER_SIZE)

        # Mix
        for i in CHANNELS:
            thread_info.channel_locks[i].acquire()
            buffer += thread_info.channel_buffer[i]

        # Average
        buffer = (buffer.astype(np.float32) / len(CHANNELS)).astype(np.int8)
        buffer = np.clip(buffer, -127, 127)

        # Pass the output to the player if theres place in the queue
        output_queue.put(buffer.tobytes())

        # Only then let the channels generate more samples
        for j in CHANNELS:
            thread_info.channel_locks[j].release()

        # increment the metronome
        thread_info.beat_ptr.note_idx += 1
    # ---- end of profiled code

    if USE_PROFILER:
        profiler.stop()
        profiler.output(HTMLRenderer(show_all=True, timeline=True))
        profiler.open_in_browser(timeline=False)


# Manages the sound settings, playback, creation and destruction of the audio stream
def player(output_queue: queue, thread_info: PlayerThreadInfo):
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
                    output=True,
                    frames_per_buffer=BUFFER_SIZE)

    # Wait for the beginning of new frame and playback the buffer
    while not thread_info.stop_flag.is_set():
        # Playback
        data = output_queue.get()
        stream.write(data)

    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()
    # ---- end of profiled code

    if USE_PROFILER:
        profiler.stop()
        profiler.output(HTMLRenderer(show_all=True, timeline=True))
        profiler.open_in_browser(timeline=False)
