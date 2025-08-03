import numpy as np
from numpy.typing import NDArray
from settings import PLAYBACK_RATE, BPM, TPB
from modformat import Note, Sample

# ---- constants

SAMPLE_RATE = 16000
TICK_RATE = 60 / (BPM * TPB)

# ---- function definitions

def transpose(data: NDArray[np.int8], period: int) -> NDArray[np.int8]:
    return data # TO IMPLEMENT

def resample(data: NDArray[np.int8]) -> NDArray[np.int8]:
    # No interpolation for now
    repeat_count = np.round(PLAYBACK_RATE / SAMPLE_RATE)
    return np.repeat(data, repeat_count)

def adjust_len(data: NDArray[np.int8]) -> NDArray[np.int8]:
    tick_length = int(TICK_RATE * PLAYBACK_RATE)
    
    if data.size > tick_length:
        result = data[0:tick_length]
    else:
        result = np.append(data, np.zeros(tick_length - data.size, dtype=np.int8)) # TO IMPLEMENT
    return result

def apply_effect(data: NDArray[np.int8], effect_id: int) -> NDArray[np.int8]:
    return data # TO IMPLEMENT

# ---- the note renderer

def render_frame(note: Note, samplelist: list[Sample]) -> NDArray[np.int8]:
    print(note)
    
    # Get the corresponding sample
    sample = samplelist[note.sample_idx]
    raw_sample = np.array(sample.data).astype(np.int8)
    
    # Transpose to the proper frequency
    transposed_sample = transpose(raw_sample, note.period)

    # Resample to the proper sample rate
    hires_sample = resample(transposed_sample)

    # Trim or loop the sample for the right timing
    timed_sample = adjust_len(hires_sample)
    
    # Apply the selected effect
    final_sample = apply_effect(timed_sample, note.effect)
    
    return final_sample