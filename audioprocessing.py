import numpy as np
from numpy.typing import NDArray
from settings import PLAYBACK_RATE
from modformat import Sample
from typelib import ChannelState, BUFFER_SIZE

# ---- local constants

SAMPLE_RATE = 16000
NO_LOOP = 2

# ---- function definitions


def interpolate(sample: Sample) -> Sample:
    stretch_factor = np.round(PLAYBACK_RATE / SAMPLE_RATE)

    # this is the interpolation part
    sample.data = np.repeat(sample.data, stretch_factor).tolist()
    # TODO: add more interpolation options

    # for some tracker editors
    if sample.looplength == NO_LOOP:
        sample.loopstart = 0
        sample.looplength = sample.length

    sample.length = int(sample.length * stretch_factor)
    sample.loopstart = int(sample.loopstart * stretch_factor)
    sample.looplength = int(sample.looplength * stretch_factor)
    return sample


def extract_view(sample: Sample, frame_no: int) -> NDArray[np.int8]:
    # convert to numpy array
    sample_data = np.array(sample.data, dtype=np.int8)

    # Loop point support
    if sample.looplength != sample.length:
        sample_data = sample_data[sample.loopstart:(sample.loopstart + sample.looplength)]

    # Loop until the sample_data is longer than the buffer
    fill_ratio = int(np.ceil(BUFFER_SIZE / sample.looplength))
    if fill_ratio > 1:
        sample_data = np.tile(sample_data, fill_ratio)

    extended_length = sample.looplength * fill_ratio
    beginpos = (frame_no * BUFFER_SIZE) % extended_length
    endpos = ((frame_no + 1) * BUFFER_SIZE) % extended_length

    # Cut out the buffer
    if endpos <= beginpos:
        result = np.append(sample_data[beginpos:extended_length], sample_data[0:endpos])
    else:
        result = sample_data[beginpos:endpos]
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

    return final_sample
