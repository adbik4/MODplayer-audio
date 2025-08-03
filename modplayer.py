import pyaudio
import threading

import numpy as np
from settings import *
from managers import *
from modformat import ModFile

BUFFER_SIZE = int(TICK_RATE * PLAYBACK_RATE)

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
    channel_buffer = np.zeros((4, BUFFER_SIZE), dtype=np.int8)
    channel_flags = [threading.Event() for _ in range(4)] # signal to the mixer when they finish writing
    
    # Start the channel threads and store them
    channel_threads = []
    for i in range(1):
        t = threading.Thread(target=channel, args=(i, clk_state, song, channel_buffer, channel_flags, stop_flag))
        t.start()
        channel_threads.append(t)

    # Start the mixer
    output_buffer = np.zeros(BUFFER_SIZE, dtype=np.int8)
    output_flag = threading.Event() # signals to the player when it finishes writing
    mixer_thread = threading.Thread(target=mixer, args=(channel_buffer, output_buffer, channel_flags, output_flag, stop_flag))
    mixer_thread.start()
    
    # Start the player
    player_thread = threading.Thread(target=player, args=(output_buffer, stream, output_flag, stop_flag))
    player_thread.start()

    # Wait until interrupt
    try:
        while True:
            time.sleep(1)

    except:
        print("Exiting program...")
        stop_flag.set() # tell threads to exit
        
    # Wait for all the threads to finish
    mixer_thread.join()
    player_thread.join()
    for t in channel_threads:
        t.join()
    
    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    main()