import numpy as np
from numpy.typing import NDArray
from settings import PLAYBACK_RATE
from modformat import Sample
from typelib import ChannelState, BUFFER_SIZE

# ---- local constants

SAMPLE_RATE = 16000

# ---- function definitions


def interpolate(sample: Sample) -> Sample:
    stretch_factor = np.round(PLAYBACK_RATE / SAMPLE_RATE)

    # this is the interpolation part
    sample.data = np.repeat(sample.data, stretch_factor).tolist()
    # TODO: add more interpolation options

    sample.length = int(sample.length * stretch_factor)
    sample.loopstart = int(sample.loopstart * stretch_factor)
    sample.looplength = int(sample.looplength * stretch_factor)
    return sample


def extract_view(sample: Sample, frame_no: int) -> NDArray[np.int8]:
    # Convert to Numpy array
    data = np.array(sample.data, dtype=np.int8)

    # Handle loop vs non-loop regions
    if sample.has_loop:
        loop_region = data[sample.loopstart:sample.loopstart + sample.looplength]
        total_len = sample.length
    else:
        loop_region = None
        total_len = len(data)

    # Playback position in samples
    start_sample = frame_no * BUFFER_SIZE
    end_sample = start_sample + BUFFER_SIZE

    # No loop
    if loop_region is None:
        # If start position is past the sample length, just return silence
        if start_sample >= total_len:
            return silence(BUFFER_SIZE)

        result = silence(BUFFER_SIZE)
        slice_end = min(end_sample, total_len)
        chunk_len = slice_end - start_sample  # always >= 0 now
        if chunk_len > 0:
            result[:chunk_len] = data[start_sample:slice_end]
        return result

    # Loop exists
    result = silence(BUFFER_SIZE)
    pos = start_sample
    out_pos = 0

    while out_pos < BUFFER_SIZE:
        if pos < sample.loopstart:
            # Before loop starts
            chunk_end = min(sample.loopstart, pos + BUFFER_SIZE - out_pos)
            chunk_len = chunk_end - pos
            result[out_pos:out_pos + chunk_len] = data[pos:pos + chunk_len]
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


def transpose(data: NDArray[np.int8], period: int) -> NDArray[np.int8]:
    # TODO: implement pitch renderer
    return data


def apply_effect(data: NDArray[np.int8], effect_id: int) -> NDArray[np.int8]:
    # TODO: implement effect renderer
    return data


def silence(length: int) -> NDArray[np.int8]:
    return np.zeros(length, dtype=np.int8)


# ---- the note renderer

def render_frame(channel_state: ChannelState, samplelist: list[Sample]) -> NDArray[np.int8]:

    if channel_state.current_sample is None:
        print("SILENCE")
        return silence(BUFFER_SIZE)

    # Extract the right sample object
    sample = samplelist[channel_state.current_sample]

    # Get a looped or trimmed sample view which is exactly BUFFER_SIZE
    trimmed_data = extract_view(sample, channel_state.current_frame)

    # Transpose to the current frequency
    transposed_sample = transpose(trimmed_data, channel_state.current_period)

    # Apply the current effect
    final_sample = apply_effect(transposed_sample, channel_state.current_effect)

    # TODO: add smoothing with a window

    return final_sample
