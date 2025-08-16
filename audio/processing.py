from numpy.typing import NDArray
from copy import deepcopy
import numpy as np
import samplerate

from settings import PLAYBACK_RATE
from core.constants import PRIMARY_PERIOD, RECORD_RATE, BUFFER_SIZE, HALF_TONE
from core.types import Sample


# ---- generators

def hann(size: int) -> NDArray[np.float32]:
    n = np.arange(size, dtype=np.float32)
    return np.sin(np.pi/size * n)**2


def silence(length: int) -> NDArray[np.float32]:
    return np.zeros(length, dtype=np.float32)


# ---- sample operations
def finetune(val: int) -> float:
    if 8 <= val <= 15:
        val -= 16
    return HALF_TONE ** val


def transpose(sample: Sample, converter: samplerate.Resampler, target_period: int) -> Sample:
    # Create an independent copy
    result = deepcopy(sample)

    scale_factor = target_period / (PRIMARY_PERIOD * RECORD_RATE/PLAYBACK_RATE * finetune(sample.finetune))

    # Transpose the sample and update its attributes
    result.data = converter.process(sample.data, ratio=scale_factor)

    transform_ratio = len(result.data) / len(sample.data)
    result.length = int(np.round(len(sample.data) * transform_ratio))
    result.loopstart = int(np.round(sample.loopstart * transform_ratio))
    result.looplength = int(np.round(sample.looplength * transform_ratio))

    return result


def extract_view(sample: Sample, frame_no: int) -> NDArray[np.float32]:
    # Allocate buffer
    result = silence(BUFFER_SIZE)

    if sample.looplength == 0:
        return result

    # Handle loop vs non-loop regions
    if sample.has_loop:
        loop_region = sample.data[sample.loopstart:sample.loopstart + sample.looplength]
        total_len = len(sample.data)
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


def apply_edge_fade(samples, fade_len=128):
    fade_in = np.sin(np.linspace(0, np.pi / 2, fade_len))**2
    fade_out = fade_in[::-1]
    samples[:fade_len] *= fade_in
    samples[-fade_len:] *= fade_out
    return samples
