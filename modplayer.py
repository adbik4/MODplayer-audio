import pyaudio
import numpy as np
from modformat import ModFile
import time
import threading

FILEPATH = "examples/remonitor.mod"
BPM = 125
TPB = 6
TICK_RATE = 60 / (BPM * TPB)
SAMPLE_RATE = 16574
PLAYBACK_RATE = 48000

def clock(tick_event):
    next_tick = time.perf_counter() + TICK_RATE
    while True:
        now = time.perf_counter()
        time.sleep(max(0, next_tick - now))
        tick_event.set()
        tick_event.clear()
        next_tick += TICK_RATE

def main():
    # Initialize threads
    tick_event = threading.Event()
    clock_thread = threading.Thread(target=clock, args=(tick_event,), daemon=True)

    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt8, channels=1, rate=PLAYBACK_RATE, input=False, output=True)
    
    # Load song
    song = ModFile.open(FILEPATH)

    # start clock
    clock_thread.run()
    
    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main()