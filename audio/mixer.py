from multiprocessing import shared_memory, Queue
import numpy as np

from settings import CHANNELS
from core.constants import BUFFER_SIZE, MAX_NOTE_COUNT
from audio.processing import silence
from core.types import BeatPtr


# Mixes channels and passes them to the player
def mix(shm_names: shared_memory, output_queue: Queue, beat_ptr: dict, song_length: int, repeat_idx: int):
    # Create a numpy array view on the shared memory buffer
    shm_buffer = []
    for name in shm_names:
        shm = shared_memory.SharedMemory(name=name)
        shm_buffer.append(shm)

    # Clear workspace
    mix_buffer = silence(BUFFER_SIZE)

    # Mix
    for i in CHANNELS:
        if 0 <= i <= 3:
            np_buffer = np.ndarray((BUFFER_SIZE,), dtype=np.float32, buffer=shm_buffer[i].buf)
            mix_buffer += np_buffer

    # Average
    mix_buffer /= len(CHANNELS)
    mix_buffer = np.clip(mix_buffer, -1.0, 1.0)     # for good measure

    # Pass the result to the player
    output_queue.put(mix_buffer.tobytes(), timeout=1)

    # Increment the position in the song
    increment_beat_ptr(beat_ptr, song_length, repeat_idx)


def increment_beat_ptr(beat_ptr: dict, song_length: int, repeat_idx: int):
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
        if new_pattern < song_length and new_pattern < repeat_idx:
            # Still in bounds
            beat_ptr["pattern_idx"] = new_pattern
        else:
            # Completely reset
            beat_ptr["note_idx"] = 0
            beat_ptr["pattern_idx"] = 0