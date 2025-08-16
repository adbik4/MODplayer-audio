from multiprocessing import Queue
import queue as BaseQueue
import pyaudio

from settings import PLAYBACK_RATE
from core.utilities import profile


# Manages the sound settings, playback, creation and destruction of the audio stream
@profile
def player(output_queue: Queue):
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=PLAYBACK_RATE,
                    input=False,
                    output=True)

    # Wait for the beginning of new frame and playback the buffer
    try:
        while True:
            # Playback
            data = output_queue.get(timeout=0.1)
            stream.write(data)

    # Detect if the mixer stops working
    except BaseQueue.Empty:
        print("exiting player")

    finally:
        # Close the stream and terminate pyAudio
        stream.stop_stream()
        stream.close()
        p.terminate()
