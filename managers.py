import queue
import pyaudio

import numpy as np
import samplerate
from multiprocessing import shared_memory, Lock
from typelib import ChannelState, increment_beat_ptr, MixerThreadInfo, PlayerThreadInfo
from typelib import profile, BUFFER_SIZE, PLAYBACK_RATE
from modformat import ModFile
from settings import CHANNELS, INTERPOLATION
from audioprocessing import render_frame, silence

# TODO: create custom thread decorator
# TODO: add visualizaton graph renderer


# ---- thread definitions
# Keeps track of the current note to play and calls the render_frame function
@profile
def channel(channel_no: int, song: ModFile, shm_name: str, beat_ptr: dict, channel_locks: list[Lock]):
    # Initialise the channel state
    channel_state = ChannelState()

    # Create the samplerate converter
    converter = samplerate.Resampler(INTERPOLATION)

    #  Create a numpy array view on the shared memory buffer
    shm = shared_memory.SharedMemory(name=shm_name)
    buffer_np = np.ndarray((BUFFER_SIZE,), dtype=np.float32, buffer=shm.buf)

    try:
        while True:
            pattern_idx = beat_ptr["pattern_idx"]
            note_idx = beat_ptr["note_idx"]

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
            with channel_locks[channel_no]:
                audio_data = render_frame(channel_state, converter, song.samplelist)
                buffer_np[:] = audio_data
    finally:
        # cleanup
        shm.close()


# Mixes channels and passes them to the player\
@profile
def mixer(shm_names: str, output_queue: queue, beat_ptr: dict, thread_info: MixerThreadInfo):
    # Create a numpy array view on the shared memory buffer
    shm_buffer = []
    for name in shm_names:
        shm = shared_memory.SharedMemory(name=name)
        shm_buffer.append(shm)

    # ---- profiled code
    while not thread_info.stop_flag.is_set():
        # Clear workspace
        mix_buffer = silence(BUFFER_SIZE)

        # Mix
        for i in CHANNELS:
            thread_info.channel_locks[i].acquire()
            np_buffer = np.ndarray((BUFFER_SIZE,), dtype=np.float32, buffer=shm_buffer[i].buf)
            mix_buffer += np_buffer

        # Average
        mix_buffer = mix_buffer / len(CHANNELS)
        mix_buffer = np.clip(mix_buffer, -1.0, 1.0)

        # Pass the output to the player if theres place in the queue
        output_queue.put(mix_buffer.tobytes())

        # Only then let the channels generate more samples
        for j in CHANNELS:
            thread_info.channel_locks[j].release()

        increment_beat_ptr(beat_ptr)

    # cleanup
    for shm in shm_buffer:
        shm.close()


# Manages the sound settings, playback, creation and destruction of the audio stream
@profile
def player(output_queue: queue, thread_info: PlayerThreadInfo):
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=PLAYBACK_RATE,
                    input=False,
                    output=True)

    # Wait for the beginning of new frame and playback the buffer
    while not thread_info.stop_flag.is_set():
        # Playback
        data = output_queue.get()
        stream.write(data)

    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()
