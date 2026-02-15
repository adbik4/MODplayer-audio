FILEPATH = "examples/brainbla.mod"           # good example: brainblast - pattern 18, BPM 120 TPB 4
CHANNELS = [0, 1, 2, 3]                      # choose from [0, 1, 2, 3]
START_PATTERN, START_NOTE = (18, 0)
BPM = 120
TPB = 4

PLAYBACK_RATE = 48000
INTERPOLATION = 'linear'   # choose from [zero_order_hold (none), linear, sinc_fastest, sinc_medium, sinc_best]

SHOW_VISUALIZER = True
USE_PROFILER = False
