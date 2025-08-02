import numpy as np
from settings import PLAYBACK_RATE, BPM, TPB
from modformat import Note, Sample

# ---- constants

SAMPLE_RATE = 16574
TICK_RATE = 60 / (BPM * TPB)

# ---- function definitions

def transpose(data: np.array, period: int) -> np.array:
    return data # TO IMPLEMENT

def resample(data: np.array) -> np.array:
    return data # TO IMPLEMENT

def adjust_len(data: np.array) -> np.array:
    tick_length = int(TICK_RATE * PLAYBACK_RATE)
    
    if data.size < tick_length:
        result = data[0:tick_length]
    else:
        result = data # TO IMPLEMENT
        print("sample too short!")
    return result

def apply_effect(data: np.array, effect_id: int) -> np.array:
    return data # TO IMPLEMENT

# ---- the note renderer

def render(note: Note, samplelist: list[Sample]) -> np.array:
    print("rendering", note.period, note.sample_idx, note.effect)
    
    # Get the corresponding sample
    raw_sample = np.array(samplelist[note.sample_idx]).astype(np.int8)
    
    # Transpose to the proper frequency
    transposed_sample = transpose(raw_sample, note.period)

    # Trim or loop the sample for the right timing
    timed_sample = adjust_len(hires_sample)

    # Resample to the proper sample rate
    hires_sample = resample(transposed_sample)
    
    # Apply the selected effect
    final_sample = apply_effect(timed_sample)    
    
    return final_sample