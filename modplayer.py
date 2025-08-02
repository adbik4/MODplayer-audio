import pyaudio
import threading

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
    tick_event = threading.Event()
    clk_state = ClockState(length=song.length, repeat_idx=song.repeat_idx)
    threading.Thread(target=clock, args=(tick_event, clk_state), daemon=True).start()
    
    # Start the channel threads and store them
    channel_threads = []
    for i in range(1):
        t = threading.Thread(target=channel, args=(i, clk_state, song))
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