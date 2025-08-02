import pyaudio
import threading

import numpy as np
from settings import *
from managers import *
from modformat import ModFile

def main():
    # For graceful shutdown
    stop_flag = threading.Event()
    
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt8, channels=1, rate=PLAYBACK_RATE, input=False, output=True)
    
    # Load song
    song = ModFile.open(FILEPATH)
    
    # Initialize and start the clock
    clk_state = ClockState(tick_event = threading.Event(),
                           length = song.length,
                           repeat_idx = song.repeat_idx)
    clock_thread = threading.Thread(target=clock, args=(clk_state, stop_flag,), daemon=True)
    clock_thread.start()
    
    # Prepare the channels output buffer
    buffer_size = int(TICK_RATE * PLAYBACK_RATE)
    channel_buffer = np.zeros((4, buffer_size), dtype=np.int8)
    ready_flags = [threading.Event() for _ in range(4)]
    
    # Start the channel threads and store them
    channel_threads = []
    for i in range(4):
        t = threading.Thread(target=channel, args=(i, clk_state, song, channel_buffer, ready_flags, stop_flag))
        t.start()
        channel_threads.append(t)

    # Program exit logic
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting program...")
        stop_flag.set() # tell threads to exit
        
    # Wait for all the threads to finish
    clock_thread.join()
    for t in channel_threads:
        t.join()
    
    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main()