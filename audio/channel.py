from multiprocessing import shared_memory, Barrier
import numpy as np
import samplerate

from settings import INTERPOLATION
from core.constants import BUFFER_SIZE
from core.types import ChannelState
from core.utilities import profile
from core.file import ModFile
from audio.renderer import render_frame


# Keeps track of the current note to play and calls the render_frame function
@profile
def channel(channel_no: int, song: ModFile, shm_name: str, beat_ptr: dict, sync_barrier: Barrier):
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
            audio_data = render_frame(channel_state, converter, song.samplelist)
            buffer_np[:] = audio_data
            sync_barrier.wait()     # wait for all the other threads and mixing to finish

    except KeyboardInterrupt:
        print("exiting channel", channel_no)

    finally:
        # cleanup
        shm.close()
