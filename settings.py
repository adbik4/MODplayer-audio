FILEPATH = "examples/brainbla.mod"           # good example: brainblast - pattern 18, BPM 120 TPB 4
SHOW_VISUALIZER = True

CHANNELS = [0, 1, 2, 3]                      # choose from [0, 1, 2, 3]
START_PATTERN, START_NOTE = (18, 0)

BPM = 120
TPB = 4

PLAYBACK_RATE = 48000
INTERPOLATION = 'zero_order_hold'   # choose from [zero_order_hold (none), linear, sinc_fastest, sinc_medium, sinc_best]

USE_PROFILER = False
