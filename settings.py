FILEPATH = "examples/remonitor.mod"
CHANNELS = [0, 1, 2, 3]                      # choose from [0, 1, 2, 3]
START_PATTERN, START_NOTE = (0, 0)

BPM = 125
TPB = 4

PLAYBACK_RATE = 48000
INTERPOLATION = 'linear'   # choose from [zero_order_hold (none), linear, sinc_fastest, sinc_medium, sinc_best]

USE_PROFILER = False