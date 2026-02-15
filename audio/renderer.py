from numpy.typing import NDArray
import numpy as np
import samplerate

from audio.processing import silence, transpose, extract_view, apply_effect, apply_edge_fade
from core.types import ChannelState, Sample
from core.constants import BUFFER_SIZE


# ---- the note renderer
def render_frame(channel_state: ChannelState, converter: samplerate.Resampler, samplelist: list[Sample]) -> NDArray[np.float32]:
    if channel_state.current_sample is None:
        return silence(BUFFER_SIZE)

    sample = samplelist[channel_state.current_sample]

    dynamic_sample = transpose(sample, converter, channel_state.current_period)
    dynamic_sample = extract_view(dynamic_sample, channel_state.current_frame)
    # dynamic_sample = apply_effect(dynamic_sample, channel_state.current_effect)
    # dynamic_sample = apply_edge_fade(dynamic_sample, fade_len=128)

    return dynamic_sample
