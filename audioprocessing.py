import numpy as np
from numpy.typing import NDArray
from settings import PLAYBACK_RATE, BPM, TPB
from modformat import Note, Sample
from managers import ChannelState

# ---- constants

SAMPLE_RATE = 16000
TICK_RATE = 60 / (BPM * TPB)
BUFFER_SIZE = int(TICK_RATE * PLAYBACK_RATE)

# ---- function definitions

def transpose(data: NDArray[np.int8], period: int) -> NDArray[np.int8]:
    return data # TO IMPLEMENT

def interpolate(sample: Sample) -> Sample:
    # No interpolation for now
    repeat_count = np.round(PLAYBACK_RATE / SAMPLE_RATE)
    sample.data = np.repeat(sample.data, repeat_count) # this is the interpolation part
    sample.length = sample.data.size
    sample.looplen =
    sample.repeatpoint = 
    return 

def extract_view(sample: Sample) -> NDArray[np.int8]:
    # if the sample should loop, loop it to the proper len
    # else, append 0s

    tick_length = int(TICK_RATE * PLAYBACK_RATE)
    
    if data.size > tick_length:
        result = data[0:tick_length]
    else:
        result = np.append(data, np.zeros(tick_length - data.size, dtype=np.int8)) # TO IMPLEMENT
    return result

def apply_effect(data: NDArray[np.int8], effect_id: int) -> NDArray[np.int8]:
    return data # TO IMPLEMENT

# ---- the note renderer

def render_frame(channel_state: ChannelState, samplelist: list[Sample]) -> NDArray[np.int8]:
    print(channel_state) # for DEBUG ONLY

    # extract the sample data
    sample = samplelist[channel_state.current_note.sample_idx] 

    # Get a looped or trimmed sample view which is exactly BUFFER_SIZE
    clean_data = extract_view(sample)
    

    # Get the right sample range for the output buffer
    start_point = (channel_state.current_frame * BUFFER_SIZE) % sample.length
    end_point = ((channel_state.current_frame + 1) * BUFFER_SIZE) % sample.length

    if start_point > sample.length:
        start_point = 0     # or later, the loop start pos
    if end_point > sample.length:
        end_point = sample.length

    raw_sample = np.array(sample.data[start_point:end_point]).astype(np.int8)

    # Trim or loop the sample for the right timing
    timed_sample = adjust_len(hires_sample)
    
    # Transpose to the proper frequency
    transposed_sample = transpose(raw_sample, note.period)

    
    
    # Apply the selected effect
    final_sample = apply_effect(timed_sample, note.effect)
    
    return final_sample