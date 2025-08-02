import pyaudio
import threading

import numpy as np
from settings import *
from managers import *
from modformat import ModFile

def main():
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt8, channels=1, rate=PLAYBACK_RATE, input=False, output=True)
    
    # Load song
    song = ModFile.open(FILEPATH)
    
    # Initialize and start the clock
    clk_state = ClockState(tick_event = threading.Event(),
                           length = song.length,
                           repeat_idx = song.repeat_idx)
    threading.Thread(target=clock, args=(clk_state), daemon=True).start()
    
    # Prepare the channels output buffer
    buffer_size = TICK_RATE * PLAYBACK_RATE
    channel_buffer = np.zeros((4, buffer_size), dtype=np.int8)
    ready_flags = [threading.Event() for _ in range(4)]
    
    # Start the channel threads and store them
    channel_threads = []
    for i in range(1):
        t = threading.Thread(target=channel, args=(i, clk_state, song, channel_buffer, ready_flags))
        t.start()
        channel_threads.append(t)

    # Wait for all the channel threads to finish
    for t in channel_threads:
        t.join()
    
    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main()