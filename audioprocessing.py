import samplerate
import numpy as np
from numpy.typing import NDArray
from copy import deepcopy
from settings import PLAYBACK_RATE
from modformat import Sample
from typelib import ChannelState, BUFFER_SIZE

# ---- local constants

RECORD_RATE = 16574
PRIMARY_PERIOD = 214


# ---- function definitions
def transpose(sample: Sample, converter: samplerate.Resampler, target_period: int) -> Sample:
    # Create an independent copy
    result = deepcopy(sample)

    scale_factor = target_period / (PRIMARY_PERIOD * RECORD_RATE/PLAYBACK_RATE)

    # Transpose the sample and update its attributes
    result.data = converter.process(sample.data, ratio=scale_factor)

    result.length = len(result.data)
    result.loopstart = int(round(sample.loopstart * scale_factor))
    result.looplength = int(round(sample.looplength * scale_factor))
    return result


def extract_view(sample: Sample, frame_no: int) -> NDArray[np.float32]:
    # Allocate buffer
    result = silence(BUFFER_SIZE)

    # Handle loop vs non-loop regions
    if sample.has_loop:
        loop_region = sample.data[sample.loopstart:sample.loopstart + sample.looplength]
        total_len = sample.length
    else:
        loop_region = None
        total_len = len(sample.data)

    # Playback position in samples
    start_sample = frame_no * BUFFER_SIZE
    end_sample = start_sample + BUFFER_SIZE

    # No loop
    if loop_region is None:
        # If start position is past the sample length, just return silence
        if start_sample >= total_len:
            return silence(BUFFER_SIZE)

        result[:] = 0
        slice_end = min(end_sample, total_len)
        chunk_len = slice_end - start_sample  # always >= 0 now
        if chunk_len > 0:
            result[:chunk_len] = sample.data[start_sample:slice_end]
        return result

    # Loop exists
    result[:] = 0
    pos = start_sample
    out_pos = 0

    while out_pos < BUFFER_SIZE:
        if pos < sample.loopstart:
            # Before loop starts
            chunk_end = min(sample.loopstart, pos + BUFFER_SIZE - out_pos)
            chunk_len = chunk_end - pos
            result[out_pos:out_pos + chunk_len] = sample.data[pos:pos + chunk_len]
            pos += chunk_len
            out_pos += chunk_len
        else:
            # Inside loop
            loop_offset = (pos - sample.loopstart) % sample.looplength
            chunk_len = min(sample.looplength - loop_offset, BUFFER_SIZE - out_pos)
            result[out_pos:out_pos + chunk_len] = loop_region[loop_offset:loop_offset + chunk_len]
            pos += chunk_len
            out_pos += chunk_len

    return result


def apply_effect(data: NDArray[np.float32], effect_id: int) -> NDArray[np.float32]:
    # TODO: implement effect renderer
    return data


def silence(length: int) -> NDArray[np.float32]:
    return np.zeros(length, dtype=np.float32)


# ---- the note renderer

def render_frame(channel_state: ChannelState, converter: samplerate.Resampler, samplelist: list[Sample]) -> NDArray[np.float32]:

    if channel_state.current_sample is None:
        return silence(BUFFER_SIZE)

    # Extract the right sample object
    sample = samplelist[channel_state.current_sample]

    # Transpose to the current frequency
    transposed_sample = transpose(sample, converter, channel_state.current_period)

    # Get a looped or trimmed sample view which is exactly BUFFER_SIZE
    trimmed_data = extract_view(transposed_sample, channel_state.current_frame)

    # Apply the current effect
    final_sample = apply_effect(trimmed_data, channel_state.current_effect)

    # TODO: add smoothing with a window?

    return final_sample
