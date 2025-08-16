from settings import BPM, TPB, PLAYBACK_RATE

CHANNEL_COUNT = 4
MAX_NOTE_COUNT = 64
RECORD_RATE = 16574
PRIMARY_PERIOD = 214

TICK_RATE = 60 / (BPM * TPB)                    # duration of a frame in seconds
BUFFER_SIZE = int(TICK_RATE * PLAYBACK_RATE)    # no of samples that need to be generated each frame
VIEW_WIDTH = min(256, BUFFER_SIZE)              # no of samples to be visualised on the channel plots
